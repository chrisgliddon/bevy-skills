# Bevy 0.18 — Run conditions catalogue

## All built-in run conditions

| Condition | Triggers when |
|-----------|---------------|
| `on_message::<M>()` | `Messages<M>` buffer has at least one unread item this tick. |
| `resource_exists::<R>()` | Resource `R` is present in the `World`. |
| `resource_changed::<R>()` | `R` was mutated (marked changed) this tick. |
| `resource_added::<R>()` | `R` was first inserted into the `World` this tick. |
| `resource_removed::<R>()` | `R` was removed from the `World` this tick. |
| `in_state(MyState::X)` | `State<MyState>` equals `X` right now. |
| `state_changed::<MyState>()` | The current `MyState` value changed this tick. |
| `any_with_component::<C>()` | At least one entity in the `World` has component `C`. |
| `not(condition)` | Wraps any condition; inverts the result. |

## Combining conditions

Conditions implement the `.and()` and `.or()` combinators:

```rust
// Only runs if currently Playing AND a network session exists.
system.run_if(in_state(GameState::Playing).and(resource_exists::<NetSession>()))

// Runs if paused OR if in menus.
system.run_if(in_state(GameState::Paused).or(in_state(GameState::MainMenu)))

// Inverted: only runs when R is absent.
system.run_if(not(resource_exists::<DebugOverlay>()))
```

## Custom run conditions

A run condition is just a system that returns `bool`. Any `SystemParam` is valid:

```rust
fn is_high_score(score: Res<Score>, best: Res<BestScore>) -> bool {
    score.0 > best.0
}

app.add_systems(Update, play_fanfare.run_if(is_high_score));
```

The condition function follows all the same borrow rules as a regular system.

## Performance rule

**Do not put expensive work in a run condition.** Conditions run every tick
regardless of whether the main system ends up running. Gate expensive checks
inside the system body instead:

```rust
// BAD: expensive iteration every tick, even if system is skipped.
fn has_any_enemy(query: Query<&Enemy>) -> bool {
    query.iter().any(|e| e.is_active)  // O(n) every tick
}

// GOOD: skip the whole system cheaply, then do the expensive check inside.
app.add_systems(Update, combat_tick.run_if(any_with_component::<Enemy>()));

fn combat_tick(enemies: Query<&Enemy>) {
    for enemy in enemies.iter().filter(|e| e.is_active) { /* ... */ }
}
```

## Run conditions are themselves systems

They share the same `SystemParam` infrastructure. This means:
- They can read resources (`Res<T>`), queries, and messages.
- They *can* technically mutate world state, but doing so is strongly discouraged — keep conditions pure boolean checks.
- Borrow conflict rules apply — a run condition and its system cannot both hold
  a mutable borrow of the same resource.

## State-based gating: run condition vs schedule

`in_state(S)` is a run condition — the system is added to the normal `Update`
schedule but skipped unless the state matches.

`OnEnter(S)` / `OnExit(S)` are **separate schedules** — systems added there run
exactly once at the transition, not every tick. For setup/teardown that fires
once, prefer the schedule approach. See [state-schedules.md](state-schedules.md).

## See also

- [state-schedules.md](state-schedules.md) — `OnEnter`/`OnExit`/`OnTransition` for one-shot hooks.
- [system-sets.md](system-sets.md) — apply a condition to a whole set.
