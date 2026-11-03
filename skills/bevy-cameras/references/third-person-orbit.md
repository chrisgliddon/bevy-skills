# Third-person orbit camera

Separate the **follow target**, **pivot**, **orientation**, **boom distance**, and
**camera pose**. Collapsing them into one transform makes shoulder offsets,
obstruction, aim, smoothing, and actor fading fight one another.

## State model

```rust
use bevy::prelude::*;

#[derive(Component)]
struct OrbitCamera {
    target: Entity,
    yaw: f32,
    pitch: f32,
    min_pitch: f32,
    max_pitch: f32,
    desired_boom: f32,
    current_boom: f32,
    shoulder: Vec3,
    probe_radius: f32,
}

#[derive(Component, Clone, Copy)]
struct FixedFollowPose {
    previous: Vec3,
    current: Vec3,
}
```

Input updates yaw/pitch and clamps pitch away from the poles. Keep yaw wrapped or
periodically normalised to preserve precision. Resolve look input through
`bevy-input-actions`; expose inversion, separate X/Y sensitivity, recenter, shoulder
swap, aim assist, and motion-reduction settings.

Compute:

```text
interpolated target -> pivot offset -> yaw/pitch rotation -> shoulder/boom endpoint
                    -> obstruction distance -> smoothed camera position -> look_at(pivot)
```

The shoulder offset should rotate with the camera orientation. The obstruction sweep
starts at the pivot and ends at the desired camera endpoint, so it protects both the
boom and offset path.

## Frame-rate-independent response

For exponential smoothing with response `lambda` and elapsed seconds `dt`:

```rust
fn exp_alpha(response: f32, dt: f32) -> f32 {
    1.0 - (-response.max(0.0) * dt.max(0.0)).exp()
}
```

Then use `current.lerp(target, alpha)`. This produces comparable behaviour across
frame rates; `speed * dt` clamping does not. Use a faster inward response when an
obstacle appears and a slower outward response when it clears. Add a small clearance
margin and outward hysteresis so contact jitter does not make the boom chatter.

Use the clock that matches policy: virtual time if pause freezes presentation, real
time if the menu can still orbit. Clamp a huge `dt` after suspension to avoid a single
violent camera jump, or snap deliberately and document it.

## Fixed simulation and visual interpolation

After the target's fixed movement/physics writeback, shift
`previous = current` and capture the new fixed pose. During presentation, interpolate:

```rust
fn interpolated_target(pose: &FixedFollowPose, fixed: &Time<Fixed>) -> Vec3 {
    pose.previous
        .lerp(pose.current, fixed.overstep_fraction())
}
```

This conventional interpolation is smooth but displays one fixed sample of latency.
If the game chooses extrapolation or lower-latency aim, make that a separate explicit
policy and test correction behaviour. Never feed the smoothed visual camera pose back
into authoritative movement or aiming unless that latency is intended.

Update an unparented camera's `Transform` in `PostUpdate` before
`TransformSystems::Propagate`. If using a pivot/boom entity hierarchy, establish the
same ordering for every local transform and avoid mixing global and local coordinates.

## Rapier sphere cast, not a ray

A ray lets the near plane/camera body clip through thin edges. Sweep a sphere from
pivot toward the desired endpoint. For `bevy_rapier3d 0.36`:

```rust
use bevy::prelude::*;
use bevy_rapier3d::{parry::shape::Shape, prelude::*};

fn clear_boom_distance(
    rapier: &ReadRapierContext,
    followed_body: Entity,
    pivot: Vec3,
    desired_camera: Vec3,
    probe_radius: f32,
    clearance: f32,
) -> f32 {
    let delta = desired_camera - pivot;
    let distance = delta.length();
    if distance <= f32::EPSILON {
        return 0.0;
    }

    let Ok(context) = rapier.single() else {
        return distance;
    };
    let probe = Collider::ball(probe_radius);
    let shape: &dyn Shape = (&probe).into();
    let filter = QueryFilter::default()
        .exclude_sensors()
        .exclude_rigid_body(followed_body);

    context
        .cast_shape(
            pivot,
            Quat::IDENTITY,
            delta / distance,
            shape,
            ShapeCastOptions::with_max_time_of_impact(distance),
            filter,
        )
        .map_or(distance, |(_, hit)| {
            (hit.time_of_impact - clearance).max(0.0)
        })
}
```

With a unit-length sweep velocity, `time_of_impact` is distance. Use collision groups
or a predicate to include only camera-blocking geometry, exclude the followed rigid
body/colliders, and ignore sensors. Run after the Rapier query pipeline represents the
desired physics step. Handle a pivot starting inside geometry: the default cast stops
at penetration and returns zero distance; a separate pivot correction may be needed.

## Recovery and actor visibility

Obstruction policy:

- move inward immediately or with a high response to prevent clipping;
- recover outward only after the clear distance exceeds current distance plus a small
  hysteresis threshold;
- recover outward more slowly, while re-casting every frame;
- snap on teleports/target changes rather than dragging through the world.

When the camera approaches or intersects the followed actor, fade or hide only that
actor's camera-facing presentation. Do not mutate a shared material asset used by
other actors; use a per-instance material/extension or dedicated visibility/fade
component. Decide whether shadows remain and prevent the actor from popping at a
single distance by using separate fade-in/fade-out thresholds.

## Acceptance tests

- orbit at min/max pitch and through yaw wrap at several frame rates;
- zero/one/multiple fixed ticks and target teleport;
- thin wall, corner, doorway, moving obstacle, sensor, and own collider;
- rapid obstruction/recovery without clipping or chatter;
- right/left shoulder swap near a wall;
- camera close enough to require actor fade, including shared-material actors;
- motion-reduction settings and mouse/gamepad/Steam Deck input.
