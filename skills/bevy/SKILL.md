---
name: bevy
description: Use when starting any Bevy task, choosing between Update and FixedUpdate, picking Cargo feature flags, or recalling which sibling skill covers ECS, assets, rendering, or migration. Routes to the right Bevy 0.18 skill and pins the engine version for downstream snippets.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "1"
  area: router
  bevy_version: "0.18"
---

# Bevy 0.18 — Router

**Read this first when working on a Bevy project.** All sibling skills assume Bevy 0.18 (released 2026-01-13). If the user's `Cargo.toml` pins a different version, stop and confirm before applying patterns from this collection.

## Smallest valid app

```rust
use bevy::prelude::*;

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_systems(Startup, setup)
        .run();
}

fn setup(mut commands: Commands) {
    commands.spawn(Camera3d::default());
}
```

## When to use which skill

| Task | Skill |
|---|---|
| App / Plugin / Schedule basics, Update vs FixedUpdate, exclusive systems | `bevy-core-concepts` |
| `#[derive(Component)]`, `#[require(...)]`, observers (`On<E>`), hooks, storage | `bevy-ecs-components` |
| `Query`, `With`/`Without`/`Or`, `Changed`/`Added`, `par_iter`, query lenses, `ArchetypeQueryData` | `bevy-ecs-queries` |
| `SystemParam`, `SystemSet`, `.run_if`, ordering, `remove_systems_in_set` | `bevy-ecs-systems` |
| `Cargo.toml` features: `2d`/`3d`/`ui`, mid-level `2d_api`, renamed features | `bevy-cargo-features` |
| Upgrading from 0.17 — `MessageReader`, `On`, `RenderTarget`, `GlobalAmbientLight`, etc. | `bevy-migration-0-17-to-0-18` |
| `AssetServer`, `Handle<T>`, hot-reload, `short-type-path`, `SeekableReader` | `bevy-assets` |
| Writing an `AssetLoader` (must `#[derive(TypePath)]` in 0.18) | `bevy-custom-assets` |
| WASM build pipeline, WebGPU vs WebGL2 | `bevy-wasm-webgpu` |
| `Camera3d`, `Projection`, `RenderTarget` component, `FreeCamera`, `PanCamera` | `bevy-cameras` |
| `StandardMaterial`, `MaterialPlugin<M>`, `AsBindGroup::label()`, 0.18 PBR shading fix | `bevy-pbr-materials` |
| Voxel meshing with `block-mesh-rs`, chunk pipeline, greedy quads | `bevy-voxel-pipeline` |
| RON block definitions, palette, KTX2 atlas baking | `bevy-voxel-data` |
| `es-fluent-manager-bevy` i18n — `FluentText<T>`, `BevyFluentText`, `LocaleChangeEvent`, `i18n.toml` | `bevy-fluent` |

## Cardinal rules (every Bevy 0.18 task)

1. **Events are messages.** `EventReader<E>` and `EventWriter<E>` were renamed to `MessageReader<M>` / `MessageWriter<M>` in 0.17. Still wrong if Claude writes the old name in 0.18.
2. **Observers use `On<E>`, not `Trigger<E>`.** `Trigger` was renamed in 0.17 (PR #19596).
3. **Schedule order is explicit.** `SimpleExecutor` was removed in 0.18 — ambiguous orderings panic at schedule-build. Use `.before()` / `.after()` / `.chain()`.
4. **No `.unwrap()` in systems.** Systems run every frame. Use `let ... else { return };` or a real error path.
5. **State changes always trigger transitions** in 0.18. Use `set_if_neq` if you need 0.17 behavior.
6. **`RenderTarget` is its own component** in 0.18, not a field on `Camera`.
7. **`Mesh::insert_attribute` → `try_insert_attribute(...)?`** — returns `Result` in 0.18.

## Gotchas

- Bevy's training-data footprint is dominated by 0.10–0.15 code. If a snippet feels obvious, double-check it against `bevy-migration-0-17-to-0-18` before trusting it.
- `bevy::prelude::*` doesn't re-export everything. Many ECS internals live under `bevy::ecs::...` — import explicitly when needed.
- The `bevy` crate now re-exports many subcrates (`bevy_camera`, `bevy_light`, `bevy_post_process`, `bevy_anti_alias`, `bevy_input_focus`, `bevy_gizmos_render`, `bevy_sprite_render`, `bevy_ui_render`). Subcrate APIs are stable points to depend on for plugins.

## See also

- `bevy-migration-0-17-to-0-18` — the catalogue of renames and breaks.
- `bevy-cargo-features` — what to put in `Cargo.toml` before any of the above will compile the way you want.
