---
name: bevy-vfx
description: Use when adding GPU particles via `bevy_hanabi 0.20.0` (`HanabiPlugin`, `EffectAsset`, `ParticleEffect`, `ExprWriter`, `SpawnerSettings`, modifiers like `SetPositionSphereModifier` / `ColorOverLifetimeModifier`), rendering Gaussian splats via `bevy_spark`, picking between hanabi and `bevy_spritesheet_animation` flipbooks or `bevy_vector_shapes`, writing custom `Material` + `.wesl` shaders for fire/water/distortion, or budgeting GPU costs and WebGPU compatibility in Bevy 0.20.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "4"
  area: render
  bevy_version: "0.20"
---

# Bevy 0.20 — VFX (particles, shaders, Gaussian splats)

## Compatibility status (checked on crates.io, 2026-11-03)

| Crate | Version | Pins Bevy | Status |
|---|---|---|---|
| `bevy_hanabi` | 0.20.0 (2026-11-01) | `^0.20` | Use it. WESL shaders, batched instances. |
| `bevy_spritesheet_animation` | 8.0.1 | `^0.20` | Use it. |
| `bevy_vector_shapes` | 0.14.0 | `^0.20` | Use it. |
| `bevy_spark` | 0.2.0 (2026-05-04) | `^0.18` | **No 0.19/0.20 release.** Snippets stay pinned to 0.18. |
| `bevy_prototype_lyon` | 0.17.0 | `^0.19` | Lags one release. Prefer `bevy_vector_shapes`. |

`bevy_hanabi` needs compute shaders: WebGPU only on WASM, no WebGL2. `bevy_spark` has a
`webgl2` feature. Custom `Material` shaders and flipbooks work on both targets.

## When to use this skill

- Spawning a GPU particle effect via `bevy_hanabi` — emitters, modifiers, gradients.
- Picking a modifier for a behaviour (radial burst, colour-over-lifetime, drag).
- Choosing between hanabi, `bevy_spritesheet_animation` flipbooks, or custom-material shaders.
- Loading and rendering a `.spz` Gaussian-splat scene via `bevy_spark` (0.18 only for now).
- Debugging "my effect doesn't show in WASM" — usually the WebGPU vs WebGL2 gotcha.
- Hanabi custom shader fails to load after 0.20 — naga_oil `#import` must become WESL.

## Canonical end-to-end pattern

API verified against the `bevy_hanabi 0.20.0` source. Not compiled in the tester crate
(third-party dependency); every symbol below exists in that release.

```rust
use bevy::prelude::*;
// Do NOT use `bevy_hanabi::prelude::*` — `Gradient` name-collides with
// `bevy::prelude::Gradient` (bevy_ui's CSS gradient). Import explicitly:
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

    // ExprWriter accumulates shader expression nodes into a Module.
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

    // Init: LIFETIME recycles particles; AGE is read by ColorOverLifetimeModifier.
    let init_lifetime = SetAttributeModifier::new(
        Attribute::LIFETIME,
        writer.lit(0.5_f32).uniform(writer.lit(1.5_f32)).expr(),
    );
    let init_age = SetAttributeModifier::new(Attribute::AGE, writer.lit(0.0_f32).expr());

    // Update: constant downward acceleration.
    let update_gravity = AccelModifier::new(writer.lit(Vec3::new(0.0, -6.0, 0.0)).expr());

    // Render: red → orange → transparent over lifetime.
    let mut color: bevy_hanabi::Gradient<Vec4> = bevy_hanabi::Gradient::new();
    color.add_key(0.0, Vec4::new(4.0, 0.5, 0.0, 1.0));
    color.add_key(0.5, Vec4::new(2.0, 1.0, 0.0, 0.8));
    color.add_key(1.0, Vec4::new(0.5, 0.5, 0.5, 0.0));
    let render_color = ColorOverLifetimeModifier::new(color);

    // Spawner: 200 particles/sec. There is no `Spawner` struct; use SpawnerSettings.
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

    // ParticleEffect is a bare component; #[require(...)] adds CompiledParticleEffect etc.
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
| `EffectAsset`, `Module` / `ExprWriter`, `SpawnerSettings`, the bare-component spawn pattern | [references/hanabi-anatomy.md](references/hanabi-anatomy.md) |
| Modifier catalog grouped by context (Init / Update / Render), 0.20 additions | [references/hanabi-modifiers.md](references/hanabi-modifiers.md) |
| 2D sprite particles vs 3D billboards, `OrientModifier`, `FlipbookModifier`, texture slots | [references/hanabi-2d-vs-3d.md](references/hanabi-2d-vs-3d.md) |
| When NOT to use hanabi — CPU particles, flipbooks, vector shapes, trails, decals | [references/non-hanabi-vfx.md](references/non-hanabi-vfx.md) |
| Custom `Material` + WESL effects (fire / water / distortion) | [references/shader-effects.md](references/shader-effects.md) |
| `bevy_spark` Gaussian-splat rendering (Bevy 0.18 pin) | [references/gaussian-splats.md](references/gaussian-splats.md) |
| GPU budgets, WASM/WebGPU caveats, profiling, mixing techniques | [references/performance.md](references/performance.md) |

## Picking the right VFX technique

| Need | Reach for |
|---|---|
| Thousands of small moving particles | `bevy_hanabi` → [hanabi-anatomy.md](references/hanabi-anatomy.md) |
| One localised animated effect (single fire, water surface) | Custom `Material` + WESL → [shader-effects.md](references/shader-effects.md) |
| Canned explosion / hit-spark, identical every time | Flipbook via `bevy_spritesheet_animation` → [non-hanabi-vfx.md](references/non-hanabi-vfx.md) |
| Tiny counts (<100) or WebGL2 | CPU particles → [non-hanabi-vfx.md](references/non-hanabi-vfx.md) |
| Photoreal scene capture | `bevy_spark` (0.18 only) → [gaussian-splats.md](references/gaussian-splats.md) |
| Stylised geometric SFX (rings, lightning) | `bevy_vector_shapes` → [non-hanabi-vfx.md](references/non-hanabi-vfx.md) |

## Gotchas

### 0.19 → 0.20

- **Hanabi shaders are WESL.** Custom shader code using naga_oil `#import` / `#ifdef` must become `import ...;` / `@if(...)`. The common module is now `bevy_hanabi::render::vfx_common` (was `bevy_hanabi::vfx_common`). Same rule for your own `Material` shaders — see `bevy-pbr-materials`.
- **`ParticleTextureModifier::new(slot: u32)`** takes a slot index fixed at module build time. Passing an expression (`writer.lit(...)`) is the stale 0.18 shape. `TextureSampleExpr::image` is now `slot_index`.
- **Same-effect instances batch** into one compute dispatch. Reuse one `EffectAsset` for many emitters.
- **New in 0.20:** `HanabiMainCamera` (tag exactly one camera), `KillFrustumModifier`, `SetPositionBoxModifier`, `TextureLoadExpr`, 1D/3D/array/cube texture slots.
- **`Sprite` now renders through `Mesh2d` + `SpriteMaterial`** and has an `alpha_mode` field. CPU sprite particles can pick `Opaque` / `Mask` to skip the transparent pass.
- **Bevy's `RenderGraph` nodes are gone (0.19).** Custom passes are systems in `Core2d` / `Core3d`.

### 0.18 → 0.19 (hanabi 0.19)

- **`EffectAsset::mesh` is `Option<AssetPath>`**, not a handle. Per-instance mesh override is the `EffectMesh` component.
- **`serde` / `typetag` features removed**; serialization is always on via `EffectAsset::serialize`.

### Still true

- **`SpawnerSettings::rate(...)`, not `Spawner::rate`.** `Spawner` does not exist.
- **`ParticleEffect` is a bare component**; `ParticleEffectBundle` is gone.
- **`ExprWriter::lit(v)` returns `WriterExpr`.** Call `.expr()` for the `ExprHandle` modifiers take.
- **`ColorOverLifetimeModifier` needs `Attribute::AGE` initialised** alongside `LIFETIME`.
- **`bevy_hanabi::Gradient` collides with `bevy::prelude::Gradient`.** Import hanabi items explicitly.
- **`bevy_spark` loads `.spz` only**, colour is baked (no Bevy lighting), and it has not moved past Bevy 0.18.
- **No 0.20-ready trail or decal crate.** Hand-roll or use `bevy_vector_shapes`.

## See also

- [`bevy-pbr-materials`](../bevy-pbr-materials/SKILL.md) — custom `Material` + WESL shader path and the naga_oil → WESL table.
- [`bevy-cameras`](../bevy-cameras/SKILL.md) — camera framing; `HanabiMainCamera` tags the camera hanabi culls against.
- [`bevy-wasm-webgpu`](../bevy-wasm-webgpu/SKILL.md) — hanabi needs WebGPU; `bevy_spark` has a `webgl2` feature.
- [`bevy-animation`](../bevy-animation/SKILL.md) — `EasingCurve` / `EaseFunction` for procedural FX without particles.
- [`bevy-migration-0-19-to-0-20`](../bevy-migration-0-19-to-0-20/SKILL.md) — WESL shader translation.
