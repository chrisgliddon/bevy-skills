# Input and adaptive controllers

## Action-first architecture

Gameplay consumes semantic actions such as `Move`, `Confirm`, `Pause`, and
`UseAbility`, never raw keyboard/gamepad controls. A binding layer combines input from
assigned devices and emits action state. This enables remapping, prompts, replays,
networking, and accessibility alternatives without forking gameplay systems.

For each action, store:

- context and priority;
- zero or more bindings per device family;
- activation mode (press, release, hold, toggle, axis, sequence);
- thresholds, deadzones, sensitivity, inversion, and curves;
- conflict policy;
- whether the action is essential and its accessible alternatives;
- localized action name and current prompt representation.

Never serialize localized key names as identity. Persist stable action/control IDs and
format prompts at runtime.

## Adaptive controller behavior

Adaptive and custom controllers may expose ordinary buttons/axes or
`GamepadButton::Other(u32)` / `GamepadAxis::Other(u32)` (`u8` before 0.20). Therefore:

- capture unknown controls during rebinding;
- bind by observed input, not a fixed list of “supported controllers”;
- tolerate sparse controllers, duplicate controls, and no analog sticks;
- support hotplug without losing the current menu or assignment;
- allow more than one gamepad plus keyboard/switch inputs to control one player;
- avoid mandatory left/right-hand assumptions;
- keep platform-reserved buttons out of remapping;
- test real devices, hubs, switches, remappers, and reconnect paths.

Do not identify an “adaptive controller mode” from vendor/product IDs. Capabilities and
player-chosen bindings are the reliable contract.

## Device-lab coverage

Virtual input and a standard gamepad are insufficient evidence. Maintain real test
configurations that include:

- an Xbox Adaptive Controller with external switches/joysticks, multiple simultaneous
  inputs, hardware/app profiles, and Windows or Xbox target behavior;
- a PlayStation Access controller with different orientations, deadzones, toggle and
  simultaneous-press mappings, expansion switches, and paired Access/DualSense or two-
  Access-controller operation on a PS5 target build;
- a sparse one-switch setup, keyboard plus controller, two controllers assigned to one
  player, unknown HID controls, stick drift, reconnects, and profile changes while the
  game is running.

Platform/hardware remapping may present a normalized virtual controller rather than the
physical topology. The game should consume those standard actions without vendor gates,
while its own prompts, rebinding, mechanic alternatives, and recovery paths continue to
work. Console SDK input and certification work remains platform-specific and is outside
public Bevy/Winit support.

## Mechanical alternatives

| Barrier | Required alternative |
|---|---|
| Hold | toggle or adjustable hold duration |
| Repeated/mash input | hold, toggle, or automatic completion |
| Simultaneous chord | sequential mode or single-action binding |
| Tight timing | adjustable window, slowdown, retry/checkpoint, or automation |
| Analog precision | deadzone/sensitivity/curve plus digital step input |
| Two-stick control | one-stick/camera assist/lock-on or alternate navigation |
| Long traversal | autorun/autodrive/path assist where compatible |
| Aiming | aim assist, snap/lock, slowdown, target cycling, sensitivity by axis |

These alternatives must work in tutorials, QTEs, minigames, vehicles, menus, and boss
mechanics—not only the primary locomotion loop.

## Bevy 0.20 details

- Native discovery uses `bevy_gilrs`; the `gamepad` feature only enables APIs.
- Connected controllers are entities with `Gamepad` and `GamepadSettings` components.
- Connection/button/axis changes are messages such as `GamepadConnectionEvent`.
- Query each `Gamepad` component or consume messages; do not use pre-0.17 events APIs.
- Tune per-device `GamepadSettings`, but expose player-facing deadzone and sensitivity
  separately from hardware normalization.
- Aggregate assigned device entities before gameplay reads an action.

`leafwing-input-manager 0.22` (pins Bevy `^0.20`) can provide an action mapping layer.
Its `gamepad` feature enables `bevy/bevy_gilrs`. Audit its defaults and build accessible binding
UI/persistence on top; installing a mapping crate is not controller accessibility.

## Rebinding UX

The flow must be navigable using the input being rebound. Include:

- restore defaults and cancel/recovery actions that cannot be stranded;
- conflict explanation and swap/unbind/keep choices;
- multiple bindings per action;
- reserved-control explanation;
- listening timeout that is adjustable or cancelable;
- filtering for stick drift while listening;
- prompt updates after bindings or active device change;
- import/export or profile slots where platform policy permits.

Test a fully remapped UI after restarting the game and migrating an older save.

## Source

- [XAG 107: Input](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/107)
- [Bevy 0.20 `Gamepad`](https://docs.rs/bevy/0.20.1/bevy/input/gamepad/struct.Gamepad.html)
- [`leafwing-input-manager 0.22`](https://docs.rs/leafwing-input-manager/0.22.0/leafwing_input_manager/)
- [Xbox Adaptive Controller](https://www.xbox.com/en-US/accessories/controllers/xbox-adaptive-controller)
- [PlayStation Access controller](https://www.playstation.com/en-us/accessories/access-controller/)
