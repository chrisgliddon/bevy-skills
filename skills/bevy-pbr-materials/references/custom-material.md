# Bevy 0.20 — Custom Material Reference

Writing a custom `Material` with `AsBindGroup` and a WESL shader. See also
[lighting](lighting.md) and [mesh-primitives](mesh-primitives.md).

---

## Complete Example: DissolveMaterial

Verified to compile against Bevy 0.20.

```rust
use bevy::prelude::*;
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
    // `&str` and `Handle<Shader>` both convert into `ShaderRef`.
    fn fragment_shader() -> ShaderRef {
        "shaders/dissolve.wesl".into()
    }

    // Prepass/shadow config lives on the trait, not on `MaterialPlugin`.
    // Both default to true; override only to opt out.
    fn enable_prepass() -> bool {
        false
    }

    fn alpha_mode(&self) -> AlphaMode {
        AlphaMode::Mask(0.5)
    }
}

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_plugins(MaterialPlugin::<DissolveMaterial>::default())
        .add_systems(Startup, setup)
        .run();
}

fn setup(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<DissolveMaterial>>,
    asset_server: Res<AssetServer>,
) {
    let mesh = meshes.add(Cuboid::new(1.0, 1.0, 1.0));
    let material = materials.add(DissolveMaterial {
        progress: 0.0,
        noise: asset_server.load("textures/noise.png"),
    });

    commands.spawn((
        Mesh3d(mesh),
        MeshMaterial3d(material),
        Transform::from_xyz(0.0, 0.5, 0.0),
    ));
}
```

`assets/shaders/dissolve.wesl`:

```wesl
import bevy_pbr::render::forward_io::VertexOutput;

@group(2) @binding(0) var<uniform> progress: f32;
@group(2) @binding(1) var noise: texture_2d<f32>;
@group(2) @binding(2) var noise_sampler: sampler;

@fragment
fn fragment(in: VertexOutput) -> @location(0) vec4<f32> {
    let n = textureSample(noise, noise_sampler, in.uv).r;
    // Alpha below the mask cutoff is discarded by `AlphaMode::Mask(0.5)`.
    let alpha = select(0.0, 1.0, n > progress);
    return vec4<f32>(0.9, 0.4, 0.1, alpha);
}
```

---

## WESL: translating a 0.19 `.wgsl` shader

Bevy 0.20 replaced the naga_oil preprocessor with WESL. Rename the file to `.wesl`
and apply these rules. Plain WGSL files with no directives still load unchanged.

| 0.19 naga_oil | 0.20 WESL |
|---|---|
| `#import bevy_pbr::forward_io::VertexOutput` | `import bevy_pbr::render::forward_io::VertexOutput;` |
| `#import bevy_pbr::mesh_view_bindings` | `import bevy_pbr::render::mesh_view_bindings;` |
| `#import bevy_pbr::prepass_utils` | `import bevy_pbr::prepass::utils;` |
| `#import "shaders/util.wgsl"::f` | `import super::util::f;` (sibling asset file) |
| `#ifdef VERTEX_COLORS ... #endif` | `@if(VERTEX_COLORS)` before the declaration |
| `#ifdef A ... #else ... #endif` | `@if(A) ... @else ...` |
| `#{MATERIAL_BIND_GROUP}` | `constants::MATERIAL_BIND_GROUP` |
| `#define_import_path my_crate::foo` | removed; the module path is the file path |

Rules:

- Imports end with `;` and come first, before any declaration or `enable` directive.
- Module names mirror the shader's path in its crate (`bevy_pbr::render::pbr_functions`).
- `@if`/`@elif`/`@else` attach to whole declarations, struct members, function
  parameters, imports and statements. Boolean shader defs become flags; `Int`/`UInt`
  defs are readable as `constants::NAME`.
- Shaders loaded from `embedded://bevy_foo/bar.wesl` import as `bevy_foo::bar`.
- GLSL support and the `shader_format_wesl` Cargo feature are gone.

---

## Material Trait Methods

Override only what you need. All have defaults.

```rust
impl Material for MyMaterial {
    fn vertex_shader() -> ShaderRef { "shaders/my.vert.wesl".into() }
    fn fragment_shader() -> ShaderRef { "shaders/my.frag.wesl".into() }

    // Depth/normal prepass participation. Default true. Disable when the vertex
    // shader moves vertices and would break prepass depth.
    fn enable_prepass() -> bool { true }

    // Shadow casting. Default true.
    fn enable_shadows() -> bool { true }

    // 0.20: per-material order-independent transparency opt-out. Default true.
    // The matching shader def is `MATERIAL_OIT_ENABLED`.
    fn enable_oit() -> bool { true }

    // Blend mode. Default AlphaMode::Opaque.
    fn alpha_mode(&self) -> AlphaMode { AlphaMode::Blend }

    // Forward vs deferred for opaque geometry. Default OpaqueRendererMethod::Auto.
    // Import from `bevy::material::OpaqueRendererMethod` (moved from bevy_pbr in 0.19).
    fn opaque_render_method(&self) -> OpaqueRendererMethod { OpaqueRendererMethod::Forward }

    // Low-level pipeline tweaks (topology, cull mode). Error type is
    // `bevy::material::SpecializedMeshPipelineError` since 0.19.
    // fn specialize(...) -> Result<(), SpecializedMeshPipelineError> { ... }
}
```

`ShaderRef` variants: `Path(AssetPath)` (from `"path".into()`), `Handle(Handle<Shader>)`,
`Default` (engine PBR shader). Import from `bevy::shader::ShaderRef`.

---

## AsBindGroup Derive Attributes

```rust
#[derive(Asset, AsBindGroup, TypePath, Debug, Clone)]
struct MyMaterial {
    // Binding 0: uniform buffer. Any `ShaderType` works: f32, Vec4, LinearRgba, Mat4,
    // or a struct with #[derive(ShaderType)] (bevy::render::render_resource::ShaderType).
    #[uniform(0)]
    progress: f32,

    // Binding 1: 2D texture; binding 2: its sampler. `Option<Handle<Image>>` is
    // allowed and binds a fallback image when `None`.
    #[texture(1)]
    #[sampler(2)]
    noise: Handle<Image>,

    // Texture array:
    // #[texture(3, dimension = "2d_array")]
    // #[sampler(4)]
    // layers: Handle<Image>,
}
```

Material bindings live in bind group 2 (`@group(2)` in the shader). The engine's view
and mesh bindings use groups 0 and 1.

---

## Manual `AsBindGroup` (rare)

- `label()` is required (the derive generates it from the type name).
- 0.20 renamed `unprepared_bind_group` to `build_bind_group`. It writes
  `UnpreparedBindingResource`s into an `output: &mut BindGroupBuilder` parameter instead
  of returning an `UnpreparedBindGroup`. `UnpreparedBindingResource::Data` now holds a
  byte range into `BindGroupBuilder::data_buffer`.

---

## Pitfalls

- **Forgetting `MaterialPlugin::<M>::default()`** — nothing renders, no error.
- **`Material` and `MaterialPlugin` are in `bevy::prelude`** (via `bevy::pbr::prelude`).
  Qualify as `bevy::pbr::Material` only if another `Material` is in scope.
- **`.wgsl` file with `#import`** — fails to load in 0.20. Rename to `.wesl` and
  translate the directives (table above).
- **Vertex animation** — override `vertex_shader()` and set `enable_prepass() -> false`,
  or the prepass writes the un-animated depth.
- **Draw functions are per phase** (`MainPassOpaqueDrawFunction`,
  `MainPassAlphaMaskDrawFunction`, `MainPassTransparentDrawFunction`,
  `PrepassOpaqueDrawFunction`, `PrepassAlphaMaskDrawFunction`). `MaterialPlugin`
  registers them; only manual registration needs to pick the right phase.
- **`BindGroupLayout::create(...)` is gone.** Build layouts with
  `BindGroupLayoutDescriptor::new(...)` and resolve through
  `pipeline_cache.get_bind_group_layout(&desc)`. `PipelineCacheError` is now
  `ShaderCacheError` (0.19).
- **Custom render passes** — `RenderGraph` nodes were removed in 0.19. Write a system
  taking `ViewQuery<...>` and `RenderContext`, add it to the `Core3d` schedule, and
  order it with `.after(main_opaque_pass_3d)` or `Core3dSystems::PostProcess`.
