# Built-in Bevy audio

## Component lifecycle

`AudioPlayer<Source>` carries a strong asset handle. Its required
`PlaybackSettings` configures initial playback. When the asset is ready and playback
starts, Bevy inserts one of:

- `AudioSink` for ordinary audio;
- `SpatialAudioSink` when `PlaybackSettings.spatial` is true.

The sink is the live control surface. It may not exist yet while the asset/backend is
starting, so systems must query it optionally rather than unwrap it.

```rust
use bevy::{audio::AudioSinkPlayback, prelude::*};

#[derive(Component)]
struct PausableAudio;

fn set_audio_paused(
    paused: Res<State<GamePause>>,
    sinks: Query<&AudioSink, With<PausableAudio>>,
) {
    for sink in &sinks {
        if *paused.get() == GamePause::Paused {
            sink.pause();
        } else {
            sink.play();
        }
    }
}

#[derive(States, Clone, Copy, Debug, Default, Eq, Hash, PartialEq)]
enum GamePause {
    #[default]
    Running,
    Paused,
}
```

The playback trait exposes volume, speed, play/pause, mute, position, seek, stop, and
empty status. `try_seek` can block briefly and may be unsupported by the decoder; do
not call it every frame.

## Pick a completion mode

| Mode | End behaviour | Typical use |
|---|---|---|
| `ONCE` | leaves drained player/sink entity | explicit owner inspects/reuses entity components |
| `LOOP` | repeats | music/ambience/machine loops |
| `DESPAWN` | despawns entity and children | fire-and-forget one-shot entity |
| `REMOVE` | removes audio components | keep non-audio entity alive |

A drained `ONCE` player is not replayable as-is. Removing the sink while the same
`AudioPlayer` remains restarts it, which can be useful deliberately and surprising
accidentally. For frequent one-shots, spawn with `DESPAWN` or manage an explicit pool;
measure entity/backend churn before inventing a pool.

## Initial versus live settings

`PlaybackSettings` fields—mode, volume, speed, paused, muted, spatial, spatial scale,
start position, and duration—are sampled when playback starts. Later edits do not
apply. `GlobalVolume` also affects initial playback only. Keep the desired mixer state
in application resources and apply it to newly added sinks plus existing sinks.

## Assets and errors

Audio waits for its asset handle to become available. For transitions and UI latency,
preload and inspect `AssetServer` load state instead of assuming a spawned player is
audible immediately. Retain source handles through the player/asset collection and
surface decode/device failures in diagnostics or UX. Avoid triggering an unbounded
number of identical sounds in one frame; apply per-cue concurrency/rate limits.

Primary source: [Bevy audio module](https://docs.rs/bevy/0.20.1/bevy/audio/index.html).
