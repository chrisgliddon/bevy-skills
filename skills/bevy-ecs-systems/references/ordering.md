# Bevy 0.20 — System ordering deep dive

## What happens with no ordering

Bevy 0.17 and earlier had a `SimpleExecutor` that ran systems in insertion order. It was removed in 0.18. The default `MultiThreadedExecutor` runs any two systems with no edge between them in an arbitrary order, in parallel when their data access allows.

Two unordered systems that write the same data are an **ambiguity**. By default Bevy ignores it (`ScheduleBuildSettings::ambiguity_detection` is `LogLevel::Ignore`). It does not panic. Declare the relationship, or opt into detection (below).

## System-level ordering

```rust
// draw_hud always runs after read_input in the same schedule.
app.add_systems(Update, (read_input, draw_hud.after(read_input)));

// Equivalent reversed form:
app.add_systems(Update, (read_input.before(draw_hud), draw_hud));
```

## `.chain()` on system tuples

```rust
// validate → consume → dispatch, in that order.
app.add_systems(Update, (validate, consume, dispatch).chain());
```

## Set-level ordering (preferred)

```rust
app.configure_sets(Update, (MySet::Input, MySet::Logic, MySet::Output).chain());
```

Systems inherit their set's edges. See [system-sets.md](system-sets.md).

## Weak ordering (0.20)

`.chain_weak()`, `.before_weak(set)` and `.after_weak(set)` keep an edge only between systems whose tracked ECS access conflicts. Non-conflicting systems in adjacent sets may run in any order or in parallel.

```rust
app.configure_sets(Update, (GameLoop::Input, GameLoop::Simulate).chain_weak());
app.add_systems(Update, draw_hud.after_weak(GameLoop::Input));
```

Rules the scheduler applies:
- A system that produces deferred effects (`Commands`) is always treated as conflicting with later systems; the `ApplyDeferred` sync point stays.
- Exclusive systems (`&mut World`) always conflict.
- Dependencies the scheduler cannot see (channels, atomics, interior mutability behind `Res<T>`, `NonSend` state) are **not** preserved. Use `.chain()` or an explicit `.after(system)` for those.

Bevy's own `PostUpdate` UI sets (`UiSystems`), the `Render` schedule's `RenderSystems` sets, `RenderGraph`, `Core2d`/`Core3d` pass sets and `ExtractSchedule` sets switched to weak ordering in 0.20. If a custom system you placed in one of those sets relied on a hidden dependency, add `.after(the_producer)`.

## Accepting intentional ambiguity

```rust
app.add_systems(Update, (draw_hud.ambiguous_with(read_input), read_input));
```

`.ambiguous_with_all()` silences every ambiguity for one system. Use it during prototyping only.

## Detecting ambiguity

```rust
use bevy::ecs::schedule::{LogLevel, ScheduleBuildSettings};

app.edit_schedule(Update, |schedule| {
    schedule.set_build_settings(ScheduleBuildSettings {
        ambiguity_detection: LogLevel::Warn, // or Error to panic at build time
        ..default()
    });
});
```

`LogLevel::Error` surfaces as `ScheduleBuildError::Ambiguity(AmbiguousSystemConflictsWarning)`. The message names both systems and the conflicting component or resource. Then:
1. Decide whether the order matters. If yes, add `.before`/`.after`.
2. If it does not (two read-only stats collectors), add `.ambiguous_with(other)`.
3. If one belongs in another set, restructure with `configure_sets`.

## Schedule randomization (0.20, `debug` feature)

With the `debug` feature on `bevy`, `ScheduleBuildSettings` has `shuffle_seed: Option<u64>`. Setting it shuffles systems while respecting explicit edges. Run your tests under several seeds to prove that every real dependency has an edge. Log the seed so a failure is reproducible. If you exhaustively list the fields of `ScheduleBuildSettings`, add `shuffle_seed: None`.

## Choosing an executor (0.19)

`ExecutorKind` is gone. Pass an executor instance:

```rust
use bevy::ecs::schedule::SingleThreadedExecutor;

app.edit_schedule(Update, |schedule| {
    schedule.set_executor(SingleThreadedExecutor::new());
});
```

`SystemExecutor` is a public trait, so you can implement your own. There is no `get_executor_kind` replacement.

## Cross-schedule ordering

`.before`/`.after` only work within one schedule. Schedules run in the order held by the `MainScheduleOrder` resource. To sequence work across schedules (`FixedUpdate` → `Update`), hand data over with a message or a resource.

## Other errors you may match on

`ScheduleBuildError` variants since 0.18: `HierarchySort(DiGraphToposortError::Loop(..))`, `DependencySort(DiGraphToposortError::Cycle(..))`, `CrossDependency`, `SetsHaveOrderButIntersect`, `SystemTypeSetAmbiguity`, `Uninitialized`, `Elevated(ScheduleBuildWarning)`. The older `HierarchyLoop` and `DependencyCycle` names are gone.

## See also

- [system-sets.md](system-sets.md) — set-level ordering via `configure_sets`.
- [runtime-removal.md](runtime-removal.md) — removing sets at runtime, which rewrites ordering edges.
