# Bevy 0.20 — State schedules: OnEnter, OnExit, OnTransition

## The three state schedules

`#[derive(States)]` plus `app.init_state::<S>()` registers three schedule families:

| Schedule | Fires | Use for |
|----------|-------|---------|
| `OnEnter(S::X)` | Once, right after the state transitions **into** `X`. | Spawning setup entities, loading assets, resetting timers. |
| `OnExit(S::X)` | Once, right before leaving `X`. | Despawning setup entities, stopping audio, saving progress. |
| `OnTransition { exited: S::A, entered: S::B }` | Once, for the specific A→B pair only. | Transition-specific effects (fade on A→B but not on C→B). |

The fields are `exited` and `entered`. Stale LLM output writes `{ from, to }`, which does not compile.

## Minimal working example

```rust
use bevy::prelude::*;

#[derive(States, Default, Hash, PartialEq, Eq, Clone, Debug)]
enum GameState { #[default] Loading, Playing, Paused }

fn wire_states(app: &mut App) {
    app.init_state::<GameState>()
        // Fires once when entering Playing.
        .add_systems(OnEnter(GameState::Playing), spawn_level)
        // Fires once when leaving Playing, whatever comes next.
        .add_systems(OnExit(GameState::Playing), despawn_level)
        // Fires only on Playing → Paused.
        .add_systems(
            OnTransition { exited: GameState::Playing, entered: GameState::Paused },
            freeze_animations,
        )
        // Runs every tick while in Playing (run condition approach).
        .add_systems(Update, game_tick.run_if(in_state(GameState::Playing)));
}

#[derive(Component)]
struct LevelEntity;

fn spawn_level(mut commands: Commands) {
    commands.spawn((LevelEntity, Name::new("level")));
}

fn despawn_level(mut commands: Commands, query: Query<Entity, With<LevelEntity>>) {
    for entity in &query {
        commands.entity(entity).despawn();
    }
}

fn freeze_animations() {}
fn game_tick() {}
```

## Registering states with `init_state`

`app.init_state::<S>()` inserts `State<S>` (current) and `NextState<S>` (pending) and registers the schedules. Do not insert `State<S>` by hand.

## Driving transitions with `NextState<S>`

```rust
fn check_loading(mut next_state: ResMut<NextState<GameState>>) {
    if loading_complete() {
        next_state.set(GameState::Playing);
    }
}
```

The transition applies in `StateTransition`, which runs after `PreUpdate` and before `Update` on the next frame. `OnExit` of the old state then `OnEnter` of the new state run during that transition.

## `set` vs `set_if_different`

`next_state.set(S::X)` **always** schedules a transition, even if `X` is already current. That re-runs `OnExit(X)`, `OnEnter(X)` and (since 0.19) `DespawnOnEnter`/`DespawnOnExit` for `X`.

`set_if_different` (renamed from `set_if_neq` in 0.20; the old name is deprecated) is a no-op when the target equals the current state:

```rust
// Re-fires OnExit/OnEnter even if already Playing.
next_state.set(GameState::Playing);

// No-op if already Playing.
next_state.set_if_different(GameState::Playing);
```

Related renames in 0.20: `NextState::PendingIfNeq` → `PendingIfDifferent`, `CommandsStatesExt::set_state_if_neq` → `set_state_if_different`.

## Automatic cleanup: `DespawnOnExit` / `DespawnOnEnter`

Attach `DespawnOnExit(S::X)` to an entity and Bevy despawns it when leaving `X`; `DespawnOnEnter(S::X)` despawns on entering `X`. 0.20 batches this with `despawn_all`, roughly 1.5× faster than per-entity despawns.

```rust
fn spawn_scoped(mut commands: Commands) {
    commands.spawn((LevelEntity, DespawnOnExit(GameState::Playing)));
}
```

## Schedule vs run condition — when to use which

| Situation | Approach |
|-----------|----------|
| One-shot setup on entering a state | `OnEnter(S::X)` |
| One-shot cleanup on leaving a state | `OnExit(S::X)` or `DespawnOnExit(S::X)` |
| Specific A→B transition effect | `OnTransition { exited, entered }` |
| Tick-by-tick logic while in a state | `Update` + `.run_if(in_state(S::X))` |
| Logic that runs in several states | `Update` + `.run_if(in_state(A).or_else(in_state(B)))` |

## Sub-states and computed states (brief)

- **Sub-states** (`#[derive(SubStates)]`) exist only while a parent state matches ("in-game menu within gameplay").
- **Computed states** (`#[derive(ComputedStates)]`) derive from other states ("is the player in any combat state?").

## See also

- [run-conditions.md](run-conditions.md) — `in_state`, `state_changed`, combinators.
- [system-sets.md](system-sets.md) — ordering work that runs inside a state.
- `bevy-core-concepts` — which schedule (`Startup`, `Update`, `FixedUpdate`) a system belongs in.
