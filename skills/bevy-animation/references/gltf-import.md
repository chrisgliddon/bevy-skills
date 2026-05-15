# bevy-animation — glTF/GLB Animation Import

> Referenced from `bevy-animation/SKILL.md § Topics`.

## Loading a clip

```rust
fn setup(asset_server: Res<AssetServer>, mut commands: Commands) {
    // Fragment syntax: #Animation0, #Animation1, … (zero-indexed, order from glTF asset)
    let walk: Handle<AnimationClip> = asset_server.load("models/character.glb#Animation0");
    let run:  Handle<AnimationClip> = asset_server.load("models/character.glb#Animation1");
    let _ = (walk, run);
}
```

Multi-clip GLBs export each Blender action as a separate index. If only one action exists, use `#Animation0`.

## AnimationTargetId matching

The glTF loader emits a `Name` component on every bone entity. `AnimationTargetId` is computed from those names — the IDs in your clip must match.

```rust
use bevy::{animation::AnimationTargetId, prelude::*};

// Single bone by name:
let hips_id = AnimationTargetId::from_name(&Name::new("Hips"));

// Nested path (parent → child chain), matches how the glTF loader encodes IDs:
let foot_id = AnimationTargetId::from_iter(["Hips", "LeftLeg", "LeftFoot"]);
```

`from_iter` takes any `IntoIterator<Item: AsRef<str>>` and hashes the full path to a UUID. Use this when the same bone name appears at multiple levels of the hierarchy.

## Component layout after glTF load

```
Player entity
  AnimationPlayer
  AnimationGraphHandle(Handle<AnimationGraph>)
  AnimationTransitions       (optional, for crossfades)

  └── Bone entity ("Hips")
        Name("Hips")
        AnimationTargetId   (Uuid computed from name path)
        AnimatedBy(player_entity)
        Transform / GlobalTransform
```

`AnimationTargetId` and `AnimatedBy` live on **bone entities**, not the player entity. The glTF loader sets them automatically — you only need to add them manually for procedurally built rigs.

## Blender export checklist

1. **Apply Transform** (`Ctrl+A → All Transforms`) before export — unexploded transforms cause unexpected root motion offsets.
2. **Y-up axis**: enable "Convert axes" in the glTF exporter (on by default). Bevy is Y-up; Blender defaults to Z-up.
3. **Animations**: tick "Include → Animations" and choose "Actions" (single action per clip) or "NLA Tracks" for multi-clip GLBs.
4. **Single GLB** (`.glb`) is easiest — the loader resolves the buffer inline. Separate `.gltf` + `.bin` works too but requires both files at the same path.

## Scale and unit mismatches

Blender's default unit scale is 1 m = 1 m. If your character is 100 units tall instead of 1–2, check:

- Blender scene unit scale (Scene Properties → Unit Scale should be 1.0).
- glTF exporter "Apply Scalings" option.
- Whether a root `Transform::scale` is needed on the spawned scene to compensate.

## Gotchas

- `KHR_animation_pointer` (animating arbitrary glTF properties, e.g. material color) is **not implemented** in Bevy 0.18's glTF loader. Bone transform animation is fully supported; material animation via pointer extension is not.
- `gltf_animation` feature is enabled by default in `bevy = "0.18"` — no feature flag needed.
- `AnimationTargetId` changed representation in 0.18: it is now `AnimationTargetId(Uuid)`. Earlier tutorials using the old `AnimationTarget { id, player }` struct are stale.
- `AnimatedBy(Entity)` is a separate component from `AnimationTargetId` — both must be present on a bone entity for the animation system to drive it.

## See also

- [`../SKILL.md`](../SKILL.md) — top-level bevy-animation skill
- [`animation-graph.md`](animation-graph.md) — building graphs and attaching clip handles
- [`state-machines.md`](state-machines.md) — playing and cross-fading loaded clips
