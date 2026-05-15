# bevy-porting — Unity Mecanim / Animator → Bevy 0.18 animation graph

> Referenced from `bevy-porting/SKILL.md § Unity (priority)`.

## The big shift

Unity's Animator window: states ARE clips; you draw transitions between states.
Bevy's `AnimationGraph`: a blend DAG of nodes; transitions are runtime weight ramps.

| Unity Mecanim | Bevy 0.18 |
|---|---|
| Animator Controller asset | `AnimationGraph` asset |
| State (with clip) | `AnimationNodeIndex` (clip node) |
| Blend Tree | blend node + weighted clip children |
| Parameter (`Float`, `Bool`, `Trigger`, `Int`) | `Resource` or `Component` + a driving system |
| "Any State" transition | system that calls `transitions.play(...)` unconditionally |
| Transition (condition + duration) | `AnimationTransitions::play(player, node, Duration)` |
| Avatar mask | `AnimationMask` bit groups |

Mental flip: stop authoring "states + conditions"; start authoring "a graph + a Rust
system that calls `transitions.play`".

See [`bevy-animation/SKILL.md`](../../bevy-animation/SKILL.md) for the full graph API
and [`bevy-animation/references/state-machines.md`](../../bevy-animation/references/state-machines.md)
for the idle/walk/run state machine pattern.

## Animator parameter → Rust state machine

Unity `Float` parameter `Speed` driving idle/walk/run:

```rust
use bevy::{animation::{graph::AnimationNodeIndex, RepeatAnimation}, prelude::*};
use core::time::Duration;

#[derive(Resource, Default)]
struct CharacterSpeed(f32);

#[derive(Resource)]
struct LocoNodes { idle: AnimationNodeIndex, walk: AnimationNodeIndex, run: AnimationNodeIndex }

fn drive_locomotion(
    speed: Res<CharacterSpeed>,
    nodes: Res<LocoNodes>,
    mut q: Query<(&mut AnimationTransitions, &mut AnimationPlayer)>,
) {
    let target = match speed.0 {
        s if s < 0.1  => nodes.idle,
        s if s < 4.0  => nodes.walk,
        _             => nodes.run,
    };
    for (mut tx, mut player) in &mut q {
        tx.play(&mut player, target, Duration::from_millis(200))
            .set_repeat(RepeatAnimation::Forever);
    }
}
```

`Bool` → branch on a `bool` field inside any resource.
`Trigger` → a one-shot `bool` that the system resets to `false` after acting on it.
`Int` → `match` on a `u32` field.

## Blend Trees

| Unity | Bevy 0.18 |
|---|---|
| 1D Blend Tree | `graph.add_clip` siblings under a blend node; weights computed from your `Resource<f32>` and written to `graph.get_mut(node).weight` |
| 2D Blend Tree | Two weighted axes; do-able but verbose — simplify to 1D where possible |
| Direct Blend Tree | Set per-node weights directly in the graph asset each frame |

Mutation: `graphs.get_mut(&handle).unwrap().get_mut(node_index).weight = computed_w;`

## "Any State" transitions

Mecanim's "Any State" is not a Bevy primitive. Replicate it:

```rust
fn any_state_death(
    mut q: Query<(&mut AnimationTransitions, &mut AnimationPlayer)>,
    nodes: Res<LocoNodes>,
    // Replace with whatever condition you detect:
    keyboard: Res<ButtonInput<KeyCode>>,
) {
    if keyboard.just_pressed(KeyCode::KeyK) {
        for (mut tx, mut player) in &mut q {
            tx.play(&mut player, nodes.idle, Duration::from_millis(100));
        }
    }
}
```

Any system can call `transitions.play` — there is no "state context" restriction.

## Animation Events (Unity AnimationEvents → Bevy AnimationEvent)

Unity: drag a marker onto the clip timeline, name a method → `MonoBehaviour` receives it.
Bevy: derive an event type, attach it to a clip at a timestamp, observe it globally.

```rust
use bevy::animation::AnimationEvent;

#[derive(AnimationEvent, Clone)]
struct FootstepEvent { foot: u8 }   // 0 = left, 1 = right

// Attach to clip:
clip.add_event(0.42, FootstepEvent { foot: 0 });

// Handle anywhere:
fn on_footstep(trigger: On<FootstepEvent>) {
    let _foot = trigger.foot;
    let _entity = trigger.trigger().target; // NOT trigger.target()
}
// app.add_observer(on_footstep);
```

See [`bevy-animation/references/animation-events.md`](../../bevy-animation/references/animation-events.md)
for `add_event_to_target` (fires on the bone entity, not the player).

## Avatar / Humanoid retargeting

Bevy 0.18 has **no built-in humanoid retargeting**. Clip targets are resolved by name:
`AnimationTargetId::from_name(&Name::new("Hips"))`.

Options:
- **Standardise bone names** across all characters so one clip plays on each rig.
- **Retarget at build time** — bake a per-character version of each clip in your DCC
  tool (Blender NLA editor or a script against the exported glTF).

If your project is Humanoid-retargeting-heavy, budget time for one of these approaches
before porting.

## animation_extractor.py

The extraction script converts a Unity `.anim` file to Bevy-ready keyframe JSON:

```bash
python3 skills/bevy-porting/scripts/unity/animation_extractor.py \
  /path/to/Assets/Animations/Walk.anim \
  --format bevy-keyframes \
  --out walk.json
```

Output shape — one entry per animated track:

```json
[
  {
    "target_path": ["Hips"],
    "property": "translation",
    "keyframes": [
      { "time": 0.0, "value": [0.0, 0.94, 0.0] },
      { "time": 0.5, "value": [0.0, 0.95, 0.0] }
    ]
  }
]
```

Feed each track's `keyframes` array into `AnimatableKeyframeCurve::new([...])`, wrap it
in `AnimatableCurve::new(animated_field!(Transform::translation), curve)`, and attach it
to an `AnimationClip` via `clip.add_curve_to_target(target_id, curve)`.

**Known limitation — `m_CompressedRotationCurves` not supported:** Unity's Mecanim
compression format stores rotations as packed integers in `m_CompressedRotationCurves`
blocks. The extractor cannot decode these; it only handles the uncompressed
`m_RotationCurves` (quaternion) and `m_EulerCurves` (Euler) blocks. If your `.anim`
files were baked with "Optimal" rotation compression in Unity's Animation Import
Settings, disable compression ("Off") and re-bake before running the extractor.

## See also

- [`../SKILL.md`](../SKILL.md) — bevy-porting dispatcher
- [`unity-input.md`](unity-input.md) — porting Unity input alongside animation state
- [`bevy-animation/SKILL.md`](../../bevy-animation/SKILL.md) — full Bevy 0.18 animation API
- [`bevy-animation/references/state-machines.md`](../../bevy-animation/references/state-machines.md)
- [`bevy-animation/references/animation-events.md`](../../bevy-animation/references/animation-events.md)
