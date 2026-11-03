#!/usr/bin/env python3
"""Check static colour pairs against WCAG 2.2 contrast thresholds."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


HEX_RE = re.compile(r"^#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def parse_hex(value: str) -> tuple[float, float, float, float]:
    match = HEX_RE.fullmatch(value)
    if not match:
        raise ValueError(f"invalid colour {value!r}; use #RGB[A] or #RRGGBB[AA]")
    raw = match.group(1)
    if len(raw) in {3, 4}:
        raw = "".join(char * 2 for char in raw)
    if len(raw) == 6:
        raw += "FF"
    return tuple(int(raw[index : index + 2], 16) / 255.0 for index in range(0, 8, 2))  # type: ignore[return-value]


def composite(
    foreground: tuple[float, float, float, float],
    background: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    fr, fg, fb, fa = foreground
    br, bg, bb, ba = background
    alpha = fa + ba * (1.0 - fa)
    if alpha == 0.0:
        return 0.0, 0.0, 0.0, 0.0
    return (
        (fr * fa + br * ba * (1.0 - fa)) / alpha,
        (fg * fa + bg * ba * (1.0 - fa)) / alpha,
        (fb * fa + bb * ba * (1.0 - fa)) / alpha,
        alpha,
    )


def linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def luminance(colour: tuple[float, float, float, float]) -> float:
    red, green, blue, _ = colour
    return 0.2126 * linear(red) + 0.7152 * linear(green) + 0.0722 * linear(blue)


def contrast(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> float:
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def threshold(pair: dict[str, Any]) -> float:
    if "minimum_ratio" in pair:
        value = float(pair["minimum_ratio"])
        if value < 1.0 or value > 21.0:
            raise ValueError("minimum_ratio must be in 1..=21")
        return value
    kind = pair.get("kind", "text")
    if kind == "non_text":
        return 3.0
    if kind != "text":
        raise ValueError("kind must be 'text' or 'non_text'")
    large = bool(pair.get("large_text", False))
    target = str(pair.get("target", "AAA")).upper()
    if target == "AAA":
        return 4.5 if large else 7.0
    if target == "AA":
        return 3.0 if large else 4.5
    raise ValueError("target must be AA or AAA")


def audit(data: Any) -> tuple[list[dict[str, Any]], list[str]]:
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    if not isinstance(data, dict) or not isinstance(data.get("pairs"), list):
        return [], ["manifest must be an object with a 'pairs' array"]
    if not data["pairs"]:
        return [], ["'pairs' must not be empty"]

    for index, pair in enumerate(data["pairs"]):
        path = f"pairs[{index}]"
        if not isinstance(pair, dict):
            errors.append(f"{path}: must be an object")
            continue
        pair_id = pair.get("id", path)
        try:
            foreground = parse_hex(str(pair["foreground"]))
            background = parse_hex(str(pair["background"]))
            canvas_value = pair.get("canvas")
            if background[3] < 1.0:
                if canvas_value is None:
                    raise ValueError("translucent background requires an opaque 'canvas' colour")
                background = composite(background, parse_hex(str(canvas_value)))
            if background[3] < 1.0:
                raise ValueError("resolved background must be opaque")
            resolved_foreground = composite(foreground, background)
            minimum = threshold(pair)
            ratio = contrast(resolved_foreground, background)
            results.append(
                {
                    "id": pair_id,
                    "ratio": round(ratio, 3),
                    "minimum": minimum,
                    "passed": ratio + 1e-9 >= minimum,
                }
            )
        except (KeyError, TypeError, ValueError) as error:
            errors.append(f"{path} ({pair_id}): {error}")
    return results, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="require explicit ids and target/kind metadata in addition to ratio checks",
    )
    args = parser.parse_args()

    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    results, errors = audit(data)
    if args.strict and isinstance(data, dict):
        for index, pair in enumerate(data.get("pairs", [])):
            if isinstance(pair, dict) and "id" not in pair:
                errors.append(f"pairs[{index}]: strict mode requires a stable id")
            if isinstance(pair, dict) and "kind" not in pair:
                errors.append(f"pairs[{index}]: strict mode requires kind='text' or 'non_text'")
            if isinstance(pair, dict) and pair.get("kind", "text") == "text" and "target" not in pair:
                errors.append(f"pairs[{index}]: strict text pairs require target='AA' or 'AAA'")

    failed = [result for result in results if not result["passed"]]
    if args.json:
        print(json.dumps({"manifest": str(args.manifest), "results": results, "errors": errors}, indent=2))
    else:
        for result in results:
            status = "PASS" if result["passed"] else "FAIL"
            print(f"{status} {result['id']}: {result['ratio']:.3f}:1 (minimum {result['minimum']:.1f}:1)")
        for error in errors:
            print(f"ERROR: {error}")
    return 1 if errors or failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
