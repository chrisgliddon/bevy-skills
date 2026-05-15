---
name: similarity-rs
description: Use when you suspect duplicate or near-duplicate Rust code — writing a utility function that might already exist, copy-paste-modifying a function, creating near-duplicate structs or enums, or running `similarity-rs 0.5` with flags like `--threshold`, `--cross-file`, or `--min-lines`. Also triggers on `cargo install similarity-rs`, reviewing CI duplication gates, or tuning false-positive thresholds.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "2"
  area: maintainability
  target_version: "similarity-rs 0.5"
---

# similarity-rs 0.5 — Rust duplication detection

**Tool status: Beta — not production-tested per the upstream README. Evaluate findings manually before acting.**

## When to use this skill

**Antipattern triggers (act before writing code):**
- About to write a utility function — grep the codebase first; it may already exist.
- Caught yourself thinking "I'll just inline this here."
- Planning to copy-paste-modify an existing function with small changes.
- Adding a new enum or struct that may overlap with an existing one.
- Two `Plugin` setups that share large blocks of boilerplate.
- Similar Bevy systems that differ only in their `Query` filter component.
- Repeated `commands.spawn((Mesh3d(...), MeshMaterial3d(...), ...))` patterns that belong in a `Bundle`.

**Tool-integration triggers (run the check):**
- Before committing: verify you haven't introduced cross-file duplication.
- During a cleanup sprint: identify consolidation candidates.
- Setting up a pre-commit hook or GitHub Actions gate.
- Adjusting `-t`/`--threshold` or `--min-lines` for a noisy or too-quiet run.

## Canonical workflow

The pattern is: **search first → write minimally → run the check.**

```bash
# 1. Search before writing — check whether the helper already exists
rg "fn <verb>"               # e.g., rg "fn normalize" to find existing helpers
cargo doc --open --package <dep>  # inventory what your deps already provide

# 2. Write only what's missing.

# 3. Before committing, check for accidental duplication
cargo install similarity-rs   # one-time install
similarity-rs ./src            # scan the src tree

# 4. If --cross-file output is needed (catches LLM's most common antipattern)
similarity-rs --cross-file ./src

# 5. Tighten or loosen if needed (see references/tuning.md)
similarity-rs -t 0.85 -m 5 --cross-file --skip-test ./src
```

Consult `cargo doc --open` for every dependency before reaching for a one-off helper. LLMs reproduce functions from stdlib, `itertools`, or an already-declared crate dep more often than from thin air.

## Topics

| Topic | Reference |
|---|---|
| LLM duplication patterns with before/after examples | [references/antipatterns.md](references/antipatterns.md) |
| Search-before-write workflow (rg, cargo doc, CLAUDE.md scan) | [references/search-before-write.md](references/search-before-write.md) |
| Pre-commit hook and GitHub Actions CI recipes | [references/ci-integration.md](references/ci-integration.md) |
| `-t`, `--min-lines`, `--cross-file`, `--no-size-penalty` knobs | [references/tuning.md](references/tuning.md) |
| When similar code is intentional — don't act on these | [references/false-positives.md](references/false-positives.md) |
| `similarity-ts`, `similarity-py`, `similarity-generic` for polyglot repos | [references/sibling-tools.md](references/sibling-tools.md) |

## Gotchas

1. **`--cross-file` is off by default.** Without it, only within-file pairs are reported. Most LLM-introduced duplication is across files. Always pass `--cross-file` unless you specifically want within-file only.

2. **Beta tool.** The upstream README marks `similarity-rs` as not production-tested. Treat output as signal, not verdict. Review each flagged pair before refactoring.

3. **`--skip-test` on CI.** Test files often contain structurally similar setup fixtures by design. Run with `--skip-test` on CI to suppress expected test-fixture symmetry; review test duplication locally.

4. **Threshold tuning is project-specific.** The default `-t 0.85` catches obvious copy-paste. Use 0.75–0.80 during a cleanup sprint (more hits), 0.90–0.95 for production gating (fewer false alarms). See [references/tuning.md](references/tuning.md).

5. **No tester snippet for this skill.** `similarity-rs` is a CLI-only tool with no library API — there is no `cargo check` example to validate. This follows the same approach as `bevy-cargo-features` and `bevy-migration-0-17-to-0-18`, which also carry no tester examples.

## See also

- `bevy-cargo-features` — installing `similarity-rs` via `cargo install` sits alongside the `Cargo.toml` feature story; also covers `default-features` decisions that can hide accidental dep duplication.
- `bevy-core-concepts` — duplicate `Plugin` setup and schedule boilerplate is the most common Bevy-specific antipattern this tool catches.
- `bevy-ecs-components` — near-duplicate component structs and overlapping enums often surface when features are added without consolidation.
