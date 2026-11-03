# Rendering, assets, and API migrations

## Render graph nodes became systems

Camera render passes now run as ordinary systems in the `Core2d` or `Core3d`
schedules. Replace `ViewNode` implementations and node edges with a function using
`ViewQuery` and `RenderContext`, ordered against actual pass systems or one of
`Core3dSystems::{Prepass, MainPass, PostProcess}`.

The top-level schedule `bevy::render::renderer::RenderGraph` remains for non-camera
rendering. The removed part is the graph/node API used to define camera passes.

Other low-level changes include:

- `RenderSystems::ManageViews` split into `CreateViews`, `PrepareViews`, and
  `PrepareViewAttachments`.
- material pipeline machinery moved into the new `bevy_material` crate, with many
  public re-exports retained;
- `FullscreenMaterial::{run_in,run_before,run_after}` became
  `schedule_configs`;
- `PipelineCacheError` became `ShaderCacheError`;
- the old `shadow_pass` feature split into `per_view_shadow_pass` and
  `shared_shadow_pass`.

## Lights and atmosphere

```rust
commands.spawn(DirectionalLight {
    shadow_maps_enabled: true,
    contact_shadows_enabled: true,
    ..default()
});

commands.spawn((Camera3d::default(), ContactShadows::default()));
```

Contact shadows need a `ContactShadows` camera component and an opted-in light.
`Atmosphere` moved to `bevy::light` and is now spawned independently;
`AtmosphereSettings` remains on the camera. Use the atmosphere entity's `Transform`
for unit scaling.

## Advanced asset loads

The supported entry points are `AssetServer::load` and
`AssetServer::load_builder`. Common translations:

```rust
asset_server
    .load_builder()
    .with_settings(settings)
    .override_unapproved()
    .load(path);

load_context.load_builder().load(path);
load_context.load_builder().load_value(path).await?;
load_context.load_builder().load_untyped(path);
```

Every custom `Reader` implements `seekable()`. Return `Ok(self)` only for a type that
also implements `AsyncSeek`; otherwise return `ReaderNotSeekableError`.

## Lifecycle and schedules

- `Replace` → `Discard`.
- `ComponentHooks::on_replace` → `on_discard`.
- `#[component(on_replace = path)]` → `#[component(on_discard = path)]`.
- `ExecutorKind` is removed. Pass `SingleThreadedExecutor::new()`,
  `MultiThreadedExecutor::new()`, or `default_executor()` to `set_executor`.
- Generic query iteration needs an `IterQueryData` bound. Operations that promise a
  single entity may need `SingleEntityQueryData`.

## Persisted data

Treat serialized dynamic worlds and animation target IDs as versioned data:

- dynamic world types and paths were renamed;
- builders and `DynamicWorld::from_world_asset` now need a type registry in relevant
  workflows;
- `AnimationTargetId` calculation changed and stored values must be regenerated;
- morph targets now live in `Mesh`; the glTF morph-target subasset label is gone.

Add migration fixtures and load old saves in tests before shipping an update.

## Primary references

- [Bevy 0.18 → 0.19 migration guide](https://bevy.org/learn/migration-guides/0-18-to-0-19/)
- [Bevy 0.19 release notes](https://bevy.org/news/bevy-0-19/)
