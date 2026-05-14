# Bevy 0.18 UI — `children![]` and `.with_children(...)`

Bevy 0.18 offers two ways to attach child entities to a UI node. Use `children![]`
for declarative tree construction at spawn time; use `.with_children(...)` when
you need a reference to the parent entity or want to spawn children conditionally.

## Quick reference

| Form | When to use |
|---|---|
| `children![bundle1, bundle2, ...]` | Declarative, co-located with the parent bundle. Best for static UI trees. |
| `.with_children(\|p\| { p.spawn(...) })` | When you need the parent `Entity`, or for dynamic / conditional children. |

`children![]` is in `bevy::prelude` as of Bevy 0.18.

## Common patterns

### `children![]` inside a parent bundle tuple

This is the preferred form for static UI trees. The macro expands to a
`ChildOf`-wiring bundle that Bevy resolves at spawn time.

```rust
use bevy::prelude::*;

fn ui_tree(asset_server: &AssetServer) -> impl Bundle {
    (
        // Parent node — full-screen flex container
        Node {
            width: percent(100),
            height: percent(100),
            align_items: AlignItems::Center,
            justify_content: JustifyContent::Center,
            ..default()
        },
        children![(
            // Child — the button
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
                // Grandchild — the text label
                Text::new("Click me"),
                TextFont {
                    font: asset_server.load("fonts/FiraSans-Bold.ttf"),
                    font_size: 28.0,
                    ..default()
                },
                TextColor(Color::WHITE),
            )]
        )],
    )
}
```

### `.with_children(...)` for dynamic children

Use this form when you need a loop, conditional spawning, or access to the parent
entity ID.

```rust
use bevy::prelude::*;

fn spawn_menu(mut commands: Commands, asset_server: Res<AssetServer>) {
    let items = ["New Game", "Load", "Settings", "Quit"];

    commands
        .spawn(Node {
            flex_direction: FlexDirection::Column,
            align_items: AlignItems::Center,
            row_gap: Val::Px(12.0),
            ..default()
        })
        .with_children(|parent| {
            for label in &items {
                parent.spawn((
                    Button,
                    Node {
                        width: px(200),
                        height: px(48),
                        justify_content: JustifyContent::Center,
                        align_items: AlignItems::Center,
                        border_radius: BorderRadius::all(Val::Px(6.0)),
                        ..default()
                    },
                    BackgroundColor(Color::srgb(0.15, 0.15, 0.15)),
                    children![(
                        Text::new(*label),
                        TextFont { font_size: 22.0, ..default() },
                        TextColor(Color::WHITE),
                    )],
                ));
            }
        });
}
```

### Mixing both forms

`children![]` and `.with_children(...)` can coexist. Spawn the outer shell with
`children![]` and attach dynamic inner children with `.with_children(...)` on a
sub-entity.

## Pitfalls

- **`children![]` requires Rust 2024 edition** (or Rust ≥ 1.85 with explicit
  edition in `Cargo.toml`). The macro uses `#![feature(..)]` stubs that stabilised
  in Rust 2024. The tester crate's `Cargo.toml` sets `edition = "2024"`.

- **Bundle order inside `children![]`.** Each comma-separated item is a complete
  bundle. Wrap multi-component children in a tuple:
  `children![(Button, Node { .. }, BackgroundColor(...))]`, not
  `children![Button, Node { .. }, BackgroundColor(...)]` (that's three separate
  child entities).

- **`with_children` closure borrows `Commands`.** You cannot call `commands.spawn`
  inside a `.with_children` closure — use the `parent: &mut ChildSpawner` argument
  (`parent.spawn(...)`) instead.

- **Spawning children after the fact.** If you need to add children to an already-
  spawned entity, use `commands.entity(parent_id).with_children(|p| { p.spawn(...) })`.
