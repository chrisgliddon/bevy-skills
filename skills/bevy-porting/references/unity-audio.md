# bevy-porting — Unity Audio → bevy_audio

> Referenced from `bevy-porting/SKILL.md § Unity (priority)`.

## Architecture difference

| Unity | Bevy 0.20 |
|---|---|
| `AudioSource` component on a GameObject | `AudioPlayer` component on an entity |
| `AudioClip` asset | `Handle<AudioSource>` (asset; the name is overloaded — `bevy::audio::AudioSource` is the *asset*, not the player) |
| `AudioListener` on Camera (singleton) | Implicit (primary camera); opt in to spatial with `SpatialListener` |
| `AudioMixer` / `AudioMixerGroup` | No core equivalent; use marker components + a user system |
| `PlayClipAtPoint` (static one-shot) | Spawn entity with `AudioPlayer` + `PlaybackSettings::DESPAWN` |

## Basic playback

```rust
use bevy::prelude::*;

fn setup(asset_server: Res<AssetServer>, mut commands: Commands) {
    // One-shot SFX — entity despawns when the clip finishes.
    commands.spawn(AudioPlayer::new(
        asset_server.load::<AudioSource>("audio/jump.ogg"),
    ));

    // Looping music — entity persists.
    commands.spawn((
        AudioPlayer::new(asset_server.load::<AudioSource>("audio/music.ogg")),
        PlaybackSettings::LOOP,
    ));

    // Fire-and-forget (explicit despawn mode)
    commands.spawn((
        AudioPlayer::new(asset_server.load::<AudioSource>("audio/coin.ogg")),
        PlaybackSettings::DESPAWN,
    ));
}
```

`PlaybackSettings::ONCE` plays once and stops; `DESPAWN` plays once and removes the entity; `LOOP` repeats. These are constants on `PlaybackSettings`, not enum variants.

## Loading audio assets

```rust
// asset_server.load uses the path extension to pick the codec.
// Supported out of the box: .ogg (Vorbis), .mp3, .flac, .wav.
let handle: Handle<AudioSource> = asset_server.load("audio/music.ogg");
```

**Naming trap:** `bevy::audio::AudioSource` is the *asset* struct, not the playback component. `AudioPlayer` is the component. This is the reverse of Unity's naming.

## 3D spatial audio

```rust
use bevy::audio::SpatialScale; // not in the prelude
// `audio` is not implied by `3d`/`2d` since 0.19 — keep it in your feature list.
commands.spawn((
    AudioPlayer::new(asset_server.load::<AudioSource>("audio/footstep.ogg")),
    PlaybackSettings {
        spatial: true,
        // Not a component: set per emitter here, or app-wide via
        // `AudioPlugin::default_spatial_scale` / `DefaultSpatialScale`.
        spatial_scale: Some(SpatialScale::new(0.01)),
        ..PlaybackSettings::ONCE
    },
    Transform::from_xyz(3.0, 0.0, -5.0),
));

// Mark the listener entity (e.g. the camera)
commands.spawn((
    Camera3d::default(),
    SpatialListener::new(0.2),  // ear separation in metres
));
```

Unity's **Spatial Blend** slider and rolloff curves have no direct equivalent. Bevy uses inverse-distance falloff, scaled by `PlaybackSettings::spatial_scale` (or the `DefaultSpatialScale` resource). There is no built-in arbitrary rolloff curve. To replicate Unity's custom curves, write a system that reads listener distance and calls `sink.set_volume(Volume::Linear(computed))` on the entity's `&mut SpatialAudioSink` each frame.

## AudioMixer / groups (workaround)

`PlaybackSettings` is consumed at spawn time — **do not mutate it on already-playing entities**.
Control live volume via `AudioSink` (mono) or `SpatialAudioSink` (3-D). `set_volume`
takes `&mut self`, so query `&mut AudioSink`; `Volume` is an enum (`Linear` / `Decibels`),
there is no `Volume::new`:

```rust
use bevy::audio::{AudioSinkPlayback, Volume};

#[derive(Component)] struct MusicTag;
#[derive(Component)] struct SfxTag;

fn apply_volume(
    settings: Res<UserAudioSettings>,
    mut music: Query<&mut AudioSink, (With<MusicTag>, Without<SfxTag>)>,
    mut sfx:   Query<&mut AudioSink, (With<SfxTag>, Without<MusicTag>)>,
) {
    for mut sink in &mut music { sink.set_volume(Volume::Linear(settings.music_volume)); }
    for mut sink in &mut sfx   { sink.set_volume(Volume::Linear(settings.sfx_volume)); }
}
```

For a full mixer graph with sends, buses, and effects, consider **`bevy_kira_audio`** (community crate). It wraps `kira` and exposes a channel-based API closer to Unity's AudioMixer.

## Adaptive music / crossfades

Bevy core has no crossfade primitive. Implement with two `AudioPlayer` entities and a system that lerps volumes via `AudioSink::set_volume`:

```rust
fn crossfade(
    time: Res<Time>,
    mut state: ResMut<CrossfadeState>,
    mut query: Query<(&MusicTrackId, &mut AudioSink)>,
) {
    state.t = (state.t + time.delta_secs() / state.duration).min(1.0);
    let t = state.t;
    for (id, mut sink) in &mut query {
        let target = if id.0 == state.target { t } else { 1.0 - t };
        sink.set_volume(Volume::Linear(target));
    }
}
```

See [`bevy-animation/references/curves-and-tweening.md`](../../bevy-animation/references/curves-and-tweening.md) for `EasingCurve` / `EaseFunction` to shape the crossfade curve instead of a linear lerp.

## Gotchas

- **`AudioSource` naming collision.** `bevy::audio::AudioSource` is an asset (loaded from disk). The playback component is `AudioPlayer`. Searching for `AudioSource` in autocomplete will find the wrong type.
- **Spatial audio requires `Transform` on the emitter entity.** Without `Transform`, `SpatialListener` distance calculations produce silent output.
- **`SpatialListener` is optional.** If no entity has `SpatialListener`, Bevy falls back to the primary camera's transform. Attach `SpatialListener` explicitly for VR / split-screen setups.
- **No rolloff curves.** Bevy 0.20 uses inverse-distance only. Custom falloff = user system reading listener distance and calling `set_volume(Volume::Linear(…))` on `&mut SpatialAudioSink` each frame.
- **`audio` feature is opt-in when trimming (0.19).** `3d`/`2d`/`ui` no longer imply `audio`; add it (plus a codec feature such as `vorbis`) or `AudioPlayer` entities never play.
- **`bevy_kira_audio` 0.27 targets Bevy 0.20** (verified 2026-11); `bevy_seedling` 0.8 targets 0.19 only as of the same date.
- **`PlaybackSettings::DESPAWN` removes the entity.** Do not hold a strong `Handle<AudioSource>` only in the entity's `AudioPlayer` if you rely on the asset staying loaded — keep a copy elsewhere.

## See also

- [`../SKILL.md`](../SKILL.md) — bevy-porting top-level skill and Unity priority map.
- [`unity-architecture.md`](unity-architecture.md) — entity/component model differences that set the context for audio entity spawning.
- `bevy-core-concepts` — `Update` schedule and `Res<Time>` patterns used in the crossfade and group-volume systems above.
- `bevy_kira_audio` (third-party, <https://github.com/NiklasEi/bevy_kira_audio>) — full mixer graph, spatial audio channels, and dynamic audio if `bevy_audio` is too limited.
