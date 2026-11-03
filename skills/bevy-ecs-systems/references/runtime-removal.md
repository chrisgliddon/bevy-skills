# Bevy 0.20 — Runtime system removal

## The API: `remove_systems_in_set`

Added in 0.18. Removes every system in a named `SystemSet` from one schedule, live at runtime. Useful for:
- Tearing down debug overlays without restarting the app.
- Hot-unloading mod systems.
- Removing a tutorial HUD after first completion.

### Signature — two receivers, different arg counts

| Receiver | Args (excluding `&mut self`) | Use when |
|----------|------------------------------|----------|
| `Schedules` (the resource) | `schedule_label, set, world, policy` — **4 args** | You hold the `Schedules` resource and name a schedule by label (the common case from `resource_scope`). |
| `Schedule` (one schedule) | `set, world, policy` — **3 args** | You already hold a `&mut Schedule`. |

Both return `Result<usize, ScheduleError>`: the number of systems removed, or `ScheduleError::{SetNotFound, ScheduleNotFound, Uninitialized, ScheduleBuildError(..)}`. Stale LLM output ignores the `Result` and gets an `unused_must_use` warning, or calls the 0.17 two-argument form.

```rust
use bevy::ecs::schedule::ScheduleCleanupPolicy;

fn unload_debug_overlay(world: &mut World) {
    world.resource_scope(|world, mut schedules: Mut<Schedules>| {
        let removed = schedules
            .remove_systems_in_set(Update, DebugOverlaySet::All, world, ScheduleCleanupPolicy::default())
            .expect("set exists in Update");
        info!("removed {removed} systems");
    });
}
```

`resource_scope` is needed because the call wants both `&mut World` and `&mut Schedules`.

## `ScheduleCleanupPolicy` variants

| Variant | What happens |
|---------|--------------|
| `RemoveSetAndSystems` (default) | Removes the set and its systems. Adds edges between the set's former before/after dependencies so transitive ordering survives. Sub-sets are not removed. |
| `RemoveSystemsOnly` | Removes the systems, keeps the set label registered. Re-links transitive dependencies. |
| `RemoveSetAndSystemsAllowBreakages` | Like `RemoveSetAndSystems` but adds no edges; transitive ordering through the set is lost. |
| `RemoveSystemsOnlyAllowBreakages` | Like `RemoveSystemsOnly` but adds no edges. |

## Nested schedules — it does NOT propagate

Only the named schedule is affected. If `DebugOverlaySet` exists in both `Update` and `FixedUpdate`, call it twice:

```rust
world.resource_scope(|world, mut schedules: Mut<Schedules>| {
    let _ = schedules.remove_systems_in_set(Update, DebugOverlaySet::All, world, policy);
    let _ = schedules.remove_systems_in_set(FixedUpdate, DebugOverlaySet::All, world, policy);
});
```

## What is NOT cleaned up

Removing systems does not:
- Despawn entities the systems spawned.
- Remove resources the systems inserted.
- Unregister observers the systems registered.
- Undo component changes the systems made.

Clean those up separately: a teardown system ordered before the removal, or an `OnExit` schedule / `DespawnOnExit` component for the relevant state.

## Pattern: pair removal with a teardown system

```rust
// 1. Request removal via a message.
fn request_overlay_removal(mut writer: MessageWriter<RemoveOverlay>) {
    writer.write(RemoveOverlay);
}

// 2. Teardown runs first (same tick, ordered before unload).
fn teardown_overlay(mut commands: Commands, query: Query<Entity, With<DebugWidget>>) {
    for entity in &query {
        commands.entity(entity).despawn();
    }
}

// 3. Exclusive system removes the set (`unload_debug_overlay` above).
fn wire_removal(app: &mut App) {
    app.add_message::<RemoveOverlay>();
    app.add_systems(
        Update,
        (teardown_overlay, unload_debug_overlay)
            .chain()
            .run_if(on_message::<RemoveOverlay>),
    );
}
```

## See also

- [system-sets.md](system-sets.md) — defining the sets you later remove.
- [state-schedules.md](state-schedules.md) — `OnExit` / `DespawnOnExit` as an alternative teardown hook.
- [ordering.md](ordering.md) — ordering the teardown system before the removal system.
