#!/usr/bin/env python3
"""Audit Bevy/Rapier Cargo features for common renderer-profile mistakes."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any


def dependency(table: dict[str, Any], name: str) -> Any:
    value = table.get(name)
    if value is not None:
        return value
    for target in table.get("target", {}).values():
        value = target.get("dependencies", {}).get(name)
        if value is not None:
            return value
    return None


def details(value: Any) -> tuple[bool, set[str], bool]:
    """Return (present, features, default_features_enabled)."""
    if value is None:
        return False, set(), False
    if isinstance(value, str):
        return True, set(), True
    if not isinstance(value, dict):
        return True, set(), True
    features = {str(item) for item in value.get("features", [])}
    defaults = bool(value.get("default-features", True))
    return True, features, defaults


def declared_minor(value: Any) -> tuple[int, int] | None:
    """Recognize only simple registry requirements confined to a 0.x minor.

    This is not a Cargo resolver. Ranges, prereleases, workspace inheritance,
    git/path sources and renamed dependencies need resolved Cargo metadata.
    """
    if isinstance(value, dict):
        if any(key in value for key in ("workspace", "git", "path", "package")):
            return None
        value = value.get("version")
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"[\^~=]?\s*0\.([1-9][0-9]*)(?:\.[0-9]+)?", value.strip())
    return (0, int(match.group(1))) if match else None


def declaration_scopes(data: dict[str, Any], name: str) -> list[str]:
    """Locate direct declarations without combining Cargo dependency scopes."""
    kinds = ("dependencies", "dev-dependencies", "build-dependencies")
    scopes = [kind for kind in kinds if name in data.get(kind, {})]
    for target, tables in data.get("target", {}).items():
        scopes.extend(
            f"target.{target}.{kind}" for kind in kinds if name in tables.get(kind, {})
        )
    return scopes


def audit(manifest: Path) -> dict[str, Any]:
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    deps: dict[str, Any] = {}
    deps.update(data.get("dependencies", {}))
    deps.update(data.get("dev-dependencies", {}))
    deps.update(data.get("build-dependencies", {}))
    deps["target"] = data.get("target", {})

    bevy = dependency(deps, "bevy")
    rapier = dependency(deps, "bevy_rapier3d")
    bevy_present, bevy_features, bevy_defaults = details(bevy)
    rapier_present, rapier_features, rapier_defaults = details(rapier)
    errors: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    if not bevy_present:
        errors.append("No direct `bevy` dependency was found (workspace inheritance is not expanded).")
    else:
        if bevy_defaults and bevy_features:
            warnings.append(
                "Bevy default features remain enabled; explicit profile features do not trim them."
            )
        if {"webgl2", "webgpu"} <= bevy_features:
            warnings.append("Both web backends are enabled; Bevy's `webgpu` feature overrides `webgl2`.")
        api_only = {"2d_api", "3d_api", "ui_api"} & bevy_features
        builtin = {"2d_bevy_render", "3d_bevy_render", "ui_bevy_render", "2d", "3d", "ui"} & bevy_features
        if api_only and not builtin and not bevy_defaults:
            notes.append("API-only profile detected: the application must supply an external/custom renderer.")
        if not bevy_defaults and "3d" in bevy_features and "ui" not in bevy_features:
            notes.append("`3d` no longer implies `ui`; this is correct only if the game intentionally has no Bevy UI.")
        if not bevy_defaults and ({"2d", "3d", "ui"} & bevy_features) and "audio" not in bevy_features:
            notes.append("Rendering profiles no longer imply `audio`; this is correct only if audio is intentionally absent or external.")

    if rapier_present:
        rapier_minor = declared_minor(rapier)
        bevy_minor = declared_minor(bevy)
        bevy_scopes = declaration_scopes(data, "bevy")
        rapier_scopes = declaration_scopes(data, "bevy_rapier3d")
        unambiguous_pair = len(bevy_scopes) == 1 and bevy_scopes == rapier_scopes
        if bevy_present and not unambiguous_pair:
            warnings.append(
                "Bevy/Rapier version pairing is ambiguous across dependency scopes; "
                "compatibility was not checked. Inspect resolved Cargo metadata for "
                "the intended target and dependency kind."
            )
        matching_bevy = {(0, 36): (0, 19), (0, 37): (0, 20)}
        if rapier_minor not in matching_bevy:
            warnings.append(
                "Rapier version-specific checks cover only simple registry requirements "
                "for 0.36 and 0.37; verify the resolved version/features with Cargo metadata."
            )
        elif unambiguous_pair and bevy_minor is not None and bevy_minor != matching_bevy[rapier_minor]:
            expected = matching_bevy[rapier_minor][1]
            errors.append(
                f"`bevy_rapier3d` 0.{rapier_minor[1]} requires Bevy 0.{expected}, "
                f"but the manifest declares Bevy 0.{bevy_minor[1]}."
            )
        if rapier_defaults and bevy_present and not bevy_defaults:
            warnings.append(
                "Rapier defaults enable Bevy debug rendering/picking/mesh helpers and may defeat a headless or external-renderer profile."
            )
        if not rapier_defaults and "dim3" not in rapier_features:
            errors.append("`bevy_rapier3d` with defaults disabled must enable its `dim3` feature.")
        if "headless" in rapier_features:
            if rapier_minor == (0, 37):
                errors.append(
                    "`bevy_rapier3d` 0.37 removed the `headless` feature; disable defaults "
                    "and enable `dim3` for a renderer-independent build."
                )
            elif rapier_minor == (0, 36):
                notes.append(
                    "Rapier 0.36's `headless` feature is an unused legacy marker; "
                    "disabling default features removes renderer-facing helpers."
                )
            else:
                warnings.append(
                    "Cannot validate `headless` for this Rapier requirement; it was "
                    "removed in 0.37. Check the resolved crate's feature list."
                )

    return {
        "manifest": str(manifest),
        "errors": errors,
        "warnings": warnings,
        "notes": notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Path to Cargo.toml")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    try:
        result = audit(args.manifest)
    except (OSError, tomllib.TOMLDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Renderer feature audit: {result['manifest']}")
        for level in ("errors", "warnings", "notes"):
            for message in result[level]:
                print(f"{level[:-1].upper()}: {message}")
        if not any(result[level] for level in ("errors", "warnings", "notes")):
            print("OK: no common renderer-profile mistakes found")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
