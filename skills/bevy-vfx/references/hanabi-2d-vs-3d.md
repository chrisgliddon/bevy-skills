# bevy-vfx — Hanabi 2D vs 3D, orient modes, and flipbook

> Referenced from `bevy-vfx/SKILL.md § Topics`.

## Feature flags

`bevy_hanabi = "0.20.0"` ships **five** Cargo features. Both `2d` and `3d` are enabled
by default:

```toml
[dependencies]
bevy_hanabi = "0.20.0"           # 2d + 3d both on (default)

# 3D-only — saves compiling the 2D render path
bevy_hanabi = { version = "0.20.0", default-features = false, features = ["3d"] }

# 2D-only
bevy_hanabi = { version = "0.20.0", default-features = false, features = ["2d"] }
```

The other default feature is `gpu_tests`. The non-default feature is `trace`. The
`serde` and `typetag` features were removed in 0.19 (serialization is always on).

The `2d` and `3d` flags gate the respective render pipeline registration inside
`HanabiPlugin`. Disabling the one you don't use shrinks compile time slightly; there is
no runtime API difference between the two.

## 2D billboard particles vs 3D billboard particles

In both 2D and 3D modes every particle is, by default, a camera-facing quad
(billboard). The difference is which Bevy render pipeline they live in:

- **3D** — particles draw in the main 3D render pass alongside `Mesh3d` geometry.
  Depth testing against the scene is active. Use `Camera3d`.
- **2D** — particles draw in the 2D render pass, sorted by Z as sprites. Use
  `Camera2d`. Depth testing against 3D meshes does not apply.

A single `EffectAsset` can only be used in the pass matching the active camera type.
Do not mix a 3D camera with an effect that was authored for 2D or vice versa.

## `OrientModifier` and `OrientMode`

`OrientModifier` controls how each particle quad is rotated to face the viewer.

```rust
use bevy_hanabi::prelude::{OrientModifier, OrientMode};

// Default — flat billboard parallel to the camera depth planes (cheapest)
let orient = OrientModifier {
    mode: OrientMode::ParallelCameraDepthPlane,
    rotation: None,
};

// True billboard — each particle's Z axis points at the camera position
// (slightly more expensive; better for wide-angle or oblique views)
let orient = OrientModifier {
    mode: OrientMode::FaceCameraPosition,
    rotation: None,
};

// Velocity-aligned — local X axis follows the particle's velocity vector
// (rocket trails, speed lines; any rotation: modifier is ignored in this mode)
let orient = OrientModifier {
    mode: OrientMode::AlongVelocity,
    rotation: None,
};
```

`OrientMode` variants verified against the `bevy_hanabi` 0.20.0 source
(`OrientModifier::new(mode)` is the shorthand constructor):

| Variant | Local axes | Cost | Typical use |
|---|---|---|---|
| `ParallelCameraDepthPlane` | XY parallel to near/far planes | Lowest | General-purpose billboards |
| `FaceCameraPosition` | Z points at camera world position | Medium | Oblique or VR cameras |
| `AlongVelocity` | X along velocity; Y from camera × vel | Low | Trails, sparks, bolts |

The optional `rotation: Option<ExprHandle>` field adds an in-plane `f32` rotation in
radians on top of the mode — useful for randomised spin:

```rust
let orient = OrientModifier {
    mode: OrientMode::ParallelCameraDepthPlane,
    rotation: Some(writer.lit(0.0_f32).uniform(writer.lit(std::f32::consts::TAU)).expr()),
};
```

## `FlipbookModifier` — animated sprite sheets

`FlipbookModifier` turns each particle into one frame of a sprite atlas. The modifier
itself does not advance the frame; it reads `Attribute::SPRITE_INDEX` (an integer) and
maps it to a UV region of the bound texture.

```rust
use bevy_hanabi::prelude::{FlipbookModifier, ParticleTextureModifier};
use bevy::math::UVec2;

// A 4×4 sprite sheet = 16 explosion frames
let flipbook = FlipbookModifier { sprite_grid_size: UVec2::new(4, 4) };
```

To animate, update `SPRITE_INDEX` over time with a `SetAttributeModifier` in the
Update context, typically by mapping `age / lifetime * frame_count` to an integer:

```rust
// pseudo-code; cast age-ratio to u32 to step through frames
let frame_count = writer.lit(16.0_f32);
let index_expr = (writer.attr(Attribute::AGE) / writer.attr(Attribute::LIFETIME)
    * frame_count).cast_u32().expr();
let advance = SetAttributeModifier::new(Attribute::SPRITE_INDEX, index_expr);
```

`FlipbookModifier` must be paired with `ParticleTextureModifier` so the GPU knows
which texture to sample. Since 0.20 the slot index is a `u32` fixed at build time:

```rust
use bevy_hanabi::prelude::{EffectMaterial, SlotDimension};

// In setup, before writer.finish(): register a 2D texture slot on the module.
let mut module = writer.finish();
let _slot = module.add_texture_slot("explosion", SlotDimension::D2);
let tex_mod = ParticleTextureModifier::new(0); // slot index 0
```

Then bind the actual texture on the particle entity:

```rust
commands.spawn((
    ParticleEffect::new(handle),
    EffectMaterial { images: vec![asset_server.load("textures/explosion.png")] },
));
```

0.20 also supports 1D, 3D, 2D-array, cube and depth slots (`SlotDimension`) and a
non-sampling `TextureLoadExpr` usable from every pass.

## `ParticleTextureModifier` — static texture

Without `FlipbookModifier`, `ParticleTextureModifier` applies a single texture to every
particle (soft glow circle, snowflake, etc.):

```rust
let _slot = module.add_texture_slot("glow", SlotDimension::D2);
let tex = ParticleTextureModifier::new(0);
```

The `sample_mapping: ImageSampleMapping` field defaults to modulating the particle
color by the texture sample. Override it if you need alpha-only or full-replace mapping.

## 3D mesh particles

Hanabi's default particle is always a quad billboard. True instanced-mesh particles
(each particle renders a 3D mesh) use `EffectAsset::mesh` (an `AssetPath` since 0.19)
or the per-instance `EffectMesh` component. Billboard quads remain the default and
cover most VFX use cases.

## Sprite-sheet alternative (non-hanabi)

For sprite-flipbook explosions that are *not* GPU particle systems, see the
[`non-hanabi-vfx.md`](non-hanabi-vfx.md) for the `bevy_spritesheet_animation`
approach, which operates on ordinary `Sprite` entities.

## See also

- [`../SKILL.md`](../SKILL.md) — top-level bevy-vfx skill
- [`hanabi-modifiers.md`](hanabi-modifiers.md) — `OrientModifier`, `FlipbookModifier` in the modifier catalog
- [`hanabi-anatomy.md`](hanabi-anatomy.md) — `EffectAsset` build flow and `SpawnerSettings`
- `bevy-cameras` — `Camera2d` vs `Camera3d` setup; billboard orientation depends on the active camera
- `bevy-pbr-materials` — texture slot binding and `StandardMaterial` for non-particle glow
