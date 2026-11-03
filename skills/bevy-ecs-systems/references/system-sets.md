# Bevy 0.20 — SystemSet deep dive

## Derive requirements

A `SystemSet` type must derive all five of `Hash`, `PartialEq`, `Eq`, `Clone`, `Debug`.

```rust
use bevy::prelude::*;

#[derive(SystemSet, Hash, PartialEq, Eq, Clone, Debug)]
enum GameLoop {
    Input,
    Simulate,
    Render,
}
```

Missing any of the five produces a compiler error from the macro.

## Registering systems into a set

`.in_set(MySet::Variant)` attaches the system to the set. A system can belong to several sets.

```rust
app.add_systems(Update, read_input.in_set(GameLoop::Input));
app.add_systems(Update, apply_physics.in_set(GameLoop::Simulate));
```

## Ordering sets with `configure_sets`

```rust
app.configure_sets(
    Update,
    (GameLoop::Input, GameLoop::Simulate, GameLoop::Render).chain(),
);
```

`.chain()` on a tuple is sugar for `.before(next)` on each consecutive pair:

```rust
app.configure_sets(Update, GameLoop::Input.before(GameLoop::Simulate));
app.configure_sets(Update, GameLoop::Simulate.before(GameLoop::Render));
```

## Strict versus weak (0.20)

`.chain()` makes every system in `Input` finish before any system in `Simulate` starts. `.chain_weak()` keeps an edge only between systems whose tracked data access conflicts; everything else may overlap.

```rust
app.configure_sets(Update, (GameLoop::Input, GameLoop::Simulate).chain_weak());
app.add_systems(Update, draw_hud.after_weak(GameLoop::Input));
```

Use weak ordering for throughput when systems only talk through ECS data. Keep `.chain()` when they talk through channels, atomics or `NonSend` state, which the scheduler cannot see. Bevy's own `PostUpdate` UI sets and the render-world sets switched to `.chain_weak()` in 0.20.

## Set-relative vs system-relative ordering

Prefer set-relative ordering. A new system added to `GameLoop::Simulate` automatically runs after everything in `GameLoop::Input`.

```rust
// Set-relative (preferred): new systems in Simulate inherit the ordering.
app.configure_sets(Update, GameLoop::Input.before(GameLoop::Simulate));

// System-relative (fragile): every new system needs its own edge.
app.add_systems(Update, new_system.after(read_input));
```

## `.chain()` on system tuples

```rust
app.add_systems(
    Update,
    (validate_input, consume_input, dispatch_input).chain(),
);
```

## Nested sets

```rust
#[derive(SystemSet, Hash, PartialEq, Eq, Clone, Debug)]
enum PhysicsSet { BroadPhase, NarrowPhase, Integration }

app.configure_sets(Update, PhysicsSet::BroadPhase.before(PhysicsSet::NarrowPhase));
app.configure_sets(Update, (PhysicsSet::NarrowPhase, PhysicsSet::Integration).chain());
// Then order PhysicsSet relative to GameLoop:
app.configure_sets(Update, GameLoop::Input.before(PhysicsSet::BroadPhase));
```

## See also

- [system-params.md](system-params.md) — what parameters systems can take.
- [ordering.md](ordering.md) — `.before`, `.after`, weak ordering, ambiguity, `.ambiguous_with`.
- [runtime-removal.md](runtime-removal.md) — removing a whole set at runtime.
