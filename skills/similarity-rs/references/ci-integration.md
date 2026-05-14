# similarity-rs 0.5 — CI Integration

Recipes for running `similarity-rs` automatically so duplication is caught
before it merges, not discovered months later.

> **Beta note:** The upstream README marks `similarity-rs` as not
> production-tested. Consider starting with an advisory (non-failing) CI job,
> then graduating to a blocking check once you've tuned the threshold for your
> project.

---

## Pre-commit hook

Create `.git/hooks/pre-commit` (or add to an existing hook):

```bash
#!/usr/bin/env bash
set -euo pipefail

# Check for similarity-rs; skip gracefully if not installed
if ! command -v similarity-rs &>/dev/null; then
    echo "[similarity-rs] not installed — skipping duplication check"
    echo "  Install with: cargo install similarity-rs --version 0.5.0"
    exit 0
fi

echo "[similarity-rs] scanning for cross-file duplication..."
similarity-rs --cross-file --skip-test -t 0.85 -m 5 ./src
```

Make it executable:

```bash
chmod +x .git/hooks/pre-commit
```

**Notes:**
- `--skip-test` prevents test-fixture symmetry from triggering false alarms.
- `-m 5` suppresses 3-line trivial matches.
- The `command -v` guard means teammates without the tool aren't blocked.

For a team workflow, use a hook manager (e.g., `pre-commit` framework or
`cargo-husky`) so the hook is committed to the repo.

---

## GitHub Actions workflow

```yaml
# .github/workflows/duplication-check.yml
name: Duplication check

on:
  pull_request:
    paths:
      - 'src/**'

jobs:
  similarity:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust stable
        uses: dtolnay/rust-toolchain@stable

      # Cache the cargo registry and the similarity-rs binary
      - uses: actions/cache@v4
        with:
          path: |
            ~/.cargo/registry
            ~/.cargo/bin/similarity-rs
          key: ${{ runner.os }}-similarity-rs-v0.5.0

      - name: Install similarity-rs
        run: |
          if ! command -v similarity-rs &>/dev/null; then
            cargo install similarity-rs --version 0.5.0
          fi

      - name: Run duplication check
        run: similarity-rs --cross-file --skip-test -t 0.85 -m 5 ./src
```

**The job fails** if `similarity-rs` exits non-zero (i.e., any pair exceeds the
threshold). Adjust `-t` to tune the gate (see [tuning.md](tuning.md)).

---

## Advisory-only job (non-blocking)

If you want visibility without blocking PRs, add `continue-on-error: true`:

```yaml
      - name: Run duplication check (advisory)
        continue-on-error: true
        run: similarity-rs --cross-file --skip-test -t 0.85 -m 5 ./src
```

This surfaces duplication in the CI log without failing the check.

---

## Failing on a specific pair

As of v0.5, `similarity-rs` has no per-function allow-list flag (no `--ignore`,
no inline-comment suppression). To accept a known pair while keeping the gate
active, raise `-m` (min-lines) so the pair falls below the minimum, or raise
`-t` to 0.95+ until the pair no longer triggers. Both are blunt — they may
mask unrelated duplication, so prefer fixing the actual duplicate over tuning
around it.

A longer-term alternative: suppress with an inline comment convention and a
post-processing filter on `similarity-rs` output — but this is not built into
the tool as of 0.5.

---

## Using `--print` / `-p` for human-readable output

By default `similarity-rs` emits VSCode-clickable `file:line` pairs. For CI
logs, the output is already readable. Use `-p` if you want extended context
lines around each match:

```bash
similarity-rs --cross-file --skip-test -p ./src
```
