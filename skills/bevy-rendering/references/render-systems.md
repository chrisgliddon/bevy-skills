# Bevy 0.20 render systems

## Architectural model

Bevy still has a main world and a render sub-app. World-side components are extracted,
GPU resources are prepared, visible work is queued, and render passes run in camera
schedules. Since 0.19 camera passes are systems, not render-graph nodes. 0.20 kept that model
and relaxed set ordering to `chain_weak`.

```rust
use bevy::{
    core_pipeline::{core_3d::main_opaque_pass_3d, Core3d, Core3dSystems},
    prelude::*,
    render::{
        camera::ExtractedCamera,
        renderer::{RenderContext, ViewQuery},
        view::ViewTarget,
        RenderApp,
    },
};

pub fn my_render_pass(
    world: &World,
    view: ViewQuery<(&ExtractedCamera, &ViewTarget)>,
    mut context: RenderContext,
) {
    let (camera, target) = view.into_inner();
    // Begin an appropriate tracked render pass and issue commands.
    let _ = (world, camera, target, &mut context);
}

pub fn install(app: &mut App) {
    let render_app = app.sub_app_mut(RenderApp);
    render_app.add_systems(
        Core3d,
        my_render_pass
            .after(main_opaque_pass_3d)
            .in_set(Core3dSystems::MainPass),
    );
}
```

Use the exact imports and pass APIs from the Bevy 0.20 examples for the chosen phase;
these low-level types are intentionally specific to the target pass.

## Ordering

- Order against real system functions when the dependency is precise.
- Use `Core3dSystems::{Prepass, MainPass, PostProcess}` or corresponding 2D sets for
  coarse grouping.
- Create custom views in `RenderSystems::CreateViews`, prepare them in
  `PrepareViews`, and allocate attachments in `PrepareViewAttachments`.
- Do not copy a 0.18 `Node3d` edge list into 0.20 system labels.
- 0.20: `Render`, `RenderGraph`, `Core2d`/`Core3d`, and `ExtractSchedule` sets are
  ordered with `chain_weak`. Only tracked ECS access conflicts keep a strict order.
  If your system waits on an earlier set through a channel, atomic, `NonSend`, or
  interior mutability, add `.after(that_system)` explicitly.

The schedule `bevy::render::renderer::RenderGraph` still runs top-level non-camera
rendering. Its name does not mean the removed `RenderGraph` node API still exists.

## Extraction and GPU resources

0.20 made extraction generic over worlds (`bevy_extract`). Name the target app:

```rust
use bevy::{
    prelude::*,
    render::{extract_component::ExtractComponent, RenderApp},
};

#[derive(Component, Clone, ExtractComponent)]
#[extract_app(RenderApp)]
pub struct GlowStrength(pub f32);
// The derive also implements `SyncComponent<RenderApp>`; a manual
// `impl SyncComponent<RenderApp> for GlowStrength` conflicts with it.
```

Keep the stages explicit:

1. Main-world gameplay mutates source components.
2. Extraction copies only render-relevant, frame-stable data.
3. Prepare creates or updates GPU resources.
4. Queue specializes pipelines and creates phase items.
5. Render systems issue commands for a view.

Avoid reading mutable gameplay state directly during rendering. Extract a compact
render representation so main-world scheduling and render scheduling stay decoupled.

## Renames in 0.20

| 0.19 | 0.20 |
|---|---|
| `UnpreparedBindGroup` | `BindGroupBuilder` / `build_bind_group` |
| `ViewDepthTexture` | `ViewDepthStencilTexture` (holds `DepthStencilAttachment`) |
| `DepthAttachment` | `DepthStencilViewAttachment` with `DepthStencilViews` |
| `ViewPrepassTextures::depth: Option<ColorAttachment>` | `Option<DepthStencilAttachment>` |
| `ViewTarget::compositing_space` | query `Option<&ResolvedCompositingSpace>` |
| `WgpuWrapper` | removed; `RenderQueue::new` / `into_inner` |
| `ExtractedWindows` / `::primary` | `Query<&ExtractedWindow>` (+ `With<PrimaryWindow>`) |
| `SortedCamera::hdr` | removed; read `ExtractedCamera::hdr` |
| `ShaderBuffer::new(&[u8])`, `set_data` | `ShaderBuffer::new(Vec<T>)`, `extend` |
| `MeshTag(x)` / `MeshAabb::compute_aabb` | `MeshTag::new(x)` / `get_aabb` |
| `Tonemapping` in `bevy_core_pipeline::tonemapping` | `bevy_render::view::Tonemapping` (re-exported) |
| `RenderAppChannels::new(a, b)` | takes a third `MainThreadExecutor` |
| naga_oil `#import a::b` / `#ifdef` | WESL `import a::b;` / `@if(DEF)` |

## When a custom pass is unnecessary

Do not write a render system merely to:

- change material parameters (`Material` is enough);
- render to an image (`RenderTarget` is enough);
- apply a supported post effect (camera component/plugin is enough);
- draw debug lines (gizmos are enough);
- choose forward/deferred (use `DefaultOpaqueRendererMethod`).

## Source examples

- [Specialized mesh pipeline](https://github.com/bevyengine/bevy/blob/v0.20.1/examples/shader_advanced/specialized_mesh_pipeline.rs)
- [Render depth to texture](https://github.com/bevyengine/bevy/blob/v0.20.1/examples/shader_advanced/render_depth_to_texture.rs)
- [0.18 → 0.19 render-system migration](https://bevy.org/learn/migration-guides/0-18-to-0-19/#render-graph-as-systems)
- [0.19 → 0.20 migration guide](https://bevy.org/learn/migration-guides/0-19-to-0-20/)
