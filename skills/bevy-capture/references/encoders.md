# bevy-capture — Encoder comparison (deep dive)

> Referenced from `bevy-capture/SKILL.md § Encoder choice`.

## Mp4Openh264Encoder

The headline differentiator of `bevy_capture`: **fully in-process, no shell-out**. The crate links against Cisco's OpenH264 dynamic library via the `openh264-sys2` crate; the binary is fetched at build time (same mechanism Mozilla Firefox uses).

**Cargo feature:** `mp4_openh264`.

**Construction:** `Mp4Openh264Encoder::new(writer, width, height) -> Result<Self, _>`. The writer is any `Write` (e.g. `std::fs::File`).

**License note:** OpenH264 ships under Cisco's OBQI (Open Binary Quality Interface) terms. Cisco covers the H.264 baseline-profile royalty. If your project policy forbids non-MIT/Apache runtime binaries, use one of the ffmpeg encoders instead.

**Typical use:**
- CI pipelines generating test output MP4s without installing `ffmpeg`.
- Desktop apps shipped as a single binary.

## Mp4FfmpegCliEncoder

Collects all frames in memory (or a tempdir, depending on impl detail) during the run, then shells out to `ffmpeg` **once** when `Capture::stop()` is called or the encoder is dropped. Quality and codec options are configurable via builder methods.

**Cargo feature:** `mp4_ffmpeg_cli`.

**Construction:** `Mp4FfmpegCliEncoder::new(path) -> Result<Self, _>` then chain `.with_framerate(fps)`, `.with_crf(crf)`, etc.

**Requirement:** `ffmpeg` on `$PATH` when stop/flush occurs.

**Pros:** Full ffmpeg codec + filter graph access; good for offline batch renders.
**Cons:** Keeps frames around until end — unsuitable for very long recordings unless backed by a tempdir.

## Mp4FfmpegCliPipeEncoder

Spawns a long-running `ffmpeg` child at `Capture::start()` and pipes raw RGBA frames to its stdin per frame. The child writes the MP4 incrementally.

**Cargo feature:** `mp4_ffmpeg_cli_pipe` (a *separate* feature from `mp4_ffmpeg_cli` — enabling one does not enable the other).

**Construction:** `Mp4FfmpegCliPipeEncoder::new(path) -> Result<Self, _>` then chain `.with_framerate`, `.with_crf`, `.with_preset(String)`, etc.

**Requirement:** `ffmpeg` on `$PATH` at startup (the child is spawned eagerly).

**Pros:** Memory-efficient for long recordings; output file grows incrementally.
**Cons:** Any ffmpeg crash mid-run corrupts the output. Pipe backpressure can stall the render loop on slow storage.

## FramesEncoder

Writes one PNG per rendered frame into a specified output directory. No video encoding at all — downstream tools (ffmpeg, gifski, DaVinci Resolve, ImageMagick) consume the sequence.

**Cargo feature:** *(none — always available).*

**Construction:** `FramesEncoder::new(dir_path)`. The directory is created at first frame; no `Result`.

**Pros:** Lossless; zero system dependencies; trivial to debug — you can open frame N in any viewer. **Note on WASM:** `FramesEncoder` is the only encoder that compiles for `wasm32-unknown-unknown`, but writing frames requires JS interop or a virtual FS (e.g. Emscripten) — there is no out-of-the-box filesystem in a browser WASM context. See `bevy-wasm-webgpu` for the full WASM build path.
**Cons:** Large output (3–10× MP4 for the same content); must be assembled into video separately.

## Choosing in practice

```
Need WASM support?                     → FramesEncoder
Need in-process, no system deps?       → Mp4Openh264Encoder
Need ffmpeg codec control, short clip? → Mp4FfmpegCliEncoder
Need ffmpeg, memory-efficient, long?   → Mp4FfmpegCliPipeEncoder
```

## See also

- [`SKILL.md`](../SKILL.md) — dispatcher with canonical pattern.
- [`bevy-0-18-patch.md`](bevy-0-18-patch.md) — patches to build 0.4.1 against Bevy 0.18.
