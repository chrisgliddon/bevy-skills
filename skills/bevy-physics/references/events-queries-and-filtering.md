# Collision events, scene queries, and filtering

Target: **Bevy 0.20 / bevy_rapier 0.37.0**. Source-reviewed; Rust compile/runtime
checks remain pending in the [readiness record](../../bevy/references/bevy-020-readiness.md).

## Collision and force messages

Rapier only emits requested messages. Enable them on at least one participating
collider:

```rust
commands.spawn((
    RigidBody::Dynamic,
    Collider::ball(0.5),
    ActiveEvents::COLLISION_EVENTS | ActiveEvents::CONTACT_FORCE_EVENTS,
    ContactForceEventThreshold(25.0),
));

fn read_physics_messages(
    mut collisions: MessageReader<CollisionEvent>,
    mut forces: MessageReader<ContactForceEvent>,
) {
    for event in collisions.read() {
        match event {
            CollisionEvent::Started(a, b, flags) => {
                let _ = (a, b, flags);
            }
            CollisionEvent::Stopped(a, b, flags) => {
                let _ = (a, b, flags);
            }
        }
    }
    for event in forces.read() {
        let _magnitude = event.total_force_magnitude;
    }
}
```

Collision messages describe start/stop transitions, not every contact point on every
step. Contact-force messages require their active flag and threshold. `Sensor`
colliders generate intersection transitions without contact forces.

Add `CollidingEntities` when a collider needs a maintained set of current partners;
it updates only when collision events are active on one of the colliders. For contact
normals/manifolds or one-off relationships, query the Rapier context instead of
rebuilding a global cache in gameplay code.

## Collision groups default to symmetric filtering

Each collider has membership bits and filter bits. With the default
`InteractionTestMode::And`, both sides must accept the other's membership:

```rust
const PLAYER: Group = Group::GROUP_1;
const WORLD: Group = Group::GROUP_2;

let player_groups = CollisionGroups::new(PLAYER, WORLD);
let world_groups = CollisionGroups::new(WORLD, PLAYER);
```

In 0.37, `CollisionGroups` and `SolverGroups` also have `test_mode`.
`::new(...)` preserves the default `And` behavior; only when **both** groups use
`InteractionTestMode::Or` does either side's acceptance suffice. Prefer constructors
over old exhaustive struct literals that omit the new field.

`CollisionGroups` controls pairwise collision/intersection eligibility. `SolverGroups`
separately controls which detected contacts produce solver constraints. Prefer groups
for stable layer rules; use physics hooks only when the rule depends on dynamic ECS
state that bitmasks cannot express.

## Current scene-query pattern

`RapierContext` is no longer a resource. Obtain it from `ReadRapierContext` and handle
the possibility of zero or multiple contexts:

```rust
fn ground_probe(contexts: ReadRapierContext, player: Single<Entity, With<Player>>) -> Result<()> {
    let context = contexts.single()?;
    let filter = QueryFilter::new()
        .exclude_sensors()
        .exclude_rigid_body(*player);

    if let Some((entity, time_of_impact)) = context.cast_ray(
        Vec3::new(0.0, 1.0, 0.0),
        -Vec3::Y,
        2.0,
        true,
        filter,
    ) {
        let _hit = (entity, time_of_impact);
    }
    Ok(())
}
```

Available operations include closest/all ray hits, shape casts, point projection,
point/shape intersection, and conservative AABB intersection. Always define:

- whether the cast starts inside a solid shape;
- maximum distance/time of impact;
- self/body exclusion;
- sensor inclusion;
- collision groups and any predicate;
- which physics phase the query observes.

The query pipeline is updated during `PhysicsSet::StepSimulation`. Query before
`SyncBackend` to observe the previous completed physics state: synchronization can
already apply live collider/body edits before simulation. Query after `StepSimulation`
for the current physics step, and after `Writeback` when also reading ECS poses.
Physics picking is an optional Rapier Cargo feature and does not replace explicit
gameplay query filters.

In 0.37, `QueryFilter::predicate` takes `Fn(Entity, &RapierCollider) -> bool`, and
`intersect_*` callbacks also receive the collider. Update one-argument closures;
keep borrowed predicates alive for the query. The default
`BevyPhysicsHooks::filter_contact_pair`/`filter_intersection_pair` implementations
now keep pairs instead of rejecting them. Test custom hooks that relied on the old
default, even if they still compile.

## Sources

- [Rapier scene queries](https://rapier.rs/docs/user_guides/bevy_plugin/scene_queries/)
- [`ReadRapierContext`](https://docs.rs/bevy_rapier3d/0.37.0/bevy_rapier3d/plugin/context/systemparams/struct.ReadRapierContext.html)
- [`CollisionGroups`](https://docs.rs/bevy_rapier3d/0.37.0/bevy_rapier3d/geometry/struct.CollisionGroups.html)
- [`CollisionEvent`](https://docs.rs/bevy_rapier3d/0.37.0/bevy_rapier3d/pipeline/enum.CollisionEvent.html)
