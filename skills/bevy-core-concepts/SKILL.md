---
name: bevy-core-concepts
description: Use when wiring up an `App`, writing a `Plugin`, choosing between `Update` and `FixedUpdate`, ordering `Startup`/`PreUpdate`/`PostUpdate`, or writing an exclusive system (`fn(&mut World)`) in Bevy 0.18. Covers the schedule graph, run order, and the `SimpleExecutor` removal.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "1"
  area: ecs
  bevy_version: "0.18"
---

# Bevy 0.18 — Core concepts (App, Plugin, Schedule, World)

## When to use this skill

- Setting up a new Bevy app or library plugin.
- Deciding which schedule (`Startup`, `Update`, `FixedUpdate`, `PostUpdate`, ...) a system belongs in.
- Writing an exclusive system that needs `&mut World`.
- Hitting `ScheduleBuildError` panics at startup ("ambiguity" or "cycle").
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
            .add_systems(PostUpdate, sync_transforms);
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

// Exclusive system — full mutable World access, runs alone.
fn rebuild_index(world: &mut World) {
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
| `PostUpdate` | Reactive bookkeeping after `Update` (transform propagation lives here). |
| `Last` | Anything that must run after `PostUpdate` (rare). |
| `FixedFirst` / `FixedPreUpdate` / `FixedUpdate` / `FixedPostUpdate` / `FixedLast` | Deterministic, tick-rate work: physics, networking simulation, gameplay state. Runs zero or more times per render frame to catch up to `Time<Fixed>`. |

**Rule of thumb:** if a system must produce the same result for the same inputs regardless of frame rate, put it in `FixedUpdate`. Otherwise `Update`.

## Gotchas (0.18)

- **`SimpleExecutor` was removed.** If two systems in the same schedule both touch the same data, the schedule no longer guesses an order — it panics. Make order explicit with `.before(other)`, `.after(other)`, `.chain()`, or `.in_set(MySet)`.
- **`ScheduleBuildError` variants were renamed.** If you `match` on them, update: `HierarchyLoop` → `HierarchySort(DiGraphToposortError::Loop(...))`, `DependencyCycle` → `DependencySort(DiGraphToposortError::Cycle(...))`.
- **`FunctionSystem` grew an `In` generic.** Type aliases like `type Boxed = FunctionSystem<M, O, F>` need `FunctionSystem<M, I, O, F>` in 0.18.
- **`State::set()` now always triggers a transition** — even if the requested state equals the current one. Use `next_state.set_if_neq(...)` for the old "no-op when equal" behavior.
- Don't put rendering systems in `Update`. The render world is extracted automatically; reaching into it from `Update` is almost always a mistake. See `bevy-rendering-core` (future skill).
- Exclusive systems block everything in their schedule — use them only when you really need `&mut World` (scene loading, batch reflection, schema migrations).

## See also

- `bevy-ecs-systems` — system params, sets, run conditions, ordering.
- `bevy-ecs-components` — what entities are made of.
- `bevy-migration-0-17-to-0-18` — full list of executor and schedule renames.
