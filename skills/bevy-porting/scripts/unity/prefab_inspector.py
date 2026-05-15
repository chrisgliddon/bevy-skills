#!/usr/bin/env python3
"""
Inspect a Unity .prefab file and emit a JSON hierarchy + component map.

Backs: references/unity-prefab-inspector.md

Usage:
    python3 prefab_inspector.py Foo.prefab [--out prefab.json] [--depth N]

Output format:
    {
      "prefab": "Foo.prefab",
      "root_file_id": "...",
      "hierarchy": [ { "file_id": "...", "name": "...", "children": [...] } ],
      "components_by_file_id": { "file_id": [ {component data...} ] }
    }

    --depth N limits how many levels deep the hierarchy tree is rendered
    (unlimited by default). Components and root_file_id are always complete.

Unity YAML note: .prefab files use the same !u!<classID> &<fileID> tag syntax
as .unity scenes. This script uses a regex pre-pass to strip those tags, then
uses stdlib 're' to extract fields — no pyyaml required.

Exit codes: 0 = success, 1 = file not found / parse error.
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Unity class-ID → component name (extend as needed)
CLASS_ID_NAMES = {
    "1": "GameObject",
    "2": "EditorExtension",  # base class — NOT Camera; Camera is class ID 20
    "4": "Transform",
    "20": "Camera",
    "23": "MeshRenderer",
    "25": "Renderer",
    "33": "MeshFilter",
    "54": "Rigidbody",
    "65": "BoxCollider",
    "114": "MonoBehaviour",
    "135": "SphereCollider",
    "136": "CapsuleCollider",
    "212": "SpriteRenderer",
    "222": "Canvas",
    "224": "RectTransform",
}

# ---------------------------------------------------------------------------
# Shared Unity YAML helpers (duplicated from scene_inventory for single-file rule)
# ---------------------------------------------------------------------------

def _strip_unity_tags(text: str) -> str:
    return re.sub(
        r"^--- !u!(\d+) &(\d+)",
        r"--- # classID: \1 fileID: \2",
        text,
        flags=re.MULTILINE,
    )


def _parse_unity_documents(text: str):
    stripped = _strip_unity_tags(text)
    doc_pattern = re.compile(
        r"^--- # classID: (\d+) fileID: (\d+)\s*$", re.MULTILINE
    )
    positions = list(doc_pattern.finditer(stripped))
    documents = []
    for i, match in enumerate(positions):
        class_id = match.group(1)
        file_id = match.group(2)
        start = match.end()
        end = positions[i + 1].start() if i + 1 < len(positions) else len(stripped)
        body = stripped[start:end]
        documents.append((class_id, file_id, body))
    return documents


def _extract_key(body: str, key: str) -> str | None:
    m = re.search(rf"^\s+{re.escape(key)}:\s*(.+)$", body, re.MULTILINE)
    return m.group(1).strip().strip("'\"") if m else None


def _extract_component_refs(body: str) -> list[str]:
    return re.findall(r"fileID:\s*(\d+)", body)


def _extract_parent_file_id(body: str) -> str | None:
    m = re.search(r"m_Father:\s*\{fileID:\s*(\d+)\}", body)
    if m:
        fid = m.group(1)
        return fid if fid != "0" else None
    return None


def _extract_children_file_ids(body: str) -> list[str]:
    """Extract child Transform fileIDs from m_Children block only.

    The m_Children block in a Unity Transform looks like:
        m_Children:
        - {fileID: 4100002}
        - {fileID: 4100003}
    followed by another key at the same indentation level (e.g. m_Father).
    We stop when we hit a line that starts with two spaces followed by a
    non-hyphen character (i.e. a new key at the same YAML level).
    """
    m_children = re.search(
        r"m_Children:((?:\n  -[^\n]*)*)(?:\n  \w|\Z)",
        body,
    )
    if not m_children:
        # Also handle empty list on same line: m_Children: []
        return []
    block = m_children.group(1)
    fids = re.findall(r"fileID:\s*(\d+)", block)
    # Exclude zero (null reference)
    return [f for f in fids if f != "0"]


# ---------------------------------------------------------------------------
# Component detail extraction
# ---------------------------------------------------------------------------

def _extract_component_detail(class_id: str, body: str) -> dict:
    """Return a dict of interesting fields for a component body."""
    ctype = CLASS_ID_NAMES.get(class_id, f"UnknownClass({class_id})")
    detail: dict = {"type": ctype, "class_id": class_id}

    # Pull all simple key: value scalar fields (skip complex sub-objects)
    for m in re.finditer(r"^\s{2}(\w+):\s*([^{\[\n][^\n]*)$", body, re.MULTILINE):
        k, v = m.group(1), m.group(2).strip()
        if k.startswith("m_") or k in ("serializedVersion",):
            detail[k] = v
    return detail


# ---------------------------------------------------------------------------
# Hierarchy builder
# ---------------------------------------------------------------------------

def _build_tree(
    go_file_id: str,
    go_by_id: dict,
    transform_by_go: dict,
    transform_to_go: dict,  # inverse of transform_by_go — O(1) child→GO lookup
    children_by_transform: dict,
    depth: int | None,
    current_depth: int = 0,
) -> dict:
    go_class_id, go_body = go_by_id.get(go_file_id, ("1", ""))
    name = _extract_key(go_body, "m_Name") or "(unnamed)"

    node: dict = {"file_id": go_file_id, "name": name}

    if depth is not None and current_depth >= depth:
        node["children"] = []
        return node

    # Get Transform for this GO
    transform_fid = transform_by_go.get(go_file_id)
    child_transforms = children_by_transform.get(transform_fid, []) if transform_fid else []

    # Map transform children back to GameObjects using pre-built inverse index
    children = []
    for child_t_fid in child_transforms:
        child_go_fid = transform_to_go.get(child_t_fid)
        if child_go_fid:
            children.append(
                _build_tree(
                    child_go_fid,
                    go_by_id,
                    transform_by_go,
                    transform_to_go,
                    children_by_transform,
                    depth,
                    current_depth + 1,
                )
            )

    node["children"] = children
    return node


# ---------------------------------------------------------------------------
# Main extraction logic
# ---------------------------------------------------------------------------

def parse_prefab(path: Path, depth: int | None) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"ERROR: Cannot read {path}: {exc}", file=sys.stderr)
        sys.exit(1)

    documents = _parse_unity_documents(text)

    # Index by file_id
    docs_by_id: dict[str, tuple[str, str]] = {}
    for class_id, file_id, body in documents:
        docs_by_id[file_id] = (class_id, body)

    # Separate GameObjects and Transforms
    go_by_id: dict[str, tuple[str, str]] = {}
    transform_by_go: dict[str, str] = {}  # go_file_id -> transform_file_id
    children_by_transform: dict[str, list[str]] = {}
    components_by_file_id: dict[str, list[dict]] = {}

    for class_id, file_id, body in documents:
        if class_id == "1":  # GameObject
            go_by_id[file_id] = (class_id, body)
            # Find its Transform among component refs
            refs = _extract_component_refs(body)
            for ref_fid in refs:
                if ref_fid in docs_by_id:
                    rcid, _ = docs_by_id[ref_fid]
                    if rcid == "4":
                        transform_by_go[file_id] = ref_fid
                        break

        elif class_id == "4":  # Transform
            children_by_transform[file_id] = _extract_children_file_ids(body)

    # Build components_by_file_id for all GameObjects
    for go_fid in go_by_id:
        go_cid, go_body = go_by_id[go_fid]
        refs = _extract_component_refs(go_body)
        comps = []
        for ref_fid in refs:
            if ref_fid in docs_by_id:
                rcid, rbody = docs_by_id[ref_fid]
                if rcid != "1":  # Exclude GO self-refs
                    comps.append(_extract_component_detail(rcid, rbody))
        if comps:
            components_by_file_id[go_fid] = comps

    # Find root GameObjects: those whose Transform has no parent
    root_fids = []
    for go_fid, t_fid in transform_by_go.items():
        if t_fid in docs_by_id:
            _, tbody = docs_by_id[t_fid]
            parent = _extract_parent_file_id(tbody)
            if parent is None:
                root_fids.append(go_fid)

    # Handle GOs without a transform (shouldn't happen in valid prefabs, but be safe)
    for go_fid in go_by_id:
        if go_fid not in transform_by_go and go_fid not in root_fids:
            root_fids.append(go_fid)

    root_file_id = root_fids[0] if root_fids else None

    # Build inverse map: transform_file_id -> go_file_id for O(1) child lookups
    transform_to_go: dict[str, str] = {t: g for g, t in transform_by_go.items()}

    hierarchy = [
        _build_tree(fid, go_by_id, transform_by_go, transform_to_go, children_by_transform, depth)
        for fid in root_fids
    ]

    return {
        "prefab": path.name,
        "root_file_id": root_file_id,
        "hierarchy": hierarchy,
        "components_by_file_id": components_by_file_id,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect a Unity .prefab file and emit JSON hierarchy."
    )
    parser.add_argument("prefab", help="Path to the .prefab file")
    parser.add_argument("--out", help="Output JSON file (default: stdout)")
    parser.add_argument(
        "--depth",
        type=int,
        default=None,
        help="Max hierarchy depth to render (default: unlimited)",
    )
    args = parser.parse_args()

    prefab_path = Path(args.prefab)
    if not prefab_path.exists():
        print(f"ERROR: File not found: {prefab_path}", file=sys.stderr)
        sys.exit(1)

    result = parse_prefab(prefab_path, args.depth)
    output = json.dumps(result, indent=2, sort_keys=True)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Written to {args.out}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
