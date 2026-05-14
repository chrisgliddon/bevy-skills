---
name: bevy-migration-0-17-to-0-18
description: Use when upgrading from Bevy 0.17 to Bevy 0.18, when an LLM writes `EventReader`/`EventWriter`/`Trigger<E>` instead of `MessageReader`/`MessageWriter`/`On<E>`, when `mesh.insert_attribute` fails to compile, when `AmbientLight` no longer works as a resource, or when `Camera { target: ... }` errors on the `target` field. Index of every breaking 0.17→0.18 change.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "1"
  area: migration
  bevy_version: "0.18"
---

# Bevy 0.17 → 0.18 — Migration cheat sheet

**Released 2026-01-13.** This skill enumerates every breaking change you're likely to hit. Apply top-down — earlier items break later builds if skipped.

## When to use this skill

- Compiler errors after a `bevy = "0.17"` → `bevy = "0.18"` bump.
- LLM emits 0.17-era API names from training data.
- Auditing a PR for hidden 0.18-incompatible patterns.
- Hot-fixing a downstream crate that hasn't shipped 0.18 yet.

## The renames you'll hit first

### Observers: `Trigger<E>` → `On<E>` (carried from 0.17)

```rust
// 0.16 or older — still in training data
// fn on_hit(trigger: Trigger<Damage>) { let e = trigger.event(); }

// 0.18 (also 0.17)
fn on_hit(on: On<Damage>) { let _e = on.event(); }
```

### Buffered events: `Event` → `Message` (carried from 0.17)

```rust
// Old (training data)
// #[derive(Event)] struct Tick;
// fn sys(mut reader: EventReader<Tick>) { for _ in reader.read() {} }
// fn write(mut w: EventWriter<Tick>) { w.send(Tick); }

// 0.18
#[derive(Message)] struct Tick;
// app.add_message::<Tick>();
fn read(mut reader: MessageReader<Tick>) { for _ in reader.read() {} }
fn write(mut w: MessageWriter<Tick>) { w.write(Tick); }
```

`Event` is now reserved for **observed**, entity-targeted events (`#[derive(EntityEvent)]`). `Message` is for the buffered, polling-style API.

### `Camera { target: ... }` → `RenderTarget` component

```rust
// 0.17
// commands.spawn(Camera3d::default()).insert(Camera {
//     target: RenderTarget::Image(handle.into()), ..default()
// });

// 0.18
commands.spawn((Camera3d::default(), RenderTarget::Image(handle.into())));
```

### `AmbientLight` is no longer a resource

```rust
// 0.17
// app.insert_resource(AmbientLight { brightness: 2000.0, ..default() });

// 0.18: per-camera override component, world default is a separate resource
app.insert_resource(GlobalAmbientLight { brightness: 2000.0, ..default() });
// Per-camera override:
commands.spawn((Camera3d::default(), AmbientLight { brightness: 5000.0, ..default() }));
```

### `MaterialPlugin<M>` config moved to trait methods

```rust
// 0.17
// app.add_plugins(MaterialPlugin::<M> { prepass_enabled: false, shadows_enabled: false, ..default() });

// 0.18
impl Material for M {
    fn enable_prepass() -> bool { false }
    fn enable_shadows() -> bool { false }
    // ...
}
app.add_plugins(MaterialPlugin::<M>::default());
```

### `AsBindGroup::label()` is now required

```rust
impl AsBindGroup for MyMaterial {
    fn label() -> &'static str { "MyMaterial" } // required in 0.18
    // ...
}
```

### `AssetLoader` must `#[derive(TypePath)]`

```rust
#[derive(TypePath)]            // required in 0.18
struct MyLoader;
impl AssetLoader for MyLoader { /* ... */ }
```

### `Mesh::insert_attribute` is now panicky — prefer `try_insert_attribute`

In 0.18 `insert_attribute` panics if the mesh has already been extracted to the render world (a real race in tools that mutate meshes post-spawn). Prefer the new fallible form:

```rust
// 0.18 — the safe form returns Result<(), MeshAccessError>.
mesh.try_insert_attribute(Mesh::ATTRIBUTE_POSITION, positions)?;
```

`insert_attribute` is still available and still works pre-extract — it just `.expect()`s the result internally.

### `State::set` always triggers a transition

```rust
// 0.17: setting to the same state was a no-op
// 0.18: always triggers OnExit + OnEnter. Use:
next_state.set_if_neq(GameState::Playing);
```

### glTF coordinate conversion replaced

```rust
// 0.17
// GltfPlugin { use_model_forward_direction: true, ..default() }

// 0.18
GltfPlugin {
    convert_coordinates: GltfConvertCoordinates {
        rotate_scene_entity: true,
        rotate_meshes: true,
    },
    ..default()
}
```

## API moves & smaller renames

| 0.17 | 0.18 |
|---|---|
| `bevy::ecs::component::Tick` | `bevy::ecs::change_detection::Tick` |
| `bevy::ecs::component::ComponentTicks` | `bevy::ecs::change_detection::ComponentTicks` |
| `bevy::ecs::component::TickCells` | `bevy::ecs::change_detection::ComponentTickCells` |
| `Entity::row()` / `Entity::from_row(...)` | `Entity::index()` / `Entity::from_index(...)` |
| `clear_children()` | `detach_all_children()` |
| `remove_children(...)` | `detach_children(...)` |
| `HashMap::get_many_mut(...)` | `HashMap::get_disjoint_mut(...)` |
| `gizmos.cuboid(...)` | `gizmos.cube(...)` |
| `LoadContext::asset_bytes()` | `let r = ctx.asset_reader(); r.read_to_end(&mut buf).await?;` |
| `FunctionSystem<M, O, F>` | `FunctionSystem<M, I, O, F>` (new `In` generic) |
| `#[reflect[Clone]]`, `#[reflect{Clone}]` | only `#[reflect(Clone)]` |
| `ScheduleBuildError::HierarchyLoop` | `HierarchySort(DiGraphToposortError::Loop(..))` |
| `ScheduleBuildError::DependencyCycle` | `DependencySort(DiGraphToposortError::Cycle(..))` |

## Schedule executor

- **`SimpleExecutor` was removed.** Schedules now panic on undeclared ambiguities. Add `.before()`, `.after()`, `.chain()`, `.in_set(...)`, or explicit `.ambiguous_with(...)`.
- System combinator `or` now coerces validation failure to `false` instead of propagating.

## AssetSource channel

```rust
// 0.17
// sender.send(event)?;        // crossbeam_channel
// 0.18
sender.send_blocking(event)?; // async_channel
```

## Cargo feature renames

| 0.17 | 0.18 |
|---|---|
| `animation` | `gltf_animation` |
| `bevy_sprite_picking_backend` | `sprite_picking` |
| `bevy_ui_picking_backend` | `ui_picking` |
| `bevy_mesh_picking_backend` | `mesh_picking` |
| `documentation` | `reflect_documentation` |

Input is no longer in `default-features = false`. Add `mouse` / `keyboard` / `gamepad` / `touch` / `gestures` explicitly.

## Gotchas

- **`bevy_gizmos` was split.** Render-side code now lives in `bevy_gizmos_render`. If you used internals, update the import path.
- **`Resource` no longer allows non-`'static` lifetimes.** A `Resource` with a borrowed field will fail to compile.
- **Reflect attribute syntax tightened.** Anything other than `#[reflect(...)]` (parens) is rejected.
- **`AnimationTarget` split into two components.** Update spawn code: `(AnimationTargetId(id), AnimatedBy(player))`.
- **`Atmosphere` now references a `Handle<ScatteringMedium>`** — what was a flat struct is now indirect.

## See also

- `bevy-core-concepts` — the schedule executor change in detail.
- `bevy-cargo-features` — feature rename table.
- `bevy-ecs-systems` — Message/MessageReader/MessageWriter ergonomics.
