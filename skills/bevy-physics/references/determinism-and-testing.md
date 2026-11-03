# Determinism, networking, testing, and performance

## Fixed timestep is necessary, not sufficient

A fixed `dt` removes frame-rate variation from stepping. It does not by itself make a
whole game deterministic across machines or replays. Results can still depend on:

- initial state and body/collider insertion order;
- floating-point architecture/compiler behavior;
- parallel scheduling and unordered gameplay iteration;
- input quantization and the exact tick where commands are applied;
- asset-derived collider differences and dependency versions;
- sleeping, contacts, solver settings, and restored internal state.

Rapier's `enhanced-determinism` feature improves cross-platform deterministic math; it
is not a guarantee for the surrounding Bevy application. Rapier 0.37 does not support
combining it with `simd8`. Pin the engine, plugin, compiler/toolchain, features, tick
rate, units, and relevant configuration for any deterministic protocol.

## Networking and rollback

Choose and document the authority model:

- server authoritative: server simulates; clients interpolate/predict visuals;
- lockstep: every peer consumes identical tick-indexed inputs and compatible state;
- rollback: restore a complete deterministic snapshot, replay inputs, then reconcile;
- state replication: transmit authoritative pose/velocity and smooth presentation.

`serde-serialize` enables serialization support; it does not design a rollback-safe
snapshot. Decide whether the snapshot includes Rapier internals or a reconstructable
set of bodies, colliders, joints, velocities, sleeping state, and game state. When
restoring Bevy transforms into an existing context, evaluate
`RapierConfiguration::force_update_from_transform_changes` and verify the exact
resimulation path.

Keep physics handles out of durable/network identities. Use stable game entity IDs and
rebuild runtime handles/links.

## Headless verification harness

For deterministic regression tests:

1. Build with a lean Bevy/Rapier profile and `MinimalPlugins`.
2. Insert a known fixed clock and `TimestepMode::Fixed` before adding Rapier.
3. Spawn a tiny named scene from constants, not render assets.
4. Advance an exact number of ticks with exact tick-indexed inputs.
5. Assert position, velocity, collision state, and controller output with justified
   tolerances.
6. Run the same case with different render/update pacing when validating schedule
   independence.

Add matrix cases for collision groups, sensors, despawn/reparent, sleeping/wakeup,
fast bodies/CCD, extreme mass ratios, joints at their limits, slopes/stairs, and
multiple physics contexts when used. Assert that no `PhysicsQuarantineEvent` is
emitted; a quarantine means the scene produced NaN/inf state.

Do not use only screenshot/debug-line evidence. Record numeric results, crate/features,
target architecture, build profile, tick rate, random seed, and scene/input fixture.

## Performance evidence

Profile release-like builds on target hardware. Track at least:

- dynamic/kinematic/fixed body and collider counts;
- broad-phase candidate pairs and active contact pairs;
- solver islands, joints, and extra iterations;
- scene-query count/filter breadth;
- substeps and CCD-enabled bodies;
- collider complexity and asset-generation time;
- physics-step time percentiles, not only averages.

Prefer fewer/simple colliders, sleeping, collision layers, targeted CCD/solver
iterations, and bounded queries before enabling broad optimizations. `parallel` can
help large simulations and hurt small ones; benchmark. Debug rendering and inspector
overlays distort timings and should be measured separately.

## Sources

- [Rapier determinism guide](https://rapier.rs/docs/user_guides/rust/determinism/)
- [`TimestepMode`](https://docs.rs/bevy_rapier3d/0.37.0/bevy_rapier3d/plugin/configuration/enum.TimestepMode.html)
- [`RapierConfiguration`](https://docs.rs/bevy_rapier3d/0.37.0/bevy_rapier3d/plugin/configuration/struct.RapierConfiguration.html)
- [Rapier performance considerations](https://rapier.rs/docs/user_guides/rust/common_mistakes/)
