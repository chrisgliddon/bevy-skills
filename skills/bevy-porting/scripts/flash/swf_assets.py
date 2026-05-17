#!/usr/bin/env python3
"""
Extract assets from a Flash .swf file and emit a JSON manifest.

Backs: references/flash-swf.md

Requires ffdec (JPEXS Free Flash Decompiler, Java 11+):
    https://github.com/jindrapetrik/jpexs-decompiler
ffdec must be on $PATH as 'ffdec', 'ffdec.sh', 'ffdec.bat', or 'ffdec.exe',
or supplied via --ffdec /path/to/ffdec.sh.

Usage:
    python3 swf_assets.py game.swf [--out /tmp/swf-assets/] \
        [--manifest manifest.json] [--ffdec /path/to/ffdec.sh] [--dry-run]

    # Safe smoke-test without ffdec installed (exits 0):
    python3 swf_assets.py game.swf --dry-run

Manifest format:
    {"swf": "game.swf", "out_dir": "...", "assets":
      {"images": [{"id":"42","path":"images/42.png","bytes":1234}],
       "sounds": [...], "scripts": [...], "shapes": [...], "fonts": [...]}}

Exit codes: 0 success, 1 bad args/file, 2 ffdec not found, 3 ffdec error.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

_FFDEC_CANDIDATES = ["ffdec", "ffdec.sh", "ffdec.bat", "ffdec.exe"]

_INSTALL_HINT = (
    "Install ffdec from https://github.com/jindrapetrik/jpexs-decompiler\n"
    "Ensure 'ffdec' (Linux/macOS: 'ffdec.sh') is on $PATH, "
    "or pass --ffdec /path/to/ffdec.sh."
)

# ffdec -export all creates subdirs; map subdir names → manifest keys.
_DIR_TO_KEY = {
    "images": "images", "image": "images", "bitmaps": "images",
    "sounds": "sounds", "sound": "sounds",
    "scripts": "scripts", "script": "scripts",
    "shapes": "shapes", "shape": "shapes",
    "fonts": "fonts", "font": "fonts",
}

_BINARY_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".mp3", ".wav", ".ogg", ".ttf", ".otf"}

# Extension → manifest key fallback (for subdirs not in _DIR_TO_KEY).
_EXT_TO_KEY = {
    ".png": "images", ".jpg": "images", ".jpeg": "images", ".gif": "images",
    ".mp3": "sounds", ".wav": "sounds", ".ogg": "sounds",
    ".as": "scripts",
    ".svg": "shapes",
    ".ttf": "fonts", ".otf": "fonts",
}


def _find_ffdec(override: str | None) -> str:
    """Return a usable ffdec path, or sys.exit(2)."""
    if override:
        found = str(Path(override)) if Path(override).exists() else shutil.which(override)
        if found:
            return found
        print(f"ERROR: --ffdec not found: {override}\n{_INSTALL_HINT}", file=sys.stderr)
        sys.exit(2)
    for name in _FFDEC_CANDIDATES:
        found = shutil.which(name)
        if found:
            return found
    print(f"ERROR: ffdec not found on $PATH.\n{_INSTALL_HINT}", file=sys.stderr)
    sys.exit(2)


def _build_manifest(swf_path: Path, out_dir: Path) -> dict:
    assets: dict[str, list] = {k: [] for k in ("images", "sounds", "scripts", "shapes", "fonts")}
    if not out_dir.exists():
        print(f"WARNING: output dir missing after extraction: {out_dir}", file=sys.stderr)
        return {"swf": swf_path.name, "out_dir": str(out_dir), "assets": assets}

    for child in sorted(out_dir.iterdir()):
        if not child.is_dir():
            continue
        # Determine manifest bucket for this subdir.
        key = _DIR_TO_KEY.get(child.name.lower())
        for f in sorted(child.rglob("*")):
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            bucket = key or _EXT_TO_KEY.get(ext)
            if bucket is None:
                continue
            entry: dict[str, object] = {"id": f.stem, "path": f.relative_to(out_dir).as_posix()}
            if ext in _BINARY_EXTS:
                try:
                    entry["bytes"] = f.stat().st_size
                except OSError:
                    pass
            assets[bucket].append(entry)

    return {"swf": swf_path.name, "out_dir": str(out_dir), "assets": assets}


def _run_extraction(ffdec_bin: str, swf_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [ffdec_bin, "-export", "all", str(out_dir), str(swf_path)]
    print(f"Running: {' '.join(cmd)}", file=sys.stderr)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as exc:
        print(f"ERROR: Failed to launch ffdec: {exc}", file=sys.stderr)
        sys.exit(3)
    if result.stdout:
        print(result.stdout, end="", file=sys.stderr)
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        print(f"ERROR: ffdec exited with code {result.returncode}", file=sys.stderr)
        sys.exit(3)


def _default_out(swf_path: Path, out_arg: str | None) -> Path:
    return Path(out_arg) if out_arg else swf_path.parent / (swf_path.stem + "-assets")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract assets from a Flash .swf and emit a JSON manifest.",
        epilog="Safe smoke-test (no ffdec needed): python3 swf_assets.py game.swf --dry-run",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("swf", help="Path to the .swf file.")
    parser.add_argument("--out", metavar="DIR", help="Output directory (default: <swf>-assets/).")
    parser.add_argument("--manifest", metavar="FILE", help="Write manifest JSON to FILE (default: stdout).")
    parser.add_argument("--ffdec", metavar="PATH", help="Explicit path to ffdec / ffdec.sh.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the ffdec command and exit 0 without running it.")
    args = parser.parse_args()

    swf_path = Path(args.swf)
    out_dir = _default_out(swf_path, args.out)

    if args.dry_run:
        import os, io, contextlib
        buf = io.StringIO()
        try:
            with contextlib.redirect_stderr(buf):
                ffdec_bin = _find_ffdec(args.ffdec)
        except SystemExit:
            # ffdec absent is fine in --dry-run; show a placeholder.
            ffdec_bin = args.ffdec or "<ffdec — install from https://github.com/jindrapetrik/jpexs-decompiler>"
        cmd = [ffdec_bin, "-export", "all", str(out_dir), str(swf_path)]
        print("DRY RUN — would execute:")
        print("  " + " ".join(cmd))
        sys.exit(0)

    if not swf_path.exists():
        print(f"ERROR: SWF file not found: {swf_path}", file=sys.stderr)
        sys.exit(1)
    if swf_path.suffix.lower() != ".swf":
        print(f"WARNING: file does not have .swf extension: {swf_path}", file=sys.stderr)

    ffdec_bin = _find_ffdec(args.ffdec)
    _run_extraction(ffdec_bin, swf_path, out_dir)

    manifest = _build_manifest(swf_path, out_dir)
    if sum(len(v) for v in manifest["assets"].values()) == 0:
        print(
            "WARNING: ffdec ran but produced no recognised assets. "
            "Check the SWF is not encrypted and ffdec supports its version.",
            file=sys.stderr,
        )

    output = json.dumps(manifest, indent=2, sort_keys=True)
    if args.manifest:
        Path(args.manifest).write_text(output, encoding="utf-8")
        print(f"Manifest written to {args.manifest}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
