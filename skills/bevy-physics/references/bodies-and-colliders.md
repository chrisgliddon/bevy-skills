# Bodies, colliders, and transform authority

## Rigid-body choice

| Type | Authority and behavior |
|---|---|
| No `RigidBody` + `Collider` | Fixed world collider |
| `RigidBody::Fixed` | Explicit fixed body; useful as a joint endpoint |
| `Dynamic` | Rapier integrates pose from gravity, forces, impulses, contacts, and joints |
| `KinematicPositionBased` | Game supplies a pose/translation; pushes dynamics but is not deflected by them |
| `KinematicVelocityBased` | Game supplies velocity; same one-way contact authority |

For a dynamic body, drive `Velocity`, `ExternalForce`, `ExternalImpulse`, or a motor.
Writing `Transform` teleports it. Teleports are valid for respawn/rollback, but they
must be deliberate and synchronized once—not reapplied each frame by presentation.

## Collider authoring

Rapier shape constructor sizes are easy to misread:

```rust
Collider::ball(0.5);                 // radius
Collider::cuboid(0.5, 1.0, 0.25);  // half-extents, full size = 1 × 2 × 0.5
Collider::capsule_y(0.6, 0.35);     // segment half-height, radius
```

Place one collider beside the `RigidBody`, or attach several collider child entities
under a body. Child `Transform`s are local offsets. Keep the body/root scale uniform;
non-uniformly scaled primitives may be approximated as more expensive shapes.

Use primitives for moving actors whenever possible. Use convex hulls/decomposition
for irregular moving objects. Triangle meshes and heightfields are best treated as
static environment collision; preserve a simpler gameplay proxy than the render mesh.
`Collider::trimesh` returns `Result` in current Rapier integrations—handle invalid
geometry instead of unwrapping asset data.

## Mass and contact material

Attached colliders contribute mass from density. Override with
`ColliderMassProperties` or add body-level `AdditionalMassProperties`; read the final
value through `ReadMassProperties`. Avoid changing visible mesh scale without updating
the collision/mass plan.

`Friction`, `Restitution`, and their combine rules determine contact behavior. Tune
materials in representative pairs: a high-bounce object on a high-friction surface
does not reveal the behavior of every other combination.

A `Sensor` reports intersections but does not generate contact forces. It can still
contribute mass when attached to a dynamic body, so set its mass contribution
explicitly when that would distort gameplay.

## Stability tools

- `Ccd` prevents selected fast rigid bodies from tunneling at additional cost.
- `SoftCcd` and `ContactSkin` can improve robustness in appropriate scenes without
  blindly enabling full CCD everywhere.
- `LockedAxes` removes unwanted degrees of freedom for 2.5D or upright actors.
- `Damping` is drag, not a substitute for stable constraints or correct units.
- `AdditionalSolverIterations` targets difficult bodies/joint islands without raising
  the global solver cost.

Since 0.37, non-finite state is quarantined: the body/collider is disabled, a
`PhysicsQuarantineEvent` message is emitted, and `RigidBodyDisabled`/`ColliderDisabled`
is inserted. Remove that component after writing finite state to re-enable.

Physics behaves best near real-world scales. Pick a documented unit convention early,
scale gravity/forces consistently, and test the smallest, largest, fastest, and
heaviest supported objects together.

## Separate simulation and presentation

A robust hierarchy is:

```text
PhysicsRoot (RigidBody, Collider, authoritative Transform)
└── Visual (mesh/scene, model offset, render-only smoothing)
```

Do not put a second collider under a visual child accidentally when loading a scene.
Do not let animation root motion, camera smoothing, network interpolation, and Rapier
all write the root transform. Assign one owner and explicit handoff points.

## Sources

- [Rapier rigid bodies](https://rapier.rs/docs/user_guides/bevy_plugin/rigid_bodies/)
- [Rapier colliders](https://rapier.rs/docs/user_guides/bevy_plugin/colliders/)
- [Collider attachment](https://rapier.rs/docs/user_guides/bevy_plugin/collider_creation_and_insertion/)
- [Continuous collision detection](https://rapier.rs/docs/user_guides/bevy_plugin/rigid_body_ccd/)
