#!/usr/bin/env python3
"""
ue5_python_export.py — Drop into <UEProject>/Content/Python/ and run from the UE5 editor.

Backing reference: references/unreal.md

WARNING: Requires UE5 — runs inside the Unreal Engine 5 editor Python console.
         NOT a headless extractor. This script does nothing outside the editor.

Invocation (from UE5 Output Log Python REPL):
    py ue5_python_export.py
    py ue5_python_export.py --out /tmp/ue5_export.json
    py ue5_python_export.py --actors-only
    py ue5_python_export.py --assets-only --out /tmp/assets.json

Output JSON shape:
    {
      "project_name": "MyGame",
      "actors": [
        {
          "name": "BP_PlayerStart_0",
          "class": "PlayerStart",
          "location": [0.0, 0.0, 0.0],
          "rotation": [0.0, 0.0, 0.0],
          "scale":    [1.0, 1.0, 1.0],
          "asset_paths": ["/Game/Characters/BP_Player.uasset"]
        }
      ],
      "assets": [
        {
          "name": "SM_RockLarge",
          "class": "StaticMesh",
          "package_path": "/Game/Environment/SM_RockLarge",
          "size_bytes": 204800
        }
      ]
    }

The output file is written to the path given by --out (default: ue5_export.json
in the project Saved/ directory, resolved at runtime via unreal.Paths).

Exit codes: 0 = success, 1 = no unreal module / runtime error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# UE5 editor-only imports — wrapped so the script still parses outside UE5
# ---------------------------------------------------------------------------
try:
    import unreal  # type: ignore[import]

    HAVE_UNREAL = True
except ImportError:
    HAVE_UNREAL = False
    print(
        "ERROR: this script must be run inside Unreal Engine 5's editor Python console.",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# Actor extraction (requires HAVE_UNREAL)
# ---------------------------------------------------------------------------

def _vector_to_list(vec) -> list[float]:
    """Convert an unreal.Vector to [x, y, z]."""
    return [vec.x, vec.y, vec.z]


def _rotator_to_list(rot) -> list[float]:
    """Convert an unreal.Rotator to [pitch, yaw, roll]."""
    return [rot.pitch, rot.yaw, rot.roll]


def _collect_actors() -> list[dict]:
    """Walk all actors in the currently loaded level and return a list of dicts."""
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    results: list[dict] = []
    for actor in actors:
        if actor is None:
            continue

        name = actor.get_actor_label()
        class_name = actor.get_class().get_name()

        transform = actor.get_actor_transform()
        location = _vector_to_list(transform.translation)
        rotation = _rotator_to_list(transform.rotation.rotator())
        scale = _vector_to_list(transform.scale3d)

        # Gather soft object references this actor holds (best-effort)
        asset_paths: list[str] = []
        try:
            for prop_name in ("StaticMesh", "SkeletalMesh", "Mesh"):
                prop = actor.get_editor_property(prop_name)  # type: ignore[arg-type]
                if prop is not None:
                    path = prop.get_path_name()
                    if path:
                        asset_paths.append(path)
        except Exception:  # noqa: BLE001 — property may not exist on all actors
            pass

        results.append(
            {
                "name": name,
                "class": class_name,
                "location": location,
                "rotation": rotation,
                "scale": scale,
                "asset_paths": asset_paths,
            }
        )
    return results


# ---------------------------------------------------------------------------
# Asset inventory (requires HAVE_UNREAL)
# ---------------------------------------------------------------------------

def _collect_assets() -> list[dict]:
    """Walk all assets under /Game/ and return a list of dicts."""
    asset_paths = unreal.EditorAssetLibrary.list_assets(
        "/Game/", recursive=True, include_folder=False
    )
    results: list[dict] = []
    registry = unreal.AssetRegistryHelpers.get_asset_registry()

    for package_path in asset_paths:
        # list_assets returns package paths like /Game/Foo/Bar.Bar
        asset_data = registry.get_asset_by_object_path(package_path)
        if not asset_data.is_valid():
            # Fall back to loading minimal metadata
            results.append(
                {
                    "name": package_path.split("/")[-1].split(".")[0],
                    "class": "Unknown",
                    "package_path": package_path,
                    "size_bytes": -1,
                }
            )
            continue

        name = str(asset_data.asset_name)
        class_name = str(asset_data.asset_class_path.asset_name)
        pkg = str(asset_data.package_name)

        # Size is not always available without loading the asset; use -1 as sentinel
        size_bytes: int = -1
        try:
            size_bytes = int(asset_data.get_tag_value("ApproxSize") or -1)
        except (TypeError, ValueError):
            pass

        results.append(
            {
                "name": name,
                "class": class_name,
                "package_path": pkg,
                "size_bytes": size_bytes,
            }
        )
    return results


# ---------------------------------------------------------------------------
# Output path resolution (requires HAVE_UNREAL)
# ---------------------------------------------------------------------------

def _default_out_path() -> str:
    """Return <ProjectSaved>/ue5_export.json using unreal.Paths."""
    saved_dir = unreal.Paths.project_saved_dir()
    return str(Path(saved_dir) / "ue5_export.json")


def _project_name() -> str:
    """Return the project name from unreal.SystemLibrary."""
    try:
        return unreal.SystemLibrary.get_game_name()
    except Exception:  # noqa: BLE001
        return "UnknownProject"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export UE5 level actor and asset metadata to JSON. "
            "Must be run from the Unreal Engine 5 editor Python console."
        )
    )
    parser.add_argument(
        "--out",
        default=None,
        help=(
            "Output JSON file path. "
            "Default: <ProjectSaved>/ue5_export.json (resolved at runtime via unreal.Paths)."
        ),
    )
    parser.add_argument(
        "--actors-only",
        action="store_true",
        dest="actors_only",
        help="Export actors only; skip asset inventory.",
    )
    parser.add_argument(
        "--assets-only",
        action="store_true",
        dest="assets_only",
        help="Export asset inventory only; skip actor walk.",
    )

    # UE5's Python REPL may pass extra args; ignore unknowns
    args, _ = parser.parse_known_args()

    if not HAVE_UNREAL:
        return 1

    payload: dict = {"project_name": _project_name()}

    if not args.assets_only:
        print("Collecting actors...", file=sys.stderr)
        payload["actors"] = _collect_actors()
        print(f"  {len(payload['actors'])} actors found.", file=sys.stderr)
    else:
        payload["actors"] = []

    if not args.actors_only:
        print("Collecting assets under /Game/...", file=sys.stderr)
        payload["assets"] = _collect_assets()
        print(f"  {len(payload['assets'])} assets found.", file=sys.stderr)
    else:
        payload["assets"] = []

    out_path = args.out if args.out else _default_out_path()
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Written to {out_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
