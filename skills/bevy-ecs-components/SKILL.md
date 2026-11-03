---
name: bevy-ecs-components
description: Use when defining `#[derive(Component)]`, declaring required components with `#[require(...)]`, writing observers with `On<E>` or lifecycle observers with `On<Add<T>>` (NOT `On<Add, T>`), choosing Table versus SparseSet storage, or registering `on_add`/`on_insert`/`on_discard`/`on_remove` hooks in Bevy 0.20.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "1"
  area: ecs
  bevy_version: "0.20"
---

# Bevy 0.20 — ECS Components

## When to use this skill

- Defining a new `Component` for game state.
- Bundling components via `#[require(...)]` (the modern replacement for "bundles").
- Reacting to component lifecycle: `Add`, `Insert`, `Discard`, `Remove`, `Despawn`.
- Observers — reacting to entity-targeted events with `On<E>`.
- Choosing storage: Table (default, fast iteration) vs SparseSet (fast add/remove).
- Compiler errors mentioning `EventPattern` or `IntoObserverSystem` after an upgrade.

## Canonical pattern

```rust
use bevy::ecs::lifecycle::HookContext;
use bevy::ecs::world::DeferredWorld;
use bevy::prelude::*;

// 1. Plain components.
#[derive(Component, Default)]
struct Health(f32);

#[derive(Component)]
struct Velocity(Vec3);

// 2. Required components: spawning `Player` auto-inserts the rest.
//    Forms: `Type` (Default), `Type = expression`, `Type::ctor(...)`.
#[derive(Component)]
#[require(Health = Health(100.0), Velocity = Velocity(Vec3::ZERO), Transform)]
struct Player;

// 3. Sparse storage for tags added/removed every frame.
#[derive(Component)]
#[component(storage = "SparseSet")]
struct Stunned;

// 4. Lifecycle hook. `on_discard` is the 0.19+ name of `on_replace`.
#[derive(Component)]
#[component(on_discard = log_discard)]
struct Shield(u32);

fn log_discard(world: DeferredWorld, ctx: HookContext) {
    let value = world.get::<Shield>(ctx.entity).map(|s| s.0);
    info!("shield {value:?} on {:?} is being overwritten or removed", ctx.entity);
}

// 5. Entity-targeted event handled by observers.
#[derive(EntityEvent)]
struct Damage {
    entity: Entity, // `entity` field or `#[event_target]` names the target.
    amount: f32,
}

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_systems(Startup, spawn_player)
        .add_systems(Update, deal_damage)
        .add_observer(on_damage)
        .add_observer(on_player_added)
        .run();
}

fn spawn_player(mut commands: Commands) {
    commands.spawn((Player, Shield(3), Name::new("hero")));
}

fn deal_damage(mut commands: Commands, query: Query<Entity, With<Player>>) {
    for entity in &query {
        commands.trigger(Damage { entity, amount: 10.0 });
    }
}

// Observer param is `On<E>`.
fn on_damage(damage: On<Damage>, mut query: Query<&mut Health>) {
    let event = damage.event();
    if let Ok(mut hp) = query.get_mut(event.entity) {
        hp.0 -= event.amount;
    }
}

// Lifecycle observer. 0.20: the component lives inside the event type,
// `On<Add<Player>>`, not in a second generic `On<Add, Player>`.
fn on_player_added(add: On<Add<Player>>, names: Query<&Name>) {
    let entity = add.event().entity;
    info!("player {:?} spawned", names.get(entity).ok());
}
```

## Lifecycle event cheat sheet

| Pattern | Fires when |
|---|---|
| `On<Add<T>>` | `T` was added to an entity that did not have it. |
| `On<Insert<T>>` | `T` was inserted (new or overwrite). |
| `On<Discard<T>>` | `T` is about to be overwritten or removed (was `Replace` before 0.19). |
| `On<Remove<T>>` | `T` is about to be removed. |
| `On<Despawn<T>>` | An entity with `T` is about to be despawned. |

`Add<(A, B)>` is an OR filter: it fires when either component is added. `On<Add<()>>` plus `Observer::with_component(id)` watches dynamic components.

## Gotchas (0.18 → 0.20)

- **Observer `B: Bundle` generic moved into the event (0.20).** `On<Add, A>` → `On<Add<A>>`; `On<Add>` → `On<Add<()>>`. `IntoObserverSystem<E, B, M, Out>` became `IntoObserverSystem<E: EventPattern, M, Out>`. An "inscrutable" error naming `IntoObserverSystem` usually means one generic too many. The `event()` of a lifecycle observer is `AddEvent`/`InsertEvent`/... with a `pub entity` field.
- **`Replace` → `Discard` (0.19).** `on_replace` → `on_discard`, `#[component(on_replace = ..)]` → `#[component(on_discard = ..)]`, `On<Replace, T>` → `On<Discard<T>>`.
- **`Trigger<E>` → `On<E>` (0.17).** Methods: `event()`, `event_mut()`, `trigger()`, `observer()`, `original_event_target()`, `propagate(bool)`.
- **`#[derive(Component, Resource)]` on one type is an error (0.19).** `Resource` is now a subtrait of `Component`. Split the type into a component and a resource. A `Query<&T>` where `T: Resource` matches the resource's hidden entity.
- **Lifecycle triggers gained fields (0.19).** `EntityComponentsTrigger` now also reports old/new archetypes. Destructure with `EntityComponentsTrigger { components, .. }`.
- **`Name: From<&'static str>` only (0.20).** `Name::from(runtime_str)` fails to compile; use `Name::new(s.to_owned())`.
- **`ComponentId` constants are typed (0.20).** `bevy::ecs::component::{ADD, INSERT, DISCARD, REMOVE, DESPAWN, IS_RESOURCE}` are `ComponentId`, not `usize`; call `.index()` for the number. `ComponentInfo::id()` is removed; keep the `ComponentId` you looked it up with.
- **`#[component(summary_tick)]` (0.20)** adds a per-column change tick so `Changed<T>` can skip whole tables. Mutations cost more; use it for rarely-changed, often-queried data.
- **`EntityEvent::set_event_target`** requires `use bevy::ecs::event::SetEntityEventTarget;` — not in the prelude.
- **Storage choice is irrevocable**: it is compiled into the component. SparseSet adds/removes faster but iterates slower. Use Table (default) unless profiling says otherwise.
- **`#[require(T)]` runs `T::default()`**. If `T: !Default`, use `#[require(T = expression)]`.
- **Hooks** (`on_add`, `on_insert`, `on_discard`, `on_remove`, `on_despawn`) are `fn(DeferredWorld, HookContext)`. They run inside `World` mutations, cannot take `SystemParam`s, and cannot despawn their own entity. Prefer observers when you need flexibility.
- **`Ref<T>` is `Clone + Copy` (0.19).** No need to re-fetch.
- **`Bundle` derive still exists** but `#[require(...)]` on a marker component keeps the spawn surface smaller.

## See also

- `bevy-ecs-queries` — reading components back out; broad queries and `IsResource`.
- `bevy-ecs-systems` — observers are systems; `&mut World` as a `SystemParam`.
- `bevy-migration-0-18-to-0-19` — `Replace`→`Discard`, resources-as-components.
- `bevy-migration-0-19-to-0-20` — `On<Add<T>>`, `EventPattern`, typed `ComponentId`.
