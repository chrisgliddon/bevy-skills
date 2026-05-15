# bevy-animation — Performance Tuning for bevy_animation

> Referenced from `bevy-animation/SKILL.md § Topics`.

## Cost model

Animation cost in Bevy 0.18 has three layers:

| Layer | Driver | Scales with |
|---|---|---|
| CPU — graph evaluation | `AnimationPlayer` count | Characters × graph depth |
| CPU — transform write | `animate_targets` | Bones per character × characters |
| GPU — skinning | `MeshSkinning` shader | Joints × vertices × draw calls |

Each concurrently animating character adds one `AnimationPlayer` evaluation per frame. There is no pooling or LOD — every active player evaluates its full graph every tick.

## Skeleton size

Per-character GPU skinning cost scales with joint count. Each joint contributes a `mat3x4` to the skin uniform buffer (roughly 48 bytes), uploaded every frame the mesh is visible.

- **< 50 joints**: low cost; no special handling needed.
- **50–100 joints**: moderate. Profile with `bevy_dev_tools` system timing.
- **> 100 joints**: significant GPU upload pressure. Consider:
  - Splitting the character into separate meshes with smaller sub-skeletons.
  - Hiding (despawning or disabling visibility on) off-screen characters rather than pausing the player.

## AnimationGraph complexity

More nodes, deeper trees, and more active blend weights all increase per-frame evaluation work.

Flatten where possible:

```
Prefer:                     Avoid:
root                        root
├── idle_node               └── blend_A
├── walk_node                   ├── blend_B
└── run_node                    │   └── idle_node
                                └── blend_C
                                    ├── walk_node
                                    └── run_node
```

Branches under a node with weight 0.0 are still evaluated for transform contribution — they are not short-circuited. Remove unused branches from the graph rather than zeroing their weight if they are permanently inactive.

## AnimationMask to skip bone evaluation

Mask groups let you skip `animate_targets` work for selected bones in a given node. Use this to prevent upper-body animation from wasting time writing lower-body bone transforms (or vice versa) when the bones are masked anyway:

```rust
// Register lower-body bones into group 1
graph.add_target_to_mask_group(hips_id, 1);
graph.add_target_to_mask_group(left_leg_id, 1);

// Upper-body node excludes group 1 — saves transform writes for those bones
let upper_node = graph.add_clip_with_mask(upper_clip, 1 << 1, 1.0, root);
```

## Runtime graph swaps

Replacing `AnimationGraphHandle` mid-play causes a one-frame discontinuity:

```rust
// Bad: raw swap
commands.entity(player).insert(AnimationGraphHandle(new_graph));

// Better: swap and immediately start a transition to a node in the new graph
commands.entity(player).insert(AnimationGraphHandle(new_graph.clone()));
// Then in the same tick, call transitions.play(...) to new_node with a short duration
```

Hot-swapping is useful for radically different rigs (e.g., biped → vehicle). For state changes within the same rig, prefer changing node weights or using `AnimationTransitions::play`.

## RepeatAnimation cost

`RepeatAnimation::Forever` and `RepeatAnimation::Count(n)` have the same per-frame evaluation cost. The difference is only in when the player stops advancing the clip timestamp. Long clips with many keyframes cost more per `animate_targets` call because more samples must be interpolated — this is content complexity, not repeat mode cost.

## Where to measure

Animation systems run in `PostUpdate`, ordered before `TransformSystems::Propagate`. Use `bevy_dev_tools` system timing UI (`bevy::dev_tools::states::*` or the diagnostics plugin) to identify animation hotspots:

```rust
app.add_plugins(bevy::dev_tools::fps_overlay::FpsOverlayPlugin::default());
```

For frame-level profiling, enable the `trace` feature and capture a trace with `cargo run --features bevy/trace`. Look for `animate_targets`, `advance_animations`, and `advance_transitions` spans.

## Gotchas

- There is no built-in animation LOD system — it must be implemented at the application level (e.g., pause `AnimationPlayer` for characters far from the camera).
- `animate_targets` runs per-bone, not per-mesh — skinned meshes with many vertices don't affect CPU animation cost, only GPU skinning cost.
- Pausing an `AnimationPlayer` (via `player.pause()`) stops CPU evaluation but does NOT stop the GPU skinning draw call for visible meshes.

## See also

- [`../SKILL.md`](../SKILL.md) — top-level bevy-animation skill
- [`animation-graph.md`](animation-graph.md) — graph structure and mask group setup
- [`state-machines.md`](state-machines.md) — `AnimationTransitions::play` for hot-swap bridging
