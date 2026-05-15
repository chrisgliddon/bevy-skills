#!/usr/bin/env python3
"""
Inventory a Unity .unity scene file and emit a JSON summary.

Backs: references/unity-scene-inventory.md

Usage:
    python3 scene_inventory.py Scene.unity [--out inventory.json] \
        [--include-components] [--include-transforms]

Output format:
    {
      "scene": "Scene.unity",
      "gameobjects": [
        {
          "file_id": "1234567890",
          "name": "Player",
          "transform": {"position": [x,y,z], "rotation": [x,y,z,w], "scale": [x,y,z], "parent_file_id": "..."},
          "components": [{"type": "MeshRenderer", "file_id": "..."}]
        }
      ]
    }

Unity YAML note: .unity files use !u!<classID> &<fileID> tags that confuse
standard YAML parsers. This script strips those tags via a regex pre-pass so
stdlib 're' + 'json' are sufficient — no pyyaml required.

Unity class IDs referenced here:
  1  = GameObject
  4  = Transform
  23 = MeshRenderer
  33 = MeshFilter
  54 = Rigidbody
  65 = BoxCollider
  114 = MonoBehaviour
  212 = SpriteRenderer

Exit codes: 0 = success, 1 = file not found / parse error.
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Unity class-ID → human name map (subset; expand as needed)
# ---------------------------------------------------------------------------
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
# Lightweight Unity YAML parser
# ---------------------------------------------------------------------------

def _strip_unity_tags(text: str) -> str:
    """Replace '--- !u!<N> &<fileID>' header lines with '--- # <classID> &<fileID>'
    so stdlib re-based parsing can handle them without a full YAML library."""
    return re.sub(
        r"^--- !u!(\d+) &(\d+)",
        r"--- # classID: \1 fileID: \2",
        text,
        flags=re.MULTILINE,
    )


def _parse_unity_documents(text: str):
    """Split a Unity YAML file into a list of (class_id, file_id, body_lines) tuples."""
    stripped = _strip_unity_tags(text)
    # Split on document separators
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
    """Extract a top-level YAML scalar value for a given key from a body string."""
    pattern = re.compile(rf"^\s+{re.escape(key)}:\s*(.+)$", re.MULTILINE)
    m = pattern.search(body)
    return m.group(1).strip() if m else None


def _extract_vec3(body: str, key: str) -> list[float] | None:
    """Extract '{x: 0, y: 1, z: 0}' style Unity vector as [x, y, z]."""
    pattern = re.compile(
        rf"^\s+{re.escape(key)}:\s*\{{x:\s*([^,}}]+),\s*y:\s*([^,}}]+),\s*z:\s*([^,}}]+)\}}",
        re.MULTILINE,
    )
    m = pattern.search(body)
    if not m:
        return None
    try:
        return [float(m.group(1)), float(m.group(2)), float(m.group(3))]
    except ValueError:
        return None


def _extract_vec4(body: str, key: str) -> list[float] | None:
    """Extract '{x: 0, y: 0, z: 0, w: 1}' style Unity quaternion as [x,y,z,w]."""
    pattern = re.compile(
        rf"^\s+{re.escape(key)}:\s*\{{x:\s*([^,}}]+),\s*y:\s*([^,}}]+),\s*z:\s*([^,}}]+),\s*w:\s*([^,}}]+)\}}",
        re.MULTILINE,
    )
    m = pattern.search(body)
    if not m:
        return None
    try:
        return [float(m.group(i)) for i in range(1, 5)]
    except ValueError:
        return None


def _extract_component_refs(body: str) -> list[str]:
    """Extract file IDs of components listed in a GameObject's m_Component block."""
    # m_Component is a YAML sequence of {component: {fileID: N}} mappings
    return re.findall(r"fileID:\s*(\d+)", body)


def _extract_parent_file_id(body: str) -> str | None:
    """Extract parent Transform fileID from a Transform body."""
    # m_Father: {fileID: N}  — 0 means no parent
    m = re.search(r"m_Father:\s*\{fileID:\s*(\d+)\}", body)
    if m:
        fid = m.group(1)
        return fid if fid != "0" else None
    return None


# ---------------------------------------------------------------------------
# Main extraction logic
# ---------------------------------------------------------------------------

def parse_scene(path: Path, include_components: bool, include_transforms: bool) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"ERROR: Cannot read {path}: {exc}", file=sys.stderr)
        sys.exit(1)

    documents = _parse_unity_documents(text)

    # Index all documents by file_id
    docs_by_id: dict[str, tuple[str, str]] = {}  # file_id -> (class_id, body)
    for class_id, file_id, body in documents:
        docs_by_id[file_id] = (class_id, body)

    gameobjects = []

    for class_id, file_id, body in documents:
        if class_id != "1":  # Only GameObjects
            continue

        name = _extract_key(body, "m_Name") or "(unnamed)"
        # Strip surrounding quotes if present
        name = name.strip("'\"")

        go_entry: dict = {"file_id": file_id, "name": name}

        # --- Components ---
        if include_components:
            comp_refs = _extract_component_refs(body)
            components = []
            for ref_fid in comp_refs:
                if ref_fid == file_id:
                    continue  # Self-reference; skip
                if ref_fid in docs_by_id:
                    cid, _ = docs_by_id[ref_fid]
                    ctype = CLASS_ID_NAMES.get(cid, f"UnknownClass({cid})")
                    if ctype != "GameObject":
                        components.append({"type": ctype, "file_id": ref_fid})
            go_entry["components"] = components

        # --- Transform ---
        if include_transforms:
            # Find the Transform component for this GameObject
            transform_entry = None
            comp_refs_all = _extract_component_refs(body)
            for ref_fid in comp_refs_all:
                if ref_fid in docs_by_id:
                    cid, cbody = docs_by_id[ref_fid]
                    if cid == "4":  # Transform
                        pos = _extract_vec3(cbody, "m_LocalPosition") or [0.0, 0.0, 0.0]
                        rot = _extract_vec4(cbody, "m_LocalRotation") or [0.0, 0.0, 0.0, 1.0]
                        scale = _extract_vec3(cbody, "m_LocalScale") or [1.0, 1.0, 1.0]
                        parent = _extract_parent_file_id(cbody)
                        transform_entry = {
                            "position": pos,
                            "rotation": rot,
                            "scale": scale,
                            "parent_file_id": parent,
                        }
                        break
            go_entry["transform"] = transform_entry

        gameobjects.append(go_entry)

    return {
        "scene": path.name,
        "gameobjects": gameobjects,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inventory a Unity .unity scene file and emit JSON."
    )
    parser.add_argument("scene", help="Path to the .unity scene file")
    parser.add_argument("--out", help="Output JSON file (default: stdout)")
    parser.add_argument(
        "--include-components",
        dest="include_components",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include component list per GameObject (default: true)",
    )
    parser.add_argument(
        "--include-transforms",
        dest="include_transforms",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include transform data per GameObject (default: true)",
    )
    args = parser.parse_args()

    scene_path = Path(args.scene)
    if not scene_path.exists():
        print(f"ERROR: File not found: {scene_path}", file=sys.stderr)
        sys.exit(1)

    result = parse_scene(scene_path, args.include_components, args.include_transforms)
    output = json.dumps(result, indent=2, sort_keys=True)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Written to {args.out}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
