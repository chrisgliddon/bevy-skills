# bevy-vfx — Hanabi anatomy: the five participants and the compile flow

> Referenced from `bevy-vfx/SKILL.md § Topics`.

## The five participants

| Participant | Role |
|---|---|
| `HanabiPlugin` | Registers simulation + render infrastructure. Must be added after `DefaultPlugins`. |
| `EffectAsset` | The reusable blueprint — capacity, spawner config, expression module, and modifier chains. Stored in `Assets<EffectAsset>`. |
| `Handle<EffectAsset>` | A lightweight clone-able reference to the asset. Multiple entities can share one `EffectAsset`. |
| `ParticleEffect` | Component that links a world entity to a specific `EffectAsset` handle. Spawned with `Transform` + `Visibility`. |
| `ExprWriter` + `Module` | The expression compiler. `ExprWriter` accumulates WGSL expression nodes; `writer.finish()` consumes it and returns a `Module` passed into `EffectAsset::new`. |

## The compile flow

```
ExprWriter::new()
  ↓  writer.lit(v)           → WriterExpr
  ↓  writer_expr.expr()      → ExprHandle  (required by modifier fields)
  ↓  assemble modifiers using ExprHandles
  ↓  writer.finish()         → Module
  ↓
EffectAsset::new(capacity, spawner, module)
  .with_name("label")
  .init(init_modifier)       // runs once per particle at spawn
  .update(update_modifier)   // runs every simulation tick
  .render(render_modifier)   // runs at draw time
  ↓
effects.add(effect)          → Handle<EffectAsset>
  ↓
commands.spawn(...)          // ParticleEffect::new(handle) + Transform + Visibility
```

## Why `ParticleEffect` is a bare component

In 0.18 `ParticleEffectBundle` was removed. `ParticleEffect` itself carries
`#[require(CompiledParticleEffect, Transform, Visibility, VisibilityClass, SyncToRenderWorld)]`,
so Bevy's required-components system inserts those six components automatically. You only
need to provide the ones where you want non-default values:

```rust
commands.spawn((
    Name::new("emitter"),
    ParticleEffect::new(handle),
    Transform::default(),    // world-space position; override to place the emitter
    Visibility::default(),   // inherited from scene; override to hide at startup
));
```

## `SpawnerSettings` modes

`SpawnerSettings::rate(n.into())` — continuous stream at *n* particles per second.

```rust
let spawner = SpawnerSettings::rate(200.0_f32.into());
```

`SpawnerSettings::burst(count, period)` — emit *count* particles at the start of each
*period*-second cycle, indefinitely.

```rust
let spawner = SpawnerSettings::burst(50.0_f32.into(), 2.0_f32.into());
```

`SpawnerSettings::once(count)` — emit *count* particles once in a single frame, then stop.

```rust
let spawner = SpawnerSettings::once(100.0_f32.into());
```

All three take `CpuValue<f32>`, created by calling `.into()` on a `f32`. `CpuValue` can
also express random ranges — see [docs.rs/bevy_hanabi/0.18.0](https://docs.rs/bevy_hanabi/0.18.0/bevy_hanabi/enum.CpuValue.html).

## `ExprWriter` deep-dive

`ExprWriter` accumulates a directed expression graph. All methods return `WriterExpr`,
**not** `ExprHandle`. Modifier struct fields expect `ExprHandle` — call `.expr()` to
convert:

```rust
let writer = ExprWriter::new();

// lit(v) — constant value of any type supported by the WGSL backend
let pos_expr: ExprHandle = writer.lit(Vec3::ZERO).expr();

// uniform(max) — uniform random in [base, max], resampled per particle
let life_expr: ExprHandle = writer.lit(0.5_f32).uniform(writer.lit(1.5_f32)).expr();

// attr(attribute) — reads a per-particle attribute value
// (useful for expressions that reference the particle's own state)
let age_expr: ExprHandle = writer.attr(Attribute::AGE).expr();

// finish() consumes the writer and returns the compiled Module
let module = writer.finish();  // call AFTER all expressions are built
```

Calling `writer.lit(...)` after `writer.finish()` panics. Build all expressions first.

## Worked example (verified against `bevy_hanabi = "0.18.0"`)

```rust
use bevy::prelude::*;
use bevy_hanabi::prelude::{
    AccelModifier, Attribute, ColorOverLifetimeModifier, EffectAsset, ExprWriter,
    HanabiPlugin, ParticleEffect, SetAttributeModifier, SetPositionSphereModifier,
    SetVelocitySphereModifier, ShapeDimension, SpawnerSettings,
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

    let writer = ExprWriter::new();

    let init_pos = SetPositionSphereModifier {
        center: writer.lit(Vec3::ZERO).expr(),
        radius: writer.lit(1.0_f32).expr(),
        dimension: ShapeDimension::Volume,
    };
    let init_vel = SetVelocitySphereModifier {
        center: writer.lit(Vec3::ZERO).expr(),
        speed: writer.lit(4.0_f32).expr(),
    };
    let init_lifetime = SetAttributeModifier::new(
        Attribute::LIFETIME,
        writer.lit(0.5_f32).uniform(writer.lit(1.5_f32)).expr(),
    );
    let init_age = SetAttributeModifier::new(Attribute::AGE, writer.lit(0.0_f32).expr());
    let gravity = AccelModifier::new(writer.lit(Vec3::new(0.0, -6.0, 0.0)).expr());

    let mut grad: bevy_hanabi::Gradient<Vec4> = bevy_hanabi::Gradient::new();
    grad.add_key(0.0, Vec4::new(4.0, 0.5, 0.0, 1.0));
    grad.add_key(1.0, Vec4::new(0.5, 0.5, 0.5, 0.0));
    let color = ColorOverLifetimeModifier::new(grad);

    let module = writer.finish();

    let handle = effects.add(
        EffectAsset::new(16384, SpawnerSettings::rate(200.0_f32.into()), module)
            .with_name("ember")
            .init(init_pos).init(init_vel).init(init_lifetime).init(init_age)
            .update(gravity)
            .render(color),
    );

    commands.spawn((
        Name::new("ember"),
        ParticleEffect::new(handle),
        Transform::default(),
        Visibility::default(),
    ));
}
```

## See also

- [`../SKILL.md`](../SKILL.md) — top-level bevy-vfx skill
- [`hanabi-modifiers.md`](hanabi-modifiers.md) — modifier catalog by context
- [`hanabi-2d-vs-3d.md`](hanabi-2d-vs-3d.md) — feature flags, orient modes, flipbook
- `bevy-custom-assets` — `AssetLoader` patterns if you serialize `EffectAsset` to RON
- `bevy-ecs-components` — required-components mechanics behind `ParticleEffect`
