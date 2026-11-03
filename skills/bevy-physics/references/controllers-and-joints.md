# Character controllers and joints

## Choose character authority first

| Character model | Use when |
|---|---|
| Dynamic rigid body + forces/motors | Physical reactions and pushing are central; accept solver-driven movement |
| Kinematic body + queries | Movement rules are highly custom and you own slide/step/ground logic |
| `KinematicCharacterController` | You want Rapier's move-and-slide, slopes, stairs, snap, and collision output as a starting point |

A kinematic body is not automatically a character controller. It follows the pose or
velocity supplied by gameplay, even through obstacles, unless queries/controller logic
adjust the requested motion.

## Component controller

```rust
use bevy::prelude::*;
use bevy_rapier3d::{control::KinematicCharacterController, prelude::*};

fn spawn_character(mut commands: Commands) {
    commands.spawn((
        RigidBody::KinematicPositionBased,
        Collider::capsule_y(0.6, 0.35),
        Transform::from_xyz(0.0, 2.0, 0.0),
        KinematicCharacterController {
            up: Vec3::Y,
            offset: CharacterLength::Absolute(0.01),
            slide: true,
            autostep: Some(CharacterAutostep {
                max_height: CharacterLength::Absolute(0.35),
                min_width: CharacterLength::Absolute(0.2),
                include_dynamic_bodies: false,
            }),
            max_slope_climb_angle: 45.0_f32.to_radians(),
            min_slope_slide_angle: 30.0_f32.to_radians(),
            apply_impulse_to_dynamic_bodies: true,
            ..default()
        },
    ));
}

fn request_motion(mut controllers: Query<&mut KinematicCharacterController>) {
    for mut controller in &mut controllers {
        controller.translation = Some(Vec3::new(0.05, -0.1, 0.0));
    }
}

fn consume_motion(outputs: Query<&KinematicCharacterControllerOutput>) {
    for output in &outputs {
        let _state = (output.effective_translation, output.grounded);
        for collision in &output.collisions {
            let _hit = collision.entity;
        }
    }
}
```

Set `translation` before `PhysicsSet::SyncBackend`; consume output after writeback.
Derive requested displacement from the selected physics `dt`, not render-frame delta.
The built-in controller does not support rotational movement and is intentionally a
generic base. Copy/customize or use `RapierContext::move_shape` when filtering and
game-specific movement require more control.

Grounded output is evidence about the resolved request, not a permanent state. Test
slopes, stair edges, ceilings, moving platforms, corners, crouch/shape changes, large
and tiny `dt`, and the transition on/off ground. Keep camera and visual animation on a
child or explicit presentation layer.

Accessible gameplay alternatives—toggle movement, autorun, camera assist, lock-on,
timing relaxation—belong in the action/gameplay layer that produces controller motion,
not in vendor-specific controller detection. See `bevy-a11y`.

## Joints

`ImpulseJoint` supports general joint graphs and closed loops. The component lives on
the second body and points to its parent endpoint:

```rust
fn hinge(commands: &mut Commands, parent: Entity, child: Entity) {
    let joint = RevoluteJointBuilder::new(Vec3::Y)
        .local_anchor1(Vec3::new(0.0, 1.0, 0.0))
        .local_anchor2(Vec3::new(0.0, -1.0, 0.0))
        .limits([-0.75, 0.75]);
    commands.entity(child).insert(ImpulseJoint::new(parent, joint));
}
```

`MultibodyJoint` is efficient for articulation trees but cannot form closed loops.
Joint anchors are local to their endpoint bodies. Test limits and motors under maximum
load; use `AdditionalSolverIterations` selectively for difficult islands before
raising global cost.

## Sources

- [Rapier character controller](https://rapier.rs/docs/user_guides/bevy_plugin/character_controller/)
- [Character-controller collisions](https://rapier.rs/docs/user_guides/bevy_plugin/character_controller_collisions/)
- [Rapier joints](https://rapier.rs/docs/user_guides/bevy_plugin/joints/)
