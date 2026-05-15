# similarity-rs 0.5 — Sibling Tools

The `mizchi/similarity` family covers Rust, TypeScript, Python, Markdown, and a
generic fallback. **All siblings are themselves Rust CLIs published to crates.io
at v0.5.0** — they use tree-sitter parsers to target other languages, but the
install path is identical to `similarity-rs`.

> **Beta status:** All tools in this family are marked "not production-tested
> yet" per the upstream README. Treat output as signal; review each flagged
> pair before refactoring.

---

## `similarity-ts` — TypeScript / JavaScript

```bash
cargo install similarity-ts
similarity-ts ./src
similarity-ts --cross-file ./src
```

Useful for frontend TypeScript in a Bevy/WASM project (the JS bootstrap, glue
code around `wasm-bindgen`, UI components). Distinct npm package does not
exist — the cargo install is the canonical path.

---

## `similarity-py` — Python

```bash
cargo install similarity-py
similarity-py ./scripts
similarity-py --cross-file ./scripts
```

Useful for Python build scripts, CI tooling, asset-pipeline scripts, or
data-processing helpers in a Rust-primary project. Like `similarity-ts`, this
is a Rust binary that reads Python via tree-sitter — not a PyPI package.

---

## `similarity-generic` — Language-agnostic fallback

```bash
cargo install similarity-generic
similarity-generic --cross-file ./
```

Token-level approach using tree-sitter; lower accuracy than language-specific
tools. Useful for configuration files (`.ron`, `.toml`), GLSL/WGSL shaders, or
languages not covered by the family (Go, Java, C/C++, C#, Ruby per the upstream
README).

---

## `similarity-md` — Markdown (experimental)

```bash
cargo install similarity-md
similarity-md ./docs
```

Flags content overlap in long-form Markdown. Useful for docs trees where the
same instructions get repeated across multiple pages and drift apart over time.

---

## Choosing the right tool

| Language / file type | Tool |
|---|---|
| Rust (`*.rs`) | `similarity-rs` |
| TypeScript / JavaScript (`*.ts`, `*.tsx`, `*.js`) | `similarity-ts` |
| Python (`*.py`) | `similarity-py` |
| Markdown (`*.md`) | `similarity-md` |
| GLSL / WGSL / RON / TOML / Go / Java / etc. | `similarity-generic` |
| Mixed-language repo | Run each tool against its own tree |

---

## Polyglot CI example

```yaml
# .github/workflows/duplication-check.yml
jobs:
  duplication:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - run: cargo install similarity-rs similarity-ts
      - run: similarity-rs --cross-file --skip-test -t 0.85 ./src
      - run: similarity-ts --cross-file ./frontend/src
```

A single Rust toolchain installs every sibling — no separate Node, Python, or
npm step required.

---

## All tools: common flags

The sibling tools share the same CLI surface as `similarity-rs` v0.5.0. Run
each binary with `--help` to confirm flag names if you script against them —
the family aims for parity but new flags land at different cadences per tool.

Confirmed-shared flags (verified for `similarity-rs`; cross-check `--help` for
others before scripting):

- `--threshold` / `-t` — similarity floor (0.0-1.0).
- `--min-lines` / `-m` — minimum function size to flag.
- `--cross-file` / `-c` — compare across files (most useful mode).
- `--print` / `-p` — include source in output.

`--skip-test` is `similarity-rs`-specific (excludes `#[test]` functions); the
language-specific siblings have their own equivalents (`similarity-ts` excludes
`*.test.ts`/`*.spec.ts` by default heuristics; verify in `--help`).
