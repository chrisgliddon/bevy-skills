---
name: bevy-ecs-systems
description: Use when deriving `SystemParam`, grouping with `SystemSet`, gating execution with `.run_if(on_message::<M>())` / `in_state(...)` / `resource_exists::<R>`, ordering with `.before`/`.after`/`.chain()`, or removing systems at runtime with `remove_systems_in_set` (new in 0.18). Covers Bevy 0.18 system params, sets, and run conditions.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "1"
  area: ecs
  bevy_version: "0.18"
---

# Bevy 0.18 — ECS Systems (params, sets, run conditions)

## When to use this skill

- Bundling related state into a single system parameter via `#[derive(SystemParam)]`.
- Grouping systems into a `SystemSet` so callers can order against the whole group.
- Gating systems with run conditions (`run_if`, `on_message`, `in_state`, `resource_exists`, `any_with_component`).
- Hot-removing systems at runtime (e.g. tearing down a debug overlay) with `remove_systems_in_set`.
- Hitting `ScheduleBuildError` ambiguity panics — the executor no longer guesses.

## Canonical pattern

```rust
use bevy::ecs::system::SystemParam;
use bevy::prelude::*;

#[derive(SystemSet, Hash, PartialEq, Eq, Clone, Debug)]
enum GameLoop {
    Input,
    Simulate,
    Render,
}

#[derive(Resource, Default)]
struct Score(u32);

#[derive(Message)]
struct GoalScored {
    team: u8,
}

// Composite param: pass one argument, get four.
// 'w = world borrow; 's = system-local state borrow.
#[derive(SystemParam)]
struct GameCtx<'w, 's> {
    time: Res<'w, Time>,
    score: ResMut<'w, Score>,
    goals: MessageReader<'w, 's, GoalScored>,
}

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .init_resource::<Score>()
        .add_message::<GoalScored>()
        .configure_sets(Update, (GameLoop::Input, GameLoop::Simulate, GameLoop::Render).chain())
        .add_systems(Update, read_input.in_set(GameLoop::Input))
        // Two run conditions: only when a GoalScored fired AND not paused.
        .add_systems(
            Update,
            tally_goals
                .in_set(GameLoop::Simulate)
                .run_if(on_message::<GoalScored>),
        )
        .add_systems(Update, draw_hud.in_set(GameLoop::Render))
        .run();
}

fn read_input(mut writer: MessageWriter<GoalScored>) {
    writer.write(GoalScored { team: 0 });
}

fn tally_goals(mut ctx: GameCtx) {
    let _ = ctx.time.delta_secs();
    for goal in ctx.goals.read() {
        ctx.score.0 += 1;
        info!("team {} scored, total {}", goal.team, ctx.score.0);
    }
}

fn draw_hud(score: Res<Score>) {
    let _ = score.0;
}

// Removing a whole set of systems at runtime — new in 0.18.
// Useful for debug overlays, mod hot-unload, transient inspector UIs.
fn unload_render(world: &mut World) {
    use bevy::ecs::schedule::ScheduleCleanupPolicy;
    world.resource_scope(|world, mut schedules: Mut<Schedules>| {
        let _ = schedules.remove_systems_in_set(
            Update,
            GameLoop::Render,
            world,
            ScheduleCleanupPolicy::default(), // RemoveSetAndSystems
        );
    });
}
```

## Run condition cheat sheet

| Built-in | Triggers when |
|---|---|
| `on_message::<M>` | The `Messages<M>` buffer has unread items. |
| `resource_exists::<R>` | Resource `R` is in the `World`. |
| `resource_changed::<R>` | `R` was mutated this tick. |
| `in_state(MyState::X)` | Current `State<MyState>` equals `X`. |
| `state_changed::<MyState>` | The state changed this tick. |
| `any_with_component::<C>` | At least one entity has `C`. |

Combine with `.and()` / `.or()`: `run_if(in_state(GameState::Playing).and(resource_exists::<NetSession>))`.

## Gotchas (0.18)

- **`SimpleExecutor` is gone.** Any ambiguity between systems that share data is now a build-time error. Fix with `.before(other)`, `.after(other)`, `.chain()`, `.ambiguous_with(other)` (explicit accept), or `.in_set(...).before(SomeSet)`.
- **`MessageReader` / `MessageWriter`, not `EventReader` / `EventWriter`.** Renamed in 0.17. The trait derive is `#[derive(Message)]` and the registrar is `app.add_message::<M>()`.
- **Run conditions are themselves systems.** They have full `SystemParam` access. Don't put expensive work in a condition — gate inside the system instead.
- **`SystemParam` derive needs two lifetimes.** `'w` is the world borrow; `'s` is the system-local state. `MessageReader<'w, 's, M>` and `Local<'s, T>` both need `'s`; `Res<'w, R>` only needs `'w`.
- **`remove_systems_in_set` doesn't propagate to nested schedules.** If `MySet` is in `Update`, you must `schedules.get_mut(Update)`, not e.g. `FixedUpdate`.
- **Hot system removal does not unwind side effects.** Resources, entities, and observers stay. If your set spawned an overlay UI, despawn the entities in a separate teardown system.

## See also

- `bevy-core-concepts` — which schedule to add a system to.
- `bevy-ecs-queries` — query is one of many `SystemParam`s.
- `bevy-migration-0-17-to-0-18` — full Message/Event rename.
