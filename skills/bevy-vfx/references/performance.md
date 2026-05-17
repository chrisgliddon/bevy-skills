# bevy-vfx — Performance: GPU budgets, profiling, and WASM caveats

> Referenced from `bevy-vfx/SKILL.md § Topics`.

## Cross-technique GPU cost table

| Technique | Primary cost centre | Secondary cost | Scales with |
|---|---|---|---|
| `bevy_hanabi` GPU particles | Compute dispatch (init + update) | Fragment overdraw (large quads) | Particle count × modifier complexity |
| Gaussian splats (`bevy_spark`) | GPU memory (upload) + sort compute | Fill-rate / overdraw | Splat count (millions) |
| Custom material shader | Fragment shader invocations | Uniform upload (1 per entity/frame) | Screen pixels covered |
| CPU / sprite particles | Draw-call overhead | Transform update (CPU) | Entity count (hundreds ceiling) |

Rule of thumb: **compute dispatches and overdraw are the two levers**. Reducing
particle count or quad screen-area are the highest-impact optimisations.

## The WASM / WebGPU caveat (most important)

Both `bevy_hanabi 0.18.0` and `bevy_spark 0.2.0` use **compute shaders** internally.
Compute shaders are WebGPU-only. They will not compile with Bevy's `webgl2` feature.

Build for WebGPU, not WebGL2, when your project uses either crate:

```toml
# Cargo.toml — correct WASM target for hanabi or bevy_spark
[dependencies]
bevy = { version = "0.18", features = ["webgpu"] }
# NOT: features = ["webgl2"]
```

Techniques that **do** work on WebGL2:
- Sprite-sheet flipbooks (`bevy_spritesheet_animation`)
- Custom material shaders that use only uniforms and texture sampling
- `bevy_vector_shapes` (uses standard rasterisation)
- CPU-particle sprite entities

Cross-reference `bevy-wasm-webgpu` for the full WASM build setup.

## Profiling VFX systems

Hanabi simulation runs in `PostUpdate`, inside the `HanabiSet::Simulate` system set,
before `TransformSystems::Propagate`. Splat sort runs in the render world.

Enable the Bevy dev tools FPS overlay for a quick sanity check:

```rust
app.add_plugins(bevy::dev_tools::fps_overlay::FpsOverlayPlugin::default());
```

For span-level profiling, enable the `trace` Bevy feature and capture a Tracy / WGPU
trace:

```sh
cargo run --features bevy/trace
```

Look for these spans:
- `hanabi::simulate` — CPU portion of hanabi (spawner bookkeeping, not GPU compute).
- `hanabi::extract` — copies effect metadata to the render world each frame.
- `spark::sort` — per-frame depth sort for Gaussian splats (GPU compute).

GPU compute timings are only visible in RenderDoc / WGPU's GPU profiler; they do not
appear in Bevy's CPU span output.

## `SpawnerSettings::rate` vs `::burst` cost

```rust
// Continuous stream: small batches every frame, high cache pressure
SpawnerSettings::rate(500.0_f32.into())

// Burst: one large dispatch at the moment of burst, then silence
SpawnerSettings::burst(1000.0_f32.into(), 2.0_f32.into()) // 1000 particles every 2s
```

Bursts at low frequency are friendlier to GPU caches than constant low-rate streams:
the compute dispatch is larger but less frequent, improving instruction-cache reuse in
the init shader. For explosion-style one-shots, burst with a short active window is
the correct model.

## Texture atlasing for `ParticleTextureModifier`

Each hanabi effect that uses a different `Handle<Image>` for particle textures forces a
separate draw call (different bind group). Bundle particle textures into a shared atlas
and assign UV sub-rects via `ParticleTextureModifier`:

- One atlas = one bind group = all effects that share it batch into fewer draw calls.
- Atlases also improve texture-cache hit rate in the fragment stage.

## Particle count rules of thumb

GPU compute is massively parallel, but not free:

| Count | Expectation |
|---|---|
| < 1 K | Negligible. Prefer hanabi over CPU sprites at this scale only if you need GPU-speed modifiers. |
| 10 K | Cheap on modern desktop GPUs. Fine for hero effects. |
| 100 K | Noticeable on mid-range mobile; measure before shipping. |
| 1 M+ | Reserved for crowd / atmospheric effects. Budget explicitly. |

Particle **quad size** multiplies cost: a 1 M-particle effect where each quad covers
64 screen pixels is 64× more expensive in the fragment pass than the same count at
1 pixel. Minimise alpha-blended coverage, not just count.

## Combining techniques: sort and blend order

When `bevy_hanabi` effects, `bevy_spark` splats, and transparent mesh materials all
appear in the same frame, they all write to the transparent render pass. That pass
serialises draw calls by depth sort order.

Risks:
- A large splat scene in the background generates many transparent quads that the sort
  must order against foreground hanabi quads.
- Multiple overlapping transparent layers at high screen coverage (splat scene +
  hanabi burst + UI overlay) compound overdraw.

Mitigations:
- Use `AlphaMode::Opaque` or `AlphaMode::Mask` for geometry that does not need
  blending.
- Confine full-screen or large-coverage transparent effects to distinct depth layers
  that do not interleave with splat geometry.
- Profile transparent pass draw-call count with the Bevy render diagnostics plugin.

## See also

- [`../SKILL.md`](../SKILL.md) — top-level bevy-vfx dispatcher
- [`non-hanabi-vfx.md`](non-hanabi-vfx.md) — CPU particle cost model; sprite-particle
  draw-call ceiling
- [`gaussian-splats.md`](gaussian-splats.md) — splat GPU memory and sort-backend
  options
- `bevy-wasm-webgpu` — WebGPU-only compute shader requirement for hanabi and bevy_spark
- `bevy-pbr-materials` — `AlphaMode` options to reduce transparent-pass pressure
