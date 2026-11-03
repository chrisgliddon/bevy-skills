# bevy-vfx — Non-hanabi VFX: CPU particles, flipbooks, vector shapes, trails, decals

> Referenced from `bevy-vfx/SKILL.md § Topics`.

## When NOT to use hanabi

`bevy_hanabi` is the right tool for GPU-computed fields of thousands of independent
particles. Reach for the alternatives below when:

- **Count < ~100 particles** — spawning individual `Sprite` entities and driving them
  with a Bevy system is simpler, debuggable, and zero dependency overhead.
- **WebGL2 target** — `bevy_hanabi 0.20.0` requires WebGPU. It will not compile or
  run on `wasm32` with the `webgl2` feature. Use sprite flipbooks or custom-material
  shaders instead.
- **Canned, identical-every-time FX** — hit-sparks, muzzle flashes, explosions where
  every instance plays the same frame sequence. A sprite-sheet flipbook is simpler and
  runs on any backend.
- **Stylized / geometric look** — rings, lightning bolts, SDF shapes. Use
  `bevy_vector_shapes` rather than fighting hanabi's shading model.

## CPU-particle pattern

For small bursts (smoke puffs, blood splatter, debris), spawn entities directly.
Cost: O(particle count) CPU, one draw call per particle (batching helps if all use the
same material and mesh).

```rust
use bevy::prelude::*;

#[derive(Component)]
struct Particle {
    velocity: Vec3,
    lifetime: Timer,
}

fn spawn_burst(mut commands: Commands, asset_server: Res<AssetServer>) {
    let image = asset_server.load("textures/spark.png");
    for i in 0..30_u32 {
        let angle = (i as f32 / 30.0) * std::f32::consts::TAU;
        commands.spawn((
            Sprite::from_image(image.clone()), // 0.20: Sprite has an `alpha_mode` field
            Transform::from_xyz(0.0, 0.0, 0.0),
            Particle {
                velocity: Vec3::new(angle.cos(), angle.sin(), 0.0) * 3.0,
                lifetime: Timer::from_seconds(0.8, TimerMode::Once),
            },
        ));
    }
}

fn tick_particles(
    mut commands: Commands,
    time: Res<Time>,
    mut q: Query<(Entity, &mut Transform, &mut Particle)>,
) {
    for (entity, mut xf, mut p) in &mut q {
        p.lifetime.tick(time.delta());
        if p.lifetime.is_finished() { // `Timer::finished` is gone; use `is_finished`
            commands.entity(entity).despawn();
        } else {
            xf.translation += p.velocity * time.delta_secs();
            p.velocity *= 0.92; // drag
        }
    }
}
```

Fine up to a few hundred particles. Past that, draw-call overhead dominates — switch
to hanabi or collapse into a single `Mesh2d` with a custom material.

## Sprite-sheet flipbooks — `bevy_spritesheet_animation 8.0.1`

`bevy_spritesheet_animation` 8.0.1 (pins `bevy = "^0.20"`) drives `TextureAtlas` index
sequences from `Animation` assets. Best fit: every instance plays the same frames
in order — explosions, hit-sparks, muzzle flashes.

```toml
[dependencies]
bevy = "0.20"
bevy_spritesheet_animation = "8.0.1"
```

Key types (8.x prelude): `SpritesheetAnimationPlugin`, `Spritesheet`, `AnimationBuilder`,
`Animation` (an asset), `Clip`, `SpritesheetAnimation { animation: Handle<Animation>, .. }`.
Build an `Animation` with `AnimationBuilder::new(spritesheet)...build()`, store it in
`Assets<Animation>`, attach `SpritesheetAnimation` to the `Sprite` + `TextureAtlas`
entity, and let the plugin drive the atlas index. The old `AnimationLibrary` /
`AnimationId` API from 6.x is gone.

What it does NOT do: individual particle physics. Every spawned entity plays the same
frame sequence — there is no per-instance velocity or simulation.

## Vector / SDF shapes — `bevy_vector_shapes 0.14.0`

`bevy_vector_shapes` 0.14.0 (pins `bevy = "^0.20"`) renders GPU-accelerated circles, lines,
arcs, and polygons with SDF anti-aliasing.

```toml
[dependencies]
bevy = "0.20"
bevy_vector_shapes = "0.14.0"
```

Key types: `Shape2dPlugin`, `ShapePainter`. Call `painter.circle(radius)`,
`painter.line(start, end)`, `painter.ngon(sides, radius)` in a system; the plugin
batches them into draw calls automatically.

Good for: stylized SFX — shockwave rings, lightning bolts, lock-on reticles, force
fields. The look is crisp and geometric rather than textured.

> **`bevy_prototype_lyon` lags a release.** 0.17.0 pins Bevy 0.19; there is no 0.20
> build at the time of writing. `bevy_vector_shapes` already ships for 0.20.

## Trails

No 0.20-ready trail crate exists. Two viable approaches:

- **`LineList` mesh history** — maintain a ring buffer of the trailing entity's recent
  world positions; rebuild a `LineList` or `TriangleStrip` `Mesh` each frame (or every
  N frames). Full control over width, UV scrolling, fading.
- **`ShapePainter` line strokes** — call `painter.line(prev, cur)` each frame from the
  history buffer. Simpler code; less control over width taper and UVs.

Both approaches are hand-rolled; choose based on how much visual polish the trail needs.

## Decals

No dedicated decal crate targets Bevy 0.20. Bevy's own `ForwardDecal` / clustered
decals (`bevy::pbr::decal`) cover projected decals on PBR geometry; the hand-roll below
is for 2D or non-PBR cases. The hand-roll approach:

1. Spawn a thin quad slightly offset from receiver geometry (or use a `DepthBiasState`).
2. Assign a custom `Material` with `AlphaMode::Blend` (or `Premultiplied`) and a
   decal texture.
3. For projected decals (arbitrary receiver geometry), add a projection matrix uniform
   to the material and clip in the fragment shader.

This is a known gap in the ecosystem. Complexity scales quickly for projected decals —
budget authoring time accordingly.

## See also

- [`../SKILL.md`](../SKILL.md) — top-level bevy-vfx dispatcher
- [`shader-effects.md`](shader-effects.md) — single-quad procedural FX as an
  alternative to particle systems
- [`performance.md`](performance.md) — draw-call cost model for each technique
- `bevy-pbr-materials` — `AsBindGroup`, `AlphaMode`, and custom material registration
- `bevy-wasm-webgpu` — which techniques survive WebGL2 vs WebGPU builds
