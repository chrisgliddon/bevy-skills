# bevy-vfx — Hanabi modifier catalog

> Referenced from `bevy-vfx/SKILL.md § Topics`.

Modifiers are attached to an `EffectAsset` via the builder chain: `.init(m)`,
`.update(m)`, `.render(m)`. Every modifier runs in exactly one context; the
context determines when in the frame it executes.

## Init modifiers — run once at particle spawn

### `SetPositionSphereModifier`

Scatters spawn positions across a sphere's volume or surface.
Fields are `ExprHandle`; construct as a struct literal.

```rust
let m = SetPositionSphereModifier {
    center: writer.lit(Vec3::ZERO).expr(),
    radius: writer.lit(2.0_f32).expr(),
    dimension: ShapeDimension::Volume, // Volume = fill, Surface = shell only
};
```

### `SetPositionCircleModifier`

Same as sphere but confined to a 2D circle (disk or ring).
Fields: `center: ExprHandle`, `axis: ExprHandle` (normal to the circle plane),
`radius: ExprHandle`, `dimension: ShapeDimension`.

### `SetPositionBoxModifier` (0.20)

Spawns inside or on the surface of a box. Same `dimension: ShapeDimension` switch as the
sphere modifier.

### `SetPositionCone3dModifier`

Spawns inside a truncated cone. Fields: `height`, `base_radius`, `top_radius`,
`dimension` — all `ExprHandle`.

### `SetVelocitySphereModifier`

Gives each particle an outward radial velocity from a center point.
Fields are `ExprHandle`; construct as a struct literal.

```rust
let m = SetVelocitySphereModifier {
    center: writer.lit(Vec3::ZERO).expr(),
    speed: writer.lit(4.0_f32).expr(),
};
```

### `SetVelocityCircleModifier`

Radial velocity in a circle's plane. Fields: `center`, `axis`, `speed` — all
`ExprHandle`.

### `SetVelocityTangentModifier`

Tangential velocity relative to a center point (creates spin / vortex).
Fields: `origin`, `axis`, `speed` — all `ExprHandle`.

### `SetAttributeModifier`

Sets any `Attribute` constant to an expression value. Required for `LIFETIME` and
`AGE` (both needed by `ColorOverLifetimeModifier` and `SizeOverLifetimeModifier`).

```rust
// Randomised lifetime in [0.5, 1.5] seconds
let lifetime = SetAttributeModifier::new(
    Attribute::LIFETIME,
    writer.lit(0.5_f32).uniform(writer.lit(1.5_f32)).expr(),
);
// AGE must also be initialized or ColorOverLifetimeModifier causes a shader error
let age = SetAttributeModifier::new(Attribute::AGE, writer.lit(0.0_f32).expr());
```

Common attributes: `LIFETIME`, `AGE`, `POSITION`, `VELOCITY`, `SIZE`, `COLOR`,
`SPRITE_INDEX`.

## Update modifiers — run every simulation tick on every alive particle

Lifetime decrement happens implicitly when `Attribute::LIFETIME` is set; you do not
need a modifier for it.

### `AccelModifier`

Applies a constant acceleration vector (e.g. gravity). Takes a `Vec3` `ExprHandle`.

```rust
let gravity = AccelModifier::new(writer.lit(Vec3::new(0.0, -9.8, 0.0)).expr());
```

### `RadialAccelModifier`

Accelerates each particle toward or away from an origin point. Use `::new(origin,
accel)` with two `ExprHandle`s, or `::constant(module, origin, accel_f32)` for fixed
values.

```rust
let radial = RadialAccelModifier::constant(&mut module, Vec3::ZERO, 3.0_f32);
```

### `TangentAccelModifier`

Accelerates tangentially around an axis (swirling motion).
Constructor mirrors `RadialAccelModifier`: `::new(origin, axis, accel)`.

### `LinearDragModifier`

Reduces particle speed each tick proportional to velocity. Takes an `ExprHandle` for
the drag coefficient (or use `::constant(module, drag_f32)`).

```rust
let drag = LinearDragModifier::new(writer.lit(0.3_f32).expr());
```

Multiple update modifiers of the same type stack: two `AccelModifier`s produce the sum
of their accelerations.

## Render modifiers — run at draw time (per particle, per frame)

Render modifiers do not mutate simulation state; they compute per-particle visual
output. Order within the render stage is deterministic by insertion order on
`EffectAsset`.

### `ColorOverLifetimeModifier`

Looks up a `Gradient<Vec4>` at `age / lifetime`. Requires **both** `Attribute::AGE`
and `Attribute::LIFETIME` to be initialized in Init; omitting `AGE` causes a runtime
shader compile error.

```rust
let mut grad: bevy_hanabi::Gradient<Vec4> = bevy_hanabi::Gradient::new();
grad.add_key(0.0, Vec4::new(4.0, 0.5, 0.0, 1.0)); // birth: bright orange
grad.add_key(1.0, Vec4::new(0.5, 0.5, 0.5, 0.0)); // death: transparent
let color = ColorOverLifetimeModifier::new(grad);
```

### `SizeOverLifetimeModifier`

Scales particle size over lifetime via a `Gradient<Vec3>`. Field
`screen_space_size: bool` switches between world-unit and screen-pixel sizing. Also
requires `AGE` + `LIFETIME`.

### `ParticleTextureModifier`

Applies a texture to each particle. Since hanabi 0.20 the slot is a plain `u32` fixed at
module build time: `ParticleTextureModifier::new(slot_index)`. Register the slot with
`module.add_texture_slot(name, SlotDimension::D2)` and bind the image through the
`EffectMaterial { images: vec![...] }` component on the effect entity. Passing an
`ExprHandle` is the stale 0.18 shape. See [`hanabi-2d-vs-3d.md`](hanabi-2d-vs-3d.md).

### `OrientModifier`

Controls billboard orientation. See [`hanabi-2d-vs-3d.md`](hanabi-2d-vs-3d.md) for
`OrientMode` variants. Field `rotation: Option<ExprHandle>` adds in-plane rotation.

```rust
use bevy_hanabi::prelude::{OrientModifier, OrientMode};
let orient = OrientModifier {
    mode: OrientMode::ParallelCameraDepthPlane,
    rotation: None,
};
```

### `KillFrustumModifier` (0.20)

Kills particles outside the main camera frustum. Tag exactly one camera with
`HanabiMainCamera` or the modifier has nothing to cull against.

### `FlipbookModifier`

Animates a sprite sheet over particle lifetime. The modifier reads
`Attribute::SPRITE_INDEX` to pick the current frame; pair it with an
`SetAttributeModifier` that maps `age / lifetime` to a frame index. See
[`hanabi-2d-vs-3d.md`](hanabi-2d-vs-3d.md) for details.

## Composition rules

- **Order within a context** matters for render modifiers (later overrides earlier
  for the same output channel). For init and update modifiers, order rarely matters
  unless one modifier depends on an attribute set by another.
- **Multiple modifiers of the same type are allowed.** Two `AccelModifier`s produce
  the vector sum of their accelerations.
- **Init runs once per particle**, at spawn time, not every frame.
- **Update runs every simulation tick** for every alive particle (respects
  `FixedUpdate` timestep when simulation is fixed-step).
- **Render is the shading stage** — it does not affect velocity or position.

## `ShapeDimension`

| Variant | Effect |
|---|---|
| `ShapeDimension::Volume` | Fills the entire ball / disk / cone interior uniformly |
| `ShapeDimension::Surface` | Restricts particles to the outer shell (ring / sphere surface) |

`Surface` is useful for effects where all particles must originate from a shell
boundary (e.g. an expanding shockwave ring).

## See also

- [`../SKILL.md`](../SKILL.md) — top-level bevy-vfx skill
- [`hanabi-anatomy.md`](hanabi-anatomy.md) — `ExprWriter`, `EffectAsset` compile flow
- [`hanabi-2d-vs-3d.md`](hanabi-2d-vs-3d.md) — `OrientMode`, flipbook, 2D vs 3D flags
- `bevy-pbr-materials` — `StandardMaterial` emissive / alpha for non-particle glow fx
- `bevy-ecs-systems` — scheduling simulation vs render system ordering
