# Bevy 0.18 — SystemSet deep dive

## Derive requirements

A type used as a `SystemSet` must derive all five of:
`Hash`, `PartialEq`, `Eq`, `Clone`, `Debug`.

```rust
use bevy::prelude::*;

#[derive(SystemSet, Hash, PartialEq, Eq, Clone, Debug)]
enum GameLoop {
    Input,
    Simulate,
    Render,
}
```

Missing any of those five traits produces a compiler error from the macro.

## Registering systems into a set

`.in_set(MySet::Variant)` attaches the system to the set. A system can belong to
multiple sets simultaneously.

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

`.chain()` on a tuple is syntactic sugar for `.before(next)` on each set in
sequence. The above is equivalent to:

```rust
app.configure_sets(Update, GameLoop::Input.before(GameLoop::Simulate));
app.configure_sets(Update, GameLoop::Simulate.before(GameLoop::Render));
```

## Set-relative vs system-relative ordering

Prefer set-relative ordering (`configure_sets`) over chaining individual
systems. When you add a new system into `GameLoop::Simulate`, it automatically
runs after everything in `GameLoop::Input` — no update to system ordering needed.

```rust
// Set-relative (preferred): new systems in Simulate auto-inherit ordering
app.configure_sets(Update, GameLoop::Input.before(GameLoop::Simulate));

// System-relative (fragile): must manually order every new system
app.add_systems(Update, new_system.after(read_input));
```

## `.chain()` on system tuples

`.chain()` also works directly on a tuple of systems, running them in sequence
within a single `add_systems` call:

```rust
app.add_systems(
    Update,
    (validate_input, consume_input, dispatch_input).chain(),
);
```

## Nested sets

Sets can be members of other sets. Configure the nested relationship the same way:

```rust
#[derive(SystemSet, Hash, PartialEq, Eq, Clone, Debug)]
enum PhysicsSet { BroadPhase, NarrowPhase, Integration }

app.configure_sets(Update, PhysicsSet::BroadPhase.before(PhysicsSet::NarrowPhase));
app.configure_sets(Update, (PhysicsSet::NarrowPhase, PhysicsSet::Integration).chain());
// Then order the PhysicsSet relative to GameLoop:
app.configure_sets(Update, GameLoop::Input.before(PhysicsSet::BroadPhase));
```

## See also

- [system-params.md](system-params.md) — what parameters systems can take.
- [ordering.md](ordering.md) — `.before`, `.after`, ambiguity, `.ambiguous_with`.
- [runtime-removal.md](runtime-removal.md) — removing a whole set at runtime.
