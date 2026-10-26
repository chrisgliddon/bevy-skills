---
name: bevy-physics
description: Use when adding `RapierPhysicsPlugin`, spawning `RigidBody`/`Collider`, reading `CollisionEvent`, querying with `ReadRapierContext`, configuring `KinematicCharacterController`, or ordering gameplay around `PhysicsSet` in Bevy 0.20 with bevy_rapier 0.37; includes the preserved Bevy 0.19 compatibility path.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "2"
  area: physics
  bevy_version: "0.20"
  target_version: "Bevy 0.20"
---

# Bevy 0.20 — physics with Rapier 0.37

**Staged update:** APIs and features below were reviewed against the published
0.37.0 source; local Rust compilation/runtime validation is still pending. See
[validation gates](../bevy/references/bevy-020-readiness.md). For an existing Bevy 0.19
project, use the [preserved 0.19 / Rapier 0.36 path](references/bevy-019-compatibility.md).

## When to use this skill

- Add 2D/3D rigid bodies, colliders, sensors, joints, or character movement.
- Decide between `bevy_rapier` and an alternative such as Avian.
- Place input/gameplay systems around a physics step without transform jitter.
- Read collision messages or perform ray, shape, point, and overlap queries.
- Configure headless physics, interpolation, CCD, collision groups, or tests.

Bevy core does not include a physics engine. The published
`bevy_rapier2d`/`bevy_rapier3d 0.37.0` depend on Bevy `^0.20`; no Git branch or fork
is needed. These binding versions are distinct from the underlying `rapier3d`
engine version. Do not carry the old Avian 0.7 recommendation into a 0.20 project
without checking its declared Bevy dependency. Do not install both engines on the
same simulated entities.

## Canonical fixed-step Rapier 3D pattern

```toml
[dependencies]
bevy = "0.20"
bevy_rapier3d = "0.37"
```

```rust
use bevy::prelude::*;
use bevy_rapier3d::prelude::*;

const PHYSICS_HZ: f64 = 60.0;
const PHYSICS_DT: f32 = 1.0 / PHYSICS_HZ as f32;

#[derive(Component)]
struct Player;

#[derive(SystemSet, Debug, Clone, Copy, PartialEq, Eq, Hash)]
enum GamePhysics {
    Drive,
    React,
}

fn main() {
    let mut app = App::new();
    app.add_plugins(DefaultPlugins)
        .insert_resource(Time::<Fixed>::from_hz(PHYSICS_HZ))
        .insert_resource(TimestepMode::Fixed {
            dt: PHYSICS_DT,
            substeps: 1,
        })
        .add_plugins((
            RapierPhysicsPlugin::<NoUserData>::default().in_fixed_schedule(),
            RapierDebugRenderPlugin::default(),
        ))
        .configure_sets(
            FixedUpdate,
            (
                GamePhysics::Drive.before(PhysicsSet::SyncBackend),
                GamePhysics::React.after(PhysicsSet::Writeback),
            ),
        )
        .add_systems(Startup, setup)
        .add_systems(FixedUpdate, drive_player.in_set(GamePhysics::Drive))
        .add_systems(FixedUpdate, react_to_collisions.in_set(GamePhysics::React));
    app.run();
}

fn setup(mut commands: Commands) {
    commands.spawn((
        Camera3d::default(),
        Transform::from_xyz(8.0, 6.0, 12.0).looking_at(Vec3::ZERO, Vec3::Y),
    ));

    // A collider without RigidBody is fixed. Cuboid arguments are half-extents.
    commands.spawn((
        Name::new("Ground"),
        Collider::cuboid(8.0, 0.25, 8.0),
        Transform::from_xyz(0.0, -0.25, 0.0),
    ));

    commands.spawn((
        Name::new("Player"),
        Player,
        RigidBody::Dynamic,
        Collider::ball(0.5),
        Velocity::linear(Vec3::new(1.5, 0.0, 0.0)),
        ActiveEvents::COLLISION_EVENTS,
        Transform::from_xyz(0.0, 4.0, 0.0),
    ));
}

fn drive_player(mut bodies: Query<&mut Velocity, With<Player>>) {
    for mut velocity in &mut bodies {
        velocity.linear.x = 1.5;
    }
}

fn react_to_collisions(mut events: MessageReader<CollisionEvent>) {
    for event in events.read() {
        if let CollisionEvent::Started(a, b, _) = event {
            let _pair = (*a, *b);
        }
    }
}
```

The plugin normally runs in `PostUpdate` with `TimestepMode::Variable`. This example
deliberately moves it to `FixedUpdate`, makes Rapier's `dt` match Bevy's fixed clock,
drives bodies before `PhysicsSet::SyncBackend`, and reacts after
`PhysicsSet::Writeback`. Keep the default schedule if frame-coupled simulation is the
intent; order systems in that same schedule.

## Choose the relevant deep dive

| Problem | Read |
|---|---|
| Cargo profiles, default vs fixed/interpolated stepping, multiple worlds | [Setup and scheduling](references/setup-and-scheduling.md) |
| Body types, collider shapes, mass, units, CCD, transform authority | [Bodies and colliders](references/bodies-and-colliders.md) |
| Collision messages, sensors, groups, ray/shape queries, hooks | [Events, queries, and filtering](references/events-queries-and-filtering.md) |
| Kinematic character motion, controller output, joints | [Controllers and joints](references/controllers-and-joints.md) |
| Rollback, determinism limits, headless tests, performance evidence | [Determinism and testing](references/determinism-and-testing.md) |

## Bevy 0.20 / Rapier 0.37 gotchas

- `Velocity` fields are `linear` and `angular`, not `linvel` and `angvel`.
- `CollisionEvent` and `ContactForceEvent` are messages. At least one collider must
  enable the corresponding `ActiveEvents` flag.
- `ReadRapierContext` is a `SystemParam`; call `.single()` and handle its `Result`.
  `RapierContext` is not a global resource and Rapier supports multiple worlds.
- Dynamic bodies own their simulated pose. Repeatedly writing their `Transform` is a
  teleport and commonly causes jitter; write forces, impulses, or velocity instead.
- Kinematic bodies follow the trajectory you prescribe and do not avoid obstacles by
  themselves. Use scene queries or `KinematicCharacterController`.
- Rapier's default Cargo features pull Bevy asset/render helpers. Disable defaults for
  headless or external-renderer builds and enable the correct `dim2`/`dim3` feature.
- The unused `headless` Cargo feature was removed in 0.37; remove it from manifests.
- Query predicates and intersection callbacks now receive the entity **and** a
  `&RapierCollider`. Review custom hooks and group modes in the
  [0.36→0.37 migration notes](references/rapier-036-to-037.md).
- `RapierDebugRenderPlugin` is diagnostic visualization, not a renderer or a shipping
  requirement.

## See also

- [Rapier 0.36→0.37](references/rapier-036-to-037.md) — required API/feature checks.
- [`bevy-migration-0-19-to-0-20`](../bevy-migration-0-19-to-0-20/SKILL.md) — engine migration.
- Other sibling implementation skills below remain pinned to **Bevy 0.19**; their
  project-level patterns are useful, but their snippets are not 0.20 certification.
- [`bevy-core-concepts`](../bevy-core-concepts/SKILL.md) — fixed schedules and ordering.
- [`bevy-rendering`](../bevy-rendering/SKILL.md) — rendering and physics ownership boundary.
- [`bevy-cameras`](../bevy-cameras/SKILL.md) — camera rays for picking and aiming.
- [Third-person orbit camera](../bevy-cameras/references/third-person-orbit.md) —
  Rapier sphere-cast obstruction and recovery hysteresis.
- [`bevy-input-actions`](../bevy-input-actions/SKILL.md) — fixed-tick movement/aim commands.
- [`bevy-testing`](../bevy-testing/SKILL.md) — deterministic app stepping and headless worlds.
- [`bevy-a11y`](../bevy-a11y/SKILL.md) — accessible movement, timing, and aim alternatives.
- [`bevy-voxel-pipeline`](../bevy-voxel-pipeline/SKILL.md) — collider proxies for voxel worlds.
