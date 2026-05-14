#!/usr/bin/env python3
"""Lint SKILL.md frontmatter against the Anthropic + OpenCode Agent Skills specs.

Rules enforced (see CLAUDE.md "Hard rules"):
  - Frontmatter delimited by --- / --- at top of file.
  - Allowed keys: name, description, license, compatibility, metadata.
  - `name` matches ^[a-z0-9]+(-[a-z0-9]+)*$ (OpenCode regex), 1-64 chars,
    and equals the parent directory's name.
  - `description` is 1-1024 chars and contains the literal "Bevy 0.18".
  - `metadata` (if present) is a mapping of simple key: value lines.

Usage:
  python3 scripts/lint-skills.py                  # lint all skills/**/SKILL.md
  python3 scripts/lint-skills.py path/to/SKILL.md # lint one file
  python3 scripts/lint-skills.py --strict         # treat warnings as errors

Exit codes: 0 clean, 1 errors found, 2 invocation error.

No external dependencies — stdlib only, so CI can run it without pip install.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata"}
REQUIRED_KEYS = {"name", "description"}
MAX_NAME_LEN = 64
MAX_DESCRIPTION_LEN = 1024
REQUIRED_VERSION_TOKEN = "Bevy 0.18"


@dataclass
class LintResult:
    path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def parse_frontmatter(text: str) -> tuple[dict[str, object], list[str]]:
    """Minimal YAML-ish parser for our constrained frontmatter.

    Returns (parsed_dict, errors). Tolerates the small subset we use:
    scalar values, comma-separated strings, and one level of nested mapping.
    Anything fancier is a lint error — skills should not need it.
    """
    errors: list[str] = []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        errors.append("frontmatter must start with `---` on the first line")
        return {}, errors

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        errors.append("frontmatter missing closing `---`")
        return {}, errors

    body = lines[1:end]
    result: dict[str, object] = {}
    current_key: str | None = None
    nested: dict[str, str] = {}

    for n, raw in enumerate(body, start=2):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # Nested mapping line (2-space indented "key: value")
        if line.startswith("  ") and current_key is not None:
            sub = line.strip()
            if ":" not in sub:
                errors.append(f"line {n}: nested entry without colon: {sub!r}")
                continue
            k, _, v = sub.partition(":")
            nested[k.strip()] = v.strip().strip('"').strip("'")
            continue
        # Top-level key
        if ":" not in line:
            errors.append(f"line {n}: top-level entry without colon: {line!r}")
            continue
        # Flush any pending nested block into result
        if current_key is not None and nested:
            result[current_key] = nested
            nested = {}
        k, _, v = line.partition(":")
        key = k.strip()
        val = v.strip()
        if not val:
            # Start of a nested block
            current_key = key
            nested = {}
            continue
        result[key] = val.strip('"').strip("'")
        current_key = None
    if current_key is not None and nested:
        result[current_key] = nested
    return result, errors


def lint_file(path: Path) -> LintResult:
    res = LintResult(path=path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        res.errors.append(f"could not read file: {e}")
        return res

    fm, parse_errs = parse_frontmatter(text)
    res.errors.extend(parse_errs)
    if not fm:
        return res

    # Keys
    extra = set(fm.keys()) - ALLOWED_KEYS
    if extra:
        res.errors.append(f"unknown frontmatter keys: {sorted(extra)}")
    missing = REQUIRED_KEYS - set(fm.keys())
    if missing:
        res.errors.append(f"missing required keys: {sorted(missing)}")

    # name
    name = fm.get("name")
    if isinstance(name, str):
        if not NAME_RE.match(name):
            res.errors.append(
                f"name {name!r} must match ^[a-z0-9]+(-[a-z0-9]+)*$ "
                "(OpenCode spec)"
            )
        if len(name) > MAX_NAME_LEN:
            res.errors.append(f"name length {len(name)} > {MAX_NAME_LEN}")
        parent = path.parent.name
        if name != parent:
            res.errors.append(
                f"name {name!r} does not match directory {parent!r}"
            )

    # description
    desc = fm.get("description")
    if isinstance(desc, str):
        if not (1 <= len(desc) <= MAX_DESCRIPTION_LEN):
            res.errors.append(
                f"description length {len(desc)} outside 1..{MAX_DESCRIPTION_LEN}"
            )
        if REQUIRED_VERSION_TOKEN not in desc:
            res.errors.append(
                f"description must contain literal {REQUIRED_VERSION_TOKEN!r} "
                "(version-pinning rule)"
            )
        if desc.lower().startswith("use this skill"):
            res.warnings.append(
                "description starts with 'Use this skill' — prefer 'Use when ...'"
            )

    # metadata (optional; if present must be a dict)
    md = fm.get("metadata")
    if md is not None and not isinstance(md, dict):
        res.errors.append("metadata must be a nested mapping")

    return res


def find_skills(root: Path) -> list[Path]:
    return sorted(root.glob("skills/*/SKILL.md"))


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    strict = "--strict" in flags

    repo_root = Path(__file__).resolve().parents[1]
    if args:
        files = [Path(a).resolve() for a in args]
    else:
        files = find_skills(repo_root)

    if not files:
        print("no SKILL.md files found", file=sys.stderr)
        return 0

    failed = 0
    for f in files:
        res = lint_file(f)
        rel = f.relative_to(repo_root) if f.is_relative_to(repo_root) else f
        if res.errors:
            failed += 1
            print(f"FAIL {rel}")
            for e in res.errors:
                print(f"  - {e}")
        elif res.warnings and strict:
            failed += 1
            print(f"WARN→FAIL {rel} (strict mode)")
            for w in res.warnings:
                print(f"  - {w}")
        elif res.warnings:
            print(f"WARN {rel}")
            for w in res.warnings:
                print(f"  - {w}")
        else:
            print(f"OK   {rel}")

    print()
    print(f"{len(files)} file(s) checked, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
