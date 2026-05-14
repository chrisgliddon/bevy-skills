# Bevy 0.18 — State schedules: OnEnter, OnExit, OnTransition

This is the **parity-trial gap** topic. Neither `OnEnter` nor `OnExit` appeared in
the previous skill body. This file closes that gap.

## The three state schedules

Bevy creates three schedules automatically for every state type derived with
`#[derive(States)]`:

| Schedule | Fires | Use for |
|----------|-------|---------|
| `OnEnter(MyState::X)` | Once, immediately after the state transitions **into** `X`. | Spawning setup entities, loading assets, resetting timers. |
| `OnExit(MyState::X)` | Once, immediately before leaving `X` (new state is set but not yet current). | Despawning setup entities, stopping audio, saving progress. |
| `OnTransition { from: MyState::A, to: MyState::B }` | Once, for the specific A→B pair only. | Transition-specific effects (e.g. fade on A→B but not on C→B). |

## Minimal working example

```rust
use bevy::prelude::*;

#[derive(States, Default, Hash, PartialEq, Eq, Clone, Debug)]
enum AppState {
    #[default]
    Loading,
    Playing,
    Paused,
}

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .init_state::<AppState>()
        // Fires once when entering Playing.
        .add_systems(OnEnter(AppState::Playing), spawn_level)
        // Fires once when leaving Playing (covers Paused and any other successor).
        .add_systems(OnExit(AppState::Playing), despawn_level)
        // Fires only on Playing → Paused, not on Playing → Loading.
        .add_systems(
            OnTransition { from: AppState::Playing, to: AppState::Paused },
            freeze_animations,
        )
        // Runs every tick while in Playing state (run condition approach).
        .add_systems(Update, game_tick.run_if(in_state(AppState::Playing)))
        .run();
}

/// Marker component so despawn_level only touches entities this system spawned.
#[derive(Component)]
struct LevelEntity;

fn spawn_level(mut commands: Commands) {
    commands.spawn((LevelEntity, Name::new("level"), /* ... */));
}

fn despawn_level(mut commands: Commands, query: Query<Entity, With<LevelEntity>>) {
    for entity in &query {
        commands.entity(entity).despawn();
    }
}

fn freeze_animations(/* ... */) {}

fn game_tick(/* ... */) {}
```

## Registering states with `init_state`

Use `app.init_state::<S>()`. This inserts both `State<S>` (current) and
`NextState<S>` (pending) resources, and registers the three schedule families.

Do NOT manually insert `State<S>` — `init_state` does all the wiring.

## Driving transitions with `NextState<S>`

Set the next state from any system by writing to `NextState<S>`:

```rust
fn check_loading(
    mut next_state: ResMut<NextState<AppState>>,
    // ...
) {
    if loading_complete() {
        next_state.set(AppState::Playing);
    }
}
```

The transition is applied at the end of the current schedule run. `OnExit` of
the old state and `OnEnter` of the new state fire immediately after.

## `set` vs `set_if_neq` — the always-fires change

In Bevy 0.18, calling `next_state.set(S::X)` **always** marks `NextState` as
changed, even if `S::X` is already the current state. This means `OnExit` and
`OnEnter` will fire again unnecessarily.

Use `set_if_neq` when you want the old 0.17 behaviour — only transition if the
value actually differs:

```rust
// 0.18 default: always transitions (re-fires OnExit/OnEnter even if already in X)
next_state.set(AppState::Playing);

// Preferred: no-op if already in Playing
next_state.set_if_neq(AppState::Playing);
```

## Schedule vs run condition — when to use which

| Situation | Approach |
|-----------|----------|
| One-shot setup on entering a state | `OnEnter(S::X)` |
| One-shot cleanup on leaving a state | `OnExit(S::X)` |
| Specific A→B transition effect | `OnTransition { from, to }` |
| Tick-by-tick logic while in a state | `Update` + `.run_if(in_state(S::X))` |
| Logic that runs in several states | `Update` + `.run_if(in_state(A).or(in_state(B)))` |

Mixing both approaches is fine and common: use `OnEnter` to spawn entities, use
`in_state` to tick them, use `OnExit` to clean up.

## State stacks, sub-states, computed states (brief)

Bevy 0.18 also supports:
- **Sub-states** (`#[derive(SubStates)]`) — a state whose existence depends on a
  parent state. Useful for "in-game-menu within gameplay".
- **Computed states** (`#[derive(ComputedStates)]`) — a state derived from one
  or more other states. Useful for "is the player in any combat state?".
- **Freeable states** — states removed from the world entirely when not active.

These are more advanced patterns. A dedicated `bevy-states` skill can cover them
in depth; this file focuses on the core `OnEnter`/`OnExit` gap.

## See also

- [run-conditions.md](run-conditions.md) — `in_state`, `state_changed`, and composing conditions.
- [system-sets.md](system-sets.md) — ordering work that runs inside a state.
- `bevy-core-concepts` — which schedule (`Startup`, `Update`, `FixedUpdate`) a system belongs in.
