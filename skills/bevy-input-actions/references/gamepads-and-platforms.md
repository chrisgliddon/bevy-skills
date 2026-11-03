# Gamepads, hot-plugging, and platform layers

## Entity-based lifecycle

In Bevy 0.20, query `(Entity, &Gamepad)` for connected devices. Connection changes
arrive through `GamepadConnectionEvent`. `GamepadEvent` preserves relative ordering
among the gamepad connection/button/axis message variants.

`GamepadSettings` is a component and can remain on the entity through disconnect so
calibration is reused if that same Bevy device entity reconnects. Still keep your
player-slot policy explicit:

- assign only after an intentional join action;
- retain a disconnected player's slot and show recovery UI;
- do not let “first gamepad in query order” take over an existing player;
- offer keyboard/controller sharing only when the game design supports it;
- persist a platform/device fingerprint only as a preference, never as a guarantee.

ECS entity IDs are process-local and must not enter config or save files.

## Axis filtering

Start with Bevy's `GamepadSettings`, then expose user-facing calibration where the
game needs it. For a stick vector, prefer a radial deadzone so diagonals are not
distorted by independent square deadzones:

```text
if length <= inner: output = 0
else:
    magnitude = clamp((length - inner) / (outer - inner), 0, 1)
    output = normalize(raw) * response_curve(magnitude)
```

Apply inversion/sensitivity after calibration. Trigger axes normally need one-sided
calibration. Record raw and filtered values in a controller diagnostics screen so
drift and inaccessible thresholds can be diagnosed without guesswork.

## Steam Deck and Steam Input

Treat Steam Input as a platform action layer, not merely another hard-coded Xbox
layout. Keep its action IDs aligned with the game's logical action IDs and action
sets. Support simultaneous mouse-like and controller input because trackpad/gyro may
emit mouse motion while face buttons remain gamepad inputs.

For camera/gyro actions, Steam recommends `absolute_mouse` when appropriate rather
than pretending the input is a stick. Provide platform glyphs from the active action
origin, switch prompt families without flicker, and ensure touch menus/action layers
do not bypass the in-game remapping/accessibility policy.

Validate on a physical Steam Deck:

- cold boot, suspend/resume, dock/undock, and controller reorder;
- trackpad plus buttons simultaneously;
- gyro enable/disable and sensitivity;
- external controller hot-plug during play and menus;
- focus loss/overlay transitions;
- save/reload of both Steam Input and in-game bindings.

Primary references:

- [Bevy gamepad input](https://docs.rs/bevy/0.20.1/bevy/input/gamepad/index.html)
- [Steam Input developer guide](https://partner.steamgames.com/doc/features/steam_controller/getting_started_for_devs)
- [Steam Input action manifest](https://partner.steamgames.com/doc/features/steam_controller/action_manifest_file)

## Adaptive controllers

Xbox Adaptive Controller, Access controller, switch interfaces, remapping middleware,
and OS-level virtual devices may present as ordinary gamepads, keyboards, or multiple
devices. Do not identify accessibility hardware by a brittle name allowlist. Make the
action layer device-agnostic, permit mixed-device control where safe, and test the
exact hardware/OS/platform path used by players.
