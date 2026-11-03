# WESL shaders in Bevy 0.20

Bevy 0.20 replaced the naga_oil preprocessor with WESL. Custom shaders written in the naga_oil dialect must be translated and renamed from `.wgsl` to `.wesl`. Plain WGSL with no preprocessor directives keeps working unchanged.

## Directive translation

| naga_oil (0.19) | WESL (0.20) |
|---|---|
| `#import bevy_pbr::forward_io::VertexOutput` | `import bevy_pbr::render::forward_io::VertexOutput;` |
| `#import "shaders/util.wgsl"::hsv_to_rgb` | `import super::util::hsv_to_rgb;` |
| `#ifdef FLAG` … `#endif` | `@if(FLAG)` on the declaration, member, parameter, import or statement |
| `#ifdef A` / `#else` | `@if(A)` / `@else` |
| `#{MATERIAL_BIND_GROUP}` | `constants::MATERIAL_BIND_GROUP` |
| `#define_import_path my_crate::foo` | removed; the module name is the file path |

Rules:
- Imports end with `;` and come first in the file, before any declaration or `enable` directive.
- Boolean shader defs become conditional-compilation flags. `Int`/`UInt` defs are readable as `constants::NAME` and also enable a flag of the same name.
- `@if` attaches to whole items. Wrap several statements in `@if(FLAG) { ... }`.

## Module paths changed

Module names now mirror the file path inside the crate.

| 0.19 | 0.20 |
|---|---|
| `bevy_pbr::mesh_view_bindings` | `bevy_pbr::render::mesh_view_bindings` |
| `bevy_pbr::forward_io` | `bevy_pbr::render::forward_io` |
| `bevy_pbr::prepass_utils` | `bevy_pbr::prepass::utils` |
| `bevy_pbr::utils::octahedral_*` | `bevy_render::utils::octahedral_*` |
| `bevy_core_pipeline::oit::oit_draw` | `bevy_core_pipeline::oit::draw::oit_draw` |

Shaders loaded from `embedded://bevy_foo/bar.wesl` are importable as `bevy_foo::bar`. Anything else is importable at its asset path.

## Worked example

```wgsl
// 0.19 — shaders/custom.wgsl
#import bevy_pbr::forward_io::VertexOutput
#ifdef VERTEX_COLORS
var<private> tint: vec4<f32>;
#endif
@group(2) @binding(#{MATERIAL_BIND_GROUP}) var<uniform> color: vec4<f32>;
```

```wgsl
// 0.20 — shaders/custom.wesl
import bevy_pbr::render::forward_io::VertexOutput;

@if(VERTEX_COLORS)
var<private> tint: vec4<f32>;

@group(2) @binding(constants::MATERIAL_BIND_GROUP) var<uniform> color: vec4<f32>;
```

On the Rust side, `Material::fragment_shader()` returns the new path (`"shaders/custom.wesl".into()`). Nothing else changes for `#[derive(AsBindGroup)]` materials.

## Cargo

- `shader_format_wesl` feature removed. WESL is always on.
- GLSL support removed. SPIR-V passthrough unchanged.
- `wesl` crates require rustc 1.97.1 or newer.

## Order independent transparency

Gate `oit_draw` behind `MATERIAL_OIT_ENABLED` (per material) rather than `OIT_ENABLED` (per view), and pass premultiplied color:

```wgsl
@if(MATERIAL_OIT_ENABLED)
import bevy_core_pipeline::oit::draw::oit_draw;

@if(MATERIAL_OIT_ENABLED) {
    if alpha_mode == pbr_types::STANDARD_MATERIAL_FLAGS_ALPHA_MODE_BLEND {
        oit_draw(in.position, vec4(out.color.rgb * out.color.a, out.color.a));
        discard;
    }
}
```

Source: https://bevy.org/learn/migration-guides/0-19-to-0-20/ ("WESL shaders").
