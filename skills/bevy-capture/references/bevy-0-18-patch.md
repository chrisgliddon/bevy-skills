# bevy-capture — Bevy 0.18 patch notes

> Referenced from `bevy-capture/SKILL.md § Compatibility status`.

`bevy_capture` 0.4.1 (latest crates.io release at time of writing) pins `bevy = "^0.17.2"`. Three small changes are needed to build against Bevy 0.18. Apply them via a `[patch.crates-io]` entry to a local fork, or wait for an upstream 0.18 release.

## Patch 1 — `Camera.target` field removed

Bevy 0.18 moves `RenderTarget` out of `Camera` into a separate required component. The `CameraTargetHeadless::target_headless` helper in `bevy_capture` previously mutated `Camera` in place and returned `&mut Self`; for 0.18 it must return the `(Camera, RenderTarget)` pair so callers can spawn both.

```rust
// before (0.17): set the target field on Camera
camera.target = RenderTarget::Image(handle);

// after (0.18): the trait now returns both components
let (camera, render_target) =
    Camera::default().target_headless(w, h, &mut images);
commands.spawn((Camera3d, camera, render_target, CaptureBundle::default()));
```

The full diff to the trait impl is one function signature change in `src/camera_target.rs` (or wherever the helper lives in your fork).

## Patch 2 — `PollType::wait` → `wait_indefinitely`

The `wgpu-types` re-export in Bevy 0.18 renamed the variant. `bevy_capture`'s render-world copy-out path uses it once:

```rust
// before
device.poll(PollType::wait());

// after
device.poll(PollType::wait_indefinitely());
```

## Patch 3 — `EventWriter<AppExit>` → `MessageWriter<AppExit>`

Bevy 0.18 split events into events and messages; `AppExit` is now a message. Examples in the `bevy_capture` repo that send `AppExit` need:

```rust
// before
fn done(mut exit: EventWriter<AppExit>) { exit.send(AppExit::Success); }

// after
fn done(mut exit: MessageWriter<AppExit>) { exit.write(AppExit::Success); }
```

This only affects example/test code that exits the app — the library proper does not write `AppExit`.

## Applying the patch

In your project's `Cargo.toml`:

```toml
[patch.crates-io]
bevy_capture = { path = "vendor/bevy_capture" } # local fork with the 3 changes above
```

Or via a Git dependency once a 0.18 branch exists on a fork:

```toml
bevy_capture = { git = "https://github.com/<your-fork>/bevy_capture", branch = "bevy-0.18" }
```

When upstream `bevy_capture` publishes a Bevy 0.18 release (likely 0.5.x), drop the patch and pin the new crates.io version.

## See also

- [`SKILL.md`](../SKILL.md) — dispatcher.
- [`encoders.md`](encoders.md) — encoder comparison.
