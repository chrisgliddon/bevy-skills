---
name: bevy-audio
description: "Use when implementing audio in Bevy 0.20 with `AudioPlayer`, `PlaybackSettings`, `AudioSink` or `SpatialAudioSink`, spatial listeners, application mix groups, ambience/music transitions, asset lifetime, browser gesture restrictions, or choosing built-in audio versus `bevy_seedling 0.8`."
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "2"
  area: audio
  bevy_version: "0.20"
---

# Bevy 0.20 — audio

## When to use this skill

- Spawn or control clips/loops through `AudioPlayer` and sink components.
- Build music/ambience transitions, mix categories, ducking, or pause policy.
- Add spatial sources/listeners or define the built-in HRTF/effects boundary.
- Ship audio on browsers or evaluate `bevy_seedling 0.8` (Bevy 0.19 only, see Gotchas).

Use Bevy's built-in entity-based audio for straightforward clips, loops, playback
control, and simple spatial stereo. Add an application mixer policy for categories and
transitions. Move to an audio-graph library only when the measured/design requirement
exceeds that boundary.

## Canonical pattern

```rust
use bevy::{audio::Volume, prelude::*};

#[derive(Component)]
struct Music;

fn start_music(mut commands: Commands, assets: Res<AssetServer>) {
    commands.spawn((
        Name::new("Exploration music"),
        Music,
        AudioPlayer::new(assets.load("audio/exploration.ogg")),
        PlaybackSettings::LOOP.with_volume(Volume::Decibels(-9.0)),
    ));
}

fn mute_music(mut sinks: Query<&mut AudioSink, With<Music>>) {
    for mut sink in &mut sinks {
        sink.mute();
    }
}
```

Bevy inserts `AudioSink` after non-spatial playback begins and `SpatialAudioSink` for
spatial playback. Query the sink for live volume, mute, pause, speed, position, seek,
and stop. Changing `PlaybackSettings` or `GlobalVolume` does not update audio that is
already playing.

`PlaybackSettings::{ONCE, LOOP, DESPAWN, REMOVE}` define completion ownership. An
`ONCE` player cannot simply replay after its sink drains; remove/reinsert the audio
components or spawn a new player. Removing a sink while `AudioPlayer` remains causes
the unchanged source to start again.

## Gotchas

- `PlaybackSettings` and `GlobalVolume` affect initial playback, not existing sinks.
- A sink appears only after playback starts; query it optionally.
- Drained `ONCE` playback is not replayable without replacing audio components.
- Removing a sink while its unchanged player remains restarts the source.
- Built-in spatial audio is stereo panning, not HRTF or a general effects graph.
- 0.20: `bevy_seedling 0.8.0` pins Bevy `^0.19`; no 0.20-compatible release exists
  (crates.io, 2026-11-03). Adding it to a 0.20 app fails with two `bevy_ecs` versions.
- 0.20: observers lost the bundle generic. React to a sink appearing with
  `On<Add<AudioSink>>` (0.19 output writes `On<Add, AudioSink>`):

  ```rust
  fn on_sink_ready(add: On<Add<AudioSink>>, mut sinks: Query<&mut AudioSink>) {
      if let Ok(mut sink) = sinks.get_mut(add.entity) {
          sink.set_volume(Volume::Decibels(-6.0));
      }
  }
  ```

- 0.20: `Name: From<&'static str>` only; `Name::new(string.to_owned())` for runtime text.
- 0.19: the `audio` feature is no longer implied by `2d`/`3d`/`ui`. With
  `default-features = false`, add `audio` (and `vorbis`/`mp3`/`flac` as needed) or
  `AudioPlayer` does not exist.

## Spatial audio boundary

```rust
fn spawn_spatial_loop(mut commands: Commands, assets: Res<AssetServer>) {
    commands.spawn((
        SpatialListener::new(0.2),
        Transform::default(),
    ));
    commands.spawn((
        AudioPlayer::new(assets.load("audio/generator.ogg")),
        PlaybackSettings::LOOP.with_spatial(true),
        Transform::from_xyz(4.0, 0.0, 0.0),
    ));
}
```

Keep exactly one `SpatialListener`; attach it to the authoritative listener/camera
pose. Configure `SpatialScale` when world units do not match audio distance. Built-in
spatialisation is simple left/right stereo panning: it does not provide HRTF or a full
3D acoustic model.

## Mix groups and transitions

Built-in audio has no general bus/effects graph. Model categories (`Master`, `Music`,
`Sfx`, `Dialogue`, `Ambience`, `Ui`) as application state and tag player entities.
Compute effective gain from master × group × transition/ducking × source gain, then
write sinks. Store sliders in decibels or a perceptually useful curve, not a raw linear
UI that puts most useful range in a few pixels.

For music/ambience changes, overlap old and new loops and crossfade using real/virtual
time according to pause policy. Do not despawn the old entity until its sink reaches
silence. Preload assets before a latency-critical transition, and define what happens
when a new track is not ready.

## Browser rule

Browsers commonly block audible playback until a user activation. Treat audio unlock
as an explicit app state: let the first intentional input resume/start audio, keep the
request pending if blocked, and present a usable muted/unlock control. Test refresh,
tab background/foreground, device change, and mobile browsers; startup playback is
not evidence that every browser will allow it.

## Built-in versus Seedling

Choose built-in Bevy audio for simple playback/control/spatial panning.
`bevy_seedling 0.8` is the graph-based option for buses/effects, pooled emitters,
sample-accurate scheduling, richer routing, or HRTF through its Firewheel stack. It
pins Bevy `^0.19`: on Bevy 0.20 stay on built-in audio until a Seedling release
declares 0.20 support, and verify on crates.io before adding the dependency. HRTF is not a default feature; enable Seedling's `hrtf` feature (and
`hrtf_subjects` only when all embedded subjects are needed). Disable Bevy's built-in
`audio` feature when using Seedling so the two backends/types do not compete. Pin and
test the exact library release and platform.

## Choose the relevant deep dive

| Problem | Read |
|---|---|
| Players, playback modes, sinks, replay and cleanup | [Built-in audio](references/built-in-audio.md) |
| Mix model, crossfades, ducking, pause and asset lifetime | [Mixing, lifecycle, and transitions](references/mixing-lifecycle-and-transitions.md) |
| Spatial limits, browser unlock, accessibility and Seedling boundary | [Spatial, web, and Seedling](references/spatial-web-and-seedling.md) |

## Review checklist

- Playback entity ownership and completion mode are intentional.
- Runtime changes target the sink, not `PlaybackSettings`.
- Group/master changes update already-playing sinks without losing source gain.
- Transitions handle delayed assets, rapid state changes, pause, and entity cleanup.
- Exactly one listener exists and scale/pose follow the intended viewpoint.
- Browser audio unlock/failure is visible and recoverable.
- Dialogue has captions and important audio cues have non-audio equivalents.
- Headless tests exercise mixer/state logic without requiring an audio device.

## See also

- [`bevy-a11y`](../bevy-a11y/SKILL.md) — captions, cue alternatives, dynamic range, and controls.
- [`bevy-assets`](../bevy-assets/SKILL.md) — load state, handles, and asset lifetime.
- [`bevy-testing`](../bevy-testing/SKILL.md) — deterministic mixer/transition tests.
- [`bevy-migration-0-19-to-0-20`](../bevy-migration-0-19-to-0-20/SKILL.md) — `On<Add<T>>`, `Name`, feature changes.
- [Bevy audio module](https://docs.rs/bevy/0.20.1/bevy/audio/index.html)
- [`bevy_seedling 0.8`](https://docs.rs/bevy_seedling/0.8.0/bevy_seedling/)
