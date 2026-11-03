# Accessibility tooling

The bundled scripts use Python's standard library and JSON so they run in CI without
additional packages. They implement project policy checks, not certification.

## Input manifest

```json
{
  "version": 1,
  "required_devices": ["keyboard", "gamepad"],
  "settings": {
    "hotplug": true,
    "simultaneous_devices": true,
    "multiple_devices_per_player": true,
    "prompt_updates": true,
    "capture_unknown_controls": true,
    "adjustable_deadzone": true,
    "adjustable_sensitivity": true,
    "invert_axes": true
  },
  "actions": [
    {
      "id": "move",
      "contexts": ["gameplay"],
      "essential": true,
      "remappable": true,
      "input_kind": "analog_2d",
      "digital_alternative": true,
      "bindings": [
        {"device": "keyboard", "control": "WASD"},
        {"device": "gamepad", "control": "LeftStick"}
      ]
    },
    {
      "id": "interact",
      "contexts": ["gameplay"],
      "essential": true,
      "remappable": true,
      "demands": ["hold"],
      "alternatives": ["toggle"],
      "bindings": [
        {"device": "keyboard", "control": "KeyE"},
        {"device": "gamepad", "control": "South"}
      ]
    }
  ]
}
```

```sh
python3 scripts/audit_input_map.py accessibility/input-map.json --strict
```

The auditor checks essential action/device coverage, remappability, duplicate
bindings, analog alternatives, settings, and alternatives for holds, mashing, chords,
and tight timing.

## Caption validation

```sh
# Use sync checking when every locale captions the same source-audio timing.
python3 scripts/validate_captions.py \
  captions/en-US.vtt captions/fr-FR.vtt --strict --max-cps 20
```

The validator parses WebVTT and SRT, checks time order/duration/overlap, reading speed,
line count/length, and (by default) localized cue timing/count. Pass `--no-sync-check`
when dubbed tracks have intentionally different timing. Reading-speed and line limits
are editable product policies; human review decides line breaks, speaker/sound context,
spoilers, placement, and translation quality.

## Contrast validation

```json
{
  "pairs": [
    {
      "id": "primary-button-label",
      "foreground": "#FFFFFF",
      "background": "#153A5B",
      "kind": "text",
      "large_text": false,
      "target": "AAA"
    },
    {
      "id": "keyboard-focus-ring",
      "foreground": "#FFE066",
      "background": "#153A5B",
      "kind": "non_text"
    }
  ]
}
```

```sh
python3 scripts/check_contrast.py accessibility/contrast.json --strict
```

Every visual state and theme needs a pair. For gradients, video, translucent panels,
HDR, and world-space UI, sample representative worst-case backgrounds and perform
in-engine review; a design-token pair is insufficient.

## CI

```sh
python3 skills/bevy-a11y/scripts/audit_input_map.py accessibility/input-map.json --strict
python3 skills/bevy-a11y/scripts/validate_captions.py captions/*.vtt --strict
python3 skills/bevy-a11y/scripts/check_contrast.py accessibility/contrast.json --strict
```

Store machine-readable output with `--json` as release evidence where supported.
