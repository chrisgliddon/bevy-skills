# Rapier setup, features, and scheduling

## Compatible lines for Bevy 0.20

| Engine | Crates | Version | Choose it for |
|---|---|---|---|
| Rapier | `bevy_rapier2d`, `bevy_rapier3d` | `0.37` | Mature 2D/3D rigid-body engine, broad feature set, official Rapier integration |
| Avian | `avian2d`, `avian3d` | `0.8` | ECS-native internals, modular plugins/schedules, Bevy-focused customization |

This skill's exact APIs are Rapier APIs. Do not silently translate component or
schedule names between engines.

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

The 0.36 `headless` feature was an empty marker and 0.37 removed it; disabling
default features is what removes renderer-facing helpers. Add `serde-serialize`, `parallel`, or `enhanced-determinism` only for a
measured requirement. `enhanced-determinism` and `simd8` are an unsupported feature
combination in Rapier 0.37's package metadata. `fem` enables soft bodies.

`async-collider`/`AsyncSceneCollider` are convenient when colliders come from Bevy
mesh or world assets. Server builds should usually bake simple collider data ahead of
time instead of enabling Rapier's renderer, image, or world-serialization conversion
features just to derive collision geometry.

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
resource.

For 2D pixel art, `RapierPhysicsPlugin::pixels_per_meter(value)` adjusts Rapier's
internal length scale. It does not rescale user-visible transforms, velocities, or
forces. In 3D, one Bevy unit per meter is the durable default.

## Sources

- [`bevy_rapier3d 0.37` features](https://docs.rs/crate/bevy_rapier3d/0.37.0/features)
- [`RapierPhysicsPlugin`](https://docs.rs/bevy_rapier3d/0.37.0/bevy_rapier3d/plugin/struct.RapierPhysicsPlugin.html)
- [`TimestepMode`](https://docs.rs/bevy_rapier3d/0.37.0/bevy_rapier3d/plugin/configuration/enum.TimestepMode.html)
- [`avian3d 0.8`](https://docs.rs/avian3d/0.8.0/avian3d/)
