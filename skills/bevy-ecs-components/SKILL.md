---
name: bevy-ecs-components
description: Use when defining `#[derive(Component)]`, declaring required components with `#[require(...)]`, writing observers with `On<E>` (NOT `Trigger<E>` — renamed in 0.17), choosing between Table and SparseSet storage, or registering `on_add`/`on_remove` hooks in Bevy 0.18.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "1"
  area: ecs
  bevy_version: "0.18"
---

# Bevy 0.18 — ECS Components

## When to use this skill

- Defining a new `Component` for game state.
- Bundling components via `#[require(...)]` (the modern replacement for "bundles").
- Reacting to component lifecycle: spawning, despawning, inserting, removing.
- Observers — reacting to entity-targeted events with `On<E>`.
- Choosing storage: Table (default, fast iteration) vs SparseSet (fast add/remove).

## Canonical pattern

```rust
use bevy::prelude::*;

// 1. Plain components.
#[derive(Component, Default)]
struct Health(f32);

#[derive(Component)]
struct Velocity(Vec3);

// 2. Required components — spawning `Player` auto-spawns the rest.
//    `#[require]` calls each form: `Type` (Default), `Type::ctor(...)`, or
//    `Type = expression`.
#[derive(Component)]
#[require(Health = Health(100.0), Velocity = Velocity(Vec3::ZERO), Transform)]
struct Player;

// 3. Sparse storage for components added/removed every frame (e.g. tags
//    flipped by gameplay). Default Table storage is faster to iterate.
#[derive(Component)]
#[component(storage = "SparseSet")]
struct Stunned;

// 4. An entity-targeted event reacted to by observers.
#[derive(EntityEvent)]
struct Damage {
    entity: Entity, // EntityEvent requires an `entity` field.
    amount: f32,
}

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_systems(Startup, spawn_player)
        .add_systems(Update, deal_damage)
        .add_observer(on_damage)
        .run();
}

fn spawn_player(mut commands: Commands) {
    commands.spawn(Player);
}

fn deal_damage(mut commands: Commands, query: Query<Entity, With<Player>>) {
    for entity in &query {
        commands.trigger(Damage { entity, amount: 10.0 });
    }
}

// Observer parameter is `On<E>`, not `Trigger<E>` (renamed in 0.17, PR #19596).
fn on_damage(damage: On<Damage>, mut query: Query<&mut Health>) {
    let event = damage.event();
    if let Ok(mut hp) = query.get_mut(event.entity) {
        hp.0 -= event.amount;
    }
}
```

## Gotchas (0.18)

- **`Trigger<E>` is gone.** Observer params are `On<E>` in 0.17+. Methods: `event()`, `event_mut()`, `observer()`, `original_event_target()`, `propagate(bool)`.
- **`EntityEvent::set_target`** requires `use bevy::ecs::entity::SetEntityEventTarget;` — not in the prelude.
- **Storage choice is irrevocable**: it's compiled into the component. SparseSet adds/removes faster but iterates 2–5× slower. Use Table (default) unless profiling proves SparseSet wins.
- **`#[require(T)]` runs `T::default()`**. If `T: !Default`, use `#[require(T = expression)]` or `#[require(T = T::new(...))]`.
- **Required components are non-recursive at the spec layer** but the spawning machinery does insert transitive requires. If you change a required-component graph, run a full scene reload to catch missing inserts.
- **Hooks** (`on_add`, `on_insert`, `on_replace`, `on_remove`) are sharp tools — they run inside `World` mutations, can't take arbitrary `SystemParam`s, and can't despawn the entity they fire on. Use observers when you need flexibility.
- **`Bundle` derive still exists** but most use-cases are better served by `#[require(...)]` on a "marker" component, which keeps the spawn surface ergonomic.

## See also

- `bevy-ecs-queries` — reading components back out.
- `bevy-ecs-systems` — observers are themselves systems.
- `bevy-migration-0-17-to-0-18` — full `Trigger`→`On` and event→message rename map.
