# Spatial audio, web startup, and Seedling

## Built-in spatial contract

Add `PlaybackSettings::with_spatial(true)` and a source `Transform`. Maintain one
`SpatialListener` with `Transform`/`GlobalTransform`. Listener ear offsets and
`SpatialScale` must match world units and viewpoint convention.

Bevy's built-in implementation provides distance-aware simple left/right stereo
panning. It does not provide HRTF, room acoustics, occlusion, reverberation buses, or
a general DSP graph. Test headphones and speakers; never make spatial direction the
only way to identify a critical threat/objective.

For accessibility, provide captions or visual/haptic equivalents with directional
and identity information, independent dialogue volume, reduced dynamic range where
needed, and a mono/low-spatial-dependence path if the product requires it.

## Browser user activation

Browser autoplay policies can suspend/block audible output until a user gesture. The
app should model `Locked -> UnlockRequested -> Ready/Failed` rather than silently
dropping startup sounds. Trigger unlock from a real keyboard/pointer/touch/controller
activation where the browser recognises one, then start or resume pending loops at
their intended logical position.

Handle tab visibility/suspension and output-device changes. Show a clear sound control
when unlock fails, and do not make sound necessary to find that control. Test Chrome,
Firefox, Safari, and target mobile devices; policy and gesture recognition differ.

Reference: [MDN autoplay guide](https://developer.mozilla.org/docs/Web/Media/Guides/Autoplay).

## Escalate to `bevy_seedling 0.8`

Seedling 0.8.0 (2026-08-09) pins Bevy `^0.19` and Firewheel 0.12. As of 2026-11-03 no
release supports Bevy 0.20, so the snippet below only builds on a Bevy 0.19 app.
Mixing `bevy = "0.20"` with `bevy_seedling = "0.8"` pulls two `bevy_ecs` versions and
fails to compile. Check crates.io for a newer release before adopting it on 0.20.

Seedling is appropriate when the design needs its Firewheel graph features: buses and
effects, richer routing, pooled emitters, sample-accurate scheduling, or HRTF/spatial
processing.

```toml
[dependencies]
bevy = { version = "0.19", default-features = false, features = ["3d", "ui"] }
bevy_seedling = "0.8"
```

Keep Bevy's built-in `audio` feature disabled when Seedling owns the backend. Confirm
the final feature graph with `cargo tree -e features`; another dependency can re-enable
features. Seedling's default features do not include HRTF: enable `hrtf` explicitly,
and add `hrtf_subjects` only if the bundled subject set is required. Port the
application-level action/mix/accessibility policy, not just calls to `AudioPlayer`,
and revalidate WASM/native backend support.

Seedling's web backend is also opt-in through `web_audio`. In 0.8 it uses
multi-threaded Wasm and requires the documented nightly/`rust-src`, atomics/linker,
secure-context, and COOP/COEP setup; the Bevy CLI `bevy run web -U multi-threading`
path configures the development build/server. These deployment requirements are
separate from browser user activation, so test both.

Primary references:

- [`bevy_seedling 0.8` documentation](https://docs.rs/bevy_seedling/0.8.0/bevy_seedling/)
- [`WebAudioPlatformPlugin` requirements](https://docs.rs/bevy_seedling/0.8.0/bevy_seedling/platform/web_audio/struct.WebAudioPlatformPlugin.html)
- [Seedling 0.8 release](https://github.com/CorvusPrudens/bevy_seedling/releases/tag/v0.8.0)
- [Bevy 0.18 → 0.19 feature migration](https://bevy.org/learn/migration-guides/0-18-to-0-19/)
- [Bevy 0.19 → 0.20 migration guide](https://bevy.org/learn/migration-guides/0-19-to-0-20/)
