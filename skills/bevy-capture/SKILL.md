---
name: bevy-capture
description: Use when adding `CapturePlugin` to record a `Camera3d` or `Camera2d` to video, spawning `CaptureBundle` with `RenderTarget::target_headless`, calling `Capture::start` with `Mp4Openh264Encoder`, `Mp4FfmpegCliEncoder`, `Mp4FfmpegCliPipeEncoder`, `GifEncoder` or `FramesEncoder`, pausing with `Capture::pause`, or hitting "failed to select a version for bevy_capture" because the crate still pins Bevy 0.19 while your app is on Bevy 0.20.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "4"
  area: render
  bevy_version: "0.20"
---

# bevy-capture — recording Bevy 0.20 cameras to MP4, GIF or PNG sequences

## Compatibility status (crates.io, checked 2026-11-03)

| `bevy_capture` | Published | Pins | Notes |
|---|---|---|---|
| 0.6.0 | 2026-06-27 | `bevy ^0.19.0` | Latest. **No Bevy 0.20 release yet.** |
| 0.5.0 | 2026-06-27 | `bevy ^0.18.0` | Native 0.18 support; the old local patch is obsolete. |
| 0.4.1 | 2025-10-06 | `bevy ^0.17.2` | |

On Bevy 0.20 a plain `bevy_capture = "0.6.0"` dependency pulls in a second Bevy (0.19)
and fails with type mismatches. Until upstream (`jannik4/bevy_capture`) publishes a 0.20
build, point Cargo at a fork that bumps the `bevy` requirement — see
[`references/bevy-0-20-port.md`](references/bevy-0-20-port.md) for what the port needs.

The API below is the 0.6.0 surface. It was verified by reading the 0.6.0 source, not by
compiling in the tester crate (third-party dependency). The 0.5/0.6 API is identical;
0.5.0 changed the API from 0.4.x (`RenderTargetHeadless`, `IntoEncoders`, `GifEncoder`).

## When to use this skill

- Recording a gameplay clip or cinematic from a `Camera3d` or `Camera2d`.
- Generating MP4 or GIF files for trailers or automated visual regression tests.
- Capturing a PNG-per-frame sequence for offline compositing.
- Choosing between in-process H.264 (`Mp4Openh264Encoder`) and ffmpeg-CLI encoders.
- "cannot find type `Mp4Openh264Encoder`" because a Cargo feature wasn't enabled.
- Pausing, resuming and stopping a recording with `Capture::pause/resume/stop`.

## Canonical pattern

```toml
# Cargo.toml
[dependencies]
bevy = "0.20"
# Pick the features for the encoders you use; FramesEncoder needs none.
bevy_capture = { version = "0.6.0", features = ["mp4_openh264", "gif"] }

# Required until bevy_capture publishes a Bevy 0.20 release — see references/bevy-0-20-port.md
[patch.crates-io]
bevy_capture = { git = "https://github.com/<your-fork>/bevy_capture", branch = "bevy-0.20" }
```

```rust
use bevy::camera::RenderTarget;
use bevy::prelude::*;
use bevy_capture::{
    encoder::{
        frames::FramesEncoder, gif::GifEncoder, mp4_ffmpeg_cli::Mp4FfmpegCliEncoder,
        mp4_ffmpeg_cli_pipe::Mp4FfmpegCliPipeEncoder, mp4_openh264::Mp4Openh264Encoder,
    },
    Capture, CaptureBundle, CapturePlugin, RenderTargetHeadless,
};
use std::fs;

fn main() {
    App::new()
        .add_plugins((DefaultPlugins, CapturePlugin))
        .add_systems(Startup, setup)
        .add_systems(Update, drive_capture)
        .run();
}

// 1. Spawn a camera with `CaptureBundle`. `RenderTarget::target_headless` (0.5+)
//    builds an off-screen `RenderTarget::Image` with COPY_SRC set.
fn setup(mut commands: Commands, mut images: ResMut<Assets<Image>>) {
    commands.spawn((
        Camera2d, // or Camera3d::default()
        RenderTarget::target_headless(1920, 1080, &mut images),
        CaptureBundle::default(),
    ));
}

// 2. `Capture::start` takes one encoder or a tuple of up to 15 (`IntoEncoders`).
//    Every rendered frame goes to each encoder until `stop()`.
fn drive_capture(
    mut q: Query<&mut Capture>,
    mut exit: MessageWriter<AppExit>,
    mut frame: Local<u32>,
    mut waited: Local<bool>,
) {
    // Skip the first frame: the render target is not ready yet (bevy#20756).
    if !*waited {
        *waited = true;
        return;
    }
    let Ok(mut capture) = q.single_mut() else { return };

    if !capture.is_capturing() {
        fs::create_dir_all("captures").ok();
        capture.start((
            // A) In-process H.264, no system ffmpeg. Width/height are u16.
            Mp4Openh264Encoder::new(fs::File::create("captures/out.mp4").unwrap(), 1920, 1080)
                .expect("openh264 init"),
            // B) GIF (feature `gif`).
            GifEncoder::new(fs::File::create("captures/out.gif").unwrap()),
            // C) One PNG per frame; no encoding, no features.
            FramesEncoder::new("captures/frames"),
        ));
        // D) Collect frames, shell out to `ffmpeg` once at stop (feature `mp4_ffmpeg_cli`):
        //    Mp4FfmpegCliEncoder::new("captures/out.mp4").unwrap().with_framerate(30).with_crf(23)
        // E) Pipe frames to a long-running ffmpeg child (feature `mp4_ffmpeg_cli_pipe`):
        //    Mp4FfmpegCliPipeEncoder::new("captures/out.mp4").unwrap().with_framerate(30).with_crf(18)
    }

    *frame += 1;
    if *frame == 150 {
        capture.pause(); // frames are rendered but not encoded while paused
    }
    if *frame == 180 {
        capture.resume();
    }
    // 3. `stop()` drops the encoders, which calls `Encoder::finish` on each one.
    if *frame >= 300 {
        capture.stop();
        exit.write(AppExit::Success);
    }
}
```

For deterministic offline rendering (no window, fixed 60 FPS), combine with
`DefaultPlugins.build().disable::<WinitPlugin>()`, `ScheduleRunnerPlugin`,
`RenderPlugin { synchronous_pipeline_compilation: true, .. }` and
`TimeUpdateStrategy::ManualDuration`. The crate's `examples/simple.rs` shows the full setup.

## Encoder choice

See [`references/encoders.md`](references/encoders.md) for the deep dive. Quick table:

| Encoder | Mechanism | System dep | Cargo feature | When to use |
|---|---|---|---|---|
| `Mp4Openh264Encoder` | In-process OpenH264 (downloaded at build) | None | `mp4_openh264` | CI without ffmpeg; single-binary distribution |
| `Mp4FfmpegCliEncoder` | Collects frames, shells out once at stop | `ffmpeg` on `$PATH` | `mp4_ffmpeg_cli` | Short clips, full ffmpeg codec control |
| `Mp4FfmpegCliPipeEncoder` | Long-running ffmpeg child, pipes per frame | `ffmpeg` on `$PATH` | `mp4_ffmpeg_cli_pipe` | Long recordings, low memory, hardware encoders |
| `GifEncoder` | In-process GIF via the `image` crate | None | `gif` | Short loops, README demos |
| `FramesEncoder` | One PNG per frame into a directory | None | *(always available)* | Compositing, WASM |

## Gotchas

- **No Bevy 0.20 release of `bevy_capture`.** 0.6.0 pins 0.19. Cargo will error with "failed to select a version" or duplicate-Bevy type errors. Use a `[patch.crates-io]` fork until upstream bumps; the port is small (see reference).
- **`CameraTargetHeadless` and `Camera::target_headless` are gone (0.5+).** The trait is `RenderTargetHeadless` on `RenderTarget`; it is an associated function, not a method on `Camera`. The old `(Camera, RenderTarget)` tuple return was only ever in the local 0.18 patch.
- **`Capture::start` wants `IntoEncoders`.** A single encoder, a `Vec<Box<dyn Encoder>>`, or a tuple of encoders all work. Each encoder runs on every frame.
- **Encoders are feature-gated.** `mp4_openh264`, `mp4_ffmpeg_cli`, `mp4_ffmpeg_cli_pipe` and `gif` are four separate features. `FramesEncoder` is always available. A missing feature gives "cannot find module", not a friendly diagnostic.
- **`Mp4Openh264Encoder::new(writer, width: u16, height: u16)`.** The writer must be `Write + Seek` (a `File` is fine). The OpenH264 binary is Cisco-licensed (OBQI); pick an ffmpeg encoder if your policy forbids it.
- **ffmpeg-CLI encoders return `Result` from `new`.** `Mp4FfmpegCliPipeEncoder` spawns ffmpeg eagerly and offers `with_hardware_encoder` / `detect_hardware_encoder` / `with_resolution`.
- **Wait one frame before `start()`.** The headless image is not uploaded on frame 0; the crate's own example skips it.
- **Camera must be active.** `CaptureBundle` reads the camera's `RenderTarget::Image`; a window target or inactive camera yields no frames.
- **WASM:** only `FramesEncoder` and `GifEncoder` have no native dependency, and neither can write files without JS interop. See `bevy-wasm-webgpu`.
- **`EasyScreenRecordPlugin` is not this crate.** That name does not exist on crates.io; `bevy_easy_screen_record` is not published. Ignore LLM output that suggests it.

## See also

- `bevy-cameras` — `RenderTarget` component model that `bevy_capture` attaches to.
- `bevy-cargo-features` — Bevy feature flags alongside `bevy_capture`'s encoder gates.
- `bevy-wasm-webgpu` — WASM caveat: only file-free encoders survive `wasm32` builds.
- `bevy-migration-0-19-to-0-20` — what a 0.19→0.20 port of the crate must absorb.
- [`references/encoders.md`](references/encoders.md) — encoder-by-encoder deep dive.
- [`references/bevy-0-20-port.md`](references/bevy-0-20-port.md) — porting 0.6.0 to Bevy 0.20.
