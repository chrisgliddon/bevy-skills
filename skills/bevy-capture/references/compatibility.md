# `bevy_capture` compatibility with Bevy 0.19

`bevy_capture 0.6.0` declares `bevy = "0.19.0"` and requires no source patch.
The compatible public shape is:

- `CapturePlugin`
- `CaptureBundle { capture, camera_source }`
- `RenderTargetHeadless` implemented for `bevy::camera::RenderTarget`
- `Capture::{start, pause, resume, stop, is_capturing, is_paused}`
- feature-gated encoder modules under `bevy_capture::encoder`

Do not reuse guidance for `bevy_capture 0.4.x`. That release targeted Bevy
0.17 and used a helper attached to `Camera`; local forks created for Bevy 0.18
should be removed when moving to 0.19.

For the authoritative implementation and example, use:

- <https://docs.rs/bevy_capture/0.6.0/bevy_capture/>
- <https://github.com/jannik4/bevy_capture/blob/v0.6.0/examples/simple.rs>

## See also

- [`SKILL.md`](../SKILL.md) — canonical capture setup.
- [`encoders.md`](encoders.md) — encoder tradeoffs.
