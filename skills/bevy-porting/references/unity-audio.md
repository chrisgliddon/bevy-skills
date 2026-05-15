# bevy-porting — Unity Audio → bevy_audio

> Referenced from `bevy-porting/SKILL.md § Unity (priority)`.

## Architecture difference

| Unity | Bevy 0.18 |
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
commands.spawn((
    AudioPlayer::new(asset_server.load::<AudioSource>("audio/footstep.ogg")),
    PlaybackSettings {
        spatial: true,
        ..PlaybackSettings::ONCE
    },
    SpatialScale::new(0.01),   // controls how distance maps to volume/pan
    Transform::from_xyz(3.0, 0.0, -5.0),
));

// Mark the listener entity (e.g. the camera)
commands.spawn((
    Camera3d::default(),
    SpatialListener::new(0.2),  // ear separation in metres
));
```

Unity's **Spatial Blend** slider and rolloff curves have no direct equivalent. Bevy uses inverse-distance falloff, scaled by `SpatialScale`. There is no built-in arbitrary rolloff curve. To replicate Unity's custom curves, write a system that reads listener distance and mutates `PlaybackSettings::volume` each frame.

## AudioMixer / groups (workaround)

`PlaybackSettings` is consumed at spawn time — **do not mutate it on already-playing entities**.
Control live volume via `AudioSink` (mono) or `SpatialAudioSink` (3-D):

```rust
#[derive(Component)] struct MusicTag;
#[derive(Component)] struct SfxTag;

fn apply_volume(
    settings: Res<UserAudioSettings>,
    music: Query<&AudioSink, With<MusicTag>>,
    sfx:   Query<&AudioSink, With<SfxTag>>,
) {
    for sink in &music { sink.set_volume(bevy::audio::Volume::new(settings.music_volume)); }
    for sink in &sfx   { sink.set_volume(bevy::audio::Volume::new(settings.sfx_volume)); }
}
```

For a full mixer graph with sends, buses, and effects, consider **`bevy_kira_audio`** (community crate). It wraps `kira` and exposes a channel-based API closer to Unity's AudioMixer.

## Adaptive music / crossfades

Bevy core has no crossfade primitive. Implement with two `AudioPlayer` entities and a system that lerps volumes via `AudioSink::set_volume`:

```rust
fn crossfade(
    time: Res<Time>,
    mut state: ResMut<CrossfadeState>,
    query: Query<(&MusicTrackId, &AudioSink)>,
) {
    state.t = (state.t + time.delta_secs() / state.duration).min(1.0);
    let t = state.t;
    for (id, sink) in &query {
        let target = if id.0 == state.target { t } else { 1.0 - t };
        sink.set_volume(bevy::audio::Volume::new(target));
    }
}
```

See [`bevy-animation/references/curves-and-tweening.md`](../../bevy-animation/references/curves-and-tweening.md) for `EasingCurve` / `EaseFunction` to shape the crossfade curve instead of a linear lerp.

## Gotchas

- **`AudioSource` naming collision.** `bevy::audio::AudioSource` is an asset (loaded from disk). The playback component is `AudioPlayer`. Searching for `AudioSource` in autocomplete will find the wrong type.
- **Spatial audio requires `Transform` on the emitter entity.** Without `Transform`, `SpatialListener` distance calculations produce silent output.
- **`SpatialListener` is optional.** If no entity has `SpatialListener`, Bevy falls back to the primary camera's transform. Attach `SpatialListener` explicitly for VR / split-screen setups.
- **No rolloff curves.** Bevy 0.18 uses inverse-distance only. Custom falloff = user system reading listener distance and calling `AudioSink::set_volume(Volume::new(…))` each frame.
- **`PlaybackSettings::DESPAWN` removes the entity.** Do not hold a strong `Handle<AudioSource>` only in the entity's `AudioPlayer` if you rely on the asset staying loaded — keep a copy elsewhere.

## See also

- [`../SKILL.md`](../SKILL.md) — bevy-porting top-level skill and Unity priority map.
- [`unity-architecture.md`](unity-architecture.md) — entity/component model differences that set the context for audio entity spawning.
- `bevy-core-concepts` — `Update` schedule and `Res<Time>` patterns used in the crossfade and group-volume systems above.
- `bevy_kira_audio` (third-party, <https://github.com/NiklasEi/bevy_kira_audio>) — full mixer graph, spatial audio channels, and dynamic audio if `bevy_audio` is too limited.
