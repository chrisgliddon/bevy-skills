# Minimal apps, schedules, and time

## Choose the smallest subject

| Behaviour | Harness |
|---|---|
| Pure meshing/math/state transition | ordinary Rust unit test |
| Query/system access and commands | `App::new()` with that system |
| Fixed schedule and timers | `App::new()` + `TimePlugin` + controlled time |
| Asset state machine | add `AssetPlugin` and a test asset source/loader |
| Renderer/window integration | dedicated rendered integration test |

Installing `DefaultPlugins` in every unit test adds global task pools, window/render
requirements, filesystem access, and startup work that can obscure the contract.

## Time strategies

`TimeUpdateStrategy` controls what happens when `app.update()` runs:

- `FixedTimesteps(n)`: after clock initialisation, advance real/virtual time by
  `Time<Fixed>::timestep() * n` and run exactly `n` fixed loops. Best for “one
  measured call equals one tick” tests.
- `ManualDuration(dt)`: add the same duration each update. Best for accumulation,
  zero-tick frames, catch-up, timers, and frame-rate variants.
- `ManualInstant(instant)`: set an absolute instant. Mutate it deliberately before
  each update when absolute time is part of the test.
- `Automatic`: wall-clock driven and normally wrong for deterministic tests.

Insert `Time::<Fixed>::from_hz(...)` before stepping. The first update initialises real
time with zero delta, including under `FixedTimesteps`; perform a setup update before
counting measured ticks or establish that zero-step frame in the expected sequence.
Bevy's own time tests make this initialisation visible.

## Test zero and catch-up ticks

For a 60 Hz fixed step, set `ManualDuration` to a smaller frame delta and count fixed
runs. Then use a duration larger than the timestep to exercise multiple fixed loops.
Assert simulation state after each `app.update()`, not only at the end, so off-by-one
accumulation is diagnosable.

For interpolation, inspect `Time<Fixed>::overstep_fraction()` after controlled
updates. Keep fixed authoritative pose and presentation pose separate so the test can
assert both contracts.

## Direct schedule runs

`world.run_schedule(MySchedule)` is useful for a custom schedule whose contract is
exactly one invocation. Running `FixedUpdate` directly bypasses Bevy's normal fixed
main loop, clock swapping, and message retention machinery; prefer controlled
`app.update()` when those semantics matter.

## Catch hidden ordering assumptions

With the `debug` cargo feature, `ScheduleBuildSettings { shuffle_seed: Some(seed), .. }`
(0.20) shuffles systems that have no explicit ordering before each build. Run the
suite under a few seeds in CI; a test that flips between seeds is missing a
`.before`/`.after`/`.chain()`. Render-side schedules (`Render`, `Core3d`, `Extract`)
now order their sets with `chain_weak` (0.20), so non-conflicting render systems may
run in either order; gameplay `Main` schedules are unchanged.

## Isolation

- Give each test a new `App`; do not share a mutable `World` across parallel tests.
- Seed RNG resources explicitly.
- Replace filesystem/network/platform services with injected traits/resources.
- Use stable entity tags/components rather than assuming entity index/order.
- Check both state and absence of forbidden side effects after failure paths.
