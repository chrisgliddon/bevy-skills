#!/usr/bin/env python3
"""
Walk a Unity Assets/ directory and emit a JSON inventory (plus optional Markdown).

Backs: references/unity-asset-audit.md

Usage:
    python3 asset_audit.py Assets/ [--out audit.json] [--report audit.md] \
        [--by-type] [--by-size] [--graph]

Output JSON shape:
    {
      "root": "Assets/",
      "totals": {
        "files": 1234,
        "bytes": 567890123,
        "by_type": { "Texture2D": 200, "Material": 50, ... }
      },
      "assets": [
        {
          "path": "Assets/Models/character.fbx",
          "guid": "abc...",
          "type": "Model",
          "bytes": 12345,
          "depends_on": ["guid1", "guid2"]
        }
      ]
    }

Type detection priority:
  1. Extension-based (fast, always runs)
  2. .meta file contents (importer class name)

--graph: includes dependency edges in JSON (reads every .meta file for guids
  in its dependencies block; adds ~O(n) overhead; off by default).

--by-type / --by-size: sort the 'assets' list in the JSON.
  --by-type sorts alphabetically by type then path.
  --by-size sorts descending by bytes.

--report audit.md: writes a Markdown summary alongside the JSON.

stdlib-only: uses 're', 'os', 'pathlib', 'json', 'argparse'. No pyyaml.

Exit codes: 0 = success, 1 = path not found / not a directory.
"""

from __future__ import annotations  # PEP 604 union syntax on Python 3.9

import argparse
import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Extension → Unity asset type map
# ---------------------------------------------------------------------------

EXT_TO_TYPE: dict[str, str] = {
    # Textures
    ".png": "Texture2D",
    ".jpg": "Texture2D",
    ".jpeg": "Texture2D",
    ".tga": "Texture2D",
    ".tiff": "Texture2D",
    ".psd": "Texture2D",
    ".exr": "Texture2D",
    ".hdr": "Texture2D",
    ".bmp": "Texture2D",
    # Models
    ".fbx": "Model",
    ".obj": "Model",
    ".dae": "Model",
    ".3ds": "Model",
    ".blend": "Model",
    # Audio
    ".mp3": "AudioClip",
    ".wav": "AudioClip",
    ".ogg": "AudioClip",
    ".aiff": "AudioClip",
    ".flac": "AudioClip",
    # Shaders
    ".shader": "Shader",
    ".cginc": "Shader",
    ".hlsl": "Shader",
    ".glsl": "Shader",
    # Scripts
    ".cs": "MonoScript",
    ".js": "MonoScript",
    # Scenes / Prefabs / Anims
    ".unity": "Scene",
    ".prefab": "Prefab",
    ".anim": "AnimationClip",
    ".controller": "AnimatorController",
    ".overrideController": "AnimatorOverrideController",
    ".mask": "AvatarMask",
    # Materials / Shaders / Render
    ".mat": "Material",
    ".renderTexture": "RenderTexture",
    ".cubemap": "Cubemap",
    # UI / Fonts
    ".ttf": "Font",
    ".otf": "Font",
    ".fontsettings": "GUIStyle",
    # Data
    ".asset": "ScriptableObject",
    ".json": "TextAsset",
    ".xml": "TextAsset",
    ".txt": "TextAsset",
    ".bytes": "TextAsset",
    ".csv": "TextAsset",
    # Video
    ".mp4": "VideoClip",
    ".mov": "VideoClip",
    ".avi": "VideoClip",
    # Physics
    ".physicMaterial": "PhysicMaterial",
    ".physicsMaterial2D": "PhysicsMaterial2D",
    # Misc Unity
    ".guiskin": "GUISkin",
    ".flare": "Flare",
    ".giparams": "LightmapParameters",
}

# Importer class name → type (from .meta files, secondary lookup)
IMPORTER_TO_TYPE: dict[str, str] = {
    "TextureImporter": "Texture2D",
    "ModelImporter": "Model",
    "AudioImporter": "AudioClip",
    "MonoImporter": "MonoScript",
    "ShaderImporter": "Shader",
    "NativeFormatImporter": "ScriptableObject",
    "DefaultImporter": "TextAsset",
    "VideoClipImporter": "VideoClip",
    "TrueTypeFontImporter": "Font",
    "SpeedTreeImporter": "SpeedTree",
    "SubstanceImporter": "ProceduralTexture",
    "PackageManifestImporter": "PackageManifest",
}

# ---------------------------------------------------------------------------
# .meta file parsing
# ---------------------------------------------------------------------------

def _read_meta(meta_path: Path) -> tuple[str | None, str | None, list[str]]:
    """Return (guid, importer_type, dependency_guids) from a .meta file."""
    try:
        text = meta_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, None, []

    guid_m = re.search(r"^guid:\s*(\w+)", text, re.MULTILINE)
    guid = guid_m.group(1) if guid_m else None

    # Importer class: look for lines like 'TextureImporter:'
    importer_m = re.search(r"^(\w+Importer):", text, re.MULTILINE)
    importer = importer_m.group(1) if importer_m else None

    # Dependencies: guids listed in externalObjects or fileIDToRecycleName or
    # dependencies block. Unity stores them as:  guid: <hex32>
    dep_guids = re.findall(r"\bguid:\s*([a-f0-9]{32})\b", text)
    # Exclude the asset's own guid
    own_guid = guid or ""
    dep_guids = [g for g in dep_guids if g != own_guid]

    return guid, importer, dep_guids


def _type_from_meta(meta_path: Path) -> str | None:
    _, importer, _ = _read_meta(meta_path)
    if importer:
        return IMPORTER_TO_TYPE.get(importer)
    return None


# ---------------------------------------------------------------------------
# Asset walking
# ---------------------------------------------------------------------------

def _classify(path: Path, meta_path: Path | None) -> str:
    ext = path.suffix.lower()
    if ext in EXT_TO_TYPE:
        return EXT_TO_TYPE[ext]
    if meta_path and meta_path.exists():
        t = _type_from_meta(meta_path)
        if t:
            return t
    return "Unknown"


def walk_assets(
    root: Path,
    include_graph: bool,
) -> tuple[list[dict], dict[str, int]]:
    """Walk the Assets directory. Returns (assets list, by_type counts)."""
    assets: list[dict] = []
    by_type: dict[str, int] = {}

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip hidden directories and Library/Temp/obj
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".") and d not in ("Library", "Temp", "obj", "Logs")
        ]
        for fname in filenames:
            fpath = Path(dirpath) / fname

            # Skip .meta files themselves and hidden files
            if fname.startswith(".") or fname.endswith(".meta"):
                continue

            meta_path = fpath.parent / (fname + ".meta")
            asset_type = _classify(fpath, meta_path if meta_path.exists() else None)

            try:
                byte_size = fpath.stat().st_size
            except OSError:
                byte_size = 0

            # GUID from .meta
            guid: str | None = None
            dep_guids: list[str] = []
            if meta_path.exists():
                guid, _, raw_deps = _read_meta(meta_path)
                if include_graph:
                    dep_guids = list(raw_deps)
                    # Also scan the asset body itself for guid references
                    # (Unity text assets embed dependency GUIDs inline, e.g. .mat, .unity)
                    _TEXT_EXTS = {
                        ".mat", ".unity", ".prefab", ".anim", ".controller",
                        ".asset", ".overrideController",
                    }
                    if fpath.suffix.lower() in _TEXT_EXTS:
                        try:
                            body_text = fpath.read_text(encoding="utf-8", errors="replace")
                            body_guids = re.findall(r"\bguid:\s*([a-f0-9]{32})\b", body_text)
                            own = guid or ""
                            for bg in body_guids:
                                if bg != own and bg not in dep_guids:
                                    dep_guids.append(bg)
                        except OSError:
                            pass

            entry: dict = {
                "bytes": byte_size,
                "guid": guid,
                "path": str(fpath),
                "type": asset_type,
            }
            if include_graph:
                entry["depends_on"] = dep_guids

            assets.append(entry)
            by_type[asset_type] = by_type.get(asset_type, 0) + 1

    return assets, by_type


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def _write_markdown(report_path: Path, result: dict) -> None:
    totals = result["totals"]
    lines = [
        f"# Unity Asset Audit: `{result['root']}`",
        "",
        f"**Total files:** {totals['files']}  ",
        f"**Total size:** {totals['bytes']:,} bytes ({totals['bytes'] / 1_048_576:.1f} MB)",
        "",
        "## By Type",
        "",
        "| Type | Count |",
        "|------|-------|",
    ]
    for t, count in sorted(totals["by_type"].items(), key=lambda x: -x[1]):
        lines.append(f"| {t} | {count} |")

    lines += [
        "",
        "## Top 20 Largest Assets",
        "",
        "| Path | Type | Size (bytes) |",
        "|------|------|-------------|",
    ]
    sorted_assets = sorted(result["assets"], key=lambda a: a["bytes"], reverse=True)
    for asset in sorted_assets[:20]:
        lines.append(f"| `{asset['path']}` | {asset['type']} | {asset['bytes']:,} |")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit a Unity Assets/ directory and emit JSON inventory."
    )
    parser.add_argument("assets_dir", help="Path to the Unity Assets/ directory")
    parser.add_argument("--out", help="Output JSON file (default: stdout)")
    parser.add_argument("--report", help="Optional Markdown summary file path")
    sort_group = parser.add_mutually_exclusive_group()
    sort_group.add_argument(
        "--by-type",
        action="store_true",
        default=False,
        help="Sort assets alphabetically by type then path",
    )
    sort_group.add_argument(
        "--by-size",
        action="store_true",
        default=False,
        help="Sort assets descending by file size",
    )
    parser.add_argument(
        "--graph",
        action="store_true",
        default=False,
        help="Include dependency GUID edges in JSON (reads every .meta; slower)",
    )
    args = parser.parse_args()

    root = Path(args.assets_dir)
    if not root.exists() or not root.is_dir():
        print(f"ERROR: Not a directory: {root}", file=sys.stderr)
        sys.exit(1)

    assets, by_type = walk_assets(root, args.graph)

    # Sorting
    if args.by_type:
        assets.sort(key=lambda a: (a["type"], a["path"]))
    elif args.by_size:
        assets.sort(key=lambda a: a["bytes"], reverse=True)

    total_bytes = sum(a["bytes"] for a in assets)

    result = {
        "assets": assets,
        "root": str(root),
        "totals": {
            "bytes": total_bytes,
            "by_type": by_type,
            "files": len(assets),
        },
    }

    output = json.dumps(result, indent=2, sort_keys=True)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"JSON written to {args.out}", file=sys.stderr)
    else:
        print(output)

    if args.report:
        _write_markdown(Path(args.report), result)
        print(f"Markdown report written to {args.report}", file=sys.stderr)


if __name__ == "__main__":
    main()
