# Bevy 0.20 UI — Interaction

## Quick reference

| Item | Path | Purpose |
|---|---|---|
| `Button` | `bevy::ui_widgets::Button` | Headless widget. Tracks `Pressed`, fires `Activate`. Requires `AccessibilityNode(Role::Button)`. |
| `Hovered(pub bool)` | `bevy::picking::hover::Hovered` | Insert `Hovered::default()`; the picking backend updates it only on enter/leave. `.get()` reads it. |
| `Pressed` | `bevy::ui::Pressed` | Unit marker inserted while the pointer is held on the button. Query with `Has<Pressed>`. |
| `Activate { entity }` | `bevy::ui_widgets::Activate` | `EntityEvent` fired on click release, or Enter/Space when focused. |
| `ActivateOnPress` | `bevy::ui_widgets::ActivateOnPress` | Marker: fire `Activate` on pointer down (menus). |
| `InteractionDisabled` | `bevy::ui::InteractionDisabled` | Marker: button ignores input. Branch on `Has<InteractionDisabled>` to grey it out. |
| `observe(..)` | `bevy::ui_widgets::observe` | Bundle helper that attaches an observer to the spawned entity. |

None of `Button`, `Hovered`, `Pressed` are in `bevy::prelude`. The prelude `Button` is the deprecated `ui::widget::Button`.

## Common patterns

### Polling system (the canonical pattern)

```rust
use bevy::{picking::hover::Hovered, prelude::*, ui::Pressed, ui_widgets::Button};

fn style_buttons(
    mut query: Query<(&Hovered, Has<Pressed>, &mut BackgroundColor), With<Button>>,
) {
    for (hovered, pressed, mut bg) in &mut query {
        *bg = match (hovered.get(), pressed) {
            (_, true) => BackgroundColor(Color::srgb(0.35, 0.75, 0.35)),
            (true, false) => BackgroundColor(Color::srgb(0.25, 0.25, 0.25)),
            (false, false) => BackgroundColor(Color::srgb(0.15, 0.15, 0.15)),
        };
    }
}
```

### Click handling with `Activate`

```rust
use bevy::{prelude::*, ui_widgets::{observe, Activate, Button}};

#[derive(Component, Clone, Copy)]
enum MenuAction { Play, Quit }

fn spawn_menu_button(mut commands: Commands) {
    commands.spawn((
        Button,
        MenuAction::Play,
        Node { width: px(200), height: px(48), ..default() },
        observe(|activate: On<Activate>, actions: Query<&MenuAction>| {
            match actions.get(activate.entity) {
                Ok(MenuAction::Play) => info!("play"),
                Ok(MenuAction::Quit) => info!("quit"),
                Err(_) => {}
            }
        }),
    ));
}
```

### Observers instead of polling

`Pressed` is inserted and removed, so lifecycle observers see every transition. The bundle generic moved onto the event type in 0.20: `On<Insert<Pressed>>`, not `On<Insert, Pressed>`.

```rust
use bevy::{prelude::*, ui::Pressed, ui_widgets::Button};

fn on_pressed(insert: On<Insert<Pressed>>, mut bg: Query<&mut BackgroundColor, With<Button>>) {
    if let Ok(mut bg) = bg.get_mut(insert.entity) {
        *bg = BackgroundColor(Color::srgb(0.35, 0.75, 0.35));
    }
}

fn on_released(remove: On<Remove<Pressed>>, mut bg: Query<&mut BackgroundColor, With<Button>>) {
    if let Ok(mut bg) = bg.get_mut(remove.entity) {
        *bg = BackgroundColor(Color::srgb(0.15, 0.15, 0.15));
    }
}
// app.add_observer(on_pressed).add_observer(on_released);
```

### Raw pointer events (no widget)

```rust
use bevy::prelude::*;

fn on_click(click: On<PointerClick>) {
    // 0.20: flat events. 0.19 was On<Pointer<Click>> with click.pointer_location.position.
    info!("clicked {} at {:?}", click.entity, click.pointer.position);
}
```

## Pitfalls

1. **`Interaction` is deprecated (0.20).** `Changed<Interaction>` compiles with a warning but is on its way out. Migrate to `Hovered` + `Has<Pressed>`; `Interaction::None` has no replacement because absence of both is the idle state.
2. **No `Hovered` component, no hover.** The picking backend only maintains `Hovered` on entities that carry it. Spawn `Hovered::default()` on the button.
3. **`Hovered` is immutable (`#[component(immutable)]`).** Read it with `&Hovered`; never `&mut Hovered`.
4. **`Hovered` covers descendants.** It is `true` while the pointer is over the entity or any child (CSS `:hover` semantics), so the text child does not need its own.
5. **`Button` still needs a `Node` with a size.** Hit-testing uses the `ComputedNode` rect; a zero-size node never hovers.
6. **Keyboard activation needs focus.** Enter/Space fire `Activate` only when the button holds `InputFocus`. Add `TabIndex(0)` under a `TabGroup` with `TabNavigationPlugin` — see [accessibility.md](accessibility.md).
