# Logical actions and rebinding

## Persist meaning, not Rust layout

Give each action an immutable namespaced string ID. Code can map IDs to a dense enum
or index at load time, but save data should survive enum reordering and new actions:

```rust
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize, Eq, Hash, PartialEq, Serialize)]
#[serde(transparent)]
struct ActionId(String);

#[derive(Clone, Debug, Deserialize, Serialize)]
enum Binding {
    Key { code: String },
    MouseButton { button: String },
    GamepadButton { button: String },
    GamepadAxis {
        axis: String,
        direction: AxisDirection,
        threshold: f32,
    },
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
enum AxisDirection {
    Negative,
    Positive,
}
```

Do not serialize debug output from `KeyCode`, `GamepadButton`, or an ECS `Entity` as
an undocumented format. Define a versioned binding DTO and an explicit conversion
table. Preserve unknown action/binding records where practical so downgrades or
temporarily absent devices do not erase user configuration.

## Separate layers

- **Action definition:** stable ID, value type (button/axis/vector), localisation key,
  essential/nonessential classification, and accessibility constraints.
- **Binding:** physical source, modifiers/chord policy, device class or device slot,
  threshold, inversion, sensitivity, and optional context.
- **Calibration:** per-device deadzones/ranges; not duplicated in every binding.
- **Runtime state:** held/axis values and ordered edges; never serialized as config.

Use action sets/contexts such as `gameplay`, `menu`, `vehicle`, and `photo_mode`.
Define whether contexts stack or replace one another. Always retain a reachable menu
back/confirm path when rebinding or switching sets.

## Rebinding transaction

1. Enter capture mode from a known input path.
2. Ignore the input that opened capture until it is released.
3. Accept the next eligible physical input above calibrated noise thresholds.
4. Show the proposed binding and every conflict before committing.
5. Apply an explicit policy: swap, unbind old, allow duplicate, or cancel.
6. Verify required actions remain reachable for the current device class.
7. Save atomically and update prompts immediately.
8. Offer reset for one action, one context, one device, or all defaults.

Do not globally forbid duplicate bindings: accessibility setups often intentionally
map multiple actions to one switch. Warn about conflicts, distinguish simultaneous
contexts from mutually exclusive contexts, and let product requirements decide which
duplicates are unsafe.

## Accessibility requirements

- Do not require simultaneous chords, repeated tapping, long holds, or analogue-only
  precision for essential progress without a configurable alternative.
- Support toggle/hold alternatives and adjustable hold/double-tap timing.
- Allow independent X/Y inversion and sensitivity for camera/aim axes.
- Expose deadzone settings and test low-force switches and one-handed layouts.
- Never encode colour, glyph shape, vibration, or sound as the only prompt signal.
- UI navigation, pause, accessibility settings, and confirmation/cancel must be
  operable with the same remapped device, without reaching for a mouse.

See [`bevy-a11y`](../../bevy-a11y/SKILL.md) for the broader evidence matrix.
