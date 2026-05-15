---
name: bevy-capture
description: Use when adding `CapturePlugin` to record a `Camera3d` or `Camera2d` to video, spawning `CaptureBundle` on a camera entity, calling `Capture::start` with `Mp4Openh264Encoder` for in-process MP4 encoding, using `Mp4FfmpegCliEncoder` or `Mp4FfmpegCliPipeEncoder` for ffmpeg-backed output, or writing per-frame PNGs with `FramesEncoder` in Bevy 0.18.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "4"
  area: render
  bevy_version: "0.18"
---

# bevy-capture — recording Bevy 0.18 cameras to MP4 or PNG sequences

## Compatibility status

`bevy_capture` 0.4.1 (the latest crates.io release as of this writing) **pins `bevy = "^0.17.2"`** upstream. For Bevy 0.18 you need three small patches against the published source — see [`references/bevy-0-18-patch.md`](references/bevy-0-18-patch.md). The API surface documented here is what the patched crate exposes, which is identical to upstream apart from `target_headless` returning a tuple.

When upstream publishes a Bevy 0.18 release, drop the patch and pin a new version. The snippet below is verified to compile against `bevy_capture = "0.4.1"` + the patch on `bevy = "0.18"`.

## When to use this skill

- Recording a gameplay clip or cinematic from a `Camera3d` or `Camera2d`.
- Generating MP4 files for trailers or automated screenshot tests.
- Capturing a PNG-per-frame sequence for offline compositing or GIF export.
- Choosing between in-process H.264 (`Mp4Openh264Encoder`) and ffmpeg-CLI encoders (`Mp4FfmpegCliEncoder`, `Mp4FfmpegCliPipeEncoder`).
- Hitting "ffmpeg not found" or "cannot find type `Mp4Openh264Encoder`" because a Cargo feature wasn't enabled.
- Wanting to stop and flush a recording mid-session via `Capture::stop()`.

## Canonical pattern

```toml
# Cargo.toml
[dependencies]
bevy = "0.18"
# Pick the features for the encoders you use; FramesEncoder needs none.
bevy_capture = { version = "0.4.1", features = ["mp4_openh264"] }

# Required until bevy_capture ships a native 0.18 release — see references/bevy-0-18-patch.md
[patch.crates-io]
bevy_capture = { path = "vendor/bevy_capture" }  # local fork with the 3 patches applied
```

```rust
use bevy::prelude::*;
use bevy_capture::{
    CameraTargetHeadless, Capture, CaptureBundle, CapturePlugin,
    encoder::{
        frames::FramesEncoder,
        mp4_ffmpeg_cli::Mp4FfmpegCliEncoder,
        mp4_ffmpeg_cli_pipe::Mp4FfmpegCliPipeEncoder,
        mp4_openh264::Mp4Openh264Encoder,
    },
};
use std::fs;

fn main() {
    App::new()
        .add_plugins((DefaultPlugins, CapturePlugin))
        .add_systems(Startup, setup)
        .add_systems(Update, drive_capture)
        .run();
}

// ① Spawn a Camera with `CaptureBundle`. For an off-screen recording
//    use `target_headless` which (in Bevy 0.18) returns the *pair* of
//    components `(Camera, RenderTarget)` — `RenderTarget` is now a
//    separate required component, no longer a field on `Camera`.
fn setup(mut commands: Commands, mut images: ResMut<Assets<Image>>) {
    let (camera, render_target) =
        Camera::default().target_headless(1920, 1080, &mut images);

    commands.spawn((
        Camera2d,                 // or Camera3d
        camera,
        render_target,
        CaptureBundle::default(),
    ));
}

// ② Call `Capture::start(encoder)` once you're ready to record.
//    The render loop encodes every subsequent frame until `stop()`.
fn drive_capture(
    mut q: Query<&mut Capture>,
    mut started: Local<bool>,
    mut stopped: Local<bool>,
    mut frame: Local<u32>,
) {
    let Ok(mut capture) = q.single_mut() else { return };

    if !*started {
        *started = true;
        fs::create_dir_all("captures").ok();

        // Pick ONE encoder. All four implement `Encoder`.

        // A) Mp4Openh264Encoder — in-process H.264, NO shell-out, no system ffmpeg.
        capture.start(
            Mp4Openh264Encoder::new(
                fs::File::create("captures/out.mp4").unwrap(), 1920, 1080,
            ).expect("openh264 init"),
        );

        // B) Mp4FfmpegCliEncoder — collects frames, shells out to `ffmpeg` once at stop.
        // capture.start(
        //     Mp4FfmpegCliEncoder::new("captures/out.mp4")
        //         .expect("tempdir").with_framerate(30).with_crf(23),
        // );

        // C) Mp4FfmpegCliPipeEncoder — pipes raw frames to a long-running ffmpeg child.
        // capture.start(
        //     Mp4FfmpegCliPipeEncoder::new("captures/out.mp4")
        //         .expect("spawn ffmpeg").with_framerate(30).with_crf(18),
        // );

        // D) FramesEncoder — one PNG per frame into a directory; no encoding.
        // capture.start(FramesEncoder::new("captures/frames"));
    }

    *frame += 1;

    // ③ Stop flushes the encoder (calls `Encoder::finish` on drop).
    //    Guard with `stopped` so `capture.stop()` is called only once —
    //    repeated calls may double-flush a pipe or panic.
    if *frame >= 300 && !*stopped {
        *stopped = true;
        capture.stop();
    }
}
```

Verified against `bevy = "0.18"` + patched `bevy_capture = "0.4.1"` — `cargo check --example bevy_capture` clean. The snippet lives at `bevy-skills-tester/skill-snippets/examples/bevy_capture.rs`.

## Encoder choice

See [`references/encoders.md`](references/encoders.md) for the deep dive. Quick table:

| Encoder | Mechanism | System dep | Cargo feature | When to use |
|---|---|---|---|---|
| `Mp4Openh264Encoder` | In-process OpenH264 (downloaded at build) | None | `mp4_openh264` | CI without ffmpeg; single-binary distribution |
| `Mp4FfmpegCliEncoder` | Collects frames, shells out once at stop | `ffmpeg` on `$PATH` | `mp4_ffmpeg_cli` | Short clips, full ffmpeg codec control |
| `Mp4FfmpegCliPipeEncoder` | Long-running ffmpeg child, pipes per-frame | `ffmpeg` on `$PATH` | `mp4_ffmpeg_cli_pipe` | Long recordings, low memory |
| `FramesEncoder` | One PNG per frame into a directory | None | *(always available)* | Compositing, GIF pipelines, WASM |

## Gotchas

- **`Camera.target` is gone in 0.18.** `RenderTarget` is a separate required component. Use `target_headless(w, h, &mut images)` (returns the `(Camera, RenderTarget)` pair) or spawn `RenderTarget::Image(handle)` alongside `Camera3d`. See `bevy-cameras`.
- **Encoders are feature-gated.** `mp4_openh264`, `mp4_ffmpeg_cli`, and `mp4_ffmpeg_cli_pipe` are three *separate* features — enable each one you import. `FramesEncoder` is always available. Missing the feature gives a "cannot find type" compile error, not a friendly diagnostic.
- **OpenH264 license.** `Mp4Openh264Encoder` links Cisco's OpenH264 binary, distributed under Cisco's OBQI (royalty-covered for H.264 baseline). If your runtime-dependency policy forbids non-MIT/Apache binaries, pick one of the ffmpeg-CLI encoders instead.
- **ffmpeg-CLI encoders need `ffmpeg` on `$PATH`.** `Mp4FfmpegCliEncoder::new` and `Mp4FfmpegCliPipeEncoder::new` return `Result` — handle the spawn error, don't `.unwrap()`. `Mp4Openh264Encoder` and `FramesEncoder` have no system dependency.
- **Camera must be active and rendering.** `CaptureBundle` hooks into the render loop on that camera entity. Inactive or unsourced cameras emit no frames; capture appears to silently do nothing.
- **WASM:** only `FramesEncoder` works. The MP4 encoders shell out (ffmpeg) or rely on the OpenH264 native binary, neither of which exist in `wasm32-unknown-unknown`. See `bevy-wasm-webgpu` for the WASM build path.
- **Upstream PollType / MessageWriter renames.** If you fork `bevy_capture` for 0.18 instead of using the patch, fix `PollType::wait` → `PollType::wait_indefinitely` and `EventWriter<AppExit>` → `MessageWriter<AppExit>` in any example code you carry over.

## See also

- `bevy-cameras` — camera spawning and the 0.18 `RenderTarget`-as-component model that `bevy_capture` attaches to.
- `bevy-cargo-features` — picking Bevy feature flags alongside `bevy_capture`'s encoder gates.
- `bevy-wasm-webgpu` — WASM caveat: only `FramesEncoder` survives `wasm32` builds.
- [`references/encoders.md`](references/encoders.md) — encoder-by-encoder deep dive.
- [`references/bevy-0-18-patch.md`](references/bevy-0-18-patch.md) — the three-line patch needed to build `bevy_capture` 0.4.1 against Bevy 0.18.
