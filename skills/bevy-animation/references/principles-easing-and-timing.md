# bevy-animation — Slow In/Out, Timing & Anticipation

> Referenced from `bevy-animation/SKILL.md § The 12 Basic Principles`.

These three principles all live in *time*. In Bevy 0.18 they map to `EaseFunction`,
clip duration / playback speed, and the build-up beat at the start of a keyframe
sequence.

---

## Slow In / Slow Out

Objects in the real world accelerate into and decelerate out of motion — they rarely
move at constant speed. "Slow in" = easing into a move; "slow out" = easing out of it.
`EasingCurve` applies these shapes in Bevy without any authored keyframe density.

```rust
use bevy::{math::curve::EasingCurve, prelude::*};
use bevy::math::cubic_splines::CubicSegment;

// Standard ease-in-out: starts slow, peaks, ends slow.
let smooth_move = EasingCurve::new(
    Vec3::ZERO,
    Vec3::new(3.0, 0.0, 0.0),
    EaseFunction::CubicInOut,
);

// CSS-style cubic-bezier for a custom ease curve.
// [x1, y1], [x2, y2] — control points, same convention as CSS cubic-bezier().
let custom_ease = CubicSegment::new_bezier_easing(
    [0.25_f32, 0.1_f32],
    [0.25_f32, 1.0_f32],
);
```

**Common ease functions and when to reach for them:**

| `EaseFunction` | Character |
|---|---|
| `CubicInOut` | General-purpose; smooth entry and exit |
| `SineIn` | Subtle; good for UI fades and camera drifts |
| `ElasticOut` | Springy overshoot; cartoony snap |
| `BounceOut` | Exaggerated landing; rubber-ball drops |
| `Linear` | No easing; use for mechanical / robotic motion |

`EasingCurve` produces a `Curve<T>` that you can sample manually or wrap into an
`AnimatableCurve` for clip-based playback.

---

## Timing

Timing is the total duration of an action — how many frames/seconds it lasts. Faster
timing reads as lighter or more urgent; slower timing reads as heavier or more
deliberate.

In Bevy 0.18, clip duration is determined at authoring time (in Blender/Maya or when
you build `AnimationClip` in code). At runtime you adjust it with playback speed:

```rust
use bevy::animation::RepeatAnimation;
use core::time::Duration;

// In a system that queries AnimationTransitions + AnimationPlayer:
transitions
    .play(&mut player, walk_node, Duration::from_millis(200))
    .set_speed(1.5)                          // 50% faster = lighter feel
    .set_repeat(RepeatAnimation::Forever);
```

`set_speed(f32)` on `ActiveAnimation` scales wall-clock time → clip time. Values
above 1.0 speed up; below 1.0 slow down. Negative values play the clip backwards.

**Audio / gameplay sync:** `AnimationClip::add_event(timestamp, event)` fires a
custom `AnimationEvent` at a precise clip timestamp. This is the correct way to
trigger footstep sounds, particle effects, or gameplay callbacks locked to a specific
beat in the motion — not frame counting.

---

## Anticipation

Anticipation is a small preparatory motion opposite to the main action — a character
crouches before jumping. It registers intent and makes the main movement read as
purposeful.

Anticipation is authored in the DCC tool (Blender/Maya): add keyframes that move
slightly against the direction of the main action during the first few frames of the
clip. Bevy plays the clip as-is; it has no built-in knowledge of anticipation.

**Software anticipation ramp via transition duration:**

```rust
// A long transition duration eases the blend from the previous pose into this clip.
// This creates a smooth ramp-up that can read as anticipation even if the clip
// itself starts at full speed. It is NOT the same as authored anticipation — the
// direction of motion does not reverse — but it softens abrupt starts.
transitions
    .play(&mut player, jump_node, Duration::from_millis(400))
    .set_speed(1.0);
```

For true anticipation (reverse-direction windup), author it in the clip. Use the
transition duration only to control blend smoothness between clips.

---

## Gotchas

- **Linear interpolation has no ease.** `AnimatableKeyframeCurve` interpolates
  linearly between samples by default. Wrap values in `EasingCurve` or add denser
  keyframes to fake non-linear motion.
- **`EaseFunction` and `EasingCurve` are not in `bevy::prelude`.** Import both
  explicitly from `bevy::math::curve`:
  `use bevy::math::curve::{EasingCurve, EaseFunction};`
- **`CubicSegment::new_bezier_easing` is in `bevy::math::cubic_splines`**, not in
  the animation module. Add that import explicitly.
- **Transition duration ≠ anticipation.** A long `Duration` in
  `AnimationTransitions::play` blends *into* the clip from the prior pose. It does not
  add a reverse-motion windup; that must be authored in the clip itself.
- **`set_speed` affects timing globally for that node.** If a node is shared
  (additive blend child), changing its speed changes timing for all consumers.

---

## See also

- [`../SKILL.md`](../SKILL.md) — canonical pattern and full trigger list
- [`curves-and-tweening.md`](curves-and-tweening.md) — building `AnimatableCurve`
  pipelines and `UnevenSampleAutoCurve`
- [`state-machines.md`](state-machines.md) — managing which clip plays when via
  `AnimationTransitions`
