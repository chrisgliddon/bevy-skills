# bevy-animation — Staging, Follow Through & Secondary Action

> Referenced from `bevy-animation/SKILL.md § The 12 Basic Principles`.

These three are about *layering* — running multiple animations in parallel, isolating
which body parts each affects, and letting trailing parts catch up after the main
action stops. Bevy 0.18's `AnimationGraph` with additive blend nodes and
`AnimationMask` is the toolkit.

---

## Staging

Staging means presenting a single dominant action clearly, with no visual noise
competing for the viewer's eye. In 3D, this often means restricting a motion to one
body region (face, arm, torso) while the rest holds.

`AnimationMask` (a `u64` bitfield) isolates which bone groups a node animates.
**Bit N set in a node's mask = that node will NOT animate bones in group N.**

To make a clip node animate *only* the face group, set all bits except face's bit:

```rust
const FACE_GROUP: u32 = 0;
// Bit 0 clear = face IS animated by this node.
// All other bits set = all other groups are excluded from this node.
const FACE_ONLY_MASK: u64 = !(1u64 << FACE_GROUP); // = 0xFFFF_FFFF_FFFF_FFFE

let mut graph = AnimationGraph::new();
let root = graph.root;

// Register the face bone into group 0 on the graph.
// Only bones registered here are affected by mask checks.
graph.add_target_to_mask_group(face_bone_id, FACE_GROUP);

// This node animates ONLY face group bones;
// all other groups are masked out.
let _emote_node = graph.add_clip_with_mask(
    emote_handle,
    FACE_ONLY_MASK,
    1.0,
    root,
);
```

**Staging tip:** pair masking with `AnimationTransitions::play` so the emote fades in
smoothly without disturbing the body's locomotion layer.

---

## Follow Through & Overlapping Action

A character stops running — their cape and hair keep moving for a moment, then settle.
Follow through is the trailing motion; overlapping action is starting secondary
elements at different times so they don't all stop simultaneously.

In Bevy, implement this by starting a secondary clip slightly before the primary stops,
using a long transition duration so the blend eases out naturally:

```rust
use core::time::Duration;

// Primary locomotion clip transitions out.
// Long duration keeps the cape clip audible as it fades.
transitions
    .play(&mut player, cape_settle_node, Duration::from_millis(600))
    .set_speed(0.8);  // slower speed = longer settle

// The cape_settle clip is authored with decaying oscillation;
// the long transition fades it out smoothly after body stops.
```

For overlapping action, build separate clips for each trailing body part (hair, cape,
ears) and start them at slightly staggered timestamps using multiple
`AnimationTransitions::play` calls — Bevy blends them together.

---

## Secondary Action

A secondary action supports and reinforces the primary without competing with it — eye
blinks during dialogue, breathing during an idle, subtle hand fidgets during a walk.
Additive blend nodes are the right tool: the secondary clip's transform *delta* is
added on top of whatever the primary produces.

```rust
let mut graph = AnimationGraph::new();
let root = graph.root;

// Primary: full-body walk cycle
let _walk = graph.add_clip(walk_handle, 1.0, root);

// Secondary: additive node at 50% weight, with eye-blink clip under it.
// The additive node is a container — it has no clip of its own.
// Its child clip's deltas are blended additively at the given weight.
let additive = graph.add_additive_blend(0.5, root);
let _eye_blink = graph.add_clip(eye_blink_handle, 1.0, additive);
```

**How additive blending works:** the child clip's output (translation/rotation/scale
relative to the bind pose) is multiplied by the additive node's weight and *added* to
the blended output of sibling nodes. The secondary action never overrides the primary;
it layers on top.

**Weight 0.5** = half-amplitude secondary. Dial it based on how subtle or emphatic
the secondary should read.

---

## Gotchas

- **Mask bit polarity is "exclude", not "include".** Bit N set → group N is excluded
  from this node. A mask of `0` = animate all groups. A mask of `!0` = animate no
  groups (effectively silent).
- **`add_additive_blend` creates a container node, not a clip node.** Do not call
  `add_clip` on the container itself — add child clip nodes *under* the additive
  parent via `graph.add_clip(handle, weight, additive_parent_index)`.
- **Weights compose multiplicatively down the graph.** An additive node at weight 0.5
  with a child clip at weight 1.0 contributes 0.5 of that clip's delta. A child
  at weight 0.5 under it would contribute 0.25 total.
- **Bone names must match across clips.** For two clips to layer correctly, the
  `AnimationTargetId` (derived from `Name` on each bone entity) must match. Naming
  inconsistencies between clips silently skip layering on mismatched bones.
- **`AnimationTransitions` plays one transition at a time per call.** Multiple calls
  to `play` on the same `AnimationTransitions` will interrupt each other; manage
  distinct secondary layers as separate graph nodes rather than separate transition
  calls if you need them to coexist.

---

## See also

- [`../SKILL.md`](../SKILL.md) — canonical pattern and full trigger list
- [`animation-graph.md`](animation-graph.md) — full `AnimationGraph` construction,
  node types, and weight semantics
- [`state-machines.md`](state-machines.md) — managing clip transitions with
  `AnimationTransitions`
