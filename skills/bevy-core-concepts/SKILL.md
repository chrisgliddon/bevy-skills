---
name: bevy-core-concepts
description: Use when wiring up an `App`, writing a `Plugin`, choosing between `Update` and `FixedUpdate`, ordering `Startup`/`PreUpdate`/`PostUpdate`, writing an exclusive system that takes `&mut World` as a `SystemParam`, or deciding between `.chain()` and `.chain_weak()` in Bevy 0.20. Covers the schedule graph, run order, `set_executor`, and ambiguity detection.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "1"
  area: ecs
  bevy_version: "0.20"
---

# Bevy 0.20 — Core concepts (App, Plugin, Schedule, World)

## When to use this skill

- Setting up a new Bevy app or library plugin.
- Deciding which schedule (`Startup`, `Update`, `FixedUpdate`, `PostUpdate`, ...) a system belongs in.
- Writing an exclusive system that needs `&mut World`.
- Hitting `ScheduleBuildError` panics at startup ("cycle", "hierarchy") or wanting ambiguity checks.
- Asking "where should X run?"

## Canonical pattern

```rust
use bevy::prelude::*;

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_plugins(GamePlugin)
        .run();
}

pub struct GamePlugin;

impl Plugin for GamePlugin {
    fn build(&self, app: &mut App) {
        app.insert_resource(Score(0))
            .add_systems(Startup, spawn_world)
            .add_systems(Update, (read_input, apply_gravity).chain())
            .add_systems(FixedUpdate, simulate_physics)
            .add_systems(PostUpdate, sync_transforms)
            .add_systems(Last, rebuild_index);
    }
}

#[derive(Resource)]
struct Score(u32);

fn spawn_world(mut commands: Commands) {
    commands.spawn((Camera3d::default(), Transform::from_xyz(0.0, 4.0, 8.0)));
}

fn read_input(_keys: Res<ButtonInput<KeyCode>>) {}
fn apply_gravity(_t: Res<Time>) {}
fn simulate_physics(_t: Res<Time<Fixed>>) {}
fn sync_transforms(_q: Query<&mut Transform>) {}

// Exclusive system. Since 0.20 `&mut World` is an ordinary `SystemParam`:
// it can sit anywhere in the list, beside params that do not borrow the
// World (`Local`). The executor still runs it alone.
fn rebuild_index(mut runs: Local<u32>, world: &mut World) {
    *runs += 1;
    let count = world.entities().len();
    world.insert_resource(EntityCount(count));
}

#[derive(Resource)]
struct EntityCount(u32);
```

## Schedule cheat sheet

| Schedule | Use for |
|---|---|
| `Startup` | One-shot setup. Runs once before `Update`. |
| `PreUpdate` | Reading input, networking ingress, frame-start bookkeeping. |
| `Update` | Per-frame game logic. Runs at render rate. **Default for game systems.** |
| `PostUpdate` | Reactive bookkeeping after `Update` (transform propagation, UI layout live here). |
| `Last` | Anything that must run after `PostUpdate`. Window close/exit systems live here since 0.19. |
| `FixedFirst` / `FixedPreUpdate` / `FixedUpdate` / `FixedPostUpdate` / `FixedLast` | Deterministic, tick-rate work: physics, networking simulation, gameplay state. Runs zero or more times per render frame to catch up to `Time<Fixed>`. |

**Rule of thumb:** if a system must produce the same result for the same inputs regardless of frame rate, put it in `FixedUpdate`. Otherwise `Update`.

## Ambiguity: it does not panic by default

Two unordered systems that write the same data run in an arbitrary order. `ScheduleBuildSettings::default()` sets `ambiguity_detection: LogLevel::Ignore`. Opt in to catch them:

```rust
fn randomize_update_order(app: &mut App) {
    use bevy::ecs::schedule::{LogLevel, ScheduleBuildSettings};
    app.edit_schedule(Update, |schedule| {
        schedule.set_build_settings(ScheduleBuildSettings {
            // Turn silent ambiguities into a build-time panic.
            ambiguity_detection: LogLevel::Error,
            ..default()
        });
    });
}
```

With the `debug` feature, `ScheduleBuildSettings` also has `shuffle_seed: Option<u64>` (0.20). Set it to shuffle unordered systems and prove your ordering constraints are complete.

## Gotchas (0.18 → 0.20)

- **Resources are components (0.19).** `#[derive(Resource)]` now implies `Component`; `#[derive(Component, Resource)]` on one type fails to compile. `Res`/`ResMut`/`insert_resource` are unchanged. Each resource lives on a hidden entity tagged `IsResource`, so broad queries (`Query<Entity>`, `Query<EntityRef>`) see it; add `Without<IsResource>` (`bevy::ecs::resource::IsResource`) when they conflict with `ResMut`.
- **Non-send resources are "non-send data" (0.19).** `init_non_send_resource` → `init_non_send`, `insert_non_send_resource` → `insert_non_send`, `World::non_send_resource` → `World::non_send`. Old names are deprecated.
- **Exclusive systems are unified (0.20).** `ExclusiveSystemParam`, `ExclusiveFunctionSystem` and `System::is_exclusive()` are gone. `&mut World` is a `SystemParam` and need not be the first argument. `WorldId` is no longer a valid exclusive param; use `world.id()` or `Local<WorldId>`.
- **`SimpleExecutor` was removed in 0.18.** Insertion order no longer means run order. The default executor is multi-threaded and ambiguities are *ignored*, not reported, unless you set `ambiguity_detection` (see above). Stale LLM output claiming "ambiguity panics at startup" is wrong.
- **`set_executor` replaced `ExecutorKind` (0.19).** `schedule.set_executor_kind(ExecutorKind::SingleThreaded)` → `schedule.set_executor(SingleThreadedExecutor::new())`. `get_executor_kind` has no replacement.
- **Built-in schedules order their sets with `.chain_weak()` (0.20).** `PostUpdate` UI sets and the render-world sets only order systems whose tracked data access conflicts. If your system relied on a previous set finishing (via channels, atomics, interior mutability), add an explicit `.after(system)`.
- **`FallbackErrorHandler` (0.19), panics become errors (0.20).** `DefaultErrorHandler` is renamed. In 0.20 a panic in a system, command or observer is routed to the fallback handler, which re-panics by default; override it to log and continue.
- **`ScheduleBuildError` variants (0.18+).** `HierarchyLoop` → `HierarchySort(DiGraphToposortError::Loop(..))`, `DependencyCycle` → `DependencySort(DiGraphToposortError::Cycle(..))`, `Ambiguity(AmbiguousSystemConflictsWarning)`.
- **`FunctionSystem<M, I, O, F>` (0.18+)** carries an `In` generic. Type aliases written as `FunctionSystem<M, O, F>` fail.
- **`System::type_id` → `System::system_type` (0.19)** to stop shadowing `Any::type_id`.
- **`NextState::set` always transitions; `set_if_different` skips same-state (0.20 name, was `set_if_neq`).** See `bevy-ecs-systems`.
- Don't put rendering systems in `Update`. The render world is extracted automatically. See `bevy-rendering`.
- Exclusive systems block everything in their schedule. Use them only when you really need `&mut World` (scene loading, batch reflection, schema migrations).

## See also

- `bevy-ecs-systems` — system params, sets, run conditions, ordering, `chain_weak`.
- `bevy-ecs-components` — what entities are made of; observers and hooks.
- `bevy-migration-0-18-to-0-19` — resources-as-components, executor and error-handler renames.
- `bevy-migration-0-19-to-0-20` — exclusive-system unification, weak ordering, observer generics.
