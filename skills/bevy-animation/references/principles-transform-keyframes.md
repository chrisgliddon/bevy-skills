# bevy-animation — Squash & Stretch, Arc & Exaggeration

> Referenced from `bevy-animation/SKILL.md § The 12 Basic Principles`.

These three live in *space* — they're about what values your keyframes hit on
`Transform`'s scale, translation, and rotation. Bevy 0.18's `AnimatableCurve` +
`animated_field!` + `AnimatableKeyframeCurve` are the toolkit.

---

## Squash & Stretch

A bouncing ball squashes flat on impact and stretches tall at peak height. Non-uniform
scale along one axis communicates mass and elasticity. Keep volume roughly constant:
when Y shrinks, X and Z grow proportionally.

```rust
use bevy::{
    animation::{animated_field, animation_curves::{AnimatableCurve, AnimatableKeyframeCurve}},
    prelude::*,
};

let squash_curve = AnimatableKeyframeCurve::new([
    (0.0_f32, Vec3::ONE),
    (0.1,     Vec3::new(1.3, 0.6, 1.3)),  // squash on impact
    (0.2,     Vec3::new(0.8, 1.4, 0.8)),  // stretch during rebound
    (0.35,    Vec3::ONE),                  // settle back to rest
])
.expect("keyframe times must be strictly increasing with ≥2 samples");

let curve = AnimatableCurve::new(
    animated_field!(Transform::scale),
    squash_curve,
);
// clip.add_curve_to_target(target_id, curve);
```

**Volume preservation guideline:** if Y scales by factor `s`, set X and Z to
`1.0 / s.sqrt()` to conserve volume. Exact math matters less than the feel — err
toward a little extra squash for cartoon reads.

**Anticipate-squash pattern:** lead with a brief squash before the stretch. The
sequence `rest → squash → stretch → rest` reads as a living, elastic object.

---

## Arc

Real-world objects travel in arcs, not straight lines — gravity, momentum, and
biomechanics curve every trajectory. Straight-line translation between two points
reads as robotic.

Build arcs by adding intermediate keyframes that bow away from the straight-line path:

```rust
let arc_curve = AnimatableKeyframeCurve::new([
    (0.0_f32, Vec3::new(-2.0, 0.0, 0.0)),  // start
    (0.25,    Vec3::new(-1.0, 1.2, 0.0)),  // apex-left — bows up
    (0.5,     Vec3::new( 0.0, 1.8, 0.0)),  // peak
    (0.75,    Vec3::new( 1.0, 1.2, 0.0)),  // apex-right — bows down
    (1.0,     Vec3::new( 2.0, 0.0, 0.0)),  // end
])
.expect("strictly increasing times");

let curve = AnimatableCurve::new(
    animated_field!(Transform::translation),
    arc_curve,
);
```

Bevy interpolates **linearly** between keyframe samples by default. For a smooth arc
with only a few key poses, sample more densely (add intermediate frames) or use
`UnevenSampleAutoCurve` from `bevy::math::curve`, which fits a smoother interpolant
through sparse samples.

---

## Exaggeration

Exaggeration means pushing values past physical reality to sell the emotion or
read of an action — wider eyes, bigger squash, faster snap. The authored amplitude
is the primary lever.

At runtime, Bevy gives you two secondary knobs:

**Timing-based intensity:** `ActiveAnimation::set_speed(f32)` makes the same motion
feel snappier (higher speed) or more ponderous (lower speed).

**Weight-based intensity via additive blend:**

```rust
// Build the graph with an additive node at a tunable weight.
// weight < 1.0 → damped (less exaggerated)
// weight = 1.0 → authored amplitude
// weight > 1.0 → overdrive — values are NOT clamped in 0.18;
//                 use carefully, especially on rotation (quaternion
//                 normalisation handles it, but scale/translation can
//                 exceed intended bounds).
let additive = graph.add_additive_blend(/*weight=*/ 1.5, root);
let _exag_node = graph.add_clip(exaggerated_handle, 1.0, additive);
```

For authored exaggeration, increase keyframe amplitude directly in your DCC tool —
that's still the most predictable approach.

---

## Gotchas

- **`Transform::scale` is `Vec3`, not `f32`.** Uniform scale = `Vec3::splat(s)`, not
  a bare float.
- **Linear interpolation through scale values near zero** can produce a visible
  "pop" or inside-out frame. Avoid keyframing through `Vec3::ZERO`; add eased
  intermediate keys.
- **`animated_field!` is not in the prelude.** Import from
  `bevy::animation::animated_field` explicitly.
- **`AnimatableKeyframeCurve::new` panics (via `.expect`) if times are not strictly
  increasing or fewer than 2 samples are provided.** Use `.unwrap()` in examples,
  but validate inputs at runtime in production code.
- **Additive blend weight > 1.0 is not clamped.** Rotation is safe (quaternion
  normalisation), but translation and scale can drift past intended bounds silently.

---

## See also

- [`../SKILL.md`](../SKILL.md) — canonical pattern and full trigger list
- [`curves-and-tweening.md`](curves-and-tweening.md) — `AnimatableCurve`,
  `UnevenSampleAutoCurve`, and sampled curve construction
- [`animation-graph.md`](animation-graph.md) — additive blend nodes, weights, and
  graph construction
