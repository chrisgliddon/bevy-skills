---
name: bevy-custom-assets
description: Use when implementing `AssetLoader` for a custom file format, depending on other assets via `LoadContext::loader().with_settings(..).load(..)`, hitting the 0.18 requirement to `#[derive(TypePath)]` on the loader, or using `reader.read_to_end(..)` / `seekable()` async access. Covers Bevy 0.18 custom asset loaders.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "2"
  area: asset
  bevy_version: "0.18"
---

# Bevy 0.18 — Custom asset loaders

## When to use this skill

- Loading a custom binary or text format (proprietary game data, sidecar configs, etc.).
- Producing an asset that depends on other assets (e.g. a level loader that pulls referenced textures).
- Needing async access to the underlying file (`reader.read_to_end`, `reader.seekable()`).
- Compiler error: "`MyLoader: TypePath` is not implemented" — 0.18 made `TypePath` mandatory on loaders.

## Canonical pattern

```rust
use bevy::asset::io::Reader;
use bevy::asset::{Asset, AssetApp, AssetLoader, LoadContext};
use bevy::prelude::*;
use bevy::reflect::TypePath;
use serde::Deserialize;
use thiserror::Error;

#[derive(Asset, TypePath, Debug, Deserialize)]
pub struct LevelDef {
    pub name: String,
    pub gravity: f32,
    pub thumbnail: String, // path to a referenced texture asset
}

#[derive(TypePath)] // 0.18: required on the loader itself.
pub struct LevelLoader;

#[derive(Debug, Error)]
pub enum LevelLoaderError {
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
    #[error("parse: {0}")]
    Parse(#[from] ron::error::SpannedError),
}

impl AssetLoader for LevelLoader {
    type Asset = LevelDef;
    type Settings = ();
    type Error = LevelLoaderError;

    async fn load(
        &self,
        reader: &mut dyn Reader,
        _settings: &Self::Settings,
        load_context: &mut LoadContext<'_>,
    ) -> Result<Self::Asset, Self::Error> {
        // Pull the whole file. For very large files prefer `seekable()`.
        let mut bytes = Vec::new();
        reader.read_to_end(&mut bytes).await?;
        let level: LevelDef = ron::de::from_bytes(&bytes)?;

        // Pull in a referenced asset so it loads alongside this one.
        // The resulting handle ends up tracked as a dependency.
        let _: Handle<Image> = load_context.load(&level.thumbnail);

        Ok(level)
    }

    fn extensions(&self) -> &[&str] {
        &["level.ron"]
    }
}

pub struct LevelLoaderPlugin;
impl Plugin for LevelLoaderPlugin {
    fn build(&self, app: &mut App) {
        app.init_asset::<LevelDef>()
            .register_asset_loader(LevelLoader);
    }
}
```

## Asking the reader for random access

```rust
// 0.18: bevy::asset::io::Reader gained `seekable()`.
# use bevy::asset::io::Reader;
# async fn _example(reader: &mut dyn Reader) -> std::io::Result<()> {
match reader.seekable() {
    Ok(seekable) => {
        // SeekableReader supports `seek(SeekFrom::Start(n))`, `seek(SeekFrom::End(-n))`, etc.
        let _ = seekable;
    }
    Err(_) => {
        // Source isn't seekable (e.g. HTTP backend). Fall back to streaming.
    }
}
# Ok(())
# }
```

## Gotchas (0.18)

- **`#[derive(TypePath)]` is required on the loader struct** (not just the asset). 0.18 enforces this so loaders can be reflected. Without it: "`MyLoader: TypePath` is not implemented".
- **`LoadContext::path()` returns `AssetPath`**, not `&Path`. To get the platform path, use `.path()` on it: `ctx.path().path()`.
- **`LoadContext::asset_bytes()` is gone.** Use `let mut bytes = Vec::new(); reader.read_to_end(&mut bytes).await?;` inside the `load` async fn, or `reader.seekable()` for random access.
- **Dependencies must be loaded through `LoadContext`**. `asset_server.load(...)` from inside a loader does **not** register the result as a dependency of the asset being built — use `load_context.load(...)` so `AssetEvent::LoadedWithDependencies` fires correctly.
- **`AssetLoader` is `async`** but you can't `tokio::spawn` inside it — the executor is Bevy's, not Tokio's. Use `bevy::tasks::futures_lite` or `bevy::tasks::AsyncComputeTaskPool` for compute-heavy work.
- **`#[derive(Asset)]` is required on the asset type** and combined with `TypePath`. The asset's `Settings` type must be `Default + Serialize + DeserializeOwned + Send + Sync + 'static` to participate in `.meta` files.
- **Extensions are matched on the full suffix.** `"level.ron"` matches `foo.level.ron` but not `foo.ron` — useful for disambiguating from generic RON.

## See also

- `bevy-assets` — using a `Handle<MyAsset>` once it's loaded.
- `bevy-voxel-data` — RON-driven asset patterns.
- `bevy-migration-0-17-to-0-18` — `LoadContext::asset_bytes` removal.
