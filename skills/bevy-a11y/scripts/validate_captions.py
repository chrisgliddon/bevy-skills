#!/usr/bin/env python3
"""Validate WebVTT/SRT structure, readability policy, and locale cue alignment."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


TIMING_RE = re.compile(r"^\s*(\S+)\s+-->\s+(\S+)(?:\s+.*)?$")
STAMP_RE = re.compile(r"^(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})$")
TAG_RE = re.compile(r"<[^>]*>")


@dataclass
class Cue:
    start: float
    end: float
    lines: list[str]
    source_line: int


def timestamp(value: str) -> float:
    match = STAMP_RE.fullmatch(value)
    if not match:
        raise ValueError(f"invalid timestamp {value!r}")
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    millis = int(match.group(4))
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f"out-of-range timestamp {value!r}")
    return hours * 3600 + minutes * 60 + seconds + millis / 1000.0


def blocks(text: str) -> list[tuple[int, list[str]]]:
    output: list[tuple[int, list[str]]] = []
    current: list[str] = []
    start = 1
    for number, line in enumerate(text.replace("\r\n", "\n").replace("\r", "\n").split("\n"), 1):
        if line.strip():
            if not current:
                start = number
            current.append(line)
        elif current:
            output.append((start, current))
            current = []
    if current:
        output.append((start, current))
    return output


def parse(path: Path) -> list[Cue]:
    text = path.read_text(encoding="utf-8-sig")
    sections = blocks(text)
    is_vtt = path.suffix.lower() == ".vtt" or text.lstrip().startswith("WEBVTT")
    cues: list[Cue] = []
    for start_line, lines in sections:
        if is_vtt and lines[0].startswith("WEBVTT"):
            continue
        if is_vtt and lines[0].split(maxsplit=1)[0] in {"NOTE", "STYLE", "REGION"}:
            continue
        timing_index = next((i for i, line in enumerate(lines[:2]) if "-->" in line), None)
        if timing_index is None:
            if not is_vtt and lines[0].isdigit():
                raise ValueError(f"{path}:{start_line}: numbered cue is missing timing line")
            raise ValueError(f"{path}:{start_line}: cue is missing timing line")
        match = TIMING_RE.fullmatch(lines[timing_index])
        if not match:
            raise ValueError(f"{path}:{start_line + timing_index}: malformed timing line")
        start = timestamp(match.group(1))
        end = timestamp(match.group(2))
        cue_lines = lines[timing_index + 1 :]
        cues.append(Cue(start, end, cue_lines, start_line))
    if not cues:
        raise ValueError(f"{path}: no cues found")
    return cues


def plain(lines: list[str]) -> str:
    return " ".join(
        part for part in (html.unescape(TAG_RE.sub("", line)).strip() for line in lines) if part
    )


def inspect_file(
    path: Path,
    cues: list[Cue],
    max_cps: float,
    max_chars_per_line: int,
    max_lines: int,
    min_duration: float,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    previous: Cue | None = None
    for index, cue in enumerate(cues, 1):
        prefix = {"file": str(path), "cue": index, "line": cue.source_line}
        duration = cue.end - cue.start
        if duration <= 0:
            findings.append({**prefix, "level": "error", "code": "duration", "message": "end must be after start"})
            continue
        if previous and cue.start < previous.start:
            findings.append({**prefix, "level": "error", "code": "order", "message": "cue starts before previous cue"})
        if previous and cue.start < previous.end:
            findings.append({**prefix, "level": "warning", "code": "overlap", "message": "cue overlaps previous cue; verify intentional placement"})
        if duration < min_duration:
            findings.append({**prefix, "level": "warning", "code": "short", "message": f"duration {duration:.3f}s is below policy {min_duration:.3f}s"})
        if not cue.lines or not plain(cue.lines):
            findings.append({**prefix, "level": "error", "code": "empty", "message": "cue has no readable text"})
        if len(cue.lines) > max_lines:
            findings.append({**prefix, "level": "warning", "code": "lines", "message": f"{len(cue.lines)} lines exceeds policy {max_lines}"})
        for line_number, line in enumerate(cue.lines, 1):
            visible = html.unescape(TAG_RE.sub("", line))
            if len(visible) > max_chars_per_line:
                findings.append({**prefix, "level": "warning", "code": "line-length", "message": f"line {line_number} has {len(visible)} characters (policy {max_chars_per_line})"})
        characters = len(plain(cue.lines))
        cps = characters / duration
        if cps > max_cps:
            findings.append({**prefix, "level": "warning", "code": "reading-speed", "message": f"{cps:.1f} characters/s exceeds policy {max_cps:.1f}"})
        previous = cue
    return findings


def alignment(reference_path: Path, reference: list[Cue], path: Path, cues: list[Cue], tolerance: float) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    if len(reference) != len(cues):
        findings.append({"file": str(path), "cue": None, "line": None, "level": "error", "code": "cue-count", "message": f"{len(cues)} cues; reference {reference_path} has {len(reference)}"})
    for index, (expected, actual) in enumerate(zip(reference, cues), 1):
        delta = max(abs(expected.start - actual.start), abs(expected.end - actual.end))
        if delta > tolerance:
            findings.append({"file": str(path), "cue": index, "line": actual.source_line, "level": "warning", "code": "timing-alignment", "message": f"timing differs from {reference_path} by up to {delta:.3f}s (tolerance {tolerance:.3f}s)"})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captions", nargs="+", type=Path, help="VTT/SRT files; first is timing reference")
    parser.add_argument("--max-cps", type=float, default=20.0)
    parser.add_argument("--max-chars-per-line", type=int, default=42)
    parser.add_argument("--max-lines", type=int, default=2)
    parser.add_argument("--min-duration", type=float, default=0.833)
    parser.add_argument("--timing-tolerance", type=float, default=0.050)
    parser.add_argument("--no-sync-check", action="store_true")
    parser.add_argument("--strict", action="store_true", help="fail on policy warnings")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.max_cps <= 0 or args.max_chars_per_line <= 0 or args.max_lines <= 0 or args.min_duration < 0 or args.timing_tolerance < 0:
        parser.error("limits must be positive (duration/tolerance may be zero)")

    parsed: list[tuple[Path, list[Cue]]] = []
    findings: list[dict[str, object]] = []
    for path in args.captions:
        try:
            cues = parse(path)
        except (OSError, UnicodeError, ValueError) as error:
            findings.append({"file": str(path), "cue": None, "line": None, "level": "error", "code": "parse", "message": str(error)})
            continue
        parsed.append((path, cues))
        findings.extend(inspect_file(path, cues, args.max_cps, args.max_chars_per_line, args.max_lines, args.min_duration))

    if not args.no_sync_check and len(parsed) > 1:
        reference_path, reference = parsed[0]
        for path, cues in parsed[1:]:
            findings.extend(alignment(reference_path, reference, path, cues, args.timing_tolerance))

    if args.json:
        print(json.dumps({"files": [str(path) for path in args.captions], "findings": findings}, indent=2))
    else:
        for finding in findings:
            location = finding["file"]
            if finding["line"] is not None:
                location += f":{finding['line']}"
            print(f"{str(finding['level']).upper()} {finding['code']} {location}: {finding['message']}")
        if not findings:
            print(f"OK: {len(parsed)} caption file(s) passed")

    has_errors = any(item["level"] == "error" for item in findings)
    has_warnings = any(item["level"] == "warning" for item in findings)
    return 1 if has_errors or (args.strict and has_warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
