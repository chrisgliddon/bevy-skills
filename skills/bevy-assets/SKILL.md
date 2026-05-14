---
name: bevy-assets
description: Use when loading anything with `AssetServer`, holding a `Handle<T>`, indexing `Assets<T>`, enabling hot-reload via `AssetPlugin { watch_for_changes_override: Some(true), .. }`, or chasing the 0.18 `LoadContext::path -> AssetPath` and `SeekableReader` changes. Covers Bevy 0.18 asset loading.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "2"
  area: asset
  bevy_version: "0.18"
---

# Bevy 0.18 — Assets

## When to use this skill

- Loading a model, texture, audio file, or scene.
- Reading the loaded data back from `Assets<T>` once it's ready.
- Reacting to load progress (`AssetEvent::Added` / `Modified`).
- Enabling hot-reload during development.
- Writing your own loader → see `bevy-custom-assets`.

## Canonical pattern

```rust
use bevy::prelude::*;

fn main() {
    App::new()
        .add_plugins(DefaultPlugins.set(AssetPlugin {
            // Hot-reload on file change — dev-only.
            watch_for_changes_override: Some(true),
            ..default()
        }))
        .init_resource::<MyHandles>()
        .add_systems(Startup, load_handles)
        .add_systems(Update, react_to_loads)
        .run();
}

#[derive(Resource, Default)]
struct MyHandles {
    hero: Handle<Scene>,
    bricks: Handle<Image>,
}

fn load_handles(asset_server: Res<AssetServer>, mut handles: ResMut<MyHandles>) {
    // GLTF scenes are addressed by sub-asset label.
    handles.hero = asset_server.load("models/hero.glb#Scene0");
    handles.bricks = asset_server.load("textures/bricks.png");
}

fn react_to_loads(
    mut ev: MessageReader<AssetEvent<Image>>,
    images: Res<Assets<Image>>,
) {
    for event in ev.read() {
        if let AssetEvent::LoadedWithDependencies { id } = event {
            if let Some(img) = images.get(*id) {
                info!("image loaded: {}x{}", img.width(), img.height());
            }
        }
    }
}
```

## Asset paths

```rust
use bevy::asset::AssetPath;

// `LoadContext::path()` returns `AssetPath` in 0.18 (was `&Path` in 0.17).
// Build paths explicitly when generating handles inside a custom loader:
let path = AssetPath::from("textures/bricks.png");
let path_with_label = AssetPath::from("models/hero.glb").with_label("Scene0");
let _ = path;
let _ = path_with_label;
```

## Asset readiness check

```rust
use bevy::prelude::*;

# fn _check(
asset_server: Res<AssetServer>,
handles: Res<MyHandles>,
# ) {
use bevy::asset::LoadState;

if asset_server.load_state(&handles.hero) == LoadState::Loaded {
    // Safe to query Assets<Scene> and use it.
}
# }
# #[derive(Resource)] struct MyHandles { hero: Handle<Scene> }
```

## Gotchas (0.18)

- **`LoadContext::path()` returns `AssetPath`**, not `&Path`. Callers that did `ctx.path().to_string_lossy()` need to `ctx.path().path().to_string_lossy()` or use the `AssetPath` API directly.
- **`SeekableReader`** is new in 0.18. Loaders that need random access into the underlying file can ask: `if let Ok(s) = reader.seekable() { /* s: &mut dyn SeekableReader */ }`.
- **`AssetSourceBuilder::new(...)`** replaces `AssetSource::build().with_reader(...)`. Existing custom asset sources need to be re-shaped.
- **`AssetSource` channel is `async_channel::Sender`** in 0.18 (was `crossbeam_channel`). Use `send_blocking(...)`.
- **`Image::reinterpret_size(size)` returns `Result`** in 0.18.
- **Sub-asset labels.** `path.glb#Scene0`, `path.glb#Mesh0/Primitive0` — distinct handles, can be loaded independently. Forgetting the label gives you the *root* asset, not the named one.
- **Hot reload is dev-only.** Don't ship `watch_for_changes_override: Some(true)` in a release build — it polls the filesystem.
- **`asset_server.load(...)` is non-blocking.** Querying `Assets<T>::get` immediately after returns `None`. Wait for `AssetEvent::LoadedWithDependencies` or poll `load_state(...)`.
- **`AssetEvent<T>` is a `Message`**, so iterate with `MessageReader<AssetEvent<T>>`, not the old `EventReader`.

## See also

- `bevy-custom-assets` — writing your own `AssetLoader` (must `#[derive(TypePath)]` in 0.18).
- `bevy-migration-0-17-to-0-18` — `LoadContext::path` and channel-type renames.
