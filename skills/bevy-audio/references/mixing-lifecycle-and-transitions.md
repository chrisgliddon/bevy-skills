# Mixing, lifetime, and transitions

## Application-owned mix model

Keep independent values for:

```text
effective gain = master × group × user/source × transition × ducking × accessibility
```

Do not repeatedly multiply a sink's current volume; that compounds error. Store the
source/base volume as data and recompute the effective target from authoritative
settings. Apply to sinks when they are added and whenever any contributing value
changes.

Use decibels for authored mix offsets and expose a perceptual slider curve. Reserve a
true mute state rather than relying on an extremely small floating-point gain. Offer
separate music, effects, dialogue, ambience, and UI controls; accessibility may also
require dynamic-range/compression options beyond volume.

## Transition state machine

Represent music changes explicitly:

```text
Idle -> LoadingNext -> Crossfading { old, new, progress } -> Playing(new)
                       | new request
                       -> retarget/cancel by documented policy
```

1. Request and retain the next asset.
2. Wait for readiness or take an explicit failure/timeout path.
3. Spawn it looping at silence and wait until its sink exists.
4. Fade new upward and old downward from their current gains.
5. At completion, stop/despawn the old entity and clear transition markers.

Using the current gains when retargeting prevents jumps during rapid state changes.
Use frame-rate-independent progress from elapsed duration. Choose `Time<Virtual>` if
pause should freeze a transition and `Time<Real>` if audio should continue through
game pause.

Built-in starts are not sample-synchronised, so crossfading stems on a musical bar or
performing gapless beat scheduling is a signal to adopt a sample-accurate audio graph.

## Ducking and priority

Dialogue ducking should be attack/hold/release state, not “set music to 0.5 when a
line starts.” Track concurrent ducking sources, take the strongest active request,
and release only when all relevant sources finish. Bound simultaneous SFX per cue or
spatial area and choose which sounds may be stolen; otherwise effect bursts can create
backend load and make important cues inaudible.

## Tests

Extract mix/transition math from the audio device:

- effective volume from master/group/source/mute states;
- fade endpoints and frame-rate variants;
- rapid retarget without gain discontinuity;
- missing/delayed asset and missing sink;
- concurrent duck requests and release ordering;
- pause clock choice and cleanup ownership.

Integration tests may assert components and sink-independent state. Do not require a
CI audio output device to prove deterministic mixer logic.
