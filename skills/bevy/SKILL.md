---
name: bevy
description: Use when starting any Bevy task, choosing between Update and FixedUpdate, picking Cargo feature flags, or recalling which sibling skill covers ECS, assets, rendering, or migration. Routes between the Bevy 0.19 general baseline, staged Bevy 0.20 migration/physics guidance, and historical upgrade paths without mixing target versions.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "1"
  area: router
  bevy_version: "0.19"
---

# Bevy 0.19 baseline / Bevy 0.20 staged guidance — Router

**Read this first when working on a Bevy project.** Inspect the relevant
`Cargo.toml`, inherited workspace dependencies, and `Cargo.lock` before choosing a
skill. General implementation guidance still targets Bevy 0.19. Only the new
migration hop and `bevy-physics` have staged 0.20 guidance; this is not a claim that
all examples compile or behave correctly on 0.20.

## Choose the version before the topic

| Resolved project target | Route |
|---|---|
| Bevy 0.19, staying on 0.19 | Use general implementation skills below. For physics, use the [0.19 / Rapier 0.36 baseline](../bevy-physics/references/bevy-019-compatibility.md), not the new 0.20 canonical example. |
| Bevy 0.19, upgrading to 0.20 | Start with `bevy-migration-0-19-to-0-20`; verify each affected dependency and feature set. |
| Bevy 0.20 | Use `bevy-migration-0-19-to-0-20` and `bevy-physics` (Rapier 0.37). Other skill examples remain 0.19 references: verify/adapt them against 0.20 APIs before use. |
| Bevy 0.18 / 0.17 | Start with the corresponding historical migration hop below; preserve a working checkpoint before advancing. |
| Missing, inherited, mixed, or unsupported version | Resolve workspace/target manifests and lockfile; ask which target to support if still ambiguous. Do not silently select 0.19 or 0.20. |

For a new project without a manifest, establish the intended engine version before
copying a dependency set. See [0.20 readiness](references/bevy-020-readiness.md) for
remaining validation and ecosystem gates. Following a cross-link does not change
the linked skill's version pin.

## Smallest valid Bevy 0.19 app

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

Unless marked otherwise, implementation rows below target Bevy 0.19.

| Task | Skill |
|---|---|
| App / Plugin / Schedule basics, Update vs FixedUpdate, exclusive systems | `bevy-core-concepts` |
| Rebindable actions, gamepad hot-plug, deadzones, mouse capture, frame-to-fixed input | `bevy-input-actions` |
| Deterministic App/time stepping, messages/observers, async and visual tests | `bevy-testing` |
| `#[derive(Component)]`, `#[require(...)]`, observers (`On<E>`), hooks, storage | `bevy-ecs-components` |
| `Query`, filters, `par_iter`, query lenses, `IterQueryData`, `SingleEntityQueryData` | `bevy-ecs-queries` |
| `SystemParam`, `SystemSet`, `.run_if`, ordering, `remove_systems_in_set` | `bevy-ecs-systems` |
| `Cargo.toml` features: `2d`/`3d`/`ui`, mid-level `2d_api`, renamed features | `bevy-cargo-features` |
| Upgrading from 0.17 — `MessageReader`, `On`, `RenderTarget`, `GlobalAmbientLight`, etc. | `bevy-migration-0-17-to-0-18` |
| Upgrading from 0.18 — resources-as-components, `FontSource`, `WorldAssetRoot`, `Discard` | `bevy-migration-0-18-to-0-19` |
| Upgrading from 0.19 — lifecycle/pointer events, WESL, query changes, Rapier 0.37 | `bevy-migration-0-19-to-0-20` |
| `AssetServer`, handles, hot-reload, glTF `WorldAssetRoot`/`WorldInstanceReady` | `bevy-assets` |
| Writing an `AssetLoader`, `LoadContext::load_builder`, `SeekableReader` | `bevy-custom-assets` |
| Versioned save DTOs, stable IDs, migrations, atomic native/browser persistence | `bevy-save-load` |
| WASM build pipeline, WebGPU vs WebGL2 | `bevy-wasm-webgpu` |
| `Camera3d`, projections/targets, free/pan controls, third-person orbit/obstruction | `bevy-cameras` |
| Built-in renderer vs custom/headless/external paths, forward vs deferred | `bevy-rendering` |
| Custom diagnostics, tracing spans, render CPU/GPU timings, platform budgets | `bevy-diagnostics-profiling` |
| Bevy 0.20: `RapierPhysicsPlugin`, `RigidBody`, `Collider`, queries, controllers | `bevy-physics` (Rapier 0.37; use the 0.19 baseline link above for older projects) |
| `StandardMaterial`, `MaterialPlugin<M>`, `AsBindGroup::label()`, PBR tuning | `bevy-pbr-materials` |
| glTF clips, `AnimationGraph`, transitions, masks, events, procedural animation | `bevy-animation` |
| Hanabi particles, shaders, Gaussian splats, compatible VFX crates | `bevy-vfx` |
| `AudioPlayer`, sinks, spatial listeners, mix/transition policy, Seedling boundary | `bevy-audio` |
| Voxel meshing with `block-mesh-rs`, chunk pipeline, greedy quads | `bevy-voxel-pipeline` |
| RON block definitions, palette, KTX2 atlas baking | `bevy-voxel-data` |
| Dirty sections, revision tokens, coalesced remesh queues, bounded mesh/collider swaps | `bevy-voxel-runtime` |
| Camera recording, MP4/PNG encoders, ffmpeg integration | `bevy-capture` |
| `es-fluent-manager-bevy` i18n — `FluentText<T>`, `BevyFluentText`, `LocaleChangeEvent`, `i18n.toml` | `bevy-fluent` |
| `Node`, `Button`, `Interaction`, `children![]`, `TextFont`, `InputFocus`, `BorderRadius`, `BackgroundColor` | `bevy-ui` |
| Screen readers, focus navigation, captions, contrast, remapping, adaptive controllers | `bevy-a11y` |
| Porting from Unity, Unreal, Godot, Cocos, web engines, Flash, Defold, Roblox, or GameMaker | `bevy-porting` |
| Detecting copy-paste / near-duplicate Rust code before committing (`similarity-rs --cross-file`) | `similarity-rs` |

## Cardinal rules (every Bevy 0.19 task)

1. **Events are messages.** `EventReader<E>` and `EventWriter<E>` were renamed to `MessageReader<M>` / `MessageWriter<M>` in 0.17. They are still wrong in 0.19.
2. **Observers use `On<E>`, not `Trigger<E>`.** `Trigger` was renamed in 0.17 (PR #19596).
3. **Declare order when behavior depends on it.** Shared mutable access prevents
   parallel execution but does not choose a logical order. Use `.before()`, `.after()`,
   or `.chain()`, especially when deferred commands must be visible downstream.
4. **No `.unwrap()` in systems.** Systems run every frame. Use `let ... else { return };` or a real error path.
5. **Resources are singleton components in 0.19.** Each resource lives on a
   resource entity. Inserting the same `Resource` type on an ordinary entity can
   move singleton ownership, so do not mix resource and ordinary-component use;
   audit broad `Query<&T>` access.
6. **Text uses `FontSource` and `FontSize`.** Convert handles with `.into()` and sizes with `FontSize::Px(...)`.
7. **Classic scene serialization moved.** Use `bevy_world_serialization`, `WorldAssetRoot`, and `DynamicWorld`; `bevy_scene` now hosts BSN.
8. **Lifecycle replacement is discard.** Use `Discard`, `on_discard`, and `#[component(on_discard = ...)]`.
9. **Camera render nodes became systems.** Extend `Core2d`/`Core3d` with render
   systems. The top-level non-camera schedule named `RenderGraph` still exists.
10. **Physics is a plugin choice.** Bevy core has no rigid-body engine. Match the
    engine/plugin pair: Bevy 0.19 uses Rapier 0.36; the updated `bevy-physics`
    canonical example uses Bevy 0.20 / Rapier 0.37. Do not mix them.
11. **Frame input is not fixed-tick input.** Queue action edges and accumulate
    relative motion after `InputSystems`; drain once on the first available fixed tick
    while carrying held/absolute state to every tick.
12. **Runtime IDs are not save IDs.** Persist immutable domain identifiers in a
    versioned DTO and rebuild dense palettes/entities/handles while loading.

## Gotchas

- Bevy's training-data footprint is dominated by older code. Check the migration skill for the relevant hop before trusting an apparently familiar snippet.
- `bevy::prelude::*` doesn't re-export everything. Many ECS internals live under `bevy::ecs::...` — import explicitly when needed.
- The `bevy` crate now re-exports many subcrates (`bevy_camera`, `bevy_light`, `bevy_post_process`, `bevy_anti_alias`, `bevy_input_focus`, `bevy_gizmos_render`, `bevy_sprite_render`, `bevy_ui_render`). Subcrate APIs are stable points to depend on for plugins.

## See also

- `bevy-migration-0-19-to-0-20` — staged 0.20 upgrade catalogue.
- `bevy-migration-0-18-to-0-19` — preserved 0.19 upgrade catalogue.
- `bevy-migration-0-17-to-0-18` — historical rename catalogue.
- `bevy-cargo-features` — what to put in `Cargo.toml` before any of the above will compile the way you want.
- `bevy-physics` — Bevy 0.20 / Rapier 0.37 setup, ordering, queries, and controllers.
- [Bevy 0.19 physics baseline](../bevy-physics/references/bevy-019-compatibility.md) — preserved Rapier 0.36 guidance.
- `bevy-input-actions` — logical input, devices, and the fixed-step bridge.
- `bevy-testing` — deterministic app stepping and visual regression.
- `bevy-diagnostics-profiling` — metrics, traces, render timing, and budgets.
