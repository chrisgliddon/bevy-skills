# Bevy 0.18 UI — Interaction

## Quick reference

| Item | Purpose |
|---|---|
| `Button` | Marker component — makes a `Node` entity respond to mouse/touch. |
| `Interaction` | Component on the button entity; updated each frame by Bevy. |
| `Interaction::None` | Cursor not over the button (or button not hovered/pressed). |
| `Interaction::Hovered` | Cursor over the button, not pressed. |
| `Interaction::Pressed` | Button actively pressed. |
| `Changed<Interaction>` | ECS filter — query only runs for entities whose `Interaction` changed. |

## Common patterns

### Standard interaction system

```rust
use bevy::{input_focus::InputFocus, prelude::*};

fn button_system(
    mut input_focus: ResMut<InputFocus>,
    mut query: Query<
        (Entity, &Interaction, &mut BackgroundColor, &mut BorderColor, &mut Button),
        Changed<Interaction>,
    >,
) {
    for (entity, interaction, mut bg, mut border, mut button) in &mut query {
        match *interaction {
            Interaction::Pressed => {
                input_focus.set(entity);
                *bg = BackgroundColor(Color::srgb(0.35, 0.75, 0.35));
                *border = BorderColor::all(Color::srgb(1.0, 0.0, 0.0));
                button.set_changed(); // required — see Pitfalls
            }
            Interaction::Hovered => {
                input_focus.set(entity);
                *bg = BackgroundColor(Color::srgb(0.25, 0.25, 0.25));
                *border = BorderColor::all(Color::WHITE);
                button.set_changed();
            }
            Interaction::None => {
                input_focus.clear();
                *bg = BackgroundColor(Color::srgb(0.15, 0.15, 0.15));
                *border = BorderColor::all(Color::BLACK);
                // No set_changed() needed for None.
            }
        }
    }
}
```

### Reading interaction without mutation

```rust
use bevy::prelude::*;

fn log_clicks(query: Query<&Interaction, (Changed<Interaction>, With<Button>)>) {
    for interaction in &query {
        if *interaction == Interaction::Pressed {
            println!("Button clicked!");
        }
    }
}
```

### Multiple buttons with a tag component

```rust
use bevy::prelude::*;

#[derive(Component)]
enum MenuAction { Play, Quit }

fn menu_system(
    query: Query<(&Interaction, &MenuAction), (Changed<Interaction>, With<Button>)>,
) {
    for (interaction, action) in &query {
        if *interaction == Interaction::Pressed {
            match action {
                MenuAction::Play => { /* start game */ }
                MenuAction::Quit => { /* exit */ }
            }
        }
    }
}
```

## Pitfalls

### 1. `button.set_changed()` is required for accessibility

`Button::set_changed()` marks the `Button` component as mutated, which triggers
the accessibility system (`bevy_a11y`) to re-read the button's state and update
the AT (assistive technology) tree. If you omit it in `Pressed` and `Hovered`
arms, focus changes will be silent to screen readers.

```rust
// CORRECT — accessibility sees the press
Interaction::Pressed => {
    button.set_changed();
    // ...
}

// WRONG — accessibility misses this press
Interaction::Pressed => {
    // ... (no set_changed)
}
```

### 2. `Changed<Interaction>` does NOT fire at frame 0

At startup the `Interaction` component is inserted as `Interaction::None`. The
`Changed` filter fires only when a component *changes*, not when it is first
inserted (that is `Added<T>`). On frame 0, `button_system` does not run for any
button.

**Consequence:** The button's visual state on frame 0 is exactly what was
spawned — the `BorderColor`, `BackgroundColor`, etc. you set in `setup`. If
your spawn-time configuration and your `Interaction::None` arm differ, the
button will show the *spawn-time* values until the user hovers or Bevy fires an
internal interaction event.

This is the root cause of the "white border at spawn, black border after first
hover" bug. See [gotchas](gotchas.md) for the full explanation and the
screenshot-parity implication.

### 3. `Button` without `Node` does nothing

`Button` requires `Node` to participate in layout and receive hit-testing.
A free-floating `Button` component with no `Node` sibling will never register
`Interaction` changes.

### 4. `Interaction` is not inherited by children

Only the entity that has both `Button` and `Node` receives `Interaction` updates.
Child text or icon entities will not. Query for `Children` on the button and
fetch the text separately (see canonical pattern in SKILL.md).
