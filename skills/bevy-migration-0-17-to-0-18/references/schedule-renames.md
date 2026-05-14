# Schedule Renames — Bevy 0.17 → 0.18

Cross-links: [ecs-renames](ecs-renames.md) | [render-renames](render-renames.md) | [asset-renames](asset-renames.md) | [cargo-feature-renames](cargo-feature-renames.md)

## `SimpleExecutor` removed

`SimpleExecutor` was the schedule executor that silently ignored system-ordering ambiguities. It was removed in 0.18. Schedules now panic on undeclared ambiguities.

**Fix — use ordering annotations to resolve ambiguities:**

```rust
// Before (silent with SimpleExecutor)
app.edit_schedule(MySchedule, |s| {
    s.set_executor_kind(ExecutorKind::Simple); // no longer exists
});

// After — declare ordering or mark explicit ambiguity
app.add_systems(MySchedule, (system_a, system_b).chain());
// or:
app.add_systems(MySchedule, system_a.before(system_b));
// or, if the ambiguity is intentional:
app.add_systems(MySchedule, system_a.ambiguous_with(system_b));
```

`ExecutorKind::Simple` is also removed. The remaining executor kinds are `SingleThreaded` and `MultiThreaded`.

## `ScheduleBuildError` variant renames

| 0.17 | 0.18 |
|---|---|
| `ScheduleBuildError::HierarchyLoop` | `ScheduleBuildError::HierarchySort(DiGraphToposortError::Loop(..))` |
| `ScheduleBuildError::DependencyCycle` | `ScheduleBuildError::DependencySort(DiGraphToposortError::Cycle(..))` |

Match on the new nested variants:

```rust
// 0.18
match err {
    ScheduleBuildError::HierarchySort(DiGraphToposortError::Loop(node)) => { /* ... */ }
    ScheduleBuildError::DependencySort(DiGraphToposortError::Cycle(cycle)) => { /* ... */ }
    _ => {}
}
```

## `State::set` always triggers a transition

```rust
// 0.17 — setting to the same state was a no-op (OnExit + OnEnter did NOT fire)
next_state.set(GameState::Playing); // no-op if already Playing

// 0.18 — ALWAYS fires OnExit + OnEnter, even when value is unchanged
next_state.set(GameState::Playing); // fires transition!

// Fix — guard with set_if_neq:
next_state.set_if_neq(GameState::Playing);
```

This is a silent logic change: no compile error, but double-transition bugs appear at runtime.

## System combinator `or` validation behaviour

The `or` system combinator now coerces a *validation* failure in either branch to `false` instead of propagating the error upward. This is only observable in custom run-condition combinators that return `Result`; most application code is unaffected.

## glTF coordinate conversion replaced

```rust
// 0.17
GltfPlugin {
    use_model_forward_direction: true,
    ..default()
}

// 0.18
GltfPlugin {
    convert_coordinates: GltfConvertCoordinates {
        rotate_scene_entity: true,
        rotate_meshes: true,
    },
    ..default()
}
```

`GltfConvertCoordinates` gives per-axis control; the boolean shorthand is gone.
