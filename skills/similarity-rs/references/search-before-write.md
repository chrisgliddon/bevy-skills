# similarity-rs 0.5 — Search Before Write

The cheapest duplication fix is the one you never introduce.
Run these checks before writing any utility function, helper, type, or trait.

---

## Step 1 — grep the codebase for likely existing helpers

```bash
# Find any function whose name starts with a verb you're about to use
rg "fn normalize"
rg "fn lerp"
rg "fn clamp"

# Find a type or struct with a specific name
rg "struct ChunkId"
rg "enum GameState"

# Broader: find any use of the concept you're about to model
rg "chunk"          # reveals all mentions before you define anything new
```

Use ripgrep (`rg`) rather than `grep -r` — it respects `.gitignore`, is faster,
and produces VSCode-clickable output (file:line) that matches `similarity-rs`.

---

## Step 2 — inventory what your existing dependencies already provide

Before adding a crate or writing a helper, check what you already depend on.

```bash
# Open docs for every dependency at once (requires cargo doc to build)
cargo doc --open

# Or target a specific crate
cargo doc --open --package itertools
cargo doc --open --package glam
cargo doc --open --package bevy
```

**Common things LLMs re-implement that already exist:**

| What you're about to write | Where it already lives |
|---|---|
| Float `clamp` | `f32::clamp` (std, stable 1.50) |
| Lerp between two values | `f32::lerp` (std, stable 1.83) or `glam::Vec3::lerp` |
| Chunk flat-index from 3D coords | likely in your own `chunk.rs` already |
| A `HashMap` with default-value insertion | `HashMap::entry(...).or_default()` (std) |
| Iterator chunking | `itertools::Itertools::chunks` |
| String joining | `Iterator::collect::<Vec<_>>().join(", ")` (std) |
| Min/max of floats | `f32::min` / `f32::max` or `Iterator::fold` |

---

## Step 3 — read CLAUDE.md or AGENTS.md for project conventions

Project-level guidance often names specific helpers or modules agents should use.

```bash
# Check the project's agent guide
cat CLAUDE.md
cat AGENTS.md

# Search for a "helpers" or "utilities" section
rg "util|helper|common" CLAUDE.md
```

If the project names a utilities module (e.g., `src/utils.rs`, `src/common/`),
read it before writing anything new.

---

## Step 4 — ask "is there a crate for this?"

For any non-trivial algorithm or data structure, the Rust ecosystem likely has a
polished crate. Check before writing:

- **crates.io search:** https://crates.io/search?q=<keyword>
- **lib.rs** (curated): https://lib.rs/search?q=<keyword>
- **docs.rs** for API browsing: https://docs.rs/<crate>

Common additions worth checking:

| Task | Crate to check first |
|---|---|
| Noise / procedural generation | `noise`, `fastnoise-lite` |
| 3-D math | `glam` (already in Bevy's prelude) |
| Graph algorithms | `petgraph` |
| Data-parallel iteration | `rayon` |
| Fuzzy string matching | `strsim` |
| Interval arithmetic | `intervallum` |

---

## Step 5 — after writing, run the check

```bash
similarity-rs --cross-file ./src
```

If similarity-rs flags something you just wrote at a score ≥ 0.85 against an
existing function, treat it as a strong hint to consolidate before committing.

See [tuning.md](tuning.md) for threshold guidance, and
[false-positives.md](false-positives.md) for cases where high similarity is fine.
