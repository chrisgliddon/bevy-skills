# Bevy 0.18 — Lighting Reference

Deep dive on light components and resources. See also
[mesh-primitives](mesh-primitives.md) and [custom-material](custom-material.md).

---

## DirectionalLight

Simulates a distant source (sun, moon). Only the **rotation** of the `Transform`
matters — position is ignored. Light shines along the entity's **-Z** axis.

```rust
use bevy::light::CascadeShadowConfigBuilder;
use bevy::prelude::*;

commands.spawn((
    DirectionalLight {
        color: Color::WHITE,
        // lux (lumens/m²). Default = light_consts::lux::AMBIENT_DAYLIGHT = 10_000.0
        illuminance: 10_000.0,
        shadows_enabled: true,
        // bias tuning — raise shadow_depth_bias to fix "shadow acne",
        // raise shadow_normal_bias to fix "peter-panning"
        shadow_depth_bias: 0.02,   // default
        shadow_normal_bias: 1.8,   // default
        ..default()
    },
    // looking_at sets the rotation; the position is irrelevant for directional lights
    Transform::from_xyz(0.0, 10.0, 0.0).looking_at(Vec3::ZERO, Vec3::Y),
    // Override cascade config on the same entity (auto-required by DirectionalLight)
    CascadeShadowConfigBuilder {
        num_cascades: 4,
        maximum_distance: 100.0,
        ..default()
    }.build(),
));
```

This exact spawn shape is what the `card_pickup` rebuild needed and couldn't find
in the skill — note that `CascadeShadowConfig` is an auto-required component, so
you can override it in the bundle.

**Default values:**
- `color`: `Color::WHITE`
- `illuminance`: `10_000.0` lux
- `shadows_enabled`: `false`
- `shadow_depth_bias`: `0.02`
- `shadow_normal_bias`: `1.8`

---

## PointLight

Emits light in all directions from a point. Units are **lumens** (total power).

```rust
commands.spawn((
    PointLight {
        color: Color::WHITE,
        // lumens. Default = 1_000_000 (very large cinema light).
        // For a 60W bulb equivalent use ~800.0.
        intensity: 800.0,
        // meters — tune together with intensity to avoid hard cut-offs
        range: 20.0,
        // sphere radius for specular highlight size (not shadow softness)
        radius: 0.0,
        shadows_enabled: true,
        shadow_depth_bias: 0.08,   // default
        shadow_normal_bias: 0.6,   // default
        shadow_map_near_z: 0.1,    // default — raise for better depth precision
        ..default()
    },
    Transform::from_xyz(0.0, 3.0, 0.0),
));
```

The `3d_scene` rebuild only needed `shadows_enabled: true` — the intensity/range
defaults are intentionally very large so lights are visible at Bevy's default
"very overcast day" exposure. For indoor lighting lower the intensity or
tune the camera's exposure/tonemapping.

**Default values:**
- `intensity`: `1_000_000.0` lumens
- `range`: `20.0` m
- `radius`: `0.0`
- `shadows_enabled`: `false`

---

## SpotLight

Like `PointLight` but confined to a cone. Same intensity/range/radius fields
plus two angle fields.

```rust
commands.spawn((
    SpotLight {
        color: Color::WHITE,
        intensity: 1_000_000.0,   // lumens, same as PointLight default
        range: 20.0,
        radius: 0.0,
        shadows_enabled: false,
        shadow_depth_bias: 0.02,
        shadow_normal_bias: 1.8,
        shadow_map_near_z: 0.1,
        // inner_angle: full-brightness cone, in radians
        inner_angle: 0.0,
        // outer_angle: edge of cone (soft falloff between inner and outer)
        // must be < PI/2; default = PI/4 (45°)
        outer_angle: std::f32::consts::FRAC_PI_4,
        ..default()
    },
    Transform::from_xyz(0.0, 5.0, 0.0).looking_at(Vec3::ZERO, Vec3::Y),
));
```

**Default values:**
- `inner_angle`: `0.0` rad (no full-brightness cone)
- `outer_angle`: `FRAC_PI_4` (45°)
- `intensity`: `1_000_000.0` lumens

---

## GlobalAmbientLight (resource)

A scene-wide ambient fill applied to all cameras that don't have an
`AmbientLight` component override. Inserted by `DefaultPlugins` at
`brightness: 80.0`.

```rust
fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        // Raise ambient to mimic an overcast sky
        .insert_resource(GlobalAmbientLight {
            color: Color::WHITE,
            brightness: 200.0,
            ..default()
        })
        .run();
}
```

Or mutate it at startup:

```rust
fn setup_ambient(mut ambient: ResMut<GlobalAmbientLight>) {
    ambient.brightness = 200.0;
}
```

---

## AmbientLight (per-camera component, 0.18 change)

New in 0.18: attach `AmbientLight` directly to a camera entity to override
`GlobalAmbientLight` for that camera only. This is a component, not a resource.

```rust
commands.spawn((
    Camera3d::default(),
    // overrides GlobalAmbientLight for this camera
    AmbientLight {
        color: Color::WHITE,
        brightness: 50.0,
        ..default()
    },
));
```

---

## Shadows

### Cascaded shadow maps (DirectionalLight)

`CascadeShadowConfig` is auto-required by `DirectionalLight`. Override it in
the same bundle or via a separate `insert`:

```rust
use bevy::light::CascadeShadowConfigBuilder;

// In the spawn bundle:
CascadeShadowConfigBuilder {
    num_cascades: 4,          // default 4 (1 on WebGL2)
    minimum_distance: 0.1,
    maximum_distance: 100.0,  // meters from camera
    first_cascade_far_bound: 10.0,
    overlap_proportion: 0.2,
    ..default()
}.build()

// Or insert_resource to change shadow map resolution:
app.insert_resource(DirectionalLightShadowMap { size: 4096 }); // default 2048
```

### Point light shadow map resolution

```rust
app.insert_resource(PointLightShadowMap { size: 2048 }); // default 1024

---

## Pitfalls

- **`Color::WHITE` is valid** — named constants work fine. You don't have to
  write `Color::srgb(1.0, 1.0, 1.0)`.
- **`Color::rgb(...)` is gone** — use `Color::srgb(...)` or `Color::linear_rgb(...)`.
- **illuminance vs intensity units** — `DirectionalLight` uses *lux* (lm/m²);
  `PointLight` / `SpotLight` use *lumens* (total power). Mixing them up produces
  scenes that are wildly over- or under-lit.
- **Directional light position doesn't matter** — the `Transform` translation is
  ignored; only the rotation (forward direction) affects shading. Place it
  anywhere for convenience.
- **Shadows are expensive** — each shadow-casting light multiplies rendering cost.
  Keep shadow-casting lights to one or two. Disable `shadows_enabled` for fill
  lights.
- **`shadow_depth_bias` defaults differ by type** — `DirectionalLight` defaults
  to `0.02`, `PointLight` to `0.08`.
