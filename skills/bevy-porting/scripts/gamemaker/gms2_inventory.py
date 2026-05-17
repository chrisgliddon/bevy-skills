#!/usr/bin/env python3
"""
gms2_inventory.py — Walk a GameMaker Studio 2 project and emit a JSON
inventory of all assets grouped by resource type.

Backing reference: references/gamemaker.md

Project layout: MyGame.yyp (root manifest, JSON) + per-asset .yy files
under objects/, sprites/, rooms/, sounds/, scripts/, fonts/, tilesets/, etc.
Each .yy has a top-level "resourceType" field: "GMObject", "GMSprite",
"GMRoom", "GMSound", "GMScript", "GMFont", "GMTileset", "GMShader", …

GMS2 event type integers (eventtype field):
    0=Create  1=Destroy  2=Alarm  3=Step(0/1/2=Step/BeginStep/EndStep)
    4=Collision  5=Keyboard  6=Mouse  7=Other
    8=Draw(0=Draw,64=DrawGUI,72=DrawResize)
    9=KeyPress  10=KeyRelease  12=CleanUp  13=Gesture  25=PreCreate

Usage:
    python3 gms2_inventory.py Project.yyp
    python3 gms2_inventory.py Project.yyp --out project.json
    python3 gms2_inventory.py Project.yyp --by-type
    python3 gms2_inventory.py Project.yyp --include-events

Output: {"project":…, "name":…, "resources_by_type": {"GMObject": […], …},
         "totals": {…}}

Exit codes: 0 = success, 1 = file not found / parse error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# GMS2 event-type decoding
# ---------------------------------------------------------------------------

_EVENT_TYPE_NAMES: dict[int, str] = {
    0: "Create",
    1: "Destroy",
    2: "Alarm",
    3: "Step",
    4: "Collision",
    5: "Keyboard",
    6: "Mouse",
    7: "Other",
    8: "Draw",
    9: "KeyPress",
    10: "KeyRelease",
    11: "Trigger",
    12: "CleanUp",
    13: "Gesture",
    25: "PreCreate",
}

_STEP_SUBTYPES: dict[int, str] = {0: "Step", 1: "BeginStep", 2: "EndStep"}
_DRAW_SUBTYPES: dict[int, str] = {0: "Draw", 64: "DrawGUI", 72: "DrawResize"}


def _decode_event(event_type: int, event_num: int) -> str:
    """Return a human-readable event name from a GMS2 event type + subtype int."""
    base = _EVENT_TYPE_NAMES.get(event_type, f"Event{event_type}")
    if event_type == 3:  # Step
        return _STEP_SUBTYPES.get(event_num, base)
    if event_type == 8:  # Draw
        return _DRAW_SUBTYPES.get(event_num, f"Draw({event_num})")
    if event_type == 2:  # Alarm
        return f"Alarm[{event_num}]"
    return base


# ---------------------------------------------------------------------------
# Per-asset enrichment
# ---------------------------------------------------------------------------

def _enrich_object(data: dict, include_events: bool) -> dict:
    """Extract Object-specific metadata from a .yy data dict."""
    entry: dict = {}
    if include_events:
        raw_events = data.get("eventList", [])
        decoded: list[str] = []
        seen: set[str] = set()
        for ev in raw_events:
            etype = ev.get("eventtype", -1)
            enum = ev.get("enumb", 0)
            label = _decode_event(int(etype), int(enum))
            if label not in seen:
                decoded.append(label)
                seen.add(label)
        entry["events"] = decoded
    return entry


def _enrich_sprite(data: dict) -> dict:
    """Extract Sprite-specific metadata."""
    frames = data.get("frames", [])
    frame_count = len(frames) if isinstance(frames, list) else 0
    sequence = data.get("sequence", {})
    # Origin stored at top level or inside sequence
    origin_x = data.get("xorig", sequence.get("xorig", 0))
    origin_y = data.get("yorig", sequence.get("yorig", 0))
    return {"frames": frame_count, "origin": [origin_x, origin_y]}


def _enrich_room(data: dict) -> dict:
    """Extract Room-specific metadata."""
    # Instances are nested inside instanceCreationOrder or layers[].instances
    count = 0
    creation_order = data.get("instanceCreationOrder", [])
    if isinstance(creation_order, list):
        count = len(creation_order)
    if count == 0:
        # Fallback: count across all layers
        for layer in data.get("layers", []):
            instances = layer.get("instances", [])
            if isinstance(instances, list):
                count += len(instances)
    return {"instances": count}


# ---------------------------------------------------------------------------
# Project walker
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | None:
    """Load a JSON file, returning None on error (with a stderr warning)."""
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"WARNING: Could not read {path}: {exc}", file=sys.stderr)
        return None


def _collect_resources(
    project_root: Path,
    yyp_data: dict,
    include_events: bool,
) -> dict[str, list[dict]]:
    """Walk project resources and build the resources_by_type dict."""
    resources_by_type: dict[str, list[dict]] = {}

    raw_resources = yyp_data.get("resources", [])
    # Handle both list-of-dicts and older list-of-{id,value} formats
    resource_paths: list[str] = []
    for item in raw_resources:
        if isinstance(item, dict):
            # Modern format: {"id": {...}, "order": n}  or  {"resourceType": ..., "filePath": ...}
            file_path = item.get("filePath") or item.get("id", {}).get("path", "")
            if file_path:
                resource_paths.append(file_path)

    # If the yyp uses a flat list of path strings (older GMS2 format), handle that too.
    if not resource_paths:
        for item in raw_resources:
            if isinstance(item, str):
                resource_paths.append(item)

    for rel_path in resource_paths:
        yy_path = project_root / rel_path
        if not yy_path.exists():
            # Try the path as-is relative to project root
            yy_path = project_root / rel_path.replace("\\", "/")
        if not yy_path.exists():
            continue

        data = _load_json(yy_path)
        if data is None:
            continue

        resource_type = data.get("resourceType", "Unknown")
        name = data.get("name", yy_path.stem)

        entry: dict = {"name": name, "path": str(yy_path.relative_to(project_root))}

        if resource_type == "GMObject":
            entry.update(_enrich_object(data, include_events))
        elif resource_type == "GMSprite":
            entry.update(_enrich_sprite(data))
        elif resource_type == "GMRoom":
            entry.update(_enrich_room(data))

        resources_by_type.setdefault(resource_type, []).append(entry)

    # Sort each type's list by name for deterministic output
    for lst in resources_by_type.values():
        lst.sort(key=lambda e: e.get("name", ""))

    return resources_by_type


def parse_project(
    yyp_path: Path,
    include_events: bool,
) -> dict:
    """Parse a GMS2 .yyp project and return the full inventory dict."""
    yyp_data = _load_json(yyp_path)
    if yyp_data is None:
        print(f"ERROR: Cannot parse .yyp file: {yyp_path}", file=sys.stderr)
        sys.exit(1)

    project_root = yyp_path.parent
    project_name = yyp_path.stem

    resources_by_type = _collect_resources(project_root, yyp_data, include_events)

    totals = {rtype: len(lst) for rtype, lst in resources_by_type.items()}

    return {
        "project": yyp_path.name,
        "name": project_name,
        "resources_by_type": resources_by_type,
        "totals": totals,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Walk a GameMaker Studio 2 project (.yyp) and emit a JSON "
            "inventory of all assets grouped by resource type."
        )
    )
    parser.add_argument(
        "project",
        help="Path to the .yyp project file.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output JSON file path. Default: stdout.",
    )
    parser.add_argument(
        "--by-type",
        dest="by_type",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Group output by resource type (default: true).",
    )
    parser.add_argument(
        "--include-events",
        dest="include_events",
        action="store_true",
        default=False,
        help=(
            "For GMObject resources, parse each .yy and list the event names "
            "(Create, Step, Draw, …). Adds a per-object 'events' list."
        ),
    )

    args = parser.parse_args()
    yyp_path = Path(args.project)

    if not yyp_path.exists():
        print(f"ERROR: File not found: {yyp_path}", file=sys.stderr)
        return 1

    result = parse_project(yyp_path, args.include_events)

    if not args.by_type:
        # Flatten to a single list of all resources
        flat: list[dict] = []
        for rtype, lst in result["resources_by_type"].items():
            for item in lst:
                flat.append({"resource_type": rtype, **item})
        result = {
            "project": result["project"],
            "name": result["name"],
            "resources": flat,
            "totals": result["totals"],
        }

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
