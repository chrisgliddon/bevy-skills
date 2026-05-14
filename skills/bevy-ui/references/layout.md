# Bevy 0.18 UI — Layout

UI layout in Bevy 0.18 is Flexbox-driven. Every visible UI entity needs a `Node`
component; the root of the tree is a direct child of the implicit UI root entity.

## Quick reference

| Type / fn | Purpose |
|---|---|
| `Node` | Core layout component (width, height, padding, margin, flex settings). |
| `Val::Px(f32)` | Absolute pixel value. |
| `Val::Percent(f32)` | Percentage of parent's dimension. |
| `Val::Auto` | Let the layout engine decide (default for most fields). |
| `px(f32)` | Shorthand for `Val::Px(f32)` — in `bevy::prelude`. |
| `percent(f32)` | Shorthand for `Val::Percent(f32)` — in `bevy::prelude`. |
| `UiRect::all(val)` | Same `Val` on all four sides (border, padding, margin). |
| `UiRect::axes(h, v)` | Horizontal / vertical pairs. |
| `FlexDirection::Row` | Children flow left-to-right (default). |
| `FlexDirection::Column` | Children flow top-to-bottom. |
| `AlignItems::Center` | Cross-axis centering of children. |
| `AlignItems::FlexStart` | Children packed at the start of the cross axis. |
| `JustifyContent::Center` | Main-axis centering. |
| `JustifyContent::SpaceBetween` | Even gaps between children. |

## Common patterns

### Centered child (the canonical full-screen button container)

```rust
use bevy::prelude::*;

fn centered_container() -> Node {
    Node {
        width: percent(100),
        height: percent(100),
        align_items: AlignItems::Center,
        justify_content: JustifyContent::Center,
        ..default()
    }
}
```

### Two-column layout

```rust
use bevy::prelude::*;

fn two_columns() -> Node {
    Node {
        width: percent(100),
        height: percent(100),
        flex_direction: FlexDirection::Row,
        align_items: AlignItems::Stretch,
        ..default()
    }
}

fn column(width_pct: f32) -> Node {
    Node {
        width: percent(width_pct),
        height: percent(100),
        flex_direction: FlexDirection::Column,
        ..default()
    }
}
```

### Full-screen overlay (HUD, modal backdrop)

```rust
use bevy::prelude::*;

fn full_screen_overlay() -> impl Bundle {
    (
        Node {
            position_type: PositionType::Absolute,
            top: Val::Px(0.0),
            left: Val::Px(0.0),
            width: percent(100),
            height: percent(100),
            ..default()
        },
        BackgroundColor(Color::srgba(0.0, 0.0, 0.0, 0.5)),
        // ZIndex::Global(10) to appear above game world if needed.
    )
}
```

## Pitfalls

- **`Val::Auto` vs `Val::Px(0.0)`** — unset fields default to `Val::Auto`, not zero.
  An element with `width: Val::Auto` sizes to its content. Explicitly set `width`
  and `height` when you need a fixed-size widget.

- **No `Node` → invisible.** An entity without `Node` is not laid out by the UI
  system at all. If a spawned entity does not appear, check that it (or a parent)
  has `Node`.

- **`UiRect` shorthand vs individual fields.** `border: UiRect::all(px(5))` sets
  all four sides. Individual sides: `UiRect { top: px(10), ..default() }`.

- **`percent(100)` on a child requires the parent to have a definite size.** If
  the parent's size is also `Auto`, the percent resolves to zero. Use `vh(100.0)`
  / `vw(100.0)` (lowercase — they're free functions in `bevy::prelude`) for
  viewport-relative sizes.
