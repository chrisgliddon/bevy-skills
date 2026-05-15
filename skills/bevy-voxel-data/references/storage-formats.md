# Voxel Storage Formats

How to store voxel data at runtime. This is the most consequential architectural
decision in a voxel engine — it affects RAM budget, modification cost, meshing
throughput, disk serialization, and network bandwidth simultaneously.

See [generation](generation.md) for the generation-time counterparts.

---

## The Framing Problem — John Lin's Argument

The most important reframe in this space: **the "which storage format is best?"
question is the wrong question.**

John Lin's 2021 essay ["The Perfect Voxel Engine"](https://voxely.net/blog/the-perfect-voxel-engine/)
argues that voxel engines should be built like graphics engines:

> *"The solution is actually rather obvious: to use whatever voxel format is
> best for the job! This means not having one or two, but as many as are
> necessary."*

A graphics engine doesn't ask "should I use OBJ or FBX?" — it uses a common
interchange format and converts per-task. Triangles for rasterization, BVHs for
ray tracing, hull meshes for physics. The same geometry, multiple
representations, conversion infrastructure between them.

**Voxel engines should work the same way.** Every format described below is
best at something and bad at something else. Picking one and forcing it to serve
every subsystem (rendering, collision, AI, lighting, modification, networking,
serialization) is the actual root problem the hybrid-storage commenters are
groping toward.

Lin's proposed three-stage pipeline:

- **Allocation** — abstracted buffer allocation (CPU, GPU, recycled, disk) so
  systems don't manage memory directly.
- **Tagging** — dynamic per-voxel attributes (albedo, normal, vegetation state,
  modder-added fields) declared at runtime rather than baked into struct
  definitions.
- **Conversion** — black-box operators that translate between formats. Mesh
  voxelization, Minecraft map imports, CSG → voxels, compressors, collision
  geometry generation, procedural terrain voxelization, serialization. All the
  same primitive.

Lin's critique of SVOs: *"For sparse voxel octrees, storage and rendering are
the only things they are acceptable (not even great) at."* The same applies to
RLE — it excels at storage and bulk writes, struggles at random access and
mutation.

**Caveat:** Lin's blog promised a follow-up rendering deep-dive that, as of the
source document's writing (late 2025), was never published. The architectural
framework is influential but the full implementation is not publicly documented.

---

## Flat Arrays — The Naive Baseline

```rust
// 32³ chunk, u16 block IDs.
struct ChunkFlat {
    voxels: Box<[u16; 32 * 32 * 32]>,
}

impl ChunkFlat {
    #[inline]
    fn get(&self, x: usize, y: usize, z: usize) -> u16 {
        self.voxels[x + z * 32 + y * 1024]
    }
    #[inline]
    fn set(&mut self, x: usize, y: usize, z: usize, v: u16) {
        self.voxels[x + z * 32 + y * 1024] = v;
    }
}
```

**Properties:**
- O(1) random access, O(1) modification.
- Dense memory: 32³ × 2 bytes = 65 536 bytes = 64 KB per chunk.
- No compression. At 36-chunk render distance this is ~15 GB RAM for u16 (2-byte) types, or ~7 GB for u8 (1-byte) types.
- Disk format requires a separate serialization step.

**When it's right:** small worlds, high per-block modification rate, ample RAM,
or as the *active* format when decompress-on-modify is in play (see Hybrid
Strategies below).

---

## Run-Length Encoding (RLE)

Tantan's runtime choice. Per-column `(voxel_type, run_length)` pairs stored in
a `Vec` rather than a dense array.

```rust
#[derive(Clone, Copy)]
struct Run { voxel: u16, len: u16 }

struct ChunkColumn {
    runs: Vec<Run>,     // sorted bottom → top
    total_height: u32,  // e.g. 256 for tall chunks
}
```

### Upsides

- **Massive RAM savings.** At 36-chunk render distance: ~400 MB (RLE) vs ~7 GB
  (flat u8) or ~15 GB (flat u16). This is the primary argument for runtime RLE.
- **Disk save = memory dump.** The runtime format is already the compressed
  format. No serialization pause.
- **Fast surface detection.** Traversal naturally yields every voxel-type
  boundary — useful for placing trees, rocks, NPCs. Cave heights are directly
  readable without a volume scan.
- **Large writes are nearly free.** Combined with extremity bounds: if
  generation proves "below Y=200 is all grass", that's one RLE entry. The
  flat-array equivalent is a 200-iteration loop.
- **Tall chunks are viable.** 32×256×32 chunks reduce chunk management overhead
  vs 8 stacked 32³ chunks. 2D noise-cache hoisting gets 8× more reuse per
  column.
- **Combines with extremity bounds.** RLE + extremity bounds compound: a
  "provably solid" region becomes a single `(solid, count)` entry.

### Downsides

- **Slow random access.** Looking up voxel at `(x=5, y=47)` requires traversing
  the column's run list from the bottom until accumulated lengths reach Y=47.
  O(runs) not O(1).
- **Slow modification.** Inserting a single block mid-run requires splitting the
  run and resizing the Vec. Worse than O(1) flat-array writes.
- **Collapses on fragmented worlds.** When a column contains many alternating
  block types (player excavation, biome mixing, redstone contraptions), run
  lengths approach 1 and RLE uses *more* memory than a flat array. This is the
  primary scaling risk.

### Prior art

Ken Silverman's **VOXLAP engine (~2000)** stored voxel data as RLE spans
in-memory, and its map format was a direct memory dump — exactly this
architecture. VOXLAP was used in the Ace of Spades beta. Tantan's formulation
stores all voxels; VOXLAP stored only surfaces (solid/non-air runs carry color
data; buried runs are implicit), which is a larger memory win. See
[ecosystem](ecosystem.md) for source/license status.

---

## Palette Compression — The Modern Scalable Answer

Minecraft's format since 1.13 (2018). Per-subchunk palette of block types
actually present, plus packed indices with **variable bit width**.

Reference: [Minecraft chunk format](https://minecraft.wiki/w/Chunk_format)
and [network protocol variant](https://minecraft.wiki/w/Java_Edition_protocol/Chunk_format).

```
Subchunk (16×16×16 = 4096 voxels):
  palette: ["air", "stone", "grass", "dirt"]   ← 4 types → 2 bits/index
  data: packed u64 array, 2 bits per voxel, 4096 × 2 = 8192 bits = 128 u64s
```

**Variable bit widths used in practice:**
- 1 type in palette → no data array needed (whole section is that type)
- 2–4 types → 2 bits/voxel
- 5–16 types → 4 bits/voxel
- 17–256 types → 8 bits/voxel
- >256 types → fall back to global block state registry

**Since Minecraft 1.16:** indices do not cross 64-bit word boundaries (minor
space waste, simpler unpacking).

```rust
// Sketch: palette-compressed subchunk.
struct PaletteChunk {
    palette: Vec<u16>,          // block IDs present in this chunk
    bits: u8,                   // bits per index (1, 2, 4, or 8)
    data: Vec<u64>,             // packed index array
}

impl PaletteChunk {
    fn get(&self, x: usize, y: usize, z: usize) -> u16 {
        let linear = x + z * 16 + y * 256;
        let bits = self.bits as usize;
        let indices_per_word = 64 / bits;
        let word_idx = linear / indices_per_word;
        let bit_offset = (linear % indices_per_word) * bits;
        let mask = (1u64 << bits) - 1;
        let palette_idx = ((self.data[word_idx] >> bit_offset) & mask) as usize;
        self.palette[palette_idx]
    }
}
```

**Properties:**
- O(1) random access (bit unpack, one palette lookup).
- Scales gracefully into fragmented worlds where RLE collapses.
- A subchunk with 4 block types uses 2 bits/voxel = 1 KB for 4096 voxels.
- Air-only sections can be omitted entirely (same as Minecraft's section elision).
- Separate palettes per attribute type (blocks, biomes, lighting) within the
  same spatial region — this maps directly to Lin's "tagging" concept.

**When it's right:** variety-tolerant worlds with hundreds of block types but
only a handful present per local 16³ region. This is almost every survival game.

**Ecosystem gap:** as of the source document, no widely-adopted Rust crate
implements palette compression in Minecraft 1.13+ style. This is an open
opportunity. See [ecosystem](ecosystem.md).

---

## Hybrid Strategies

The community converged on several patterns independently. Through Lin's lens,
these are all partial implementations of his conversion-operator idea:

### Decompress-on-Modify

Keep chunks in RLE (or palette) by default. When a chunk enters a modification
zone (e.g. 3×3 around the player), decompress to flat array. Recompress on
eviction to the unloaded pool.

- Sidesteps RLE's random-access cost entirely: you only pay it on cold chunks.
- The flat "hot" representation is what block-placement, physics, and
  lighting queries see.
- `block-mesh-rs` can consume either format via a custom adapter.

### Distance-Based Fidelity

- RLE (or palette) for far chunks with a coarse palette (air/grass/stone).
- Full per-voxel storage near the player.
- Naturally combines with chunk LOD (see Distant Horizons pattern in
  [ecosystem](ecosystem.md)).

### Sparse Overlay

Keep RLE as the base layer (generated world), store player modifications as a
sparse `HashMap<IVec3, u16>` on top. Query the overlay first, fall back to RLE.
Efficient when player modifications are rare relative to world volume.

### Per-Chunk Format Selection

Pick RLE or flat array per chunk based on measured compression ratio, or extend
RLE with a "literal run" type that stores a voxel sequence inline when runs are
too short to compress. Choose at generation time and re-evaluate on eviction.

---

## Sparse Structures — Brief Mention

For genuinely sparse 3D data (lots of air, irregular geometry):

- **OpenVDB** — DreamWorks' open-source format, industry standard in VFX. A
  B+tree-like hierarchy with tile compression for uniform regions. No mature
  pure-Rust binding as of the source document; `nanovdb` C++ via FFI is the
  usual route.
- **Sparse Voxel Octrees (SVO) / Sparse Voxel DAGs (SVDAG)** — the academic
  answer for high-detail static voxel worlds. Lin's critique: SVOs are
  acceptable (not great) at storage and rendering; bad at modification.
- **Run-volume encoding** — effectively what OpenVDB's tile system implements;
  extends 1D RLE to 3D regions.

These are not the focus here; see [ecosystem](ecosystem.md) for crate status.

---

## Parallel Bitmaps

Maintain a **1-bit-per-voxel "is solid" mask** alongside whichever primary
format you choose. Cheap to maintain (one bitset write per voxel change),
dramatically speeds up every system that doesn't need the full block type:

- Collision detection — walk the bitset, not the type array.
- Raycasts — DDA over the bitset first, read type only on hit.
- Ambient occlusion — bitset bitwise AND over neighbour samples.
- Meshing — `block-mesh-rs` visible-faces pass only needs solidity, not type.

Combines with any storage format. The bitset itself is tiny: 32³ voxels = 4 KB.

```rust
struct ChunkBitmask {
    solid: [u64; 32 * 32 * 32 / 64], // 512 u64s = 4 KB
}

impl ChunkBitmask {
    #[inline]
    fn is_solid(&self, linear_idx: usize) -> bool {
        (self.solid[linear_idx / 64] >> (linear_idx % 64)) & 1 == 1
    }
    #[inline]
    fn set_solid(&mut self, linear_idx: usize, solid: bool) {
        let word = &mut self.solid[linear_idx / 64];
        let bit = 1u64 << (linear_idx % 64);
        if solid { *word |= bit; } else { *word &= !bit; }
    }
}
```

---

## The Real Performance Lens — Memory Bandwidth

The video never states this explicitly, but it is the actual reason compressed
runtime formats win:

**Modern CPUs spend most of their time waiting for memory, not computing.**
A 400 MB world fits in L3 cache footprint patterns that a 7 GB world cannot.
RLE's "logically more work" (traversing run lists) can still be faster than
flat-array indexed reads because the RLE data stays cache-resident. This is the
real argument for runtime compression, and it deserves to be the lede in any
performance analysis.

The 25× throughput gain documented in the source is a combined-technique number.
The analysis in the source document suggests **extremity bounds and 4× upsampling
account for most of the compute reduction**; RLE's contribution to throughput is
largely indirect (enables tall chunks → more 2D noise-cache reuse).

---

## Pitfalls

- **RLE collapses on fragmented worlds.** Player-modified terrain, redstone
  contraptions, and biomes with many stacked alternating types push run lengths
  toward 1. Monitor compression ratio empirically; switch to palette or flat
  when it degrades past a threshold.

- **SVO is not a general-purpose format.** Lin is explicit: SVOs are acceptable
  (not great) at storage and rendering, and bad at modification. Do not reach
  for octrees as the single format.

- **OpenVDB has no mature pure-Rust binding.** The C++ FFI route (`nanovdb`)
  works but adds build complexity. No pure-Rust equivalent exists with the
  same production polish.

- **Palette bit-packing is subtle.** The Minecraft 1.16 change (indices don't
  cross 64-bit word boundaries) is a portability concern if you are importing
  pre-1.16 data. Implement both variants or use a library that handles both.

- **Precomputed heightmaps are worth it.** Store the surface Y per (x, z) as
  a flat `[u16; 32*32]` per chunk column alongside your primary storage.
  Spawning, pathfinding, AO queries, and surface detection all need this; don't
  recompute it from storage on every query.
