# Bevy 0.18 — Runtime system removal

## The API: `remove_systems_in_set`

New in 0.18. Removes all systems belonging to a named `SystemSet` from a
specific schedule, live at runtime. Useful for:
- Tearing down debug overlays without restarting the app.
- Hot-unloading mod systems.
- Removing a tutorial HUD after first completion.

### Signature (3-arg form in 0.18)

```rust
schedules.remove_systems_in_set(
    schedule_label,   // e.g. Update
    set,              // impl SystemSet
    world,            // &mut World (for cleanup callbacks)
    policy,           // ScheduleCleanupPolicy
);
```

The 0.17 version had a 2-arg form without `world` and `policy`. If you see a
"expected 3 arguments" or "wrong number of arguments" compiler error after
upgrading, this is why.

## `ScheduleCleanupPolicy` variants

| Variant | What happens |
|---------|--------------|
| `RemoveSetAndSystems` (default) | Removes the set label and all systems in it from the schedule. The systems are dropped. |
| `RemoveSystemsOnly` | Removes the systems but leaves the set label registered (it can be re-populated later). |
| `RemoveSetAndSystemsAllowBreakages` | Like `RemoveSetAndSystems` but suppresses errors if the removal would break ordering constraints. Use only when you know what you're doing. |

## Working example inside an exclusive system

`remove_systems_in_set` requires `&mut World`, so it must be called from inside
`world.resource_scope` (to avoid simultaneous `&mut World` + `Mut<Schedules>`
aliasing) or from an exclusive system:

```rust
use bevy::ecs::schedule::ScheduleCleanupPolicy;

fn unload_debug_overlay(world: &mut World) {
    world.resource_scope(|world, mut schedules: Mut<Schedules>| {
        schedules.remove_systems_in_set(
            Update,
            DebugOverlaySet::All,
            world,
            ScheduleCleanupPolicy::default(), // RemoveSetAndSystems
        );
    });
}
```

Trigger the exclusive system via a message or a one-shot system to avoid
scheduling it every tick.

## Nested schedules — it does NOT propagate

`remove_systems_in_set` only affects the named schedule. If `DebugOverlaySet`
exists in both `Update` and `FixedUpdate`, you must call it once per schedule:

```rust
world.resource_scope(|world, mut schedules: Mut<Schedules>| {
    schedules.remove_systems_in_set(Update, DebugOverlaySet::All, world, policy);
    schedules.remove_systems_in_set(FixedUpdate, DebugOverlaySet::All, world, policy);
});
```

## What is NOT cleaned up

Removing systems does not:
- Despawn entities the systems spawned.
- Remove resources the systems inserted.
- Unregister observers the systems registered.
- Undo any component changes the systems made.

If your removed systems owned side effects (e.g. a debug overlay UI), clean
those up separately — either in a teardown system that runs before removal, or
in an `OnExit` schedule for the relevant state.

## Pattern: pair removal with a teardown system

```rust
// 1. Mark the overlay for removal via a message.
fn request_overlay_removal(mut writer: MessageWriter<RemoveOverlay>) {
    writer.write(RemoveOverlay);
}

// 2. Teardown runs first (same tick, ordered before unload).
fn teardown_overlay(mut commands: Commands, query: Query<Entity, With<DebugWidget>>) {
    for entity in &query {
        commands.entity(entity).despawn();
    }
}

// 3. Exclusive system removes the set.
fn unload_overlay_systems(world: &mut World) {
    world.resource_scope(|world, mut schedules: Mut<Schedules>| {
        schedules.remove_systems_in_set(
            Update,
            DebugOverlaySet::All,
            world,
            ScheduleCleanupPolicy::default(),
        );
    });
}

app.add_systems(
    Update,
    (teardown_overlay, unload_overlay_systems)
        .chain()
        .run_if(on_message::<RemoveOverlay>()),
);
```

## See also

- [system-sets.md](system-sets.md) — defining the sets you'll later remove.
- [state-schedules.md](state-schedules.md) — `OnExit` as an alternative teardown hook.
- [ordering.md](ordering.md) — ordering the teardown system before the removal system.
