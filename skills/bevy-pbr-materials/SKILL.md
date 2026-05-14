---
name: bevy-pbr-materials
description: Use when spawning a mesh with `StandardMaterial`, writing a custom `Material` with `AsBindGroup` and a required `label()` (new in 0.18), wiring `MaterialPlugin<M>` whose `prepass_enabled`/`shadows_enabled` config moved to trait methods, or chasing visual shifts caused by the 0.18 PBR shading fix. Covers Bevy 0.18 PBR materials.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "2"
  area: render
  bevy_version: "0.18"
---

# Bevy 0.18 — PBR Materials

## When to use this skill

- Texturing a mesh with the built-in physically based shader.
- Writing a custom `Material` (e.g. for stylised shading, dissolve effects, world-space shaders).
- Wondering why your scene looks less glossy after upgrading to 0.18.
- Compiler error on `AsBindGroup::label()` (now required).
- Compiler error on `MaterialPlugin::<M> { prepass_enabled: ... }` (fields removed in 0.18).

## Canonical pattern — StandardMaterial

```rust
use bevy::prelude::*;

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_systems(Startup, setup)
        .run();
}

fn setup(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
) {
    let mesh = meshes.add(Cuboid::new(1.0, 1.0, 1.0));
    let material = materials.add(StandardMaterial {
        base_color: Color::srgb(0.8, 0.3, 0.2),
        perceptual_roughness: 0.4,
        metallic: 0.1,
        ..default()
    });

    commands.spawn((
        Mesh3d(mesh),
        MeshMaterial3d(material),
        Transform::from_xyz(0.0, 0.5, 0.0),
    ));

    commands.spawn((
        Camera3d::default(),
        Transform::from_xyz(0.0, 2.0, 4.0).looking_at(Vec3::ZERO, Vec3::Y),
    ));

    commands.spawn((
        DirectionalLight::default(),
        Transform::from_xyz(2.0, 4.0, 2.0).looking_at(Vec3::ZERO, Vec3::Y),
    ));
}
```

## Custom Material — 0.18 shape

Custom materials with the `Material` trait and `AsBindGroup` are covered in
detail at [references/custom-material.md](references/custom-material.md).

## Topics

| Topic | Reference |
|-------|-----------|
| `PointLight`, `DirectionalLight`, `SpotLight` field shapes; `GlobalAmbientLight`; shadow cascades | [references/lighting.md](references/lighting.md) |
| `Plane3d`, `Cuboid`, `Sphere`, `Circle`, `Cylinder`, `Capsule3d`, `Torus` constructors and orientation gotchas | [references/mesh-primitives.md](references/mesh-primitives.md) |
| `Material` trait methods, `AsBindGroup` attributes, `ShaderRef` variants, `MaterialPlugin` wiring | [references/custom-material.md](references/custom-material.md) |

## Gotchas (0.18)

- **`MaterialPlugin::<M> { prepass_enabled, shadows_enabled, ..default() }` is gone.** Override the `Material` trait methods instead — see [references/custom-material.md](references/custom-material.md).
- **`AsBindGroup::label()` is required.** The `#[derive(AsBindGroup)]` macro generates it automatically; hand-rolled impls must add it.
- **PBR shading fix.** 0.18 corrected a long-standing Fresnel/specular issue that made everything look "overly glossy". Materials authored for 0.17 may look less reflective in 0.18 — re-tune `perceptual_roughness` / `reflectance`.
- **Mesh component wrappers.** Use `Mesh3d(handle)` and `MeshMaterial3d(material_handle)` — the wrappers are what the renderer queries on.
- **`Plane3d::new` takes `Vec2` for `half_size`**, not a scalar — see [references/mesh-primitives.md](references/mesh-primitives.md).
- **`Color::rgb(...)` is gone** — use `Color::srgb(...)` or `Color::linear_rgb(...)`.
- **Directional light position is ignored** — only rotation matters. See [references/lighting.md](references/lighting.md).

## See also

- `bevy-cameras` — what's looking at the materials.
- `bevy-migration-0-17-to-0-18` — `MaterialPlugin` field removal, `AsBindGroup::label` requirement.
