---
name: bevy-animation
description: Use when wiring `AnimationPlayer` + `AnimationGraphHandle`, building an `AnimationGraph` from glTF clips, blending state-driven animations with `AnimationTransitions::play`, isolating body parts with `AnimationMask`, firing gameplay sync via `#[derive(AnimationEvent)]` + `On<E>` observers, tweening with `AnimatableCurve` / `EaseFunction` / `CubicSegment::new_bezier_easing`, or applying the 12 Basic Principles of Animation to 3D characters in Bevy 0.18.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "3"
  area: animation
  bevy_version: "0.18"
---

# Bevy 0.18 — Animation (graphs, blending, events, 12 principles)

## When to use this skill

- Loading a glTF clip and playing it on a character: `AnimationPlayer` + `AnimationGraphHandle`.
- Cross-fading between idle / walk / run via `AnimationTransitions::play(player, node, Duration)`.
- Building an `AnimationGraph` in code: blend nodes, additive nodes, weights, `AnimationMask`.
- Triggering gameplay events from a clip timeline (footsteps, hitbox activation, VFX cues) with `#[derive(AnimationEvent)]` + `clip.add_event_to_target(...)` + `On<MyEvent>` observers.
- Procedural tweening *without* an `AnimationClip` — sampling a `Curve` per frame via `EasingCurve` + `EaseFunction` or `CubicSegment::new_bezier_easing`.
- Applying the 12 Basic Principles of Animation (Thomas & Johnston, 1981) to a Bevy character.
- Importing a Blender rig and finding bones aren't animated — usually the `Name` requirement for `AnimationTargetId::from_name`.

## Canonical end-to-end pattern

Verified against `bevy = "0.18"` — `cargo check` clean in `bevy-skills-tester/skill-snippets/examples/bevy_animation.rs`.

```rust
use bevy::{
    animation::{
        animated_field,
        animation_curves::{AnimatableCurve, AnimatableKeyframeCurve},
        AnimationEvent, AnimationTargetId,
    },
    prelude::*,
};
use core::time::Duration;

#[derive(AnimationEvent, Clone)]
struct FootstepEvent { foot: u8 }

fn setup(
    mut commands: Commands,
    asset_server: Res<AssetServer>,
    mut clips: ResMut<Assets<AnimationClip>>,
    mut graphs: ResMut<Assets<AnimationGraph>>,
) {
    // 1. Load a glTF clip
    let walk: Handle<AnimationClip> =
        asset_server.load("models/character.glb#Animation0");

    // 2. Build a tiny procedural clip with a sample curve + an event
    let bone = AnimationTargetId::from_name(&Name::new("Hips"));
    let tween = AnimatableKeyframeCurve::new([
        (0.0_f32, Vec3::ZERO),
        (0.5,     Vec3::new(0.0, 1.0, 0.0)),
        (1.0,     Vec3::ZERO),
    ]).expect("strictly-increasing times");
    let curve = AnimatableCurve::new(animated_field!(Transform::translation), tween);
    let mut proc = AnimationClip::default();
    proc.add_curve_to_target(bone, curve);
    proc.add_event(0.5, FootstepEvent { foot: 0 });
    let proc = clips.add(proc);

    // 3. Compose a graph: root → walk + additive(proc, mask=group 0 excluded)
    const MASK_GROUP_0_BIT: u64 = 1 << 0;
    let mut graph = AnimationGraph::new();
    let root = graph.root;
    let _walk_node = graph.add_clip(walk, 1.0, root);
    let additive = graph.add_additive_blend(0.5, root);
    let _proc_node = graph.add_clip_with_mask(proc, MASK_GROUP_0_BIT, 1.0, additive);

    // 4. Spawn the player entity (bones come from the loaded glTF scene)
    commands.spawn((
        Name::new("AnimationRoot"),
        AnimationPlayer::default(),
        AnimationGraphHandle(graphs.add(graph)),
        AnimationTransitions::new(),
    ));
}

fn start(mut q: Query<(&mut AnimationTransitions, &mut AnimationPlayer), Added<AnimationPlayer>>) {
    use bevy::animation::{graph::AnimationNodeIndex, RepeatAnimation};
    for (mut tx, mut player) in &mut q {
        tx.play(&mut player, AnimationNodeIndex::new(1), Duration::from_millis(250))
            .set_repeat(RepeatAnimation::Forever);
    }
}

fn on_footstep(trigger: On<FootstepEvent>) {
    let foot = trigger.foot;                        // On<E> derefs to &E
    let _entity = trigger.trigger().target;          // AnimationEventTrigger::target
    let _ = foot;
}

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)                 // gltf_animation is a default feature
        .add_systems(Startup, setup)
        .add_systems(Update, start)
        .add_observer(on_footstep)
        .run();
}
```

## Topics

| Topic | Reference |
|---|---|
| Building blend / additive graphs, `AnimationMask`, hot-swap | [references/animation-graph.md](references/animation-graph.md) |
| Blender → glTF → Bevy import: `Name`, axis, multi-clip, unsupported extensions | [references/gltf-import.md](references/gltf-import.md) |
| Procedural animation in `Update` vs `FixedUpdate`, root-motion extraction | [references/procedural-animation.md](references/procedural-animation.md) |
| Idle / walk / run blending; `AnimationTransitions::play` + Bevy `States` integration | [references/state-machines.md](references/state-machines.md) |
| `#[derive(AnimationEvent)]`, `add_event_to_target`, `On<E>` observer wiring | [references/animation-events.md](references/animation-events.md) |
| `AnimatableCurve`, `EasingCurve`, `EaseFunction`, cubic-bezier, `UnevenSampleAutoCurve` | [references/curves-and-tweening.md](references/curves-and-tweening.md) |
| `AnimationPlayer` cost, skin buffers, graph complexity, runtime graph swaps | [references/performance.md](references/performance.md) |
| **Principles** — Slow In/Out, Timing, Anticipation → easing + duration | [references/principles-easing-and-timing.md](references/principles-easing-and-timing.md) |
| **Principles** — Squash & Stretch, Arc, Exaggeration → `Transform` keyframes | [references/principles-transform-keyframes.md](references/principles-transform-keyframes.md) |
| **Principles** — Staging, Follow Through, Secondary Action → graph layering + masks | [references/principles-graph-layering.md](references/principles-graph-layering.md) |
| **Principles** — Straight-Ahead vs Pose-to-Pose, Solid Drawing, Appeal → upstream authoring | [references/principles-authoring.md](references/principles-authoring.md) |

## The 12 Basic Principles of Animation

The four `principles-*.md` references group Thomas & Johnston's twelve principles by which Bevy primitive they actually exercise. Quick map:

- **Easing & Timing** — Slow In/Out, Timing, Anticipation map to `EaseFunction` / `EasingCurve` / `CubicSegment::new_bezier_easing` and clip duration + `ActiveAnimation::set_speed`.
- **Transform keyframes** — Squash & Stretch, Arc, Exaggeration are `AnimatableKeyframeCurve` over `Transform::scale` / `::translation` via `animated_field!`.
- **Graph layering** — Staging, Follow Through & Overlapping Action, Secondary Action are `AnimationGraph::add_additive_blend` + `AnimationMask` group isolation.
- **Authoring** — Straight-Ahead vs Pose-to-Pose, Solid Drawing, Appeal live in your DCC tool (Blender, Maya). Bevy plays whatever you authored.

## Gotchas

- **0.17 → 0.18 split.** `AnimationTarget { id, player }` no longer exists. It's now two separate components on each bone entity: `AnimationTargetId(Uuid)` + `AnimatedBy(Entity)`. The glTF loader spawns these for you.
- **`gltf_animation` is on by default.** It's already in `bevy = "0.18"`'s default features — no opt-in needed unless you ran `default-features = false`.
- **`AnimationTransitions::play_with_transition` does NOT exist.** The real and only method is `play(&mut self, player, node, Duration) -> &mut ActiveAnimation`. Chain `.set_repeat(RepeatAnimation::Forever)` / `.set_speed(f32)` on the returned value.
- **`animated_field!` and `AnimatableCurve` are not in the prelude.** Import explicitly from `bevy::animation::{animated_field, animation_curves::{AnimatableCurve, AnimatableKeyframeCurve}}`.
- **`On<AnimationEvent>` is not an `EntityEvent` observer.** `On<E>` derefs to `&E` (access event fields directly). The firing entity is at `trigger.trigger().target` (the `AnimationEventTrigger::target` field renamed from `animation_player` in 0.18). `.target()` is not available — that's for `EntityEvent`s.
- **`Name` is required on bone entities** for `AnimationTargetId::from_name(&Name)` to resolve. The glTF loader sets this; hand-built skeletons must too.
- **`AnimationMask` bit polarity.** A bit set in a node's `u64` mask means that node will *not* animate targets in that group. Register a bone into a group via `graph.add_target_to_mask_group(target_id, group_u32)`. To restrict a node to a single group, set every bit *except* that group's.
- **Schedule.** Bevy's animation systems run in `PostUpdate`, chained `.before(TransformSystems::Propagate)`. Procedural systems that also write `Transform` should run in `Update` or order explicitly relative to `AnimationSystems` in `PostUpdate`.
- **Out of scope in 0.18 core animation.** No built-in IK, morph-target/blend-shape animation isn't first-class, particle/FX systems are separate, `KHR_animation_pointer` glTF extension is unsupported — see [`references/gltf-import.md`](references/gltf-import.md).

## See also

- `bevy-cameras` — camera animation (panning, dolly, focus follow) overlaps with this skill; use the same `EaseFunction` / `EasingCurve` toolkit.
- `bevy-core-concepts` — `Update` vs `FixedUpdate` choice matters for procedural animation; see [`procedural-animation.md`](references/procedural-animation.md).
- `bevy-ecs-systems` — observer wiring patterns (`On<E>`, `add_observer`) used for `AnimationEvent`s.
- `bevy-pbr-materials` — material-parameter animation via `AnimatableCurve` targeting `StandardMaterial` fields (emissive flicker, alpha fades).
- `bevy-custom-assets` — `AssetLoader` patterns if you serialise `AnimationGraph` to RON (`.animgraph.ron`) and load it as an asset.
