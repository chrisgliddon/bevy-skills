---
name: bevy-input-actions
description: "Use when building Bevy 0.20 input with `InputSystems`, entity-based `Gamepad`/`GamepadSettings`, `AccumulatedMouseMotion`, or `CursorOptions`: rebindable actions, hot-plugging, deadzones, Steam Deck, accessibility controllers, and correct transfer into `FixedUpdate`."
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "2"
  area: input
  bevy_version: "0.20"
---

# Bevy 0.20 — input actions

## When to use this skill

- Gameplay needs device-neutral, persisted, rebindable actions and prompts.
- Controllers can hot-plug/reorder or multiple players/devices share input.
- Mouse capture, focus loss, Steam Deck, or adaptive hardware needs one policy.
- Frame-scoped edges/motion must drive deterministic `FixedUpdate` simulation.

Gameplay consumes logical actions, never raw keys or a hard-coded controller entity.
Translate Bevy's frame input into an action state once, then feed presentation and
fixed simulation from that state.

## Canonical pattern

Bevy updates raw input in `PreUpdate` inside `InputSystems`. Run the translator after
that set so `ButtonInput`, `Gamepad`, input messages, and accumulated mouse motion
represent the current frame:

```rust
use bevy::{input::InputSystems, prelude::*};

fn install_input(app: &mut App) {
    app.init_resource::<ActionBuffer>().add_systems(
        PreUpdate,
        translate_physical_input.after(InputSystems),
    );
}

#[derive(Resource, Default)]
struct ActionBuffer;

fn translate_physical_input(mut _actions: ResMut<ActionBuffer>) {}
```

```text
keyboard / mouse / touch / Gamepad entities / Steam Input
                     |
                     v
        physical bindings + device calibration
                     |
                     v
       active action set/context + conflict policy
                     |
                     v
       frame action state + ordered transition queue
              |                         |
        Update/UI consumers      fixed-tick bridge
```

Use stable serialized action IDs such as `gameplay.jump`, `menu.confirm`, and
`camera.look`. Bindings, labels, prompts, save data, and analytics refer to those IDs;
Rust enum discriminants and catalog order are not persistence contracts.

For an edge whose precise per-device-stream order matters, translate the underlying
keyboard, mouse, or gamepad messages into an ordered queue. A single `just_pressed`
boolean cannot represent two transitions or their order. Held state and filtered axes
may be stored as the latest values.

## Gamepads are entities in Bevy 0.20

```rust
fn inspect_gamepads(gamepads: Query<(Entity, &Gamepad)>) {
    for (entity, gamepad) in &gamepads {
        let move_x = gamepad.get(GamepadAxis::LeftStickX).unwrap_or(0.0);
        let jump_started = gamepad.just_pressed(GamepadButton::South);
        let _sample = (entity, move_x, jump_started);
    }
}
```

Use `GamepadConnectionEvent` for connection changes and `GamepadEvent` when relative
ordering among connection, button, and axis changes matters. Store active-player
assignment separately from bindings. An ECS `Entity` is a live device handle, not a
stable device identity or save-file key.

Configure per-device filtering through its `GamepadSettings` component. Apply an
inner deadzone, optional outer calibration, response curve, and final clamp once.
Do not apply a second hidden deadzone in gameplay code.

## Gotchas: frame input is not fixed-tick input

Raw input is frame-scoped; fixed simulation may run zero, one, or many ticks in that
frame. Therefore:

- retain ordered press/release transitions until a fixed tick consumes them;
- accumulate relative motion until that same tick;
- drain transitions and relative motion once, on the first available tick;
- copy held buttons and absolute axes to every fixed tick;
- never re-read `just_pressed` or `AccumulatedMouseMotion` independently in each
  `FixedUpdate` iteration.

For rollback/network simulation, convert the bridge output into an explicit command
frame keyed by simulation tick and retain it for replay.

### Mouse capture and focus

Capture through the primary window's `CursorOptions`: hide the cursor and request
`CursorGrabMode::Locked` when gameplay owns look input. On focus loss, pause or
neutralise gameplay input, release capture, synthesize required action releases, and
clear relative motion. Reacquire only from an intentional user gesture; never trap
the pointer merely because focus returned.

Keyboard state is released by Bevy on focus loss, while gamepad state is independent
of window focus. Your action layer still needs one policy that prevents stuck or
unexpected gameplay actions.

### Version traps

- 0.20: `GamepadButton::Other(u32)` / `GamepadAxis::Other(u32)` (were `u8`).
- 0.20: UI pointer events are flat. Write `On<PointerPress>` with
  `event.pointer.position`, not `On<Pointer<Press>>` with `pointer_location`.
- 0.20: `EntityCursor`, `DefaultCursor`, `CursorIconPlugin` live in
  `bevy::picking::cursor`; the `custom_cursor` feature belongs to `bevy_picking`.
  `CursorOptions` (grab mode, visibility) is still a window-entity component:
  `Single<&mut CursorOptions, With<PrimaryWindow>>`.
- 0.20: `chain_weak` relaxed several built-in schedules; `PreUpdate`/`InputSystems`
  is not one of them, and `.after(InputSystems)` is still a strict edge.
- 0.19: `InputFocus` fields are private (`set`/`get`/`clear`), and
  `bevy_input_focus` is no longer implied by the `picking` feature.
- 0.18+: connection changes are messages: `MessageReader<GamepadConnectionEvent>`,
  not `EventReader`.

## Choose the relevant deep dive

| Problem | Read |
|---|---|
| Stable actions, binding grammar, contexts, rebinding and conflicts | [Actions and rebinding](references/action-model-and-rebinding.md) |
| Device assignment, hot-plug, deadzones, Steam Deck and adaptive hardware | [Gamepads and platforms](references/gamepads-and-platforms.md) |
| Edge queues, mouse accumulation, zero/multiple fixed ticks, rollback | [Fixed-step buffering](references/fixed-step-buffering.md) |

## Review checklist

- Every gameplay operation is bindable through a named action, including menu and
  accessibility paths; essential actions offer alternatives to chords/holds.
- Prompts resolve the active binding and device glyph rather than naming a key.
- Disconnecting one controller does not silently transfer its player to another.
- Press+release between two fixed ticks is delivered, exactly once, in order.
- Mouse motion is neither lost on a zero-tick frame nor multiplied on catch-up ticks.
- Focus loss cannot leave a held action or captured pointer stuck.
- Steam Deck and adaptive-controller testing uses real hardware and saved rebinding.

## See also

- [`bevy-a11y`](../bevy-a11y/SKILL.md) — action accessibility and controller acceptance criteria.
- [`bevy-core-concepts`](../bevy-core-concepts/SKILL.md) — `PreUpdate`, `Update`, and `FixedUpdate`.
- [`bevy-testing`](../bevy-testing/SKILL.md) — deterministic fixed-step input tests.
- [`bevy-migration-0-19-to-0-20`](../bevy-migration-0-19-to-0-20/SKILL.md) — cursor module move, flat pointer events.
- [Bevy gamepad module](https://docs.rs/bevy/0.20.1/bevy/input/gamepad/index.html)
