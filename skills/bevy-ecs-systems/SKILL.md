---
name: bevy-ecs-systems
description: Use when deriving `SystemParam`, grouping with `SystemSet`, gating execution with `.run_if(on_message::<M>)` / `in_state(...)` / `resource_exists::<R>`, combining conditions with `.and_then()` / `.or_else()`, ordering with `.before`/`.after`/`.chain()`/`.chain_weak()`, driving states with `NextState::set_if_different`, or removing systems with `remove_systems_in_set` in Bevy 0.20.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "1"
  area: ecs
  bevy_version: "0.20"
---

# Bevy 0.20 — ECS Systems (params, sets, run conditions)

## When to use this skill

- Bundling related state into one parameter via `#[derive(SystemParam)]`.
- Grouping systems into a `SystemSet` so callers can order against the whole group.
- Gating systems with run conditions (`run_if`, `on_message`, `in_state`, `resource_exists`, `any_with_component`).
- Hooking into state transitions with `OnEnter(S)` / `OnExit(S)` / `OnTransition { exited, entered }`.
- Hot-removing systems at runtime (tearing down a debug overlay) with `remove_systems_in_set`.
- Choosing strict `.chain()` versus weak `.chain_weak()` ordering (0.20).

## Canonical pattern

```rust
use bevy::ecs::system::SystemParam;
use bevy::prelude::*;

#[derive(SystemSet, Hash, PartialEq, Eq, Clone, Debug)]
enum GameLoop { Input, Simulate, Render }

#[derive(States, Default, Hash, PartialEq, Eq, Clone, Debug)]
enum AppState { #[default] Loading, Playing }

#[derive(Resource, Default)]
struct Score(u32);

#[derive(Message)]
struct GoalScored { team: u8 }

// Composite param: pass one argument, get three.
// 'w = world borrow; 's = system-local state borrow.
#[derive(SystemParam)]
struct GameCtx<'w, 's> {
    time:  Res<'w, Time>,
    score: ResMut<'w, Score>,
    goals: MessageReader<'w, 's, GoalScored>,
}

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .init_resource::<Score>()
        .add_message::<GoalScored>()
        .init_state::<AppState>()
        .configure_sets(Update, (GameLoop::Input, GameLoop::Simulate, GameLoop::Render).chain())
        .add_systems(OnEnter(AppState::Playing), spawn_level)
        .add_systems(OnExit(AppState::Playing), despawn_level)
        .add_systems(Update, read_input.in_set(GameLoop::Input))
        .add_systems(
            Update,
            tally_goals
                .in_set(GameLoop::Simulate)
                .run_if(on_message::<GoalScored>),
        )
        .add_systems(Update, (draw_hud, start_game).in_set(GameLoop::Render))
        .run();
}

#[derive(Component)]
struct LevelEntity;

fn spawn_level(mut commands: Commands) {
    commands.spawn((LevelEntity, Name::new("level")));
}

fn despawn_level(mut commands: Commands, query: Query<Entity, With<LevelEntity>>) {
    for e in &query { commands.entity(e).despawn(); }
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

fn draw_hud(score: Res<Score>) { let _ = score.0; }

// 0.20: `set_if_different` (was `set_if_neq`) skips OnExit/OnEnter when
// the target equals the current state.
fn start_game(mut next: ResMut<NextState<AppState>>) {
    next.set_if_different(AppState::Playing);
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

Combine with `.and_then()` / `.or_else()` (short-circuit) or `.and_eager()` / `.or_eager()` (always evaluate both): `run_if(in_state(GameState::Playing).and_then(resource_exists::<NetSession>))`. Stale LLM output uses `.and()` / `.or()`; those methods do not exist.

## Topics

| Topic | Reference |
|---|---|
| `#[derive(SystemParam)]`, `'w`/`'s` lifetimes, `Local<T>`, `&mut World` as a param, `Commands` deferred apply | [references/system-params.md](references/system-params.md) |
| `#[derive(SystemSet)]` requirements, `.in_set`, `.configure_sets`, `.chain()` | [references/system-sets.md](references/system-sets.md) |
| Every built-in condition, combinators, custom conditions, cost rule | [references/run-conditions.md](references/run-conditions.md) |
| `OnEnter(S)` / `OnExit(S)` / `OnTransition`, `NextState<S>`, `set_if_different`, `DespawnOnExit` | [references/state-schedules.md](references/state-schedules.md) |
| `.before`, `.after`, `.chain()`, `.chain_weak()`, `.ambiguous_with`, `shuffle_seed`, debugging ambiguity | [references/ordering.md](references/ordering.md) |
| `remove_systems_in_set`, `ScheduleCleanupPolicy`, 3-arg vs 4-arg receivers, side-effect limits | [references/runtime-removal.md](references/runtime-removal.md) |

## Gotchas (0.18 → 0.20)

- **`&mut World` is a `SystemParam` (0.20).** It may appear anywhere in the parameter list, beside params that do not borrow the World (`Local<T>`, `&mut SystemState`, `&mut QueryState`). `ExclusiveSystemParam`, `ExclusiveFunctionSystem` and `System::is_exclusive()` are removed; exclusivity is tracked at runtime via `SystemAccess::is_exclusive()`.
- **`SystemParam` validation happens in `get_param` (0.19).** `SystemParam::validate_param` is gone; `get_param` returns `Result<Item, SystemParamValidationError>`. `SystemState::get`/`get_mut` now return `Result`, so add `.unwrap()` or `?`. Frequently-skipped systems (`Single`) now spawn a task before failing validation; add a `run_if` if that shows in profiles.
- **Generic `ResMut<R>` needs `R: Resource<Mutability = Mutable>` (0.19)** because resources can be immutable. `Res<R>` is unchanged.
- **`Command::Out` is an associated type (0.19).** `fn cmd() -> impl Command<Result>` → `impl Command`; `impl Command for Foo` must declare `type Out = ...`.
- **`NextState::set_if_neq` → `set_if_different` (0.20).** `PendingIfNeq` → `PendingIfDifferent`, `set_state_if_neq` → `set_state_if_different`. `set()` always runs `OnExit`/`OnEnter`, and since 0.19 `DespawnOnEnter`/`DespawnOnExit` also fire on a same-state `set()`.
- **`OnTransition { exited, entered }`**, not `{ from, to }`.
- **`.chain_weak()`, `.before_weak()`, `.after_weak()` (0.20)** order only systems whose tracked data access conflicts. Bevy's own `PostUpdate` UI sets and render sets use them; dependencies through channels or interior mutability need an explicit `.after(system)`.
- **No `SimpleExecutor` since 0.18.** Unordered conflicting systems run in arbitrary order and are *not* reported unless `ambiguity_detection` is raised. See [references/ordering.md](references/ordering.md).
- **`MessageReader` / `MessageWriter`, not `EventReader` / `EventWriter`.** `#[derive(Message)]`, `app.add_message::<M>()` (0.17+).
- **`remove_systems_in_set` returns `Result<usize, ScheduleError>`.** `Schedules::remove_systems_in_set` takes 4 args (`label, set, world, policy`); `Schedule::remove_systems_in_set` takes 3.
- **`System::type_id` → `System::system_type` (0.19).** `DefaultErrorHandler` → `FallbackErrorHandler` (0.19); it now also receives panics (0.20).
- **`WindowPlugin` exit systems run in `Last` (0.19)**, inside the `ExitSystems` set; systems after `Update` that rely on a window no longer panic on the final frame.

## See also

- `bevy-core-concepts` — which schedule (`Startup`, `Update`, `FixedUpdate`) to add a system to.
- `bevy-ecs-queries` — query is one of many `SystemParam`s; `Changed<T>` / `Added<T>` filters.
- `bevy-ecs-components` — defining the `Component` types your systems act on; observers.
- `bevy-migration-0-18-to-0-19` — param validation, `Command::Out`, executor renames.
- `bevy-migration-0-19-to-0-20` — exclusive unification, `chain_weak`, `set_if_different`.
