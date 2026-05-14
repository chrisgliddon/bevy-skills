# similarity-rs 0.5 — Threshold and Flag Tuning

Choosing the right flags determines whether the tool is a useful signal or
noise. Start with the defaults and adjust based on what the report shows.

---

## `-t` / `--threshold` (default: 0.85)

The similarity score below which pairs are not reported. Range: 0.0–1.0.

| Threshold | Effect | When to use |
|---|---|---|
| 0.75–0.80 | Broad: catches near-paraphrases. More false positives. | Cleanup sprints where you want every consolidation candidate. |
| **0.85** | **Default. Catches obvious copy-paste and copy-paste-modify.** | **Day-to-day development gate.** |
| 0.90–0.95 | Strict: only near-identical code. Very few false positives. | Production CI gate; graduate to this after a cleanup sprint. |
| 0.98+ | Catches verbatim duplicates only. | Rarely useful — `rg` finds exact duplication faster. |

```bash
# Loose scan during a cleanup sprint
similarity-rs -t 0.78 --cross-file ./src

# Production gate
similarity-rs -t 0.92 --cross-file --skip-test -m 5 ./src
```

---

## `-m` / `--min-lines` (default varies; typically 3–5)

Ignore pairs where either function is shorter than this many lines.

- **3** (or default): Includes trivial one-liners and two-line helpers. Noisy.
- **5**: Filters most trivial helpers — good general default.
- **10+**: Focus only on substantial duplication. Use when fixing a specific
  class of duplicated algorithms.

```bash
similarity-rs -m 8 --cross-file ./src   # only 8-line+ functions
```

---

## `--min-tokens`

Similar to `--min-lines` but counts tokens instead of lines. Useful for very
compact Rust style where meaningful functions can be short by line count.

```bash
similarity-rs --min-tokens 50 --cross-file ./src
```

The exact default `--min-tokens` value isn't documented in the v0.5 release notes; run `similarity-rs --help` against the version you've installed to confirm.

---

## `--cross-file` / `-c` (default: off)

**This is the most important flag for catching LLM antipatterns.**

Without it, only pairs within the same file are reported. Most LLM-introduced
duplication is across files — `utils.rs` vs `rendering.rs`, `setup_a.rs` vs
`setup_b.rs`.

Always use `--cross-file` unless you specifically want within-file analysis.

```bash
# WEAK — within-file only
similarity-rs ./src

# STRONG — catches the most common LLM antipattern
similarity-rs --cross-file ./src
```

---

## `--no-size-penalty`

By default, the similarity score is penalized when the two functions differ
significantly in length. A 20-line function and a 200-line function that share a
common kernel will score lower than two 20-line functions with the same kernel.

Use `--no-size-penalty` when:
- You want to find a shared kernel between functions of different sizes.
- You suspect a large function was written by expanding a copy of a smaller one.

```bash
similarity-rs --cross-file --no-size-penalty ./src
```

Caution: raises false-positive rate for functions that share only an import line
or a common prefix.

---

## `--skip-test`

Exclude files in `tests/`, `benches/`, and any file with `#[cfg(test)]`.

Always use on CI; review test duplication locally where context is available.

```bash
similarity-rs --cross-file --skip-test ./src
```

---

## `--print` / `-p`

Emit extended context (source lines around each match) in addition to the
file:line clickable pairs. Useful when reviewing locally; adds noise on CI.

---

## Recommended flag combination per use-case

| Use-case | Command |
|---|---|
| Quick pre-commit check | `similarity-rs --cross-file --skip-test -t 0.85 -m 5 ./src` |
| Full cleanup sprint | `similarity-rs --cross-file -t 0.78 -m 3 -p ./src` |
| Strict production gate | `similarity-rs --cross-file --skip-test -t 0.92 -m 5 ./src` |
| Kernel-hunting (find shared logic between large fns) | `similarity-rs --cross-file --no-size-penalty -t 0.80 ./src` |
