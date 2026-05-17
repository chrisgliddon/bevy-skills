---
name: bevy-vfx
description: Use when adding GPU particles via `bevy_hanabi 0.18.0` (`HanabiPlugin`, `EffectAsset`, `ParticleEffect`, `Module` + `ExprWriter`, modifiers like `SetPositionSphereModifier` / `ColorOverLifetimeModifier`), rendering Gaussian splats via `bevy_spark 0.2.0` for photoreal scene captures, picking between hanabi and lighter sprite-sheet flipbooks, writing custom `Material` + WGSL shaders for fire/water/distortion, or budgeting GPU costs and WebGPU compatibility in Bevy 0.18.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "4"
  area: render
  bevy_version: "0.18"
---

# Bevy 0.18 — VFX (particles, shaders, Gaussian splats)

## Compatibility status

Both major VFX crates pin Bevy 0.18 cleanly — no patches required (unlike `bevy_capture`):

- `bevy_hanabi = "0.18.0"` (published 2026-02-01) for GPU-compute particles.
- `bevy_spark = "0.2.0"` (published 2026-05-04, repo `htdt/bevy_spark`) for Gaussian-splat rendering.

Both require **WebGPU** in WASM builds — there is no WebGL2 path. Custom `Material` shaders and `bevy_spritesheet_animation` work on both targets.

## When to use this skill

- Spawning a GPU particle effect via `bevy_hanabi` — emitters, modifiers, gradients.
- Picking a specific modifier for a behaviour (radial burst, color-over-lifetime, drag).
- Choosing between hanabi vs `bevy_spritesheet_animation` flipbooks vs custom-material shaders.
- Loading and rendering a `.spz` Gaussian-splat scene via `bevy_spark`.
- Debugging "my effect doesn't show in WASM" — usually the WebGPU vs WebGL2 gotcha.
- Budgeting GPU cost across particle counts, splat counts, and shader-effect coverage.

## Canonical end-to-end pattern

Verified against `bevy = "0.18"` + `bevy_hanabi = "0.18.0"` — `cargo check` clean in `bevy-skills-tester/skill-snippets/examples/bevy_particle_effects.rs`.

```rust
use bevy::prelude::*;
// Do NOT use `bevy_hanabi::prelude::*` — `Gradient` name-collides with
// `bevy::prelude::Gradient` (bevy_ui's CSS Gradient in 0.18). Import explicitly:
use bevy_hanabi::prelude::{
    AccelModifier, Attribute, ColorOverLifetimeModifier, EffectAsset, ExprWriter, HanabiPlugin,
    ParticleEffect, SetAttributeModifier, SetPositionSphereModifier, SetVelocitySphereModifier,
    ShapeDimension, SpawnerSettings,
};

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_plugins(HanabiPlugin)
        .add_systems(Startup, setup)
        .run();
}

fn setup(mut commands: Commands, mut effects: ResMut<Assets<EffectAsset>>) {
    commands.spawn((
        Camera3d::default(),
        Transform::from_xyz(0.0, 3.0, 20.0).looking_at(Vec3::ZERO, Vec3::Y),
    ));

    // ExprWriter accumulates WGSL expression nodes into a Module.
    // lit() returns WriterExpr — call .expr() to get the ExprHandle modifiers need.
    let writer = ExprWriter::new();

    // Init: scatter particles across a sphere's volume + push outward.
    let init_pos = SetPositionSphereModifier {
        center: writer.lit(Vec3::ZERO).expr(),
        radius: writer.lit(1.0_f32).expr(),
        dimension: ShapeDimension::Volume,
    };
    let init_vel = SetVelocitySphereModifier {
        center: writer.lit(Vec3::ZERO).expr(),
        speed: writer.lit(4.0_f32).expr(),
    };

    // Init: LIFETIME is required to recycle particles.
    // Init: AGE is required because ColorOverLifetimeModifier reads age/lifetime.
    let init_lifetime = SetAttributeModifier::new(
        Attribute::LIFETIME,
        writer.lit(0.5_f32).uniform(writer.lit(1.5_f32)).expr(),
    );
    let init_age = SetAttributeModifier::new(Attribute::AGE, writer.lit(0.0_f32).expr());

    // Update: constant downward acceleration.
    let update_gravity = AccelModifier::new(writer.lit(Vec3::new(0.0, -6.0, 0.0)).expr());

    // Render: red → orange → transparent over lifetime.
    // Fully qualified: bevy_hanabi::Gradient (not bevy::prelude::Gradient).
    let mut color: bevy_hanabi::Gradient<Vec4> = bevy_hanabi::Gradient::new();
    color.add_key(0.0, Vec4::new(4.0, 0.5, 0.0, 1.0));
    color.add_key(0.5, Vec4::new(2.0, 1.0, 0.0, 0.8));
    color.add_key(1.0, Vec4::new(0.5, 0.5, 0.5, 0.0));
    let render_color = ColorOverLifetimeModifier::new(color);

    // Spawner: 200 particles/sec continuous stream. NOTE: Spawner::rate
    // does NOT exist in 0.18 — use SpawnerSettings::rate(n.into()).
    let spawner = SpawnerSettings::rate(200.0_f32.into());

    // finish() consumes the writer, producing the Module passed to EffectAsset::new.
    let module = writer.finish();

    let effect = EffectAsset::new(16384, spawner, module)
        .with_name("ember_burst")
        .init(init_pos)
        .init(init_vel)
        .init(init_lifetime)
        .init(init_age)
        .update(update_gravity)
        .render(render_color);
    let handle = effects.add(effect);

    // ParticleEffect is a bare component in 0.18 — no ParticleEffectBundle.
    // #[require(CompiledParticleEffect, ...)] fills in the rest automatically.
    commands.spawn((
        Name::new("ember_burst"),
        ParticleEffect::new(handle),
        Transform::default(),
        Visibility::default(),
    ));
}
```

## Topics

| Topic | Reference |
|---|---|
| `EffectAsset`, `Module` / `ExprWriter`, `Spawner` settings, the bare-component spawn pattern | [references/hanabi-anatomy.md](references/hanabi-anatomy.md) |
| Full modifier catalog grouped by `ModifierContext` (Init / Update / Render) | [references/hanabi-modifiers.md](references/hanabi-modifiers.md) |
| 2D sprite particles vs 3D billboards/meshes, `OrientModifier`, `FlipbookModifier` | [references/hanabi-2d-vs-3d.md](references/hanabi-2d-vs-3d.md) |
| When NOT to use hanabi — CPU particles, sprite-sheet flipbooks, vector shapes, trails, decals | [references/non-hanabi-vfx.md](references/non-hanabi-vfx.md) |
| Custom `Material` + WGSL effects (fire / water / distortion) as alternative to particles | [references/shader-effects.md](references/shader-effects.md) |
| `bevy_spark` Gaussian-splat rendering: `SparkPlugin`, `Splats`, `SplatCloud`, `.spz` loading | [references/gaussian-splats.md](references/gaussian-splats.md) |
| GPU budgets, WASM/WebGPU caveats, profiling, mixing techniques | [references/performance.md](references/performance.md) |

## Picking the right VFX technique

| Need | Reach for |
|---|---|
| Thousands of small moving particles | `bevy_hanabi` → [hanabi-anatomy.md](references/hanabi-anatomy.md) |
| One localised animated effect (single fire, water surface) | Custom `Material` + WGSL → [shader-effects.md](references/shader-effects.md) |
| Canned explosion / hit-spark, identical every time | Sprite-sheet flipbook via `bevy_spritesheet_animation` → [non-hanabi-vfx.md](references/non-hanabi-vfx.md) |
| Tiny counts (<100) or need WebGL2 support | CPU particles → [non-hanabi-vfx.md](references/non-hanabi-vfx.md) |
| Photoreal scene capture / "the world is the asset" | `bevy_spark` Gaussian splats → [gaussian-splats.md](references/gaussian-splats.md) |
| Stylised geometric SFX (rings, lightning) | `bevy_vector_shapes` → [non-hanabi-vfx.md](references/non-hanabi-vfx.md) |

## Gotchas

- **`SpawnerSettings::rate(...)` — not `Spawner::rate`.** The `Spawner` struct does NOT exist in `bevy_hanabi 0.18`. The whole emission API is on `SpawnerSettings`.
- **`ParticleEffect` is a bare component**, not a bundle. `ParticleEffectBundle` was removed in 0.18. Spawn `ParticleEffect::new(handle)` alongside `Transform::default()` + `Visibility::default()`; the `#[require(...)]` attribute fills in `CompiledParticleEffect`, `VisibilityClass`, `SyncToRenderWorld`.
- **`ExprWriter::lit(v)` returns `WriterExpr`, NOT `ExprHandle`.** Call `.expr()` to get the `ExprHandle` that modifier fields expect.
- **`ColorOverLifetimeModifier` requires `Attribute::AGE` to be initialized** alongside `LIFETIME`. Omitting `AGE` causes a runtime shader error reading undefined memory.
- **`bevy_hanabi::Gradient` name-collides with `bevy::prelude::Gradient`** — the latter is `bevy_ui`'s CSS gradient enum added in 0.18. Do NOT `use bevy_hanabi::prelude::*` blindly. Either list specific imports (see the snippet above) or qualify `Gradient` everywhere.
- **WebGPU only.** Both `bevy_hanabi` and `bevy_spark` require compute shaders / WebGPU. WebGL2 builds will fail. Target `wasm32-unknown-unknown` with Bevy's `webgpu` feature, not `webgl2`. See `bevy-wasm-webgpu`.
- **`bevy_spark` loads `.spz` files**, not `.ply` or `.splat` — convert via the `gsplat` Python toolchain or similar capture-pipeline tools. The crate ships an `SpzLoader` asset loader.
- **Splat colour is baked.** Gaussian-splat scenes don't respond to Bevy lighting. If you need dynamic lighting on a captured scene, you need a different representation.
- **`bevy_prototype_lyon` is abandoned for 0.18.** Don't reach for it — last release pins 0.17. Use `bevy_vector_shapes 0.12.0` instead for stylised geometric SFX.
- **No 0.18-ready trail or decal crate exists.** Hand-roll or use `bevy_vector_shapes` for trails. Decals: custom material + alpha blending.

## See also

- [`bevy-pbr-materials`](../bevy-pbr-materials/SKILL.md) — required for the custom-`Material` + WGSL shader path; covers the 0.18 `AsBindGroup::label()` requirement.
- [`bevy-cameras`](../bevy-cameras/SKILL.md) — camera framing for VFX composition; especially relevant for Gaussian-splat scenes where camera *is* the user experience.
- [`bevy-wasm-webgpu`](../bevy-wasm-webgpu/SKILL.md) — the WebGPU caveat: hanabi and splats both require WebGPU; neither runs on WebGL2.
- [`bevy-animation`](../bevy-animation/SKILL.md) — `EasingCurve` / `EaseFunction` toolkit if you want simple procedural FX without particles.
- [`bevy-cargo-features`](../bevy-cargo-features/SKILL.md) — picking the right `bevy_hanabi` feature flags (`2d`, `3d`) and bundle-size considerations.
