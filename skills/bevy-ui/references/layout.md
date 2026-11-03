# Bevy 0.20 UI — Layout

UI layout is Flexbox / Grid driven (Taffy). Every visible UI entity needs a `Node`.

## Quick reference

| Type / fn | Purpose |
|---|---|
| `Node` | Core layout component (size, padding, margin, flex, grid, `border_radius`, `direction`). |
| `px(v)` → `Val::Px` | Logical pixels. |
| `percent(v)` → `Val::Percent` | Percentage of the parent's dimension. |
| `vw(v)` / `vh(v)` | Viewport-relative. |
| `em(v)` → `Val::Em` | Relative to the node's own font size (`EmSize`). New in 0.20. |
| `rem(v)` → `Val::Rem` | Relative to the `RemSize` resource (default 20 px). New in 0.20. |
| `Val::Auto` | Let the layout engine decide (default for most fields). |
| `UiRect::all(val)` / `UiRect::axes(h, v)` | Padding, margin, border shorthands. |
| `FlexDirection::{Row, Column}` | Main-axis direction. |
| `AlignItems::Center` / `JustifyContent::Center` | Cross-axis / main-axis centering. |
| `Node::direction: Direction` | LTR / RTL layout direction (0.19). |

All of these are in `bevy::prelude`.

## Common patterns

### Centered child

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

### Full-screen overlay

```rust
use bevy::prelude::*;

fn full_screen_overlay() -> impl Bundle {
    (
        Node {
            position_type: PositionType::Absolute,
            top: px(0),
            left: px(0),
            width: percent(100),
            height: percent(100),
            ..default()
        },
        BackgroundColor(Color::srgba(0.0, 0.0, 0.0, 0.5)),
        GlobalZIndex(10),
    )
}
```

### Font-relative spacing (0.20)

```rust
use bevy::prelude::*;

fn label_row() -> impl Bundle {
    (
        Node {
            padding: UiRect::axes(em(1.0), em(0.5)), // scales with this node's TextFont
            row_gap: rem(0.5),                        // scales with RemSize
            ..default()
        },
        TextFont { font_size: FontSize::Px(18.0), ..default() },
        Text::new("label"),
    )
}
```

## Pitfalls

- **`Val::Auto` vs `px(0)`.** Unset fields default to `Auto`; set `width` and `height` explicitly for fixed widgets.
- **No `Node` → invisible.** Not laid out at all.
- **`percent(100)` on a child needs a definite parent size.** Use `vw` / `vh` for viewport-relative sizes.
- **`Val::resolve` grew two arguments in 0.20** (`EmSize`, `RemSize`). Custom measure or layout code reads them from `ComputedNode::em_size` / `rem_size`. `Measure::measure` lost its `style: &taffy::Style` parameter in 0.19.
- **`em` on a node without `TextFont`:** `EmSize` is required by `Node` and left at its default; set it yourself if you want `em` to mean something there.
