# Capture-based visual regression

## Capture through Bevy's screenshot event

Spawn a `Screenshot` entity and attach an observer:

```rust
use bevy::{
    prelude::*,
    render::view::window::screenshot::{save_to_disk, Screenshot, ScreenshotCaptured},
};

fn request_capture(mut commands: Commands) {
    commands
        .spawn(Screenshot::primary_window())
        .observe(save_to_disk("artifacts/actual.png"));
}

#[derive(Component)]
struct CaptureDone;

// Completion marker the test loop can poll for (0.20 `On<E>` has no bundle generic).
fn mark_done(_captured: On<ScreenshotCaptured>, mut commands: Commands) {
    commands.spawn(CaptureDone);
}
```

The module path is `bevy::render::view::window::screenshot`; stale output drops the
`window` segment and fails to resolve.

Capture is asynchronous. Completion is `ScreenshotCaptured`; file existence after an
arbitrary sleep is not the contract. A test runner should advance/render until that
event or another observer-owned completion marker appears, with a hard frame/deadline
bound, then compare.

## Make the scene reproducible

Pin:

- window/render-target dimensions, scale factor, camera/projection, and clear colour;
- world seed, animation/simulation time, particle seed, and asset readiness;
- renderer/backend, GPU/driver, Bevy features, colour space, anti-aliasing, shadows,
  and post-processing;
- fonts and every external asset by version/content hash.

Wait on asset/world-instance readiness, not guessed frame counts. Disable uncontrolled
animation and temporal effects or advance them to a known time.

## Compare with an explicit policy

Exact pixels work for tightly controlled software/data paths but are brittle across
GPU vendors and drivers. Otherwise define:

- per-channel or perceptual error metric;
- maximum differing-pixel ratio and maximum local error;
- ignored/masked regions, justified in the test metadata;
- target-specific baselines when a legitimate backend difference exists.

Do not auto-update baselines on failure. Store expected, actual, amplified diff, and
metadata as CI artifacts. Baseline changes need human review beside the product/code
change that caused them.

## Test layers

1. Unit-test geometry, layout, colours, and visibility numerically.
2. Headless-world test entity/component state and camera inputs.
3. Capture a few high-value integrated scenes.
4. Use human/accessibility review for quality that image diffs cannot judge.

Visual regression can catch changed output; it cannot prove readability, motion
safety, screen-reader semantics, caption timing, or input accessibility.

Primary API: [Bevy `save_to_disk`](https://docs.rs/bevy/0.20.1/bevy/render/view/window/screenshot/fn.save_to_disk.html).
