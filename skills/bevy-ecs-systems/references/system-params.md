# Bevy 0.20 — SystemParam deep dive

## Derive basics

```rust
use bevy::ecs::system::SystemParam;
use bevy::prelude::*;

#[derive(SystemParam)]
struct PlayerCtx<'w, 's> {
    transform: Query<'w, 's, &'static Transform, With<PlayerTag>>,
    speed:     Res<'w, PlayerSpeed>,
    goals:     MessageReader<'w, 's, GoalScored>,
}
```

`'w` = world borrow (resources, queries, component data).
`'s` = system-local state borrow (per-system state such as `Local`, the `MessageReader` cursor).

Rules:
- Every field must itself implement `SystemParam`.
- Lifetime names must be exactly `'w` and `'s` (the macro is hard-coded).
- You may omit `'s` entirely if no field needs it.

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
| `&'w mut World` | yes | no |

## `Local<T>` — per-system state

`Local<'s, T>` lives inside the system, not in the `World`. It persists across frames and is invisible to other systems.

```rust
fn count_frames(mut frame: Local<u32>) {
    *frame += 1;
    if *frame % 60 == 0 {
        info!("still alive after {} frames", *frame);
    }
}
```

`T` must implement `Default`. Use `Local<Option<T>>` when it does not.

## `&mut World` — exclusive access (unified in 0.20)

`&mut World` implements `SystemParam`. It may sit anywhere in the parameter list, as long as no other param borrows the World. `Local<T>`, `&mut SystemState<P>` and `&mut QueryState<D, F>` are allowed beside it.

```rust
fn immediate(world: &mut World) {
    world.spawn(MyComponent);
    // Entity is visible to the next line:
    let count = world.query::<&MyComponent>().iter(world).count();
    info!("{count}");
}

// 0.20: order no longer matters.
fn immediate_with_local(mut calls: Local<u32>, world: &mut World) {
    *calls += 1;
    world.spawn(MyComponent);
}
```

Removed in 0.20: `ExclusiveSystemParam`, `ExclusiveFunctionSystem`, `ExclusiveSystemParamFunction`, `ExclusiveMarker`, `System::is_exclusive()`. `WorldId` is not a valid param next to `&mut World`; call `world.id()` or take `Local<WorldId>`.

## `Commands` — deferred application

`Commands` queues structural changes (spawn, despawn, insert, remove). They apply at the next sync point, not immediately. Within the same system you cannot read back an entity you just spawned via `Commands`. Take `&mut World` for immediate changes.

Since 0.19 the `Command` trait has an associated `type Out`. A closure `|world: &mut World| -> Result { .. }` still works; `fn cmd() -> impl Command<Result>` becomes `impl Command`.

## Validation happens on fetch (0.19)

`SystemParam::validate_param` is gone. `get_param` returns `Result<Item, SystemParamValidationError>`. Consequences:
- `SystemState::get`, `get_mut`, `fetch` and `get_unchecked` return `Result`; add `.unwrap()` or `?`.
- Custom `SystemParam` impls move their checks into `get_param` and return `Err(SystemParamValidationError::invalid::<Self>("reason"))`.
- The multithreaded executor spawns a task for a system before it learns the params are invalid. If a `Single<D>` system is skipped most frames, add a cheap `run_if` to avoid the task.

## Generic resource bounds (0.19)

Resources can be immutable, so `ResMut<R>` requires `R: Resource<Mutability = Mutable>`:

```rust
use bevy::ecs::component::Mutable;

fn touch_generic<R: Resource<Mutability = Mutable>>(mut res: ResMut<R>) {
    res.set_changed();
}
```

## When to compose vs when to take separate args

**Use a composite `SystemParam` when:**
- You always need three or more of the same params together.
- The struct is a coherent "view" of the world (`UiCtx`, `AudioCtx`).
- You want to pass this view to helper functions.

**Take separate args when:**
- Mixing unrelated params.
- Fewer than three params.

```rust
fn my_system(mut ctx: PlayerCtx) {
    apply_velocity(&mut ctx);
}

fn apply_velocity(ctx: &mut PlayerCtx) {
    let _ = (ctx.transform.iter().count(), ctx.speed.0, ctx.goals.len());
}
```

## See also

- [system-sets.md](system-sets.md) — grouping systems into ordered sets.
- [run-conditions.md](run-conditions.md) — gating systems; conditions are also systems.
