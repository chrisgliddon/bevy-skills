# Voxel Generation Optimizations

Best practices for fast procedural voxel world generation in Bevy 0.18.
The techniques below account for the bulk of a documented ~25× throughput gain
(~20M → ~500M voxels/sec) on a Bevy/Rust voxel engine. See
[storage-formats](storage-formats.md) for complementary runtime-storage choices.

---

## 1. Extremity Bound Checking

**The single most powerful generation optimization** — documented at ~15× speedup
in isolation (side-by-side: 2 s with bounds vs 29 s without, on equivalent shaping logic).

### How it works

A shaping function determines, per voxel, whether that voxel is solid or air.
Typically this calls a noise function, scales the result to a height, and
compares with the voxel's Y coordinate. **The key insight**: if you know the
output range of every sub-expression in your shaping function, you can
short-circuit the entire noise evaluation for any chunk (or voxel slab) that
is provably all-air or all-solid.

```rust
// Simplified: height noise remapped to [0, 10].
// MAX_HEIGHT = 10, MIN_HEIGHT = 0.

fn shape_voxel(x: i32, y: i32, z: i32, noise: &impl NoiseFn<[f64; 2]>) -> VoxelType {
    // Extremity check: entire chunk above maximum possible height → all air.
    // Entire chunk below minimum possible height → all solid.
    // Only call noise when y is within the uncertain band.
    let height = noise.get([x as f64, z as f64]) * 10.0; // range [0, 10]
    if y as f64 > height { VoxelType::Air } else { VoxelType::Grass }
}

fn fill_chunk(chunk_min_y: i32, chunk_max_y: i32, /* ... */) {
    const MAX_HEIGHT: i32 = 10; // extremity bound
    const MIN_HEIGHT: i32 = 0;

    if chunk_min_y > MAX_HEIGHT {
        // Entire chunk is above the tallest possible terrain → skip all noise calls.
        fill_all_air(/* ... */);
        return;
    }
    if chunk_max_y <= MIN_HEIGHT {
        fill_all_solid(/* ... */);
        return;
    }
    // Only reach here for chunks in the uncertain band.
    fill_mixed(/* ... */);
}
```

**Benchmark numbers (from source):**
- Baseline: ~300 µs per chunk
- With bounds checking: ~100 µs (3× within the uncertain band)
- Chunk entirely outside bounds: ~245 ns (noise calls skipped entirely)

### The catch — bounds must track shaping changes

Every time you add a noise layer, domain-warp pass, or threshold adjustment,
you must manually recalculate the output bounds. In practice this becomes
fragile and hostile to iteration by world designers.

**Author's solution — serialized shaping config with auto-bounds:**
Represent shaping logic as a declarative config (layers, noise params, mappings)
interpreted at runtime rather than compiled Rust. The interpreter calculates
extremity bounds automatically from the layer definitions. Changing mountain
height in config updates the bounds without touching code.

This is an architectural lift — not an early-stage optimization. The tradeoff:
- **Hand-maintained bounds**: fast, brittle, painful after the first few layers.
- **Interpreter approach**: large upfront investment, scales to complex worlds.

---

## 2. Noise Upsampling

**Should be in every voxel engine.** Reduces noise evaluations *inside* the
uncertain band (complementary to extremity bounds which reduce evaluations
*outside* it).

### How it works

Sample noise every 2nd / 4th / 8th voxel and trilinearly interpolate the gaps.
More upsampling = slightly less terrain detail, but 4× looks "surprisingly good"
per the benchmark author.

**Math:** for a 64³ chunk at 4× upsampling you sample noise 17³ = 4 913 times
instead of 64³ = 262 144. That's ~53× fewer calls — but you don't get 53× speedup
because trilinear interpolation has non-trivial per-voxel cost.

### Benchmark table (3D noise, 64³ chunk)

| Upsampling | Time     | Notes                         |
|------------|----------|-------------------------------|
| 1× baseline | ~7 ms   |                               |
| 2×          | ~2.4 ms  |                               |
| **4×**      | **~1.4 ms** | **Practical sweet spot**   |
| 8×          | ~1 ms    | Diminishing returns begin      |
| 16×         | ~1 ms    | Floor: interpolation dominates |

**Conclusion:** 4× upsampling delivers ~5× throughput gain with minimal
perceptual quality loss. Returns diminish past 8× because per-voxel
interpolation cost becomes the bottleneck.

```rust
// Sketch: 4× upsampled noise fill for a 32³ chunk.
// Sample at every 4th voxel on each axis (9×9×9 = 729 samples).
const STEP: usize = 4;
const SAMPLES: usize = 32 / STEP + 1; // 9

let mut corners = [[[0.0f32; SAMPLES]; SAMPLES]; SAMPLES];
for cx in 0..SAMPLES {
    for cy in 0..SAMPLES {
        for cz in 0..SAMPLES {
            let wx = (chunk_origin.x + cx * STEP) as f64;
            let wy = (chunk_origin.y + cy * STEP) as f64;
            let wz = (chunk_origin.z + cz * STEP) as f64;
            corners[cx][cy][cz] = noise.get([wx, wy, wz]) as f32;
        }
    }
}

// Per-voxel: trilinear interpolation from the 8 surrounding corner samples.
for lx in 0..32 {
    for ly in 0..32 {
        for lz in 0..32 {
            let cx = lx / STEP;  let tx = (lx % STEP) as f32 / STEP as f32;
            let cy = ly / STEP;  let ty = (ly % STEP) as f32 / STEP as f32;
            let cz = lz / STEP;  let tz = (lz % STEP) as f32 / STEP as f32;
            let v = trilinear(&corners, cx, cy, cz, tx, ty, tz);
            // use v to determine voxel type
        }
    }
}
```

---

## 3. Noise Caching / Hoisting

**Core rule: never ask the same question twice.**

### Loop-invariant hoisting

In a Y-axis inner loop, X and Z coordinates are constant — so a 2D height-map
noise call is computed 32 times with identical inputs. Hoist it out:

```rust
// Without hoisting: 32 × 32 × 32 = 32768 noise calls per chunk.
for x in 0..32 {
    for z in 0..32 {
        for y in 0..32 {
            let height = height_noise.get([x as f64, z as f64]); // wasted!
            // ...
        }
    }
}

// With hoisting: 32 × 32 = 1024 noise calls — 32× reduction.
for x in 0..32 {
    for z in 0..32 {
        let height = height_noise.get([x as f64, z as f64]); // computed once
        for y in 0..32 {
            // use cached `height`
        }
    }
}
```

**Tall-chunk multiplier:** with 32×256×32 chunks, the inner Y loop runs 256
iterations instead of 32 — so a hoisted 2D noise call is reused 256 times,
an 8× additional gain over standard 32³ chunks. Biome lookup (also X/Z-only)
gets the same 256× reuse.

### Cross-biome noise sharing

At biome borders the engine must blend two or more biomes simultaneously,
running each biome's full shaping logic in parallel. Biomes typically share the
same low-frequency and medium-frequency noise parameters (e.g. continental
elevation, temperature gradient). Recomputing identical noise for each biome at
every border voxel is pure waste.

**Solution:** define shared global noise parameters in one config/resource, bake
them once before entering any biome shaper, and pass the baked values in:

```rust
// Conceptual structure — adapt to your shaping system.
struct GlobalNoise {
    pub continental: f32, // low-freq, X/Z only — baked once per column
    pub temperature: f32, // X/Z only
    // ...
}

fn shape_forest(voxel: IVec3, global: &GlobalNoise, local_noise: &impl NoiseFn<[f64; 3]>) -> VoxelType {
    // uses global.continental + local detail noise
}

fn shape_snow(voxel: IVec3, global: &GlobalNoise, local_noise: &impl NoiseFn<[f64; 3]>) -> VoxelType {
    // uses same global.continental — no re-evaluation
}
```

This matters most at biome borders, which is precisely where the cost spikes.

---

## 4. SIMD Noise Libraries

Some noise libraries generate an **entire array of values in a single call**
using SIMD internally, rather than evaluating one point at a time. For bulk
chunk fills this is often faster than manual hoisting because the SIMD
vectorisation is more aggressive than what scalar loop-hoisting achieves.

**Recommended crates (from community discussion):**

- [`fastnoise2-rs`](https://crates.io/crates/fastnoise2-rs) — bindings to
  FastNoise2, SIMD-accelerated, generates arrays in one call.
- [`fastnoise-lite`](https://crates.io/crates/fastnoise-lite) — lightweight
  single-point evaluator (no SIMD, no bulk array fill). Simpler to integrate
  than `fastnoise2-rs` but must be called per-voxel in a loop; does not share
  the bulk-generation performance characteristics of FastNoise2.

Contrast with `noise-rs` (ergonomic, per-point, not SIMD) or `bracket-noise`
(FastNoise port, roguelike ecosystem).

```rust
// fastnoise2-rs pattern: fill an entire chunk's noise in one call.
// (Exact API varies — check crate docs for current method names.)
let mut output = vec![0.0f32; 32 * 32 * 32];
generator.gen_uniform_grid_3d(
    &mut output,
    chunk_origin.x, chunk_origin.y, chunk_origin.z,
    32, 32, 32,
    frequency, seed,
);
// output[x + z*32 + y*1024] is now the noise value for voxel (x, y, z).
```

---

## 5. Bevy Integration — AsyncComputeTaskPool

Chunk generation is CPU-intensive and must not block the main thread. Spawn
generation tasks on `AsyncComputeTaskPool` and poll them via a system that
processes completed `Task<ChunkData>` components:

```rust
use bevy::prelude::*;
use bevy::tasks::{AsyncComputeTaskPool, Task};
use futures_lite::future;

#[derive(Component)]
struct GenerateChunkTask(Task<ChunkData>);

fn spawn_chunk_generation(
    mut commands: Commands,
    chunks_to_generate: Query<(Entity, &ChunkPosition), With<NeedsGeneration>>,
) {
    let pool = AsyncComputeTaskPool::get();
    for (entity, &pos) in &chunks_to_generate {
        let task = pool.spawn(async move {
            generate_chunk(pos) // your generation function
        });
        commands.entity(entity)
            .remove::<NeedsGeneration>()
            .insert(GenerateChunkTask(task));
    }
}

fn poll_chunk_generation(
    mut commands: Commands,
    mut tasks: Query<(Entity, &mut GenerateChunkTask)>,
) {
    for (entity, mut task) in &mut tasks {
        if let Some(chunk_data) = future::block_on(future::poll_once(&mut task.0)) {
            commands.entity(entity)
                .remove::<GenerateChunkTask>()
                .insert(chunk_data);
        }
    }
}
```

See `bevy-voxel-pipeline` for the meshing step that follows generation.

---

## Pitfalls

- **Bounds rot on shaping changes.** Every noise layer you add or modify
  requires recalculating extremity bounds. Without the interpreter approach,
  bounds drift from reality as the world design evolves, silently corrupting
  chunks near the boundary threshold.

- **Manual hoisting is brittle.** Adding a second 2D noise layer (e.g.
  erosion on top of base height) requires carefully identifying which calls
  can be hoisted and which are 3D. SIMD library array-fills sidestep this
  maintenance burden.

- **Upsampling breaks sharp terrain features.** Cliffs, overhangs, and cave
  mouths with tight curvature will be smoothed at high upsampling levels.
  Use lower upsampling (2×) near feature regions or blend a high-frequency
  detail pass on top.

- **Cross-biome sharing requires stable noise IDs.** The global parameters
  must hash/seed consistently so biome borders sample the same values on
  adjacent chunks regardless of generation order.
