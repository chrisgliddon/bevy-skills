# bevy-animation — Curves, Tweening, and AnimatableKeyframeCurve

> Referenced from `bevy-animation/SKILL.md § Topics`.

## Imports

These types are **not** in `bevy::prelude`. Explicit imports are required:

```rust
use bevy::{
    animation::{
        animated_field,
        animation_curves::{AnimatableCurve, AnimatableKeyframeCurve},
    },
    curve::{EasingCurve, EaseFunction},
    curve::cubic_splines::CubicSegment,
    prelude::*,
};
```

## AnimatableKeyframeCurve — building a clip curve from keyframes

```rust
use bevy::{
    animation::{
        animated_field, AnimationTargetId,
        animation_curves::{AnimatableCurve, AnimatableKeyframeCurve},
    },
    prelude::*,
};

fn build_procedural_clip() -> AnimationClip {
    // Keyframe curve: time/value pairs, times must be strictly increasing
    let tween = AnimatableKeyframeCurve::new([
        (0.0_f32, Vec3::ZERO),
        (0.5,     Vec3::new(0.0, 1.0, 0.0)),
        (1.0,     Vec3::ZERO),
    ])
    .expect("keyframe times must be strictly increasing with >= 2 samples");

    // animated_field!(Component::field) returns an AnimatedField implementing AnimatableProperty.
    // Wrap with AnimatableCurve to produce an AnimationCurve attachable to a clip.
    let anim_curve = AnimatableCurve::new(animated_field!(Transform::translation), tween);

    let bone_id = AnimationTargetId::from_name(&Name::new("Hips"));
    let mut clip = AnimationClip::default();
    clip.add_curve_to_target(bone_id, anim_curve);
    clip
}
```

`AnimatableKeyframeCurve::new` returns `Result` — the error fires if sample times are not strictly increasing or fewer than 2 samples are provided.

## EasingCurve — simple two-value lerp with easing

```rust
use bevy::curve::{EasingCurve, EaseFunction};

// Interpolates Vec3 from start to end over t ∈ [0, 1]
let rise = EasingCurve::new(
    Vec3::ZERO,
    Vec3::new(0.0, 5.0, 0.0),
    EaseFunction::CubicInOut,
);

// Sample at any t:
let pos = rise.sample_clamped(0.75); // Vec3 at 75% of the ease
```

Common `EaseFunction` variants: `Linear`, `SineIn`, `SineOut`, `SineInOut`, `CubicIn`, `CubicOut`, `CubicInOut`, `QuarticInOut`, `ExponentialOut`, and others.

## CubicSegment::new_bezier_easing — CSS cubic-bezier

```rust
use bevy::curve::cubic_splines::CubicSegment;

// CSS cubic-bezier(0.25, 0.1, 0.25, 1.0) — equivalent to "ease"
let bezier = CubicSegment::new_bezier_easing([0.25_f32, 0.1], [0.25, 1.0]);
// Returns a CubicSegment<Vec2>; evaluate via .position(t)
let value = bezier.position(0.5_f32);
```

Arguments are `p1` and `p2` control points in the CSS convention (p0 = [0,0], p3 = [1,1]). `x` is time, `y` is output value.

## UnevenSampleAutoCurve — auto-smooth between sparse keyframes

`UnevenSampleAutoCurve` lives in `bevy::curve::sample_curves` (also in the prelude). It interpolates through unevenly spaced samples using the value type's own `StableInterpolate`, which for `Vec3` is a plain lerp but for `Quat` is slerp — so it is the right choice for rotation keys.

```rust
use bevy::prelude::*;

fn smooth_rotation() -> UnevenSampleAutoCurve<Quat> {
    // Samples are sorted and non-finite times dropped; fewer than 2 valid samples is an Err.
    UnevenSampleAutoCurve::new([
        (0.0_f32, Quat::IDENTITY),
        (0.4, Quat::from_rotation_y(1.0)),
        (1.0, Quat::from_rotation_y(2.5)),
    ])
    .expect("at least two finite-time samples")
}
```

Prefer `AnimatableKeyframeCurve` for clip curves (it already interpolates per type); prefer `UnevenSampleAutoCurve` when sampling by hand in a system.

## Non-clip tweening: a UI panel scale-up system

When you don't need the full `AnimationClip` pipeline, sample a curve directly in `Update`:

```rust
use bevy::curve::{EasingCurve, EaseFunction};

#[derive(Component)]
struct ScaleTween {
    curve: EasingCurve<Vec3>,
    elapsed: f32,
    duration: f32,
}

fn scale_tween_system(
    time: Res<Time>,
    mut query: Query<(&mut Transform, &mut ScaleTween)>,
) {
    for (mut tf, mut tween) in &mut query {
        tween.elapsed = (tween.elapsed + time.delta_secs()).min(tween.duration);
        let t = tween.elapsed / tween.duration;
        tf.scale = tween.curve.sample_clamped(t);
    }
}

// Spawn a panel with this component:
// commands.spawn((
//     Node::default(),
//     ScaleTween {
//         curve: EasingCurve::new(Vec3::ZERO, Vec3::ONE, EaseFunction::CubicOut),
//         elapsed: 0.0,
//         duration: 0.4,
//     },
// ));
```

This approach runs in `Update`, avoids `AnimationPlayer`, and has no scheduling conflicts with `PostUpdate` animation systems.

## Gotchas

- `animated_field!` is NOT re-exported from `bevy::prelude`. Always import from `bevy::animation::animated_field`.
- `AnimatableCurve` and `AnimatableKeyframeCurve` are in `bevy::animation::animation_curves`, not `bevy::animation` directly.
- `EaseFunction`, `EasingCurve`, `CubicSegment`, and the sample curves are in `bevy::curve` (crate `bevy_curve`, split from `bevy_math` in 0.20). `bevy::math::curve::*` and `bevy::math::cubic_splines` no longer exist. `bevy::prelude` re-exports the `bevy_curve` prelude, so explicit imports are only needed for module paths.
- `AnimatableKeyframeCurve::new` panics on unwrap if inputs are invalid — always `.expect()` or `.unwrap_or_else()`.

## See also

- [`../SKILL.md`](../SKILL.md) — top-level bevy-animation skill
- [`procedural-animation.md`](procedural-animation.md) — scheduling procedural writes relative to animation systems
- [`animation-graph.md`](animation-graph.md) — attaching `AnimatableCurve` via `clip.add_curve_to_target`
