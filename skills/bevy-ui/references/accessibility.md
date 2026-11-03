# Bevy 0.20 UI — Accessibility and focus

## Quick reference

| Item | Purpose |
|---|---|
| `bevy::input_focus::InputFocus` | Resource holding the logically focused entity. Inserted by `InputFocusPlugin`, part of `DefaultPlugins` since 0.19. |
| `input_focus.get()` | `Option<Entity>`. |
| `input_focus.set(entity, FocusCause::Pressed)` | Move focus. Takes a `FocusCause` since 0.19 (fields went private). |
| `input_focus.clear()` | Drop focus. |
| `FocusCause::{Navigated, Pressed, Auto}` | `Auto` is new in 0.20 (emitted by `AutoFocus`). |
| `bevy::input_focus::AutoFocus` | Marker: entity takes focus when spawned. |
| `bevy::input_focus::tab_navigation::{TabNavigationPlugin, TabGroup, TabIndex}` | Tab / Shift-Tab keyboard navigation. |
| `AccessibleLabel` | In `bevy::prelude`. Spoken name for the accessibility tree. |
| `ui_widgets::Button` | Requires `AccessibilityNode(Role::Button)` — nothing to do by hand. |

## Common patterns

### Keyboard-navigable button

```rust
use bevy::{
    input_focus::tab_navigation::{TabGroup, TabIndex, TabNavigationPlugin},
    prelude::*,
    ui_widgets::{observe, Activate, Button},
};

fn main() {
    App::new()
        .add_plugins((DefaultPlugins, TabNavigationPlugin))
        .add_systems(Startup, setup)
        .run();
}

fn setup(mut commands: Commands) {
    commands.spawn(Camera2d);
    commands.spawn((
        Node { width: percent(100), height: percent(100), ..default() },
        TabGroup::default(),
        children![(
            Button,
            TabIndex(0),
            AccessibleLabel("Start game".into()),
            Node { width: px(160), height: px(48), ..default() },
            observe(|_: On<Activate>| info!("activated by click, Enter, or Space")),
        )],
    ));
}
```

### Reading and moving focus by hand

```rust
use bevy::{input_focus::{FocusCause, InputFocus}, prelude::*};

fn focus_first_button(
    mut focus: ResMut<InputFocus>,
    buttons: Query<Entity, With<bevy::ui_widgets::Button>>,
) {
    if focus.get().is_none()
        && let Some(first) = buttons.iter().next()
    {
        focus.set(first, FocusCause::Navigated);
    }
}
```

## Pitfalls

- **Do not `init_resource::<InputFocus>()`.** 0.18 required it; 0.19+ `DefaultPlugins` inserts it. Re-initialising silently resets focus state.
- **`input_focus.0` no longer compiles (0.19).** Use `get` / `set` / `clear`.
- **Exhaustive `FocusCause` matches break in 0.20.** Add the `Auto` arm.
- **`button.set_changed()` is obsolete.** It belonged to the deprecated `ui::widget::Button`. `ui_widgets::Button` ships its own `AccessibilityNode`.
- **Escape propagates out of text inputs (0.20).** A focused `EditableText` + `TextInput` clears focus on Escape and lets the event bubble, so a dialog's Escape handler fires on the same press.
- **`bevy_picking` no longer enables `bevy_input_focus` (0.19).** Use the `ui` feature collection; it carries `ui_picking` and `bevy_input_focus`.
- **`InputFocus` is not in the prelude.** Import `bevy::input_focus::InputFocus`.
