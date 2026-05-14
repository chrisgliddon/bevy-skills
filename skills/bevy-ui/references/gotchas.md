# Bevy 0.18 UI — Gotchas

Cross-cutting invariants that don't belong to a single sub-topic. Most of these
surfaced during the `ui_button` and `diplopod` parity rebuilds.

## 1. `Changed<Interaction>` does NOT fire at frame 0

**The invariant:** `Changed<Interaction>` fires only when the component *changes*,
not when it is first inserted. `Interaction::None` is inserted at spawn time.
Until something changes that value, any system filtered by `Changed<Interaction>`
will not run for that button.

**Consequence for visual state:** On frame 0 the button displays exactly what was
spawned — its spawn-time `BorderColor`, `BackgroundColor`, etc. If the
`Interaction::None` arm of your system would set different values, those do not
take effect until the first interaction event (hover, press, or an internal Bevy
focus event).

**Consequence for screenshot-based parity tests:** A screenshot taken at frame 0
captures spawn-time values. A screenshot taken at frame 120 (after Bevy may have
fired an internal interaction event) can differ. The parity test for `ui_button`
was designed around this — if a rebuild sets `BorderColor::all(Color::BLACK)` at
spawn time but the reference sets `BorderColor::all(Color::WHITE)`, they will
differ at frame 0.

**Fix:** Make spawn-time component values consistent with what `Interaction::None`
would produce, OR accept the frame-0 spawn appearance and let the interaction
system converge on the correct state thereafter.

See also: [interaction](interaction.md).

---

## 2. `button.set_changed()` — required for accessibility

Calling `button.set_changed()` in the `Pressed` and `Hovered` arms of your
interaction system is not optional if your app targets accessibility. It marks
the `Button` component as mutated, which triggers `bevy_a11y` to refresh the
button's node in the platform accessibility tree.

Without it:
- Screen readers do not announce hover/press changes.
- `InputFocus` changes alone are not sufficient to update the AT.

See also: [interaction](interaction.md), [accessibility](accessibility.md).

---

## 3. The "white border → black border" bug

**Symptoms:** A button spawned with `BorderColor::all(Color::WHITE)` shows a white
border for exactly one frame, then switches to a black border without any user
interaction. The switch happens around frame 60–120 depending on the platform.

**Root cause:** Bevy's internal accessibility or focus system fires a synthetic
`Interaction` event shortly after startup. When that fires, the
`Interaction::None` arm of the `button_system` runs and overwrites the spawn-time
border color with whatever the system sets (e.g. `BorderColor::all(Color::BLACK)`).

**Why it's confusing:** The `Changed<Interaction>` query *did* fire — but from
`None → None` triggered by Bevy's internal bookkeeping, not from a user action.

**Fix options:**
1. Spawn the button with the border color that `Interaction::None` would set
   (consistent spawn state). This is the approach in the parity reference.
2. Track `Interaction` state explicitly and only mutate border color on
   *meaningful* transitions (e.g. `None → Hovered`, `Hovered → Pressed`).

---

## 4. `InputFocus` must be explicitly initialized

`app.init_resource::<InputFocus>()` is required. `DefaultPlugins` does not insert
`InputFocus`. Missing this causes a panic at schedule-build when any system
requests `ResMut<InputFocus>`.

See also: [accessibility](accessibility.md).

---

## 5. `children![]` bundle grouping

Each item in `children![]` is a *single* bundle. Multiple components for one
child entity must be wrapped in a tuple:

```rust
// CORRECT — one child entity with three components
children![(Button, Node { .. }, BackgroundColor(Color::BLACK))]

// WRONG — three separate child entities (Button-only, Node-only, BackgroundColor-only)
children![Button, Node { .. }, BackgroundColor(Color::BLACK)]
```

See also: [children-macro](children-macro.md).

---

## 6. Interaction requires both `Button` AND `Node`

A `Button` component alone is a marker. The UI hit-testing and `Interaction`
update systems only run on entities that have both `Button` and `Node`. If a
button never transitions from `Interaction::None`, check that the entity has a
`Node` with a nonzero `width` and `height`.

---

## 7. `bevy::input_focus::InputFocus` is not in the prelude

```rust
// Must import explicitly:
use bevy::input_focus::InputFocus;

// This will NOT compile — InputFocus is not in bevy::prelude:
use bevy::prelude::*; // InputFocus not included
```
