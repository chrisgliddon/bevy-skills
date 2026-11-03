---
name: bevy-ecs-queries
description: Use when writing `Query<D, F>` with `With`/`Without`/`Or`, detecting changes with `Changed<T>`/`Added<T>`, parallelising with `par_iter_mut`, looking up entity lists with `iter_many(..).matched()`, building a lens with `transmute_lens`, filtering resource entities with `Without<IsResource>`, or fixing generic-query errors naming `IterQueryData` or `SingleEntityQueryData` in Bevy 0.20.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "1"
  area: ecs
  bevy_version: "0.20"
---

# Bevy 0.20 — ECS Queries

## When to use this skill

- Reading or writing components from a system.
- Filtering by presence (`With`/`Without`), alternation (`Or`), or change detection (`Changed`/`Added`).
- Parallelising over a large entity set with `par_iter_mut`.
- Iterating a list of entities with `iter_many` / `iter_many_mut` (yield `Result` since 0.20).
- Borrowing a subset of a query via a lens (`transmute_lens`).
- Compiler error mentioning `IterQueryData`, `SingleEntityQueryData` or `ArchetypeQueryData`.
- A broad query (`Query<Entity>`, `Query<EntityRef>`) conflicting with `ResMut` since 0.19.

## Canonical pattern

```rust
use bevy::ecs::resource::IsResource;
use bevy::prelude::*;

#[derive(Component, Default)]
struct Health(f32);

#[derive(Component, Default)]
struct Velocity(Vec3);

#[derive(Component)]
struct Player;

#[derive(Component)]
struct Enemy;

#[derive(Resource, Default)]
struct Targets(Vec<Entity>);

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .init_resource::<Targets>()
        .add_systems(
            Update,
            (
                move_things,
                on_health_changed,
                damage_visible_enemies,
                integrate_in_parallel,
                heal_targets,
                count_world_entities,
            ),
        )
        .run();
}

// Sequential iteration. `&` for read, `&mut` for write.
fn move_things(time: Res<Time>, mut q: Query<(&Velocity, &mut Transform)>) {
    let dt = time.delta_secs();
    for (vel, mut tf) in &mut q {
        tf.translation += vel.0 * dt;
    }
}

// Change detection. `Changed<T>` fires on insert OR mutation; `Added<T>` only on insert.
fn on_health_changed(q: Query<(Entity, &Health), Changed<Health>>) {
    for (entity, hp) in &q {
        info!("entity {:?} now has {} hp", entity, hp.0);
    }
}

// Combined filters. `Or<(...)>` alternates over filters, not components.
fn damage_visible_enemies(
    mut q: Query<&mut Health, (With<Enemy>, Without<Player>, Or<(Added<Enemy>, Changed<Transform>)>)>,
) {
    for mut hp in &mut q {
        hp.0 -= 1.0;
    }
}

// Parallel iteration. No `Commands` inside the closure.
fn integrate_in_parallel(mut q: Query<(&Velocity, &mut Transform)>) {
    q.par_iter_mut().for_each(|(vel, mut tf)| {
        tf.translation += vel.0 * 0.016;
    });
}

// Many-entity lookup. 0.20: `iter_many*` yield `Result`; `.matched()` skips misses.
fn heal_targets(targets: Res<Targets>, mut q: Query<&mut Health>) {
    let mut iter = q.iter_many_mut(targets.0.iter()).matched();
    while let Some(mut hp) = iter.fetch_next() {
        hp.0 += 1.0;
    }
}

// Broad queries (`Entity`, `EntityRef`, `Option<&T>`) also match resource
// entities since 0.19. `Without<IsResource>` avoids conflicts with `ResMut`.
fn count_world_entities(q: Query<EntityRef, Without<IsResource>>, mut targets: ResMut<Targets>) {
    targets.0.clear();
    let _ = q.iter().count();
}

// Query lens: narrow a query for a helper without a new system param.
fn use_lens(mut q: Query<(&mut Transform, &Velocity)>) {
    let mut lens = q.transmute_lens::<&Transform>();
    let _read_only: Query<&Transform> = lens.query();
}
```

## Generic query bounds (0.19+)

```rust
use bevy::ecs::query::{IterQueryData, QueryData};

// Iterating generic query data needs `IterQueryData`.
fn generic_iter<D: IterQueryData>(mut query: Query<D>) {
    for _item in &mut query {}
}

// Any `QueryData` can still be walked with the lending `fetch_next`.
fn generic_fetch<D: QueryData>(mut query: Query<D>) {
    let mut iter = query.iter_mut();
    while let Some(_item) = iter.fetch_next() {}
}
```

| Bound | Required by |
|---|---|
| `IterQueryData` | `into_iter`, `iter_mut` as `Iterator`, `par_iter_mut`, `single_mut`, `get_many_mut`, `iter_combinations_mut`, `Single<D>`. |
| `SingleEntityQueryData` | `transmute`/`transmute_lens`, `join`, `QueryIter::sort*`, `EntityRef::get_components`, `Traversal`. |
| `ArchetypeQueryData` | Query data whose per-archetype item count is known statically. Dynamic data (`FilteredEntityRef`/`Mut`) does not satisfy it. |

All built-in query types satisfy all three. Only manual `QueryData` impls and generic helpers need to name them.

## Gotchas (0.18 → 0.20)

- **`iter_many`, `iter_many_mut`, `iter_many_unique*` and `par_iter_many*` yield `Result<Item, QueryEntityError>` (0.20).** Stale code `for hp in q.iter_many(list)` fails to compile. Add `.matched()` to keep the old skip-misses behaviour, or handle the `Err` (entity despawned or not matching the filter). `QueryManyIter::sort*` has no `.matched()`: use `.flat_map(Result::ok)`. In `par_iter_many(..).for_each(|item| ..)` do `let Ok(item) = item else { return };`.
- **Resources are entities (0.19).** `Query<Entity>`, `Query<EntityRef>`, `Query<EntityMut>`, `Query<Option<&T>>` and `Query<()>` match the hidden resource entities. They conflict with `ResMut<R>` / `NonSendMut`; add `Without<IsResource>` or `Without<R>`. Counting "all entities" with a broad query overcounts by the number of resources.
- **`FilteredResources*` are deprecated (0.20).** Build the system with `QueryParamBuilder::new(|b| { b.data::<Ref<ResA>>().with::<IsResource>(); })` and take `Query<FilteredEntityRef>` (or `Single<FilteredEntityRef>`). Use `ResourceEntities` to find a resource's entity when the query holds several.
- **`DeferredWorld::query` is deprecated (0.20).** Call `query_state.query_mut(&mut deferred_world)`; `QueryState::query_mut` takes `impl Into<DeferredWorld>`.
- **Manual `WorldQuery` impls must write `init_nested_access` and `update_archetypes` (0.20).** The default bodies were removed; empty bodies keep old behaviour for single-entity queries.
- **`EntityMut::get_components_mut::<(&mut A, &mut B)>()`** takes two `&mut` out of one entity safely; it needs `SingleEntityQueryData`.
- **`Query::get`/`get_mut` returns `Result<_, QueryEntityError>`**, not `Option`. Keep the error if you need to know why the lookup missed.
- **`Or<(With<A>, With<B>)>`** — `Or` takes filters. `Or<(A, B)>` does not compile.
- **`Changed`/`Added` are tick-based.** A system that runs every other frame misses changes from the skipped frame. Use observers or a message if you cannot miss one. `#[component(summary_tick)]` (0.20) makes `Changed<T>` cheap on rarely-mutated columns.
- **`Ref<T>` is `Clone + Copy` (0.19).**
- **Don't pair `par_iter_mut` with `Commands`.** Spawn/despawn from a sequential system that drains a queue written by the parallel one.

## See also

- `bevy-ecs-components` — declaring the components queried here; lifecycle observers.
- `bevy-ecs-systems` — query is one of many `SystemParam`s; run conditions.
- `bevy-migration-0-18-to-0-19` — `IterQueryData` bounds, broad queries versus resources.
- `bevy-migration-0-19-to-0-20` — `Result` from many-iterators, `FilteredResources` deprecation.
