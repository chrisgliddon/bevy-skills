#!/usr/bin/env python3
"""
tscn_inventory.py — Parse a Godot 4 .tscn (scene) or .tres (resource) text file
and emit a JSON inventory of nodes and external resource references.

Backing reference: references/godot.md

No Godot installation required — parses the plain-text format directly
using stdlib re, json, argparse, and pathlib.

Usage:
    python3 tscn_inventory.py path/to/Scene.tscn
    python3 tscn_inventory.py path/to/Scene.tscn --out scene.json
    python3 tscn_inventory.py path/to/Scene.tscn --include-properties
    python3 tscn_inventory.py path/to/Scene.tscn --resolve-resources
    python3 tscn_inventory.py path/to/Scene.tscn --no-include-properties --out minimal.json

Output JSON shape:
    {
      "scene": "Scene.tscn",
      "ext_resources": [
        {"id": "1_abc12", "type": "Script", "path": "res://player.gd"}
      ],
      "nodes": [
        {
          "name": "Player",
          "type": "CharacterBody3D",
          "parent": "",
          "properties": {
            "position": "Vector3(0, 1, 0)",
            "script": "ExtResource(\\"1_abc12\\")"
          }
        },
        {
          "name": "Camera3D",
          "type": "Camera3D",
          "parent": "Player",
          "properties": {}
        }
      ]
    }

Nodes with parent="." (Godot root sentinel) are output with parent="".
--resolve-resources replaces ExtResource("id") values in node properties
with the corresponding path from ext_resources, e.g.
  "script": "res://player.gd"

Exit codes: 0 = success, 1 = file not found / parse error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

# Matches a section header like:
#   [node name="Player" type="CharacterBody3D" parent="."]
#   [ext_resource type="Script" path="res://player.gd" id="1_abc12"]
#   [gd_scene load_steps=3 format=3 uid="uid://abc"]
_SECTION_RE = re.compile(r"^\[(\w+)(.*?)\]\s*$", re.MULTILINE)

# Matches key=value pairs inside a section header, e.g. name="Player"
_ATTR_RE = re.compile(r'(\w+)\s*=\s*(?:"([^"]*)"|(\S+))')


def _parse_attrs(attr_string: str) -> dict[str, str]:
    """Parse space-separated key=value pairs from a section header attribute string."""
    result: dict[str, str] = {}
    for m in _ATTR_RE.finditer(attr_string):
        key = m.group(1)
        # Prefer quoted value (group 2) over unquoted (group 3)
        value = m.group(2) if m.group(2) is not None else m.group(3)
        result[key] = value
    return result


def _parse_properties(block: str) -> dict[str, str]:
    """
    Parse the key = value property lines that follow a section header.

    Each property line has the form:
        key = <value>
    where <value> may be a quoted string, a Vector3(...), a boolean, a number,
    or an ExtResource("id") reference. We store all values as raw strings.
    Multi-line values (arrays, sub-resources) are collected until the next
    top-level key or section boundary.
    """
    props: dict[str, str] = {}
    # Lines that look like "key = value" at the start of the line
    prop_line_re = re.compile(r"^(\w+)\s*=\s*(.*)$")
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = prop_line_re.match(line)
        if m:
            key = m.group(1)
            value = m.group(2).strip()
            # Accumulate continuation lines (arrays, multiline values)
            # A continuation line starts with a space/tab or is a PoolArray item
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if next_line.strip() == "" or prop_line_re.match(next_line):
                    break
                value = value + "\n" + next_line.rstrip()
                j += 1
            props[key] = value
            i = j
        else:
            i += 1
    return props


# ---------------------------------------------------------------------------
# Core parsing
# ---------------------------------------------------------------------------

def parse_tscn(
    path: Path,
    include_properties: bool,
    resolve_resources: bool,
) -> dict:
    """Parse a .tscn or .tres file and return an inventory dict."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"ERROR: Cannot read {path}: {exc}", file=sys.stderr)
        sys.exit(1)

    # Split the file into (section_header_match, body_text) pairs
    sections: list[tuple[re.Match, str]] = []
    matches = list(_SECTION_RE.finditer(text))
    for idx, match in enumerate(matches):
        body_start = match.end()
        body_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections.append((match, text[body_start:body_end]))

    ext_resources: list[dict] = []
    nodes: list[dict] = []

    for match, body in sections:
        section_type = match.group(1)
        attrs = _parse_attrs(match.group(2))

        if section_type == "ext_resource":
            ext_resources.append(
                {
                    "id": attrs.get("id", ""),
                    "type": attrs.get("type", ""),
                    "path": attrs.get("path", ""),
                }
            )

        elif section_type == "node":
            raw_parent = attrs.get("parent", "")
            # Godot uses "." to mean "root" (no parent); normalise to ""
            parent = "" if raw_parent == "." else raw_parent

            node_entry: dict = {
                "name": attrs.get("name", ""),
                "type": attrs.get("type", ""),
                "parent": parent,
            }

            if include_properties:
                props = _parse_properties(body)
                if resolve_resources:
                    props = _resolve_ext_resources(props, ext_resources)
                node_entry["properties"] = props
            else:
                node_entry["properties"] = {}

            nodes.append(node_entry)

    return {
        "scene": path.name,
        "ext_resources": ext_resources,
        "nodes": nodes,
    }


# ---------------------------------------------------------------------------
# Resource resolution
# ---------------------------------------------------------------------------

def _resolve_ext_resources(
    props: dict[str, str],
    ext_resources: list[dict],
) -> dict[str, str]:
    """
    Replace ExtResource("id") references in property values with their resolved paths.

    e.g. 'ExtResource("1_abc12")' → 'res://player.gd'
    """
    # Build id → path lookup
    id_to_path: dict[str, str] = {r["id"]: r["path"] for r in ext_resources}
    ext_res_re = re.compile(r'ExtResource\(\s*"([^"]+)"\s*\)')

    resolved: dict[str, str] = {}
    for key, value in props.items():
        def _replace(m: re.Match) -> str:
            res_id = m.group(1)
            return id_to_path.get(res_id, m.group(0))

        resolved[key] = ext_res_re.sub(_replace, value)
    return resolved


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Parse a Godot 4 .tscn/.tres file and emit a JSON node/resource inventory. "
            "No Godot install required."
        )
    )
    parser.add_argument(
        "scene",
        help="Path to the .tscn or .tres file to parse.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output JSON file path. Default: stdout.",
    )
    parser.add_argument(
        "--include-properties",
        dest="include_properties",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include per-node property dict in output (default: true).",
    )
    parser.add_argument(
        "--resolve-resources",
        dest="resolve_resources",
        action="store_true",
        default=False,
        help=(
            "Replace ExtResource(id) values in node properties with the "
            "resolved resource path from ext_resources (default: false)."
        ),
    )

    args = parser.parse_args()

    scene_path = Path(args.scene)
    if not scene_path.exists():
        print(f"ERROR: File not found: {scene_path}", file=sys.stderr)
        return 1

    result = parse_tscn(scene_path, args.include_properties, args.resolve_resources)
    output = json.dumps(result, indent=2, sort_keys=True)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"Written to {args.out}", file=sys.stderr)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
