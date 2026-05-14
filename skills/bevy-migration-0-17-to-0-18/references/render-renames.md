# Render Renames — Bevy 0.17 → 0.18

Cross-links: [ecs-renames](ecs-renames.md) | [asset-renames](asset-renames.md) | [schedule-renames](schedule-renames.md) | [cargo-feature-renames](cargo-feature-renames.md)

## `Camera { target: ... }` → `RenderTarget` component

`Camera.target` was removed as a field. Attach `RenderTarget` as a separate component.

```rust
// 0.17
commands.spawn(Camera3d::default()).insert(Camera {
    target: RenderTarget::Image(handle.into()),
    ..default()
});

// 0.18
commands.spawn((Camera3d::default(), RenderTarget::Image(handle.into())));
```

For the default (window) target, simply omit `RenderTarget` — the renderer defaults to the primary window.

## `AmbientLight` is no longer a resource

```rust
// 0.17
app.insert_resource(AmbientLight { brightness: 2000.0, ..default() });

// 0.18: global default → GlobalAmbientLight resource
app.insert_resource(GlobalAmbientLight { brightness: 2000.0, ..default() });

// Per-camera override: attach AmbientLight as a component
commands.spawn((Camera3d::default(), AmbientLight { brightness: 5000.0, ..default() }));
```

## `MaterialPlugin<M>` config moved to trait methods

Struct fields `prepass_enabled` and `shadows_enabled` were removed from `MaterialPlugin`.

```rust
// 0.17
app.add_plugins(MaterialPlugin::<M> {
    prepass_enabled: false,
    shadows_enabled: false,
    ..default()
});

// 0.18 — override the Material trait instead
impl Material for M {
    fn enable_prepass() -> bool { false }
    fn enable_shadows() -> bool { false }
    // all other methods keep their default impls
}
app.add_plugins(MaterialPlugin::<M>::default());
```

## `AsBindGroup::label()` is now required

The `#[derive(AsBindGroup)]` macro generates this automatically. Hand-rolled impls must add it:

```rust
impl AsBindGroup for MyMaterial {
    fn label() -> &'static str { "MyMaterial" } // required in 0.18
    // ...
}
```

## `gizmos.cuboid` → `gizmos.cube`

```rust
// 0.17
gizmos.cuboid(transform, color);

// 0.18
gizmos.cube(transform, color);
```

## `bevy_gizmos` split

Render-side internals now live in a separate crate `bevy_gizmos_render`. If you imported from `bevy_gizmos` internals directly, update the import path. Application-level `Gizmos` use via the prelude is unaffected.

## `Atmosphere` is now indirect

What was a flat embedded struct is now a handle:

```rust
// 0.17
commands.spawn(AtmosphereCamera { atmosphere: Atmosphere { ... } });

// 0.18
let atmosphere = atmospheres.add(ScatteringMedium { ... });
commands.spawn(AtmosphereCamera { atmosphere });
```
