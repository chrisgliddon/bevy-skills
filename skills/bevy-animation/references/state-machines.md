# bevy-animation — Animation State Machines and Transitions

> Referenced from `bevy-animation/SKILL.md § Topics`.

## Weight-blended locomotion state machine

Three clip nodes under a blend root; weights driven by a speed resource.

```rust
use bevy::{animation::graph::AnimationNodeIndex, prelude::*};
use core::time::Duration;

#[derive(Resource)]
struct LocomotionNodes {
    idle: AnimationNodeIndex,
    walk: AnimationNodeIndex,
    run:  AnimationNodeIndex,
}

fn build_locomotion_graph(
    idle_clip: Handle<AnimationClip>,
    walk_clip: Handle<AnimationClip>,
    run_clip:  Handle<AnimationClip>,
    mut graphs: ResMut<Assets<AnimationGraph>>,
) -> (Handle<AnimationGraph>, LocomotionNodes) {
    let mut graph = AnimationGraph::new();
    let root = graph.root;
    let idle = graph.add_clip(idle_clip, 1.0, root);
    let walk = graph.add_clip(walk_clip, 0.0, root); // start silent
    let run  = graph.add_clip(run_clip,  0.0, root);
    let handle = graphs.add(graph);
    (handle, LocomotionNodes { idle, walk, run })
}
```

Drive weights in `Update` by writing to the `AnimationGraph` asset directly (get a mutable reference via `graphs.get_mut(&handle)`), or use `AnimationTransitions` for crossfades.

## AnimationTransitions::play

`AnimationTransitions::play` is the only transition method in Bevy 0.18. There is no `play_with_transition`.

```rust
use bevy::{animation::{graph::AnimationNodeIndex, RepeatAnimation}, prelude::*};
use core::time::Duration;

fn start_walk(
    mut query: Query<(&mut AnimationTransitions, &mut AnimationPlayer)>,
    walk_node: Res<WalkNodeIndex>, // your stored AnimationNodeIndex
) {
    for (mut transitions, mut player) in &mut query {
        // play() signature:
        //   play(&mut self, player: &mut AnimationPlayer,
        //        node: AnimationNodeIndex, duration: Duration) -> &mut ActiveAnimation
        transitions
            .play(&mut player, walk_node.0, Duration::from_millis(250))
            .set_repeat(RepeatAnimation::Forever)
            .set_speed(1.0);
    }
}
```

`play` blends from whatever is currently playing to the new node over `duration`. The returned `&mut ActiveAnimation` lets you chain:

- `.set_repeat(RepeatAnimation::Forever)` — loop indefinitely
- `.set_repeat(RepeatAnimation::Count(n))` — play n times then stop
- `.set_repeat(RepeatAnimation::Never)` — play once (default)
- `.set_speed(f32)` — playback rate multiplier

## Integration with Bevy States

Trigger transitions on state changes using `OnEnter` / `OnExit` systems:

```rust
#[derive(States, Default, Debug, Clone, PartialEq, Eq, Hash)]
enum PlayerState { #[default] Idle, Walking, Combat }

#[derive(Resource)]
struct AnimNodes {
    idle: AnimationNodeIndex,
    walk: AnimationNodeIndex,
    combat_idle: AnimationNodeIndex,
}

fn on_enter_walking(
    mut query: Query<(&mut AnimationTransitions, &mut AnimationPlayer)>,
    nodes: Res<AnimNodes>,
) {
    for (mut transitions, mut player) in &mut query {
        transitions
            .play(&mut player, nodes.walk, Duration::from_millis(200))
            .set_repeat(RepeatAnimation::Forever);
    }
}

fn on_enter_combat(
    mut query: Query<(&mut AnimationTransitions, &mut AnimationPlayer)>,
    nodes: Res<AnimNodes>,
) {
    for (mut transitions, mut player) in &mut query {
        transitions
            .play(&mut player, nodes.combat_idle, Duration::from_millis(300))
            .set_repeat(RepeatAnimation::Forever);
    }
}

// Registration:
// app.add_systems(OnEnter(PlayerState::Walking), on_enter_walking);
// app.add_systems(OnEnter(PlayerState::Combat),  on_enter_combat);
```

## Gotchas

- `AnimationTransitions` must be inserted **alongside** `AnimationPlayer` on the same entity. If it is absent, `play` has no effect.
- `play_with_transition` does **not exist** in Bevy 0.18. Use `play(player, node, duration)`.
- Transitions outlive the system tick — a 250 ms crossfade continues across many frames without re-calling `play`.
- Swapping `AnimationGraphHandle` at runtime causes a one-frame pose snap unless you call `transitions.play` on a node in the new graph in the same tick.
- Node weights set on the `AnimationGraph` asset and transition weights from `AnimationTransitions` multiply together.

## See also

- [`../SKILL.md`](../SKILL.md) — top-level bevy-animation skill
- [`animation-graph.md`](animation-graph.md) — building graphs, blend vs additive nodes
- [`animation-events.md`](animation-events.md) — firing events from state-change frames
