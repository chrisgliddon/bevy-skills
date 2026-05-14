# Bevy 0.18 — SystemParam deep dive

## Derive basics

```rust
use bevy::ecs::system::SystemParam;
use bevy::prelude::*;

#[derive(SystemParam)]
struct PlayerCtx<'w, 's> {
    transform: Query<'w, 's, &'static Transform, With<Player>>,
    speed:     Res<'w, PlayerSpeed>,
    goals:     MessageReader<'w, 's, GoalScored>,
}
```

`'w` = world borrow (resources, queries, component data).  
`'s` = system-local state borrow (internal per-system state, e.g. `Local`, `MessageReader` cursor).

Rules:
- Every field must itself implement `SystemParam`.
- Lifetime names must be exactly `'w` and `'s` (the macro is hard-coded).
- You may omit `'s` entirely if no fields need it — the macro still compiles.

## Common param types and their lifetimes

| Type | `'w` | `'s` |
|------|------|------|
| `Res<'w, R>` | yes | no |
| `ResMut<'w, R>` | yes | no |
| `Query<'w, 's, D, F>` | yes | yes |
| `Commands` | yes | yes |
| `MessageReader<'w, 's, M>` | yes | yes |
| `MessageWriter<'w, M>` | yes | no |
| `Local<'s, T>` | no | yes |

## `Local<T>` — per-system state

`Local<'s, T>` is a value stored inside the system itself, not in the `World`.
It persists across frames but is invisible to other systems.

```rust
fn count_frames(mut frame: Local<u32>) {
    *frame += 1;
    if *frame % 60 == 0 {
        info!("still alive after {} frames", *frame);
    }
}
```

`T` must implement `Default` (used for first-run initialization). You can also
write `Local<'s, Option<T>>` when `T` does not.

## `Commands` — deferred application

`Commands` queues structural changes (spawn, despawn, insert, remove). Changes
are applied at the next command-flush point, **not immediately**. Within the same
system tick you cannot read back an entity you just spawned via `Commands`.

For immediate structural changes, take `&mut World` (exclusive system):

```rust
fn immediate(world: &mut World) {
    world.spawn(MyComponent);
    // Entity is visible to the *next* line:
    let count = world.query::<&MyComponent>().iter(world).count();
    info!("{count}");
}
```

## When to compose vs when to take separate args

**Use a composite `SystemParam` when:**
- You always need ≥3 of the same params together.
- The struct represents a coherent "view" of the world (e.g. `UiCtx`, `AudioCtx`).
- You want to pass this view to helper functions.

**Take separate args when:**
- Mixing unrelated params (just clutters the struct definition).
- Fewer than 3 params — the derive overhead isn't worth it.

Helper call example:

```rust
fn my_system(mut ctx: PlayerCtx) {
    apply_velocity(&mut ctx);
}

fn apply_velocity(ctx: &mut PlayerCtx) {
    // ctx.transform, ctx.speed, ctx.goals are all accessible here
}
```

## See also

- [system-sets.md](system-sets.md) — grouping systems into ordered sets.
- [run-conditions.md](run-conditions.md) — gating systems; conditions are also SystemParams.
