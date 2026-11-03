# Bevy 0.20 UI — `children![]` and `.with_children(...)`

Two ways to attach child entities. Use `children![]` for declarative trees at spawn time; use `.with_children(...)` when you need the parent `Entity` or conditional children.

## Quick reference

| Form | When to use |
|---|---|
| `children![bundle1, bundle2, ...]` | Static trees, co-located with the parent bundle. In `bevy::prelude`. |
| `.with_children(\|p\| { p.spawn(...) })` | Loops, conditionals, or when you need the parent id. |

## Common patterns

### `children![]` inside a parent bundle tuple

```rust
use bevy::{picking::hover::Hovered, prelude::*, ui_widgets::Button};

fn ui_tree(asset_server: &AssetServer) -> impl Bundle {
    (
        Node {
            width: percent(100),
            height: percent(100),
            align_items: AlignItems::Center,
            justify_content: JustifyContent::Center,
            ..default()
        },
        children![(
            Button,
            Hovered::default(),
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
                Text::new("Click me"),
                TextFont {
                    font: asset_server.load("fonts/FiraSans-Bold.ttf").into(),
                    font_size: FontSize::Px(28.0),
                    ..default()
                },
                TextColor(Color::WHITE),
            )]
        )],
    )
}
```

### `.with_children(...)` for dynamic children

```rust
use bevy::{prelude::*, ui_widgets::Button};

fn spawn_menu(mut commands: Commands) {
    let items = ["New Game", "Load", "Settings", "Quit"];

    commands
        .spawn(Node {
            flex_direction: FlexDirection::Column,
            align_items: AlignItems::Center,
            row_gap: px(12),
            ..default()
        })
        .with_children(|parent| {
            for label in items {
                parent.spawn((
                    Button,
                    Node {
                        width: px(200),
                        height: px(48),
                        justify_content: JustifyContent::Center,
                        align_items: AlignItems::Center,
                        border_radius: BorderRadius::all(px(6)),
                        ..default()
                    },
                    BackgroundColor(Color::srgb(0.15, 0.15, 0.15)),
                    children![(
                        Text::new(label),
                        TextFont { font_size: FontSize::Px(22.0), ..default() },
                        TextColor(Color::WHITE),
                    )],
                ));
            }
        });
}
```

### Attaching an observer in the same bundle

`bevy::ui_widgets::observe(..)` is itself a bundle item, so click handlers sit next to the widget:

```rust
use bevy::{prelude::*, ui_widgets::{observe, Activate, Button}};

fn quit_button() -> impl Bundle {
    (
        Button,
        Node { width: px(120), height: px(40), ..default() },
        observe(|_: On<Activate>| info!("quit")),
    )
}
```

## Pitfalls

- **Bundle grouping.** Each comma-separated item is one child entity. Wrap multi-component children in a tuple.
- **`with_children` borrows `Commands`.** Use the `parent: &mut ChildSpawner` argument, not `commands.spawn`, inside the closure.
- **`Name` from `&str` must be `'static` (0.20).** `Name::new(label)` with a `&'static str` is fine; a `String` or `format!` result also works. A borrowed non-static `&str` no longer converts.
- **Children spawned later:** `commands.entity(parent).with_children(|p| ..)`.
