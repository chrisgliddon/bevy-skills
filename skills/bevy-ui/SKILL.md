---
name: bevy-ui
description: Use when building UI with `Node`, `Button`, `children![]`, `TextFont`, `InputFocus`, `BackgroundColor`, `BorderColor`, or `BorderRadius` in Bevy 0.18. Covers layout, text styling, interaction handling, colors, palettes, accessibility, and the frame-0 `Changed<Interaction>` invariant.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "2"
  area: ui
  bevy_version: "0.18"
---

# Bevy 0.18 — UI

## When to use this skill

- Spawning any `Node`-based UI element (panels, buttons, text labels, overlays).
- Handling `Button` interaction states (`Hovered`, `Pressed`, `None`).
- Styling text with `TextFont`, `TextColor`, `TextShadow`.
- Setting `BackgroundColor`, `BorderColor`, `BorderRadius` on a widget.
- Using palette constants from `bevy::color::palettes`.
- Wiring up `InputFocus` for accessibility / screen-reader integration.
- Nesting child entities with `children![]` or `.with_children(...)`.
- Debugging a button that shows the wrong color at frame 0 or frame 120.

## Canonical pattern

Centered button — full-screen flex container, rounded pill button, text child.

```rust
use bevy::{input_focus::InputFocus, prelude::*};

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .init_resource::<InputFocus>()
        .add_systems(Startup, setup)
        .add_systems(Update, button_system)
        .run();
}

fn setup(mut commands: Commands, asset_server: Res<AssetServer>) {
    commands.spawn(Camera2d);
    commands.spawn((
        // Full-screen flex container — centres the button.
        Node {
            width: percent(100),
            height: percent(100),
            align_items: AlignItems::Center,
            justify_content: JustifyContent::Center,
            ..default()
        },
        children![(
            Button,
            Node {
                width: px(150),
                height: px(65),
                border: UiRect::all(px(5)),
                justify_content: JustifyContent::Center,
                align_items: AlignItems::Center,
                border_radius: BorderRadius::MAX,
                ..default()
            },
            BorderColor::all(Color::WHITE),
            BackgroundColor(Color::BLACK),
            children![(
                Text::new("Button"),
                TextFont {
                    font: asset_server.load("fonts/FiraSans-Bold.ttf"),
                    font_size: 33.0,
                    ..default()
                },
                TextColor(Color::srgb(0.9, 0.9, 0.9)),
                TextShadow::default(),
            )]
        )],
    ));
}

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
                button.set_changed(); // signal accessibility system
            }
            Interaction::Hovered => {
                input_focus.set(entity);
                *bg = BackgroundColor(Color::srgb(0.25, 0.25, 0.25));
                *border = BorderColor::all(Color::WHITE);
                button.set_changed();
            }
            Interaction::None => {
                input_focus.clear();
                *bg = BackgroundColor(Color::BLACK);
                *border = BorderColor::all(Color::BLACK);
                // No set_changed() for None — not required by the a11y system.
            }
        }
    }
}
```

## Topics

| Topic | Reference |
|---|---|
| `Node`, `Val`, `FlexDirection`, `AlignItems`, layout recipes | [references/layout.md](references/layout.md) |
| `Text::new`, `TextFont`, `TextColor`, `TextShadow`, default font swap | [references/text.md](references/text.md) |
| `Button`, `Interaction`, `Changed<Interaction>`, footguns | [references/interaction.md](references/interaction.md) |
| `BackgroundColor`, `BorderColor`, `BorderRadius` constructors | [references/colors-and-borders.md](references/colors-and-borders.md) |
| `bevy::color::palettes::{basic,css,tailwind}` | [references/palettes.md](references/palettes.md) |
| `InputFocus`, `init_resource`, `set` / `clear` | [references/accessibility.md](references/accessibility.md) |
| `children![]` vs `.with_children(...)` | [references/children-macro.md](references/children-macro.md) |
| Cross-cutting invariants, frame-0 trap, black-border bug | [references/gotchas.md](references/gotchas.md) |

## Gotchas

1. **`Changed<Interaction>` does NOT fire at frame 0.** The button shows its
   spawn-time components (e.g. `BorderColor::all(Color::WHITE)`) on the first
   frame, not the output of `button_system`. Screenshot-based parity tests
   taken at frame 0 must account for this. See [references/gotchas.md](references/gotchas.md).

2. **Call `button.set_changed()` in `Hovered` and `Pressed` arms.** This is a
   manual dirty-marker required so the accessibility system re-processes the
   button. Omitting it causes screen readers to miss focus changes. See
   [references/interaction.md](references/interaction.md).

## See also

- `bevy-cameras` — spawn a `Camera2d` alongside any UI scene.
- `bevy-ecs-queries` — `Changed<T>`, `Added<T>`, query filters used in `button_system`.
- `bevy-fluent` — localized UI text via `FluentText<T>`.
- `bevy-cargo-features` — feature flags; the `ui` collection enables all UI crates.
