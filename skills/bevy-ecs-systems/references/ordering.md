# Bevy 0.18 — System ordering deep dive

## The problem: `SimpleExecutor` is gone

In Bevy 0.17 and earlier the `SimpleExecutor` ran systems in insertion order
when no ordering was specified, masking many latent data-hazard bugs. In 0.18,
the `SimpleExecutor` was removed. Any two systems that share mutable access to
the same data and have no ordering relationship between them now produce a
`ScheduleBuildError::Ambiguity` — a **build-time panic**.

You must explicitly declare the relationship or accept that it is intentional.

## System-level ordering

```rust
// B always runs after A in the same schedule.
app.add_systems(Update, (a, b.after(a)));

// Equivalent reversed form:
app.add_systems(Update, (a.before(b), b));
```

Both `.before(other)` and `.after(other)` are valid. Pick whichever reads more
naturally at the call site.

## `.chain()` on system tuples

`.chain()` is syntactic sugar for `.before` on each consecutive pair:

```rust
// These three run in order: validate → consume → dispatch.
app.add_systems(Update, (validate, consume, dispatch).chain());
```

## Set-level ordering (preferred)

Order sets in `configure_sets`; individual systems in those sets inherit the
ordering automatically. This is more maintainable than chaining every system
individually.

```rust
app.configure_sets(Update, (MySet::Input, MySet::Logic, MySet::Output).chain());
```

See [system-sets.md](system-sets.md) for the full configure_sets reference.

## Accepting intentional ambiguity

When two systems genuinely do not conflict in practice but the analyzer cannot
prove it, use `.ambiguous_with(other)` to silence the error:

```rust
app.add_systems(
    Update,
    (audio_tick.ambiguous_with(render_tick), render_tick),
);
```

Use this sparingly — it hides real hazards. Prefer explicit ordering whenever
the order matters or the systems share data.

You can also use `.ambiguous_with_all()` to suppress all ambiguity warnings for
a given system (useful during prototyping; clean up before shipping).

## Debugging `ScheduleBuildError::Ambiguity`

The error message names both systems and the conflicting component/resource.
Steps:
1. Read the error — it tells you exactly which two systems and which data.
2. Decide if the order matters. If yes, add `.before`/`.after`.
3. If the order genuinely doesn't matter (e.g. two read-only stats collectors),
   add `.ambiguous_with(other)`.
4. If one system should be in a separate set, restructure with `configure_sets`.

Enable extra diagnostics with:
```rust
app.edit_schedule(Update, |schedule| {
    schedule.set_build_settings(
        bevy::ecs::schedule::ScheduleBuildSettings {
            ambiguity_detection: LogLevel::Warn, // or Error
            ..default()
        },
    );
});
```

## Cross-schedule ordering

`.before`/`.after` only work within the same schedule. To sequence work across
schedules (e.g. `FixedUpdate` → `Update`), use Bevy's message/event system or
shared resources as a handoff. Schedules have a fixed execution order defined by
the `MainScheduleOrder` resource — you cannot reorder schedules with `.before`.

## See also

- [system-sets.md](system-sets.md) — set-level ordering via `configure_sets`.
- [runtime-removal.md](runtime-removal.md) — removing sets at runtime, which also affects ordering graphs.
