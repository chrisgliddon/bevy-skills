# bevy-vfx — Shader-based effects: custom materials, animated uniforms, WGSL FX

> Referenced from `bevy-vfx/SKILL.md § Topics`.

## The alternative model

Instead of spawning thousands of small particles, a single quad or mesh with a custom
shader can produce the entire visual effect procedurally. The GPU does the work; the
CPU only updates a time uniform. Good candidates:

- Fire / flame walls (scrolling noise + colour ramp)
- Water and liquid surfaces (normal-map animation)
- Energy shields and forcefields (Fresnel + distortion)
- Chromatic-aberration or screen-space distortion overlays
- Glowing / pulsing emissive cores that pair with hanabi sparks around them

## Custom `Material` in Bevy 0.20

```rust
use bevy::{prelude::*, render::render_resource::AsBindGroup, shader::ShaderRef};

#[derive(Asset, AsBindGroup, TypePath, Clone)]
struct FlickerMaterial {
    #[uniform(0)]
    time: f32,
    #[uniform(0)]
    intensity: f32,
}

impl Material for FlickerMaterial {
    fn fragment_shader() -> ShaderRef {
        "shaders/flicker.wesl".into()
    }
    // alpha_mode can be overridden here; default is Opaque
}
```

> **0.20 gotcha — shaders are WESL.** naga_oil is gone. A `.wgsl` file with
> `#import` or `#ifdef` fails to load. Use `import ...;` and `@if(...)`, and name the
> file `.wesl`. Plain WGSL with no directives still works. `bevy-pbr-materials` has
> the full translation table.

Register the plugin once in your `App`:

```rust
app.add_plugins(MaterialPlugin::<FlickerMaterial>::default());
```

## Animated uniform: emissive flicker in ~20 lines

```toml
[dependencies]
bevy = "0.20"
```

```rust
// System: write elapsed time into the material uniform each frame
fn update_flicker(
    time: Res<Time>,
    mut materials: ResMut<Assets<FlickerMaterial>>,
    q: Query<&MeshMaterial3d<FlickerMaterial>>,
) {
    for handle in &q {
        // 0.19: get_mut returns AssetMut and only fires AssetEvent::Modified on write.
        if let Some(mut mat) = materials.get_mut(handle) {
            mat.time = time.elapsed_secs();
        }
    }
}
```

The paired WESL shader (`assets/shaders/flicker.wesl`). Two `#[uniform(0)]` fields
share one uniform struct at binding 0:

```wesl
import bevy_pbr::render::forward_io::VertexOutput;

struct Flicker { time: f32, intensity: f32 }
@group(2) @binding(0) var<uniform> flicker_u: Flicker;

@fragment
fn fragment(in: VertexOutput) -> @location(0) vec4<f32> {
    let flicker = 0.7 + 0.3 * sin(flicker_u.time * 8.0 + in.uv.x * 3.14159);
    let emissive = vec3<f32>(1.0, 0.4, 0.05) * flicker * flicker_u.intensity;
    return vec4<f32>(emissive, 1.0);
}
```

Spawn the quad:

```rust
fn setup(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<FlickerMaterial>>,
) {
    commands.spawn((
        Mesh3d(meshes.add(Rectangle::new(2.0, 2.0))),
        MeshMaterial3d(materials.add(FlickerMaterial {
            time: 0.0,
            intensity: 2.5,
        })),
        Transform::default(),
    ));
}
```

Add `update_flicker` to `Update`. The effect runs entirely on the GPU fragment shader;
CPU cost is one `Assets::get_mut` per visible entity per frame.

## Combining with hanabi

A common layered pattern: a shader-material "core" (e.g., fireball centre quad with a
radial glow shader) surrounded by hanabi embers/sparks spawned from the same origin.

Ordering matters for transparent blending:
- Set `alpha_mode: AlphaMode::Blend` on the core material.
- Hanabi effects also write to the transparent pass.
- Both sort by distance from camera each frame — deep overlaps between many transparent
  objects can cause the sort to serialise the transparent pass.

Keep transparent layering shallow: one core quad + one hanabi effect is fine. Four
overlapping transparent layers at high screen coverage will cause fragment overdraw.

## Decision: shader vs hanabi vs flipbook

| Situation | Best tool |
|---|---|
| Single localised animated effect, one instance | Custom material shader |
| Field of many small moving things with individual behaviour | `bevy_hanabi` |
| Canned, identical-every-time frame sequence | Sprite-sheet flipbook |
| Stylized geometric shapes (rings, arcs, lines) | `bevy_vector_shapes` |

## WASM compatibility

Custom `Material` + WESL shaders work on both WebGL2 and WebGPU targets in Bevy 0.20,
provided the shader stays within WGSL's core feature set:

- Texture sampling, uniforms, basic arithmetic — both backends.
- Compute shaders — WebGPU only.
- Storage buffers (`var<storage>`) — WebGPU only; use uniform buffers for WebGL2.
- `@builtin(sample_index)` and multisampling queries — WebGPU only.

If your effect only needs animated uniforms and texture sampling (like the flicker
example above), it will run unchanged on WebGL2. Cross-reference `bevy-wasm-webgpu`
for the full feature matrix.

## See also

- [`../SKILL.md`](../SKILL.md) — top-level bevy-vfx dispatcher
- [`non-hanabi-vfx.md`](non-hanabi-vfx.md) — CPU particles, flipbooks, trails, decals
- [`performance.md`](performance.md) — transparent-pass cost and overdraw budget
- `bevy-pbr-materials` — `AsBindGroup`, `AlphaMode`, full `Material` trait reference
- `bevy-wasm-webgpu` — WebGL2 vs WebGPU feature matrix for shaders
