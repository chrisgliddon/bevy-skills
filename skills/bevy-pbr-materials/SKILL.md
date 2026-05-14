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

```rust
use bevy::asset::{Asset, AssetPath};
use bevy::pbr::{Material, MaterialPlugin};
use bevy::prelude::*;
use bevy::reflect::TypePath;
use bevy::render::render_resource::AsBindGroup;
use bevy::shader::ShaderRef;

#[derive(Asset, AsBindGroup, TypePath, Debug, Clone)]
struct DissolveMaterial {
    #[uniform(0)]
    progress: f32,
    #[texture(1)]
    #[sampler(2)]
    noise: Handle<Image>,
}

impl Material for DissolveMaterial {
    // 0.18: shader paths via ShaderRef::Path or ShaderRef::Handle.
    fn fragment_shader() -> ShaderRef {
        ShaderRef::Path(AssetPath::from("shaders/dissolve.wgsl"))
    }

    // 0.18: prepass/shadow config moved from plugin fields to trait methods.
    // Override only when you need to opt out — both default to true.
    fn enable_prepass() -> bool { false }
}

# fn _wire(app: &mut App) {
app.add_plugins(MaterialPlugin::<DissolveMaterial>::default());
# }
```

## Gotchas (0.18)

- **`MaterialPlugin::<M> { prepass_enabled, shadows_enabled, ..default() }` is gone.** Override the `Material` trait methods instead:
  ```rust
  fn enable_prepass() -> bool { false }
  fn enable_shadows() -> bool { false }
  ```
- **`AsBindGroup::label()` is required.** The `#[derive(AsBindGroup)]` macro generates a `label()` automatically; if you hand-roll the impl, you must add it.
- **PBR shading fix.** 0.18 corrected a long-standing Fresnel/specular issue that made everything look "overly glossy". Materials authored for 0.17 may look noticeably less reflective in 0.18 — re-tune `perceptual_roughness` / `reflectance` if shipped textures look wrong.
- **Mesh component wrappers.** Use `Mesh3d(handle)` and `MeshMaterial3d(material_handle)` rather than spawning bare `Handle<Mesh>` / `Handle<StandardMaterial>`. The wrappers are what the renderer queries on.
- **Draw functions are per-phase.** If you used `MaterialDrawFunction`, the 0.18 split is `MainPassOpaqueDrawFunction`, `MainPassAlphaMaskDrawFunction`, `PrepassOpaqueDrawFunction`. Pick the phase you actually run in.
- **Bind group layouts**: `BindGroupLayout::create(...)` was replaced — use `BindGroupLayoutDescriptor::new(...)` then `pipeline_cache.get_bind_group_layout(&desc)`.
- **`Color::rgb(...)` is gone** — use `Color::srgb(...)` (sRGB-aware) or `Color::linear_rgb(...)`. This is a 0.13+ change but still in stale training data.

## See also

- `bevy-cameras` — what's looking at the materials.
- `bevy-migration-0-17-to-0-18` — `MaterialPlugin` field removal, `AsBindGroup::label` requirement.
