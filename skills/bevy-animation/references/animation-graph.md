# bevy-animation — Animation Graph Construction and Masking

> Referenced from `bevy-animation/SKILL.md § Topics`.

## Building a graph in code

`AnimationGraph::new()` returns a graph with a single blend root. Add clips and blend nodes onto it, then wrap the resulting `Handle<AnimationGraph>` in `AnimationGraphHandle` and insert that component alongside `AnimationPlayer` on the player entity.

```rust
use bevy::{animation::AnimationTargetId, prelude::*};
use core::time::Duration;

fn build_graph(
    asset_server: Res<AssetServer>,
    mut graphs: ResMut<Assets<AnimationGraph>>,
    mut commands: Commands,
) {
    let walk: Handle<AnimationClip> = asset_server.load("models/character.glb#Animation0");
    let emote: Handle<AnimationClip> = asset_server.load("models/character.glb#Animation1");

    let mut graph = AnimationGraph::new();
    let root = graph.root; // AnimationNodeIndex — the implicit blend root

    // Simple clip directly under root: weight 1.0, mask 0 (no masking)
    let _walk_node = graph.add_clip(walk, 1.0, root);

    // Additive subtree: an Add node at weight 0.5, then a masked clip beneath it
    let additive_node = graph.add_additive_blend(0.5, root);

    // Bit 0 = mask group 0.  Register LOWER-body bones into group 0 so this
    // node excludes them, leaving the emote to animate the upper body only.
    const LOWER_BODY_BIT: u64 = 1 << 0; // bit N set → group N is excluded
    let _emote_node = graph.add_clip_with_mask(emote, LOWER_BODY_BIT, 1.0, additive_node);

    let graph_handle = graphs.add(graph);

    commands.spawn((
        Name::new("AnimationRoot"),
        AnimationPlayer::default(),
        AnimationGraphHandle(graph_handle),
        AnimationTransitions::new(),
    ));
}
```

## Tree structure

```
root (Blend)
├── walk_node   (clip, weight=1.0, mask=0b00)
└── additive_node (Add, weight=0.5)
    └── emote_node  (clip, weight=1.0, mask=0b01 — excludes lower-body group 0)
```

Weights compose multiplicatively as the graph evaluates from root downward. An `Add` node's output is _added_ to its sibling contributions rather than blended. A `Blend` node (the root) averages its children weighted by their node weight.

## AnimationMask semantics

`AnimationMask` is a `u64` bitfield. Bit N set in a node's mask means that node will **not** animate targets registered in mask group N. This lets you exclude upper-body bones from a lower-body locomotion clip without a separate rig.

```rust
// Register a bone into group 0 on the graph:
let hips_id = AnimationTargetId::from_name(&Name::new("Hips"));
graph.add_target_to_mask_group(hips_id, 0_u32);

// A node with mask = 1 << 0 will skip Hips and any other group-0 bones.
let _masked_node = graph.add_clip_with_mask(clip_handle, 1 << 0, 1.0, root);
```

`add_target_to_mask_group` takes a `u32` group index; the graph internally stores this as a bitmask per bone.

## Runtime graph swap

Replace the `AnimationGraphHandle` component to switch graphs:

```rust
fn hot_swap_graph(
    mut commands: Commands,
    player_q: Query<Entity, With<AnimationPlayer>>,
    new_graph: Res<NewGraphHandle>,
) {
    if let Ok(entity) = player_q.single() {
        // Causes a one-frame discontinuity unless you simultaneously
        // call AnimationTransitions::play on a node in the new graph.
        commands.entity(entity).insert(AnimationGraphHandle(new_graph.0.clone()));
    }
}
```

Swap and immediately start a transition to prevent a pose snap. See `references/state-machines.md` for transition details.

## Gotchas

- `gltf_animation` is on by default in `bevy = "0.18"` — you don't need to opt in.
- `AnimationGraphHandle` must live on the **same entity** as `AnimationPlayer`, not on a bone child.
- Weights compose multiplicatively root-to-leaf; a node at weight 0.0 silences its entire subtree.
- `add_additive_blend` creates an `Add` node; `add_clip` under root creates a `Blend` (weighted average) child.

## See also

- [`../SKILL.md`](../SKILL.md) — top-level bevy-animation skill
- [`state-machines.md`](state-machines.md) — `AnimationTransitions::play` and cross-fades
- [`gltf-import.md`](gltf-import.md) — loading clips from `.glb` and `AnimationTargetId` matching
