# bevy-vfx — Hanabi 2D vs 3D, orient modes, and flipbook

> Referenced from `bevy-vfx/SKILL.md § Topics`.

## Feature flags

`bevy_hanabi = "0.18.0"` ships **six** Cargo features. Both `2d` and `3d` are enabled
by default:

```toml
[dependencies]
bevy_hanabi = "0.18.0"           # 2d + 3d both on (default)

# 3D-only — saves compiling the 2D render path
bevy_hanabi = { version = "0.18.0", default-features = false, features = ["3d"] }

# 2D-only
bevy_hanabi = { version = "0.18.0", default-features = false, features = ["2d"] }
```

Other default features: `gpu_tests`, `serde`, `typetag`. The non-default feature is
`trace`.

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

`OrientMode` variants verified against `bevy_hanabi` 0.18.0 docs:

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
which texture to sample. The texture slot is registered in the `Module`:

```rust
// In setup, before writer.finish():
let slot = module.add_texture_slot("explosion");
let tex_mod = ParticleTextureModifier::new(writer.lit(slot as f32).expr());
```

Then bind the actual texture via `EffectMaterial` on the particle entity (see
[docs.rs/bevy_hanabi/0.18.0](https://docs.rs/bevy_hanabi/0.18.0/bevy_hanabi/struct.EffectMaterial.html)).

## `ParticleTextureModifier` — static texture

Without `FlipbookModifier`, `ParticleTextureModifier` applies a single texture to every
particle (soft glow circle, snowflake, etc.):

```rust
let slot = module.add_texture_slot("glow");
let tex = ParticleTextureModifier::new(writer.lit(slot as f32).expr());
```

The `sample_mapping: ImageSampleMapping` field defaults to modulating the particle
color by the texture sample. Override it if you need alpha-only or full-replace mapping.

## 3D mesh particles

Hanabi's default particle is always a quad billboard. True instanced-mesh particles
(each particle renders a 3D mesh) are not directly supported by `bevy_hanabi` 0.18.0 —
use Bevy's built-in `GpuPickable` / instanced rendering or `bevy_particle_systems` for
that pattern. Mention it only to clarify scope; billboard particles cover the vast
majority of VFX use cases.

## Sprite-sheet alternative (non-hanabi)

For sprite-flipbook explosions that are *not* GPU particle systems, see the
`non-hanabi-vfx` reference (Author B's file) for the `bevy_spritesheet_animation`
approach, which operates on ordinary `Sprite` entities.

## See also

- [`../SKILL.md`](../SKILL.md) — top-level bevy-vfx skill
- [`hanabi-modifiers.md`](hanabi-modifiers.md) — `OrientModifier`, `FlipbookModifier` in the modifier catalog
- [`hanabi-anatomy.md`](hanabi-anatomy.md) — `EffectAsset` build flow and `SpawnerSettings`
- `bevy-cameras` — `Camera2d` vs `Camera3d` setup; billboard orientation depends on the active camera
- `bevy-pbr-materials` — texture slot binding and `StandardMaterial` for non-particle glow
