# Rust / Bevy Voxel Ecosystem

Current state of the crate and production-reference landscape for Bevy voxel
development. The ecosystem moves fast — verify crate activity status and
dependency health before adopting. Source: optimization deep-dive and community
discussion synthesis (see [generation](generation.md) and
[storage-formats](storage-formats.md) for context).

---

## Meshing

| Crate | Notes |
|-------|-------|
| [`block-mesh-rs`](https://crates.io/crates/block-mesh-rs) | Greedy quads and visible-block-faces meshing for blocky voxels. De facto standard in the Bevy ecosystem. Consumes a `VoxelVisibility` trait; works with any storage backend. |
| [`fast-surface-nets`](https://crates.io/crates/fast-surface-nets) | Surface nets / dual contouring for smooth voxels (terrain-style). Different paradigm from block-mesh. |
| [`bevy_meshem`](https://crates.io/crates/bevy_meshem) | Bevy-native meshing plugin; higher-level API wrapping block-mesh concepts. |

See `bevy-voxel-pipeline` skill for the Bevy 0.18 integration pattern that
connects these crates to `AsyncComputeTaskPool` chunk tasks.

---

## Storage and Indexing

| Crate | Status | Notes |
|-------|--------|-------|
| [`ndshape`](https://crates.io/crates/ndshape) | Active | Flat-array indexing helpers (XYZ ↔ linear index) for fixed-size voxel chunks. Pairs naturally with `block-mesh-rs`. |
| [`building-blocks`](https://crates.io/crates/building-blocks) | **ARCHIVED** | Formerly the most complete Rust voxel library (chunk management, LOD, SDFs, octrees). Archived by the author (bonsairobo). **Do not depend on new projects.** |
| [`feldspar`](https://github.com/bonsairobo/feldspar) | Intended successor to `building-blocks` — check activity status before depending on it. As of the source document it was under active rethinking. | |
| `nanovdb` (C++ FFI) | No mature pure-Rust binding | OpenVDB / NanoVDB requires C++ FFI. Build complexity; no pure-Rust equivalent with equivalent production polish. |

**Ecosystem gap:** no widely-adopted Rust crate implements palette compression
in the Minecraft 1.13+ style (per-subchunk palette + packed variable-bit-width
indices). This is a real opportunity — see [storage-formats](storage-formats.md)
for the full format description.

---

## Noise

| Crate | Notes |
|-------|-------|
| [`fastnoise2-rs`](https://crates.io/crates/fastnoise2-rs) | Bindings to FastNoise2. SIMD-accelerated; generates entire arrays of noise values in a single call rather than one point at a time. Preferred for bulk chunk generation. |
| [`fastnoise-lite`](https://crates.io/crates/fastnoise-lite) | Lightweight alternative; also supports array-at-a-time generation. |
| [`noise-rs`](https://crates.io/crates/noise) | Pure-Rust noise functions. Ergonomic API, good documentation, **not SIMD**. Use for quick prototyping or when SIMD dependencies are a concern. |
| [`bracket-noise`](https://crates.io/crates/bracket-noise) | Port of FastNoise; used in the bracket-lib roguelike ecosystem. Fine for roguelikes, not tuned for voxel bulk generation. |

For bulk chunk generation, prefer `fastnoise2-rs` or `fastnoise-lite`. They
sidestep the manual loop-hoisting maintenance burden by vectorising internally.
See [generation](generation.md) §4 for context.

---

## File Formats

| Crate | Notes |
|-------|-------|
| [`dot_vox`](https://crates.io/crates/dot_vox) | MagicaVoxel `.vox` file parser. Useful for loading artist-authored voxel assets. |
| [`bevy_vox`](https://crates.io/crates/bevy_vox) | Bevy asset loader for MagicaVoxel scenes. |
| [`bevy-vox-scene`](https://crates.io/crates/bevy-vox-scene) | More featureful Bevy loader; handles multi-model `.vox` scenes with named sub-objects. |

For procedural worlds you will likely produce your own binary or RON format
rather than using these. The RON catalog pattern is covered in the main
`bevy-voxel-data` skill.

---

## Full Engines and World Plugins

| Crate | Notes |
|-------|-------|
| [`bevy_voxel_world`](https://crates.io/crates/bevy_voxel_world) | Chunk management, procedural generation hooks, and meshing as a Bevy plugin. The closest off-the-shelf analog to a full voxel game framework in the Bevy ecosystem. Evaluate carefully: it bakes in specific chunk-management opinions. |
| [`bevy_voxel_engine`](https://crates.io/crates/bevy_voxel_engine) | GPU-driven voxel raymarching renderer. **Different rendering paradigm** from mesh-based engines — not a drop-in replacement. Worth studying for rendering ideas but incompatible with the `block-mesh-rs` + `StandardMaterial` pattern. |

---

## Production References Worth Reading

These are external projects, not Rust crates. The algorithms and architectures
are the valuable part.

### Sodium — Minecraft renderer rewrite
- **Repo:** https://github.com/CaffeineMC/sodium
- **License:** MIT
- **Language:** Java
- **Why read it:** The single highest-leverage study resource for a Bevy voxel
  developer. Key techniques: batched chunk rendering via large shared VBO
  atlases, multi-draw indirect to collapse per-chunk draw calls, compressed
  vertex formats (16-bit positions), CPU-side frustum culling, async chunk
  meshing on worker threads. Reports 300%+ frame-rate improvements on low-end
  hardware. Architecturally clear despite being Java.

### VOXLAP — Ken Silverman's column-span engine (~2000)
- **Source:** http://advsys.net/ken/voxlap.htm
- **License:** Custom non-commercial. Attribution required, free distribution
  only, commercial use requires Silverman's explicit permission. **Not OSI
  open source.** GitHub mirrors (Ericson2314/Voxlap, aponigricon/Voxlap,
  billyzhaoj/Voxlap-Port) inherit the same license.
- **License note:** Algorithms are not copyrightable — studying the
  architecture and reimplementing in Rust is legal. **Do not copy code.**
- **Why read it:** The original runtime-RLE voxel engine. Column-of-spans
  layout, surface-only storage (massive memory win over storing all voxels),
  span-aware modification (`setcube` splits/merges spans). The architecture
  Tantan's system echoes — and with 25 years of hindsight on its tradeoffs.
- **What does not translate:** Software raycasting renderer (x86 inline
  assembly, SSE2/3DNow!), single-threaded assumptions. Bevy is parallel-first
  and GPU-based.

### Cuberite — Open-source C++ Minecraft-compatible server
- **Repo:** https://github.com/cuberite/cuberite
- **License:** Apache 2.0
- **Why read it:** Production Minecraft-protocol implementation in C++.
  Chunk format handling, palette compression, lighting propagation. More
  approachable than the Mojang decompiled source.

### Luanti (formerly Minetest)
- **Site:** https://www.luanti.org/
- **License:** LGPL 2.1+
- **Why read it:** Fully open-source voxel game engine, Lua-scriptable. Mature
  codebase (~15 years). Good reference for chunk I/O, block registration, and
  map storage without reverse-engineering anything.

### John Lin — "The Perfect Voxel Engine"
- **URL:** https://voxely.net/blog/the-perfect-voxel-engine/
- **Why read it:** The most important architectural piece for understanding
  format choice. Argues for multi-format + conversion infrastructure rather
  than a single "best" format. See [storage-formats](storage-formats.md) §1
  for the detailed summary.

---

## Ecosystem Gaps

Two specific gaps exist where a well-maintained Rust crate would have
meaningful ecosystem impact:

1. **Palette compression.** No widely-adopted Rust crate implements the
   Minecraft 1.13+ palette + packed-indices format. The format is documented
   at https://minecraft.wiki/w/Chunk_format and is not complex to implement —
   the gap is curation and testing, not algorithmic difficulty.

2. **Pure-Rust OpenVDB equivalent.** No mature pure-Rust sparse hierarchical
   voxel structure with production-quality performance and API. The C++ FFI
   route (`nanovdb`) works but introduces build friction. Until this gap is
   filled, sparse-world use cases in Bevy remain underserved.
