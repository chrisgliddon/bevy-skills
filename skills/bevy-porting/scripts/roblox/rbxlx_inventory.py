#!/usr/bin/env python3
"""
rbxlx_inventory.py — Parse a Roblox `.rbxlx` place file (XML) and emit a JSON
inventory of every Instance in the tree plus a list of all referenced
`rbxassetid://` URLs.

Backing reference: references/roblox.md

IMPORTANT — `.rbxl` vs `.rbxlx`:
    This script handles `.rbxlx` (XML format). Binary `.rbxl` files cannot be
    parsed here. Use `rbx-dom` (Rust crate) or `rojo` (Go CLI) to convert a
    `.rbxl` to `.rbxlx` first, then run this script.

Usage:
    python3 rbxlx_inventory.py place.rbxlx
    python3 rbxlx_inventory.py place.rbxlx --out place.json
    python3 rbxlx_inventory.py place.rbxlx --include-properties
    python3 rbxlx_inventory.py place.rbxlx --asset-urls-only

Output JSON shape (default):
    {
      "place": "place.rbxlx",
      "instances": [
        {
          "class": "Workspace",
          "name": "Workspace",
          "parent": null,
          "depth": 0
        },
        {
          "class": "Part",
          "name": "Baseplate",
          "parent": "Workspace",
          "depth": 1
        }
      ],
      "asset_urls": ["rbxassetid://12345"]
    }

With --include-properties each instance entry gains a "properties" dict
containing the scalar property values found in the <Properties> block.

With --asset-urls-only the output is a bare JSON array of asset URL strings,
suitable for piping into a re-sourcing workflow.

Exit codes: 0 = success, 1 = file not found / parse error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Asset URL extraction
# ---------------------------------------------------------------------------

_ASSET_URL_RE = re.compile(r"rbxassetid://\d+", re.IGNORECASE)


def _find_asset_urls(root: ET.Element) -> list[str]:
    """Walk the XML tree and collect every distinct rbxassetid:// URL."""
    found: set[str] = set()
    for elem in root.iter():
        text = elem.text or ""
        for url in _ASSET_URL_RE.findall(text):
            found.add(url.lower())
        for attr_val in elem.attrib.values():
            for url in _ASSET_URL_RE.findall(attr_val):
                found.add(url.lower())
    return sorted(found)


# ---------------------------------------------------------------------------
# Property extraction
# ---------------------------------------------------------------------------

# Property tag names whose text content is useful as scalar values.
_SCALAR_TAGS = frozenset(
    {
        "string",
        "int",
        "int64",
        "float",
        "double",
        "bool",
        "token",
        "BinaryString",
        "ProtectedString",
        "Content",
    }
)

# Tags that contain child elements rather than flat text (we skip deep nesting
# to keep properties readable; callers can extend if needed).
_SKIP_TAGS = frozenset({"Vector3", "CFrame", "CoordinateFrame", "Color3", "UDim2", "Rect"})


def _extract_properties(props_elem: ET.Element | None) -> dict[str, str]:
    """Extract scalar property name→value pairs from a <Properties> element."""
    if props_elem is None:
        return {}
    result: dict[str, str] = {}
    for child in props_elem:
        name = child.attrib.get("name", "")
        if not name:
            continue
        tag = child.tag
        if tag in _SCALAR_TAGS:
            result[name] = (child.text or "").strip()
        elif tag not in _SKIP_TAGS:
            # For structured types, emit a compact repr of sub-children text.
            parts = []
            for sub in child:
                sub_text = (sub.text or "").strip()
                if sub_text:
                    parts.append(f"{sub.tag}={sub_text}")
            if parts:
                result[name] = "; ".join(parts)
    return result


# ---------------------------------------------------------------------------
# Recursive instance walk
# ---------------------------------------------------------------------------

def _walk_items(
    element: ET.Element,
    parent_name: str | None,
    depth: int,
    include_properties: bool,
    instances: list[dict],
) -> None:
    """Recursively walk <Item> elements and append to the instances list."""
    for item in element.findall("Item"):
        class_name = item.attrib.get("class", "")

        # Resolve instance name from Properties/string[@name="Name"]
        props_elem = item.find("Properties")
        name_text = "(unnamed)"
        if props_elem is not None:
            name_elem = props_elem.find("string[@name='Name']")
            if name_elem is not None and name_elem.text:
                name_text = name_elem.text.strip()

        entry: dict = {
            "class": class_name,
            "name": name_text,
            "parent": parent_name,
            "depth": depth,
        }

        if include_properties:
            entry["properties"] = _extract_properties(props_elem)

        instances.append(entry)

        # Recurse into children
        _walk_items(item, name_text, depth + 1, include_properties, instances)


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------

def parse_rbxlx(path: Path, include_properties: bool) -> dict:
    """Parse a .rbxlx file and return the full inventory dict."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"ERROR: Cannot read {path}: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        print(f"ERROR: XML parse failed for {path}: {exc}", file=sys.stderr)
        sys.exit(1)

    instances: list[dict] = []
    _walk_items(root, None, 0, include_properties, instances)

    asset_urls = _find_asset_urls(root)

    return {
        "place": path.name,
        "instances": instances,
        "asset_urls": asset_urls,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Parse a Roblox .rbxlx place file (XML) and emit a JSON inventory "
            "of all Instances plus referenced rbxassetid:// URLs. "
            "For binary .rbxl files, convert with rbx-dom or rojo first."
        )
    )
    parser.add_argument(
        "place",
        help="Path to the .rbxlx file to parse.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output JSON file path. Default: stdout.",
    )
    parser.add_argument(
        "--include-properties",
        dest="include_properties",
        action="store_true",
        default=False,
        help="Include per-instance property dict in output (default: false).",
    )
    parser.add_argument(
        "--asset-urls-only",
        dest="asset_urls_only",
        action="store_true",
        default=False,
        help=(
            "Output only the list of rbxassetid:// URLs found in the place "
            "(useful for asset re-sourcing). Ignores --include-properties."
        ),
    )

    args = parser.parse_args()
    place_path = Path(args.place)

    if not place_path.exists():
        print(f"ERROR: File not found: {place_path}", file=sys.stderr)
        return 1

    result = parse_rbxlx(place_path, args.include_properties)

    if args.asset_urls_only:
        output = json.dumps(result["asset_urls"], indent=2)
    else:
        output = json.dumps(result, indent=2)

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
