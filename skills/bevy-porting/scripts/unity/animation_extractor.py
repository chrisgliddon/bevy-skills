#!/usr/bin/env python3
"""
Extract animation tracks from a Unity .anim file and emit JSON.

Backs: references/unity-animation-extractor.md

Usage:
    python3 animation_extractor.py Foo.anim [--out anim.json] \
        [--format bevy-keyframes|raw]

Output format (--format bevy-keyframes, default):
    {
      "clip": "Foo.anim",
      "tracks": [
        {
          "path": "Armature/Hips",
          "property": "Transform.translation",
          "keyframes": [ [0.0, [0,0,0]], [0.5, [0,1,0]], [1.0, [0,0,0]] ]
        }
      ]
    }

    keyframes entries: [time_seconds, value]
    value is a list for vector/quaternion properties, a float for scalar.

Output format (--format raw):
    Same outer shape but keyframes entries are:
    {"time": t, "value": v, "inSlope": s, "outSlope": s}

Unity YAML note: .anim files use the same !u!<classID> &<fileID> dialect.
Curve data lives under AnimationClip (class 74):
  m_PositionCurves  -> list of {path, curve.m_Curve[{time, value{x,y,z}}]}
  m_RotationCurves  -> list of {path, curve.m_Curve[{time, value{x,y,z,w}}]}
  m_ScaleCurves     -> list of {path, curve.m_Curve[{time, value{x,y,z}}]}
  m_FloatCurves     -> list of {path, attribute, curve.m_Curve[{time, value}]}
  m_EulerCurves     -> list of {path, curve.m_Curve[{time, value{x,y,z}}]}

This script uses stdlib 're' only — no pyyaml required.

Exit codes: 0 = success, 1 = file not found / parse error.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Unity YAML tag pre-processing (same approach as scene_inventory.py)
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


# ---------------------------------------------------------------------------
# Curve parsing helpers
# ---------------------------------------------------------------------------

def _parse_keyframe_scalar(kf_text: str, fmt: str) -> dict | list:
    """Parse a single scalar keyframe block."""
    time_m = re.search(r"time:\s*([^\n,}]+)", kf_text)
    val_m = re.search(r"(?<!\w)value:\s*([^\n,}]+)", kf_text)
    in_m = re.search(r"inSlope:\s*([^\n,}]+)", kf_text)
    out_m = re.search(r"outSlope:\s*([^\n,}]+)", kf_text)

    time = float(time_m.group(1).strip()) if time_m else 0.0
    value = float(val_m.group(1).strip()) if val_m else 0.0
    in_slope = float(in_m.group(1).strip()) if in_m else 0.0
    out_slope = float(out_m.group(1).strip()) if out_m else 0.0

    if fmt == "raw":
        return {"time": time, "value": value, "inSlope": in_slope, "outSlope": out_slope}
    else:
        return [time, value]


def _parse_keyframe_vec3(kf_text: str, fmt: str) -> dict | list:
    time_m = re.search(r"time:\s*([^\n,}]+)", kf_text)
    x_m = re.search(r"value:\s*\{x:\s*([^,}]+),\s*y:\s*([^,}]+),\s*z:\s*([^,}]+)\}", kf_text)
    in_m = re.search(r"inSlope:\s*\{x:\s*([^,}]+),\s*y:\s*([^,}]+),\s*z:\s*([^,}]+)\}", kf_text)
    out_m = re.search(r"outSlope:\s*\{x:\s*([^,}]+),\s*y:\s*([^,}]+),\s*z:\s*([^,}]+)\}", kf_text)

    time = float(time_m.group(1).strip()) if time_m else 0.0

    def _vec3_or_none(m):
        if not m:
            return None
        try:
            return [float(m.group(i)) for i in range(1, 4)]
        except ValueError:
            return None

    value = _vec3_or_none(x_m) or [0.0, 0.0, 0.0]
    in_slope = _vec3_or_none(in_m)
    out_slope = _vec3_or_none(out_m)

    if fmt == "raw":
        entry: dict = {"time": time, "value": value}
        if in_slope is not None:
            entry["inSlope"] = in_slope
        if out_slope is not None:
            entry["outSlope"] = out_slope
        return entry
    else:
        return [time, value]


def _parse_keyframe_vec4(kf_text: str, fmt: str) -> dict | list:
    time_m = re.search(r"time:\s*([^\n,}]+)", kf_text)
    v_m = re.search(
        r"value:\s*\{x:\s*([^,}]+),\s*y:\s*([^,}]+),\s*z:\s*([^,}]+),\s*w:\s*([^,}]+)\}",
        kf_text,
    )

    time = float(time_m.group(1).strip()) if time_m else 0.0

    def _vec4_or_none(m):
        if not m:
            return None
        try:
            return [float(m.group(i)) for i in range(1, 5)]
        except ValueError:
            return None

    value = _vec4_or_none(v_m) or [0.0, 0.0, 0.0, 1.0]

    if fmt == "raw":
        return {"time": time, "value": value}
    else:
        return [time, value]


def _split_keyframe_blocks(curve_text: str) -> list[str]:
    """Split curve text into individual keyframe blocks.

    Unity keyframe list items begin with a YAML list marker '- ' at a
    consistent indentation. We split on that marker. Each block will contain
    'time:' somewhere inside it.
    Handles two common Unity shapes:
      - time: 0           (time is the first key)
      - serializedVersion: 3   (serializedVersion precedes time)
        time: 0
    """
    # Split on any line that starts a new list item at the outermost list level.
    # We look for lines that match ^\s+- (not preceded by another '-' at same level).
    blocks = re.split(r"(?=^\s+- (?:time:|serializedVersion:))", curve_text, flags=re.MULTILINE)
    return [b.strip() for b in blocks if b.strip() and "time:" in b]


def _parse_curve_block(curve_body: str, prop_type: str, fmt: str) -> list:
    """Parse a full m_Curve: [...] block and return a list of keyframes.

    Unity layout (inside an entry block):
      - curve:
          serializedVersion: 2
          m_Curve:
          - serializedVersion: 3
            time: 0
            value: {x: 0, y: 0, z: 0}
            ...
          m_PreInfinity: 2
        path: Armature/Hips

    We locate 'm_Curve:' and collect all lines until we hit a line whose
    leading whitespace is <= the indentation of the 'm_Curve:' line itself
    (indicating a sibling/parent key). This handles arbitrary indentation.
    """
    # Find the line containing 'm_Curve:'
    m_curve_start = re.search(r"^( *)(m_Curve:.*)", curve_body, re.MULTILINE)
    if not m_curve_start:
        return []

    indent_len = len(m_curve_start.group(1))
    # Collect everything after this line until we find a non-empty line
    # whose indentation is <= indent_len (a sibling or parent key)
    rest = curve_body[m_curve_start.end():]
    collected_lines = []
    for line in rest.splitlines():
        if line == "" or line.isspace():
            collected_lines.append(line)
            continue
        line_indent = len(line) - len(line.lstrip())
        if line_indent <= indent_len and line.lstrip() and not line.lstrip().startswith("-"):
            break
        collected_lines.append(line)

    curve_text = "\n".join(collected_lines)
    kf_blocks = _split_keyframe_blocks(curve_text)

    result = []
    for kf in kf_blocks:
        if prop_type == "vec3":
            result.append(_parse_keyframe_vec3(kf, fmt))
        elif prop_type == "vec4":
            result.append(_parse_keyframe_vec4(kf, fmt))
        else:
            result.append(_parse_keyframe_scalar(kf, fmt))
    return result


# ---------------------------------------------------------------------------
# Curve group parsers
# ---------------------------------------------------------------------------

def _parse_curve_group(body: str, section_key: str, bevy_property: str,
                       prop_type: str, fmt: str) -> list[dict]:
    """Parse one of the m_*Curves sections and return a list of track dicts."""
    # Find the section
    section_m = re.search(
        rf"{re.escape(section_key)}:(.*?)(?=\n  m_\w+Curves:|\n  m_\w+:|\Z)",
        body,
        re.DOTALL,
    )
    if not section_m:
        return []

    section_text = section_m.group(1)

    # Split into per-path entries (each starts with '- curve:' after path)
    # Unity format: each entry starts with a list item containing 'path:' and 'curve:'
    # We split on entries that begin with '  - curve:' preceded by a path
    entry_pattern = re.compile(r"(?=^\s+-\s+curve:)", re.MULTILINE)
    # Alternative: split on '  - curve:' anchors
    raw_entries = re.split(r"(?=^\s+- curve:)", section_text, flags=re.MULTILINE)

    tracks = []
    for entry in raw_entries:
        if "curve:" not in entry:
            continue
        path_m = re.search(r"path:\s*(.+)", entry)
        path = path_m.group(1).strip().strip("'\"") if path_m else ""

        # For float curves, also grab 'attribute'
        attribute = None
        if section_key == "m_FloatCurves":
            attr_m = re.search(r"attribute:\s*(.+)", entry)
            attribute = attr_m.group(1).strip().strip("'\"") if attr_m else ""

        keyframes = _parse_curve_block(entry, prop_type, fmt)
        if not keyframes:
            continue

        prop = bevy_property
        if attribute:
            prop = f"{bevy_property}.{attribute}"

        tracks.append({"path": path, "property": prop, "keyframes": keyframes})

    return tracks


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def parse_anim(path: Path, fmt: str) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"ERROR: Cannot read {path}: {exc}", file=sys.stderr)
        sys.exit(1)

    documents = _parse_unity_documents(text)

    # Find AnimationClip document (class ID 74)
    anim_body = None
    for class_id, file_id, body in documents:
        if class_id == "74":
            anim_body = body
            break

    if anim_body is None:
        print(f"ERROR: No AnimationClip (class 74) found in {path}", file=sys.stderr)
        sys.exit(1)

    tracks: list[dict] = []

    tracks += _parse_curve_group(anim_body, "m_PositionCurves", "Transform.translation", "vec3", fmt)
    tracks += _parse_curve_group(anim_body, "m_RotationCurves", "Transform.rotation", "vec4", fmt)
    tracks += _parse_curve_group(anim_body, "m_ScaleCurves", "Transform.scale", "vec3", fmt)
    tracks += _parse_curve_group(anim_body, "m_EulerCurves", "Transform.euler_angles", "vec3", fmt)
    tracks += _parse_curve_group(anim_body, "m_FloatCurves", "Float", "scalar", fmt)

    return {"clip": path.name, "tracks": tracks}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract animation tracks from a Unity .anim file."
    )
    parser.add_argument("anim", help="Path to the .anim file")
    parser.add_argument("--out", help="Output JSON file (default: stdout)")
    parser.add_argument(
        "--format",
        choices=["bevy-keyframes", "raw"],
        default="bevy-keyframes",
        help=(
            "bevy-keyframes (default): [(time, value), ...] ready for "
            "AnimatableKeyframeCurve::new([...]). raw: Unity's curve structure "
            "with inSlope/outSlope for custom curve types."
        ),
    )
    args = parser.parse_args()

    anim_path = Path(args.anim)
    if not anim_path.exists():
        print(f"ERROR: File not found: {anim_path}", file=sys.stderr)
        sys.exit(1)

    result = parse_anim(anim_path, args.format)
    output = json.dumps(result, indent=2, sort_keys=True)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Written to {args.out}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
