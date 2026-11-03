# Bevy 0.20 — Run conditions catalogue

## All built-in run conditions

Conditions are plain `fn` items. Pass them without parentheses: `run_if(resource_exists::<R>)`.

| Condition | Triggers when |
|-----------|---------------|
| `run_once` | The first time only. |
| `on_message::<M>` | `Messages<M>` has at least one unread item this tick. |
| `resource_exists::<R>` | Resource `R` is present in the `World`. |
| `resource_equals(value)` | `R` is present and `== value`. |
| `resource_exists_and_equals(value)` | Same, but does not fail validation when absent. |
| `resource_exists_and(pred)` | `R` exists and `pred(&R)` holds. |
| `resource_added::<R>` | `R` was first inserted this tick. |
| `resource_changed::<R>` | `R` was mutated (marked changed) this tick. |
| `resource_exists_and_changed::<R>` | `R` exists and changed this tick. |
| `resource_changed_or_removed::<R>` | `R` changed or was removed this tick. |
| `resource_removed::<R>` | `R` was removed this tick. |
| `state_exists::<S>` | `State<S>` is registered. |
| `in_state(S::X)` | `State<S>` equals `X` right now. |
| `state_changed::<S>` | The current `S` changed this tick. |
| `any_with_component::<C>` | At least one entity has `C`. |
| `any_component_removed::<C>` | Some entity lost `C` this tick. |
| `any_match_filter::<F>` | At least one entity matches query filter `F`. |
| `not(condition)` | Inverts any condition. |
| `condition_changed(condition)` | The wrapped condition's result flipped since last tick. |
| `condition_changed_to(to, condition)` | The wrapped condition's result became `to`. |

## Combining conditions

The combinators live on the `SystemCondition` trait (in the prelude). `.and()` / `.or()` do not exist; stale LLM output uses them.

| Method | Semantics |
|---|---|
| `a.and_then(b)` | `a && b`, `b` only evaluated if `a` is true. |
| `a.and_eager(b)` | `a && b`, both always evaluated. |
| `a.or_else(b)` | `a \|\| b`, `b` only evaluated if `a` is false. |
| `a.or_eager(b)` | `a \|\| b`, both always evaluated. |
| `a.nand_then(b)`, `a.nand_eager(b)` | `!(a && b)`. |
| `a.nor_else(b)`, `a.nor_eager(b)` | `!(a \|\| b)`. |
| `a.xor(b)`, `a.xnor(b)` | Exclusive or and its inverse. |

```rust
// Playing AND a best score exists.
app.add_systems(
    Update,
    draw_hud.run_if(in_state(AppState::Playing).and_then(resource_exists::<BestScore>)),
);

// Absent resource.
app.add_systems(Update, draw_hud.run_if(not(resource_exists::<BestScore>)));
```

"Eager" variants matter when the second condition has side effects such as consuming change ticks (`resource_changed`) — eager evaluation keeps its tick bookkeeping consistent.

## Custom run conditions

A run condition is a read-only system that returns `bool`. Any `SystemParam` is valid:

```rust
fn is_high_score(score: Res<Score>, best: Res<BestScore>) -> bool {
    score.0 > best.0
}

app.add_systems(Update, draw_hud.run_if(is_high_score));
```

## Performance rule

**Do not put expensive work in a run condition.** Conditions run every tick whether or not the system runs.

```rust
// BAD: O(n) every tick, even when the system is skipped.
fn has_any_active_enemy(query: Query<&EnemyTag>) -> bool {
    query.iter().any(|e| e.is_active)
}

// GOOD: cheap gate, expensive filter inside.
app.add_systems(Update, combat_tick.run_if(any_with_component::<EnemyTag>));

fn combat_tick(enemies: Query<&EnemyTag>) {
    for _enemy in enemies.iter().filter(|e| e.is_active) {}
}
```

## Run conditions are systems

- They can read resources, queries and messages.
- They must be read-only (`ReadOnlySystem`); `ResMut` in a condition fails to compile.
- A condition whose params fail validation (missing resource, `Single` with zero or many matches) evaluates to `false` and the system is skipped. A hard failure (`RunSystemError::Failed`) also goes to the `FallbackErrorHandler`, then counts as `false`. Since 0.20 a panic inside a condition is caught and routed the same way.

## State-based gating: run condition vs schedule

`in_state(S)` keeps the system in `Update` and skips it unless the state matches. `OnEnter(S)` / `OnExit(S)` are separate schedules that run once at the transition. Prefer the schedule for setup/teardown. See [state-schedules.md](state-schedules.md).

## See also

- [state-schedules.md](state-schedules.md) — `OnEnter`/`OnExit`/`OnTransition` for one-shot hooks.
- [system-sets.md](system-sets.md) — apply a condition to a whole set.
