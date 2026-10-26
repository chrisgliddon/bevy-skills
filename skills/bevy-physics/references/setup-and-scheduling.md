# Rapier setup, features, and scheduling

Target: **Bevy 0.20 / bevy_rapier 0.37.0**. Source-reviewed; Rust compile/runtime
checks remain pending in the [readiness record](../../bevy/references/bevy-020-readiness.md).

## Choose the matching engine line

| Bevy | Crates | Version | Status |
|---|---|---|---|
| `0.20` | `bevy_rapier2d`, `bevy_rapier3d` | `0.37.0` | Published manifests declare Bevy `^0.20`; this guide's target |
| `0.19` | `bevy_rapier2d`, `bevy_rapier3d` | `0.36` | [Preserved older guidance](bevy-019-compatibility.md), not a 0.20 fallback |

This skill's exact APIs are Rapier APIs. Do not silently translate component or
schedule names between engines. Avian's compatible 0.20 line is not established by
this update; check its manifest before choosing it. The active upstream is now
[`dimforge/rapier`, `bindings/bevy_rapier`](https://github.com/dimforge/rapier/tree/master/bindings/bevy_rapier);
the former `dimforge/bevy_rapier` repository is archived.

## Cargo profiles

Convenient game profile:

```toml
bevy = "0.20"
bevy_rapier3d = "0.37" # use bevy_rapier2d for Vec2 physics
```

Rapier 0.37's default features are `dim3`/`dim2`, `async-collider`, the matching
debug-render backend, `picking-backend`, and `to-bevy-mesh`. Defaults make sense for
authoring and rendered games, but they pull Bevy asset/render crates even if the
debug plugin is never added.

Lean 3D server profile:

```toml
bevy = { version = "0.20", default-features = false, features = [
  "default_app", "multi_threaded"
] }
bevy_rapier3d = { version = "0.37", default-features = false, features = [
  "dim3"
] }
```

**Do not add `headless`: that unused feature was removed in 0.37.** Disabling default
features removes renderer-facing helpers; Cargo feature unification can still enable
them through another dependency. Inspect `cargo tree -e features` in the actual app.
Add `serde-serialize`, `parallel`, or `enhanced-determinism` only for a
measured requirement. `enhanced-determinism` and `simd8` are an unsupported feature
combination in Rapier 0.37's package metadata.

`async-collider`/`AsyncSceneCollider` are convenient when colliders come from Bevy
mesh or world assets. Server builds should usually bake simple collider data ahead of
time instead of enabling Rapier's renderer, image, or world-serialization conversion
features just to derive collision geometry. A headless app still needs transform/time
plugins: `MinimalPlugins` does not include `TransformPlugin`.

## Three timestep choices

### Default: `PostUpdate` + variable step

`RapierPhysicsPlugin::default()` installs its phases in `PostUpdate` and initializes:

```rust
TimestepMode::Variable {
    max_dt: 1.0 / 60.0,
    time_scale: 1.0,
    substeps: 1,
}
```

Order game systems in `PostUpdate` around `PhysicsSet` if this is intentional.

### Tick-coupled simulation: `FixedUpdate`

Call `.in_fixed_schedule()`, set `Time<Fixed>`, and set `TimestepMode::Fixed` to the
same `dt`. The plugin warns if it is placed in `FixedUpdate` with another timestep
mode. Input sampling can happen in `PreUpdate`, but convert it to durable action state
before consuming it in a fixed tick that may run zero or several times per frame.

### Smooth frame-coupled output: interpolated mode

Keep Rapier in its default schedule, insert `TimestepMode::Interpolated`, and add
`TransformInterpolation` to bodies that need smoothing. Do not also run a second
visual interpolation system over the same `Transform`.

Substeps split one physics tick into solver steps. They can improve fast/contact-heavy
simulation, but they do not create extra gameplay ticks or justify unbounded values.
Measure before raising them.

## Phase ordering

`PhysicsSet` is a chained pipeline:

1. `SyncBackend` copies changed Bevy components into Rapier.
2. `StepSimulation` advances physics and updates the query pipeline.
3. `Writeback` updates Rapier-facing components, `CollidingEntities`, and transforms.

Systems that set velocity, force, impulses, kinematic translation, or colliders run
before `SyncBackend`. Systems that consume poses, controller output, or collisions run
after `Writeback`. These constraints must be configured in the schedule selected for
the plugin.

## Configuration and multiple worlds

`TimestepMode` is a resource. `RapierConfiguration` is a component on each context
entity, allowing independent worlds with different gravity and activation. The
default context has `DefaultRapierContext`; use `ReadRapierContext`/
`WriteRapierContext`, or a filtered context query, instead of assuming a singleton
resource. In 0.37, an entity without an explicit context link inherits the closest
linked ancestor's context before falling back to the default. Re-test reparenting
and multiple-world hierarchies rather than assuming every unlinked child is default.

For 2D pixel art, `RapierPhysicsPlugin::pixels_per_meter(value)` adjusts Rapier's
internal length scale. It does not rescale user-visible transforms, velocities, or
forces. In 3D, one Bevy unit per meter is the durable default.

## Sources

- [`bevy_rapier3d 0.37` features](https://docs.rs/crate/bevy_rapier3d/0.37.0/features)
- [`RapierPhysicsPlugin`](https://docs.rs/bevy_rapier3d/0.37.0/bevy_rapier3d/plugin/struct.RapierPhysicsPlugin.html)
- [`TimestepMode`](https://docs.rs/bevy_rapier3d/0.37.0/bevy_rapier3d/plugin/configuration/enum.TimestepMode.html)
- [Published 0.37.0 manifest](https://docs.rs/crate/bevy_rapier3d/0.37.0/source/Cargo.toml)
- [Rapier binding changelog](https://github.com/dimforge/rapier/blob/475caa3ff4646fd9a796b67d14116256f4962bc7/bindings/bevy_rapier/CHANGELOG.md)
