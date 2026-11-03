# bevy-capture — porting 0.6.0 to Bevy 0.20

> Referenced from `bevy-capture/SKILL.md § Compatibility status`.

`bevy_capture` 0.6.0 (latest on crates.io as of 2026-11-03) declares `bevy = "0.19.0"`.
Cargo cannot unify that with a Bevy 0.20 app, so you get a duplicate Bevy and type
errors such as `expected bevy::app::App, found bevy_app::App`. Fix it with a fork and a
`[patch.crates-io]` entry until upstream (`jannik4/bevy_capture`) publishes a 0.20 build.

## What the crate touches

The library is two files (`src/lib.rs`, `src/render_world.rs`) plus encoders. Every
Bevy symbol it uses still exists in Bevy 0.20.1 (checked against the 0.20.1 sources):

| Symbol | 0.20.1 location | Status |
|---|---|---|
| `bevy::camera::RenderTarget`, `ImageRenderTarget` | `bevy_camera` | unchanged |
| `Image::new_fill`, `TextureUsages::COPY_SRC` | `bevy_image` / wgpu-types 30 | unchanged |
| `ExtractSchedule`, `Extract<Query<..>>`, `RenderApp`, `Render`, `RenderSystems::Render` | `bevy_render` | unchanged |
| `RenderGraph` schedule, `RenderGraphSystems::{Render, Submit}` | `bevy::render::renderer` | unchanged |
| `RenderContext` as a system parameter | `bevy::render::renderer` | unchanged (0.19 render-systems API) |
| `RenderAssets<GpuImage>`, `RenderDevice::align_copy_bytes_per_row` | `bevy_render` | unchanged |
| `PollType::wait_indefinitely()` | wgpu-types 30.0.1 | unchanged |
| `TextureFormatPixelInfo::pixel_size` | `bevy_image` | returns `Result` (already handled with `.expect`) |

The crate does not use `ExtractComponent`, `SyncComponent`, `WgpuWrapper`,
`ShaderStorageBuffer`, custom shaders or `ViewTarget`, so the headline 0.20 breakages
(WESL, `#[extract_app(RenderApp)]`, `WgpuWrapper` removal) do not apply.

## Expected port

1. Fork, change `bevy = "0.19.0"` to `bevy = "0.20.0"` in `Cargo.toml` (keep the feature
   list: `bevy_image`, `bevy_render`, `bevy_core_pipeline`, `bevy_asset`, `bevy_log`).
2. `cargo check --features mp4_openh264,mp4_ffmpeg_cli,mp4_ffmpeg_cli_pipe,gif`.
3. Fix whatever the compiler reports. Based on the symbol table above, expect zero or
   near-zero changes; this has not been compile-verified here, so treat it as a
   starting point rather than a guarantee.
4. Point your app at the fork:

```toml
[patch.crates-io]
bevy_capture = { git = "https://github.com/<your-fork>/bevy_capture", branch = "bevy-0.20" }
# or a local checkout:
# bevy_capture = { path = "vendor/bevy_capture" }
```

Pin the crates.io version again as soon as a release with `bevy = "0.20"` appears
(check with `curl -s -A bevy-skills https://crates.io/api/v1/crates/bevy_capture`).

## History: the old Bevy 0.18 patch

Earlier versions of this skill carried a three-line local patch to build 0.4.1 on
Bevy 0.18 (`Camera::target_headless` returning `(Camera, RenderTarget)`,
`PollType::wait_indefinitely`, `MessageWriter<AppExit>`). That patch is obsolete:
`bevy_capture` 0.5.0 (2026-06-27) supports Bevy 0.18 natively and replaced
`CameraTargetHeadless` with `RenderTargetHeadless` on `RenderTarget`. Do not resurrect
the tuple-returning `target_headless`; it never existed upstream.

## See also

- [`SKILL.md`](../SKILL.md) — dispatcher.
- [`encoders.md`](encoders.md) — encoder comparison.
