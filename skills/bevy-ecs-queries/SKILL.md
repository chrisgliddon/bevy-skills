---
name: bevy-ecs-queries
description: Use when writing `Query<D, F>` with filters like `With`/`Without`/`Or`, detecting changes with `Changed<T>`/`Added<T>`, parallelising with `par_iter`/`par_iter_mut`, building a query lens with `transmute_lens`, or hitting the new 0.18 `ArchetypeQueryData` bound. Covers Bevy 0.18 query patterns.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "1"
  area: ecs
  bevy_version: "0.18"
---

# Bevy 0.18 — ECS Queries

## When to use this skill

- Reading or writing components from a system.
- Filtering by presence (`With`/`Without`), alternation (`Or`), or change detection (`Changed`/`Added`).
- Parallelising over a large entity set with `par_iter_mut`.
- Borrowing a subset of a query via a lens (`transmute_lens`).
- Compiler error mentioning `ArchetypeQueryData` (new bound in 0.18).

## Canonical pattern

```rust
use bevy::prelude::*;

#[derive(Component, Default)]
struct Health(f32);

#[derive(Component, Default)]
struct Velocity(Vec3);

#[derive(Component)]
struct Player;

#[derive(Component)]
struct Enemy;

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_systems(Update, (
            move_things,
            on_health_changed,
            damage_visible_enemies,
            integrate_in_parallel,
        ))
        .run();
}

// Sequential iteration. `&` for read, `&mut` for write.
fn move_things(time: Res<Time>, mut q: Query<(&Velocity, &mut Transform)>) {
    let dt = time.delta_secs();
    for (vel, mut tf) in &mut q {
        tf.translation += vel.0 * dt;
    }
}

// Change detection. `Changed<T>` triggers on insert OR mutation.
// `Added<T>` triggers only on insert.
fn on_health_changed(q: Query<(Entity, &Health), Changed<Health>>) {
    for (entity, hp) in &q {
        info!("entity {:?} now has {} hp", entity, hp.0);
    }
}

// Combined filters. `With`/`Without` constrain entities;
// `Or<(...)>` alternates over filters (not components).
fn damage_visible_enemies(
    mut q: Query<&mut Health, (With<Enemy>, Without<Player>, Or<(Added<Enemy>, Changed<Transform>)>)>,
) {
    for mut hp in &mut q {
        hp.0 -= 1.0;
    }
}

// Parallel iteration. Use when N is large (>10k) and per-entity work is non-trivial.
// Cannot use `Commands` or external mutable state — task pool runs items in parallel.
fn integrate_in_parallel(mut q: Query<(&Velocity, &mut Transform)>) {
    q.par_iter_mut().for_each(|(vel, mut tf)| {
        tf.translation += vel.0 * 0.016;
    });
}

// Query lens: temporarily view a query as a narrower one. Useful for
// passing a stricter query into a helper without re-binding the system's
// SystemParam list.
#[allow(dead_code)]
fn use_lens(mut q: Query<(&mut Transform, &Velocity)>) {
    // Read-only narrowed view of just the Transform column.
    let mut lens = q.transmute_lens::<&Transform>();
    let _read_only: Query<&Transform> = lens.query();
}
```

## Gotchas (0.18)

- **`ArchetypeQueryData`** is a new trait that bounds query data types where the exact item count must be known at compile time (e.g. `for_each`-style ergonomics). If you get a "trait `ArchetypeQueryData` not implemented" error, you're using a dynamic query (`FilteredEntityRef`/`FilteredEntityMut`) where a static one is required. Re-shape the query.
- **`EntityMut::get_components_mut::<(&mut A, &mut B)>()`** is the safe way to grab two `&mut`s out of one entity in 0.18 — returns `Result<_, QueryAccessError>`. Don't reach for `unsafe` `World::get_mut` aliasing tricks.
- **`Query::get`/`get_mut` returns `Result`, not `Option`**. The error type carries the entity, so don't swallow it with `.ok()` if you actually need to know why a lookup missed.
- **`Or<(With<A>, With<B>)>`** — `Or` alternates over **filters**, not raw component types. `Or<(A, B)>` does not compile.
- **`Changed`/`Added` are tick-based.** A system that runs every other frame can miss changes only seen in the skipped frame. If you must not miss a change, use observers or a buffered queue.
- **Don't pair `par_iter_mut` with `Commands`.** Spawn/despawn from a sequential system that consumes a `Resource` queue written by the parallel one.

## See also

- `bevy-ecs-components` — declaring the components queried here.
- `bevy-ecs-systems` — using queries inside `SystemParam` and run conditions.
- `bevy-migration-0-17-to-0-18` — `EntityMut::get_components_mut` and tick-type move.
