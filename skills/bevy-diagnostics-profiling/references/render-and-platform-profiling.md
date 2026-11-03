# Render and platform profiling

## Enable render diagnostics intentionally

```rust
use bevy::{prelude::*, render::diagnostic::RenderDiagnosticsPlugin};

fn install(app: &mut App) {
    app.add_plugins((DefaultPlugins, RenderDiagnosticsPlugin));
}
```

Recorded spans are synced into the main world's `DiagnosticsStore`. Paths begin with
`render/` and end with fields such as:

- `elapsed_cpu` in milliseconds;
- `elapsed_gpu` in milliseconds when timestamp queries are supported;
- `vertex_shader_invocations`, `fragment_shader_invocations`,
  `compute_shader_invocations`, and clipper statistics when pipeline queries work.

Custom render passes call `RenderContext::diagnostic_recorder()` (an `Option`; `None`
without the plugin) and bracket a command encoder, render pass, or compute pass with
`time_span`. Always end the returned span guard with
the same encoder/pass; dropping it unended is an error.

## On-screen overlay (0.20)

```rust,ignore
// Requires the `dev` Cargo feature (or `bevy_dev_tools` + `render_dev_tools`).
use bevy::dev_tools::render_debug::RenderDebugOverlayKeybindings;

app.add_plugins(DefaultPlugins)
    .insert_resource(RenderDebugOverlayKeybindings {
        enable_keybindings: true, // F1 cycles mode, F2 cycles opacity
        ..Default::default()
    });
```

`RenderDebugOverlayPlugin` is already in `DefaultPlugins` when the feature is on; add
it manually only in a custom plugin set. It is a visual aid, not a measurement source.

## Know what each timing means

- CPU pass time measures command recording/submission-side work, not the GPU's actual
  execution duration.
- GPU timestamp duration measures work between GPU timestamps, not end-to-end input
  latency or transfer wait elsewhere.
- pipeline invocation counts describe workload volume, not cost per invocation.
- frame time can be dominated by present/vsync, asset upload, ECS extraction, driver
  synchronisation, or CPU simulation even when individual pass times look small.

Correlate render diagnostics with CPU traces, GPU captures, upload counters, and
frame-time percentiles.

## Backend matrix in Bevy 0.20

| Backend/target | CPU render timings | GPU timestamps | Pipeline statistics |
|---|---:|---:|---:|
| Vulkan | yes | yes, subject to device support | yes, subject to device support |
| DX12 | yes | yes, subject to device support | yes, subject to device support |
| Metal | yes | no through this plugin | no through this plugin |
| Browser WebGPU | yes | no through this plugin | no through this plugin |
| WebGL2 | yes | no through this plugin | no through this plugin |

Do not compare an absent browser GPU diagnostic to a native zero. Use browser GPU
profiling/timing facilities that are available on the tested browser and device, and
label evidence by browser, version, adapter, backend, resolution, and power mode.

## Tool choice

- Tracy/Chrome tracing: Bevy systems, task scheduling, queue waits, CPU spans.
- NVIDIA Nsight, Radeon GPU Profiler, Intel GPA, or Xcode GPU tools: GPU performance.
- RenderDoc: render correctness, resources, passes, and draw debugging; not profiling.
- Bevy render diagnostics: lightweight continuous pass-level telemetry and correlation.

Capture in a release-like build. Debug builds mostly measure missing optimisation.
Keep symbols enabled when the profiler needs them, and record all non-default Cargo
features used for the capture.

Primary source: [Bevy render diagnostics](https://docs.rs/bevy/0.20.1/bevy/render/diagnostic/index.html).
