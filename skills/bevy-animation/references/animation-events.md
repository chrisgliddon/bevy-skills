# bevy-animation — Animation Events for Gameplay Sync

> Referenced from `bevy-animation/SKILL.md § Topics`.

## Defining an event

```rust
use bevy::animation::AnimationEvent;

// Reflect is NOT required — AnimationEvent alone is sufficient.
#[derive(AnimationEvent, Clone)]
struct FootstepEvent {
    foot: u8, // 0 = left, 1 = right
}

#[derive(AnimationEvent, Clone)]
struct HitboxActivate {
    bone: &'static str,
    radius: f32,
}
```

Import `AnimationEvent` from `bevy::animation::AnimationEvent`, not from `bevy::prelude`. The derive macro handles all wiring.

## Attaching events to a clip

```rust
use bevy::{animation::AnimationTargetId, prelude::*};

fn build_clip_with_events() -> AnimationClip {
    let mut clip = AnimationClip::default();

    // add_event: fires on the AnimationPlayer entity at time_secs into the clip
    clip.add_event(0.5, FootstepEvent { foot: 0 }); // left foot at 0.5 s
    clip.add_event(1.0, FootstepEvent { foot: 1 }); // right foot at 1.0 s

    // add_event_to_target: fires on the bone entity matching the target ID
    let foot_id = AnimationTargetId::from_iter(["Hips", "LeftLeg", "LeftFoot"]);
    clip.add_event_to_target(foot_id, 0.8, HitboxActivate {
        bone: "LeftFoot",
        radius: 0.3,
    });

    clip
}
```

Use `add_event` when the handler only needs the player entity (e.g., audio, game state). Use `add_event_to_target` when the handler needs to act on a specific bone entity (e.g., attaching a particle to a foot socket).

## Observing events

```rust
use bevy::prelude::*;

fn on_footstep(trigger: On<FootstepEvent>) {
    // On<E> derefs to &E — access event fields directly:
    let foot = trigger.foot;

    // To get the entity that fired the event:
    // For AnimationEvent (uses AnimationEventTrigger), use trigger.trigger().target
    // NOT trigger.target() — that method is for EntityEvent, not AnimationEventTrigger.
    let _source_entity = trigger.trigger().target;

    match foot {
        0 => { /* play left footstep sound */ }
        _ => { /* play right footstep sound */ }
    }
}

fn on_hitbox(trigger: On<HitboxActivate>) {
    let bone = trigger.bone;
    let radius = trigger.radius;
    let entity = trigger.trigger().target;
    let _ = (bone, radius, entity);
    // spawn a collider child entity on `entity` for one frame
}

// Register observers in App::build:
// app.add_observer(on_footstep);
// app.add_observer(on_hitbox);
```

## Common patterns

| Pattern | Event placement | Handler action |
|---|---|---|
| Footstep SFX | `add_event` on player entity | Lookup terrain, play matching audio |
| Hitbox activation | `add_event_to_target` on bone | Spawn or resize a collider |
| Projectile fire | `add_event` on player entity | Spawn bullet from socket transform |
| VFX emission | `add_event_to_target` on hand bone | Spawn particle system at bone position |
| Dialogue cue | `add_event` on player entity | Trigger subtitle / voice line |

## Gotchas

- Events fire **after** `animate_targets` resolves the timestamp within the current tick — they are within-tick accurate but not exact-frame from the render perspective.
- `trigger.target()` is **not available** on `AnimationEventTrigger`. Use `trigger.trigger().target` instead. Attempting `.target()` will fail to compile because `AnimationEvent` uses `AnimationEventTrigger`, which is not `EntityEvent`.
- `Reflect` is **not required** on your event type. Adding it is harmless but unnecessary for event dispatch.
- If no observer is registered for an event type, the event fires silently with no error.
- Events on the clip timeline are sampled once per `advance_animations` call — scrubbing or seeking can cause events to fire out of order or be skipped.

## See also

- [`../SKILL.md`](../SKILL.md) — top-level bevy-animation skill
- [`gltf-import.md`](gltf-import.md) — `AnimationTargetId::from_iter` for nested bone paths
- [`state-machines.md`](state-machines.md) — coordinating state changes with animation transitions
