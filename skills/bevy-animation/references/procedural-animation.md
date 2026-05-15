# bevy-animation — Procedural Animation and Root Motion

> Referenced from `bevy-animation/SKILL.md § Topics`.

## Schedule choice

| Use case | Schedule |
|---|---|
| Camera bob, UI tween, particle follow | `Update` |
| Physics-coupled locomotion (velocity-driven) | `FixedUpdate` |

For physics-driven characters, write velocity integration in `FixedUpdate` and smooth the rendered `Transform` in `Update` using `Time<Fixed>::overstep_fraction()`:

```rust
#[derive(Component)]
struct Velocity(Vec3);

#[derive(Component)]
struct PreviousTranslation(Vec3);

fn integrate_physics(
    mut query: Query<(&mut Transform, &mut PreviousTranslation, &Velocity)>,
) {
    // Runs in FixedUpdate — discrete physics step
    for (mut tf, mut prev, vel) in &mut query {
        prev.0 = tf.translation;
        tf.translation += vel.0 * (1.0 / 64.0); // fixed timestep
    }
}

fn smooth_render(
    time: Res<Time<Fixed>>,
    mut query: Query<(&mut Transform, &PreviousTranslation, &Velocity)>,
) {
    // Runs in Update — interpolates between two FixedUpdate ticks
    let alpha = time.overstep_fraction();
    for (mut tf, prev, vel) in &mut query {
        let next = prev.0 + vel.0 * (1.0 / 64.0);
        tf.translation = prev.0.lerp(next, alpha);
    }
}
```

## Root motion extraction

By default, `bevy_animation` writes the root bone's full transform from the clip. To decouple visual root motion from game-side velocity:

1. Register the root bone in a mask group on the graph.
2. Set that group's bit in every clip node's mask so the root is excluded from all animation.
3. Drive the character's `Transform` from a `Velocity` component in your physics system.

```rust
use bevy::{animation::AnimationTargetId, prelude::*};

fn build_rootless_graph(
    clip: Handle<AnimationClip>,
    root_bone_name: &str,
    mut graphs: ResMut<Assets<AnimationGraph>>,
) -> Handle<AnimationGraph> {
    let mut graph = AnimationGraph::new();
    let root = graph.root;

    // Register root bone into group 0
    let root_id = AnimationTargetId::from_name(&Name::new(root_bone_name));
    graph.add_target_to_mask_group(root_id, 0_u32);

    // Bit 0 set = this node will NOT animate group-0 bones (the root)
    const EXCLUDE_ROOT: u64 = 1 << 0;
    graph.add_clip_with_mask(clip, EXCLUDE_ROOT, 1.0, root);

    graphs.add(graph)
}
```

## Ordering relative to animation systems

Animation systems (`animate_targets`, `advance_animations`, `advance_transitions`) run in `PostUpdate`, before `TransformSystems::Propagate`. If your procedural system also writes `Transform`:

- Run it in `Update` (before `PostUpdate`) — animation then overwrites your write for bones it tracks, which is usually correct for root-excluded rigs.
- Or explicitly order it with `app.add_systems(PostUpdate, my_system.before(AnimationSystems::AnimateTargets))`.

Avoid writing `Transform` on a bone entity in `PostUpdate` _after_ `animate_targets` without explicit ordering — the write will silently race.

## Procedural tweening without AnimationClip

For one-off UI or camera motion, skip `AnimationClip` entirely and sample a curve directly:

```rust
use bevy::math::curve::EasingCurve;

#[derive(Component)]
struct PanelTween {
    curve: EasingCurve<Vec3>,
    elapsed: f32,
    duration: f32,
}

fn drive_tween(time: Res<Time>, mut query: Query<(&mut Transform, &mut PanelTween)>) {
    for (mut tf, mut tween) in &mut query {
        tween.elapsed = (tween.elapsed + time.delta_secs()).min(tween.duration);
        let t = tween.elapsed / tween.duration;
        tf.scale = tween.curve.sample_clamped(t);
    }
}
```

See [`curves-and-tweening.md`](curves-and-tweening.md) for curve construction details.

## Gotchas

- `Time<Fixed>::overstep_fraction()` returns a value in `[0, 1]` representing how far the current frame is between the last and next fixed step. Use it for rendering interpolation, not for logic.
- Writing both a physics velocity _and_ `AnimationClip` root motion to the same `Transform` will cause jitter. Pick one.
- `animate_targets` runs in `PostUpdate` — check ordering if you see procedural motion being overwritten by clip animation.

## See also

- [`../SKILL.md`](../SKILL.md) — top-level bevy-animation skill
- [`animation-graph.md`](animation-graph.md) — mask groups for root bone exclusion
- [`curves-and-tweening.md`](curves-and-tweening.md) — `EasingCurve`, `AnimatableKeyframeCurve`, and `animated_field!`
