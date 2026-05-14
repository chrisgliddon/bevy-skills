---
name: bevy-wasm-webgpu
description: Use when targeting `wasm32-unknown-unknown`, picking between the `webgl2` and `webgpu` Bevy features, configuring `wasm-bindgen` glue, sizing down the bundle via `default-features = false`, or hitting "asset 404" errors caused by relative path handling in the browser. Covers Bevy 0.18 WASM build pipeline.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "2"
  area: platform
  bevy_version: "0.18"
---

# Bevy 0.18 — WASM + WebGPU

## When to use this skill

- Targeting `wasm32-unknown-unknown` for browser delivery.
- Choosing the WebGL2 default vs the more capable WebGPU.
- Trimming the bundle from 30 MB down to 5–10 MB.
- Configuring asset paths so the browser actually finds your `assets/` folder.
- Debugging "context lost" or "no canvas found" errors at startup.

## Canonical Cargo.toml

```toml
[package]
name = "myclient"
version = "0.1.0"
edition = "2024"

[dependencies]
bevy = { version = "0.18", default-features = false, features = [
    # Bring just the renderer + window plumbing.
    "3d_api",
    "bevy_winit",
    # Pick one or both backends. WebGL2 has best browser coverage today;
    # WebGPU is faster and supports compute shaders but is still gated on
    # current Chrome / Firefox / Safari versions.
    "webgl2",
    # "webgpu",
    # Input — input is NOT in default-features = false anymore in 0.18.
    "mouse",
    "keyboard",
    "touch",
    "gestures",
] }

[profile.release]
opt-level = "z"      # size, not speed — WASM is bandwidth-bound, not CPU-bound
lto = "fat"
codegen-units = 1
strip = "debuginfo"
panic = "abort"
```

## Build & serve

```bash
# 1. Build the WASM binary.
cargo build --release --target wasm32-unknown-unknown

# 2. Bind it for the browser.
wasm-bindgen --target web --out-dir public/ \
    target/wasm32-unknown-unknown/release/myclient.wasm

# 3. (Optional but big win) shrink with wasm-opt.
wasm-opt -Oz public/myclient_bg.wasm -o public/myclient_bg.wasm

# 4. Serve. Must serve `assets/` next to `myclient.js` / `myclient_bg.wasm`.
#    Bevy looks for `./assets/...` relative to the page URL.
python3 -m http.server -d public/ 8080
```

## Picking a backend

```rust
// At runtime, force a backend by setting `WgpuSettings.backends` before
// `DefaultPlugins`. By default Bevy picks the best available.
use bevy::prelude::*;
use bevy::render::settings::{Backends, WgpuSettings};
use bevy::render::RenderPlugin;

fn main() {
    App::new()
        .add_plugins(DefaultPlugins.set(RenderPlugin {
            render_creation: WgpuSettings {
                backends: Some(Backends::GL),     // WebGL2
                // backends: Some(Backends::BROWSER_WEBGPU), // WebGPU
                ..default()
            }
            .into(),
            ..default()
        }))
        .run();
}
```

## Minimal `index.html`

```html
<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><title>myclient</title></head>
  <body style="margin:0;background:#000">
    <canvas id="bevy"></canvas>
    <script type="module">
      import init from "./myclient.js";
      // Bevy auto-finds <canvas id="bevy"> if present.
      init();
    </script>
  </body>
</html>
```

## Gotchas

- **`default-features = true` for WASM = 30 MB+ bundle.** Always pass `default-features = false` and pick features explicitly. This is the single biggest size lever.
- **Backend coverage 2026:** WebGPU is on by default in Chrome and Edge, behind a flag in Firefox and Safari (improving). Ship both if you care about reach — Bevy picks WebGPU when present, falls back to WebGL2 otherwise.
- **Compute shaders need WebGPU.** WebGL2 has none. If your renderer plugin requires compute, you must build with the `webgpu` feature and accept the smaller addressable browser pool.
- **Assets are served, not bundled.** `assets/` must sit next to your HTML at the served URL root. There is no built-in embed-in-WASM mode without a custom asset source.
- **`wasm-pack` vs `wasm-bindgen` CLI.** `wasm-pack` adds an npm-style wrapper. For raw `<script type="module">` delivery, `wasm-bindgen --target web` is leaner.
- **Coop/Coep headers** are required for `SharedArrayBuffer`, which Bevy's threadpool needs for `multi_threaded`. Without them you'll be single-threaded in the browser. Configure your server: `Cross-Origin-Opener-Policy: same-origin` + `Cross-Origin-Embedder-Policy: require-corp`.
- **No `std::time::Instant` in WASM.** Bevy's `Time` works, but if you use raw `std::time::Instant` in a system it panics. Use `bevy::time::Instant` or wrap behind `#[cfg(target_arch = "wasm32")]`.
- **`println!` lands in the JS console** as a generic log line. Use the `tracing` machinery (`info!`/`warn!`) for structured browser-devtools output.

## Source-confirmed scope

This skill covers the parts of the WASM workflow that are uncontroversial and stable in 0.18. The Bevy 0.18 release notes did not call out WASM-specific renderer changes; the migration story is mostly the same Cargo-features rename as for native (`animation` → `gltf_animation`, etc. — see `bevy-cargo-features`).

## See also

- `bevy-cargo-features` — the feature collection table you need for trimmed WASM builds.
- `bevy-assets` — asset loading rules apply identically to WASM, with the file-source caveat above.
