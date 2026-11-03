# Bevy 0.20 UI — Colors and Borders

## Quick reference

| Component / constructor | Purpose |
|---|---|
| `BackgroundColor(Color)` | Fill colour for a `Node` entity. |
| `BorderColor::all(Color)` | Same border colour on all four sides. |
| `border_color.set_all(Color)` | Mutate in place (used by the button example). |
| `Node::border_radius: BorderRadius` | Corner rounding. A field on `Node`, not a component. |
| `BorderRadius::MAX` | Maximum rounding: pill for rectangles, circle for squares. |
| `BorderRadius::all(impl Into<CornerRadius>)` | Same radius on all corners. `px(12)` converts. |
| `BorderRadius::px(tl, tr, br, bl)` | Per-corner radius in pixels (`const`). |
| `CornerRadius::circular(Val)` | One circular corner (0.20). `CornerRadius::new(x, y)` for elliptical. |

`BorderRadius` fields are `CornerRadius` since 0.20 (elliptical corners). `BorderRadius` constructors accept `impl Into<CornerRadius>` and are no longer `const`.

## Common patterns

### Solid coloured panel

```rust
use bevy::prelude::*;

fn coloured_panel() -> impl Bundle {
    (
        Node { width: px(200), height: px(100), ..default() },
        BackgroundColor(Color::srgb(0.2, 0.2, 0.8)),
    )
}
```

### Rounded pill button

```rust
use bevy::{prelude::*, ui_widgets::Button};

fn pill_button() -> impl Bundle {
    (
        Button,
        Node {
            width: px(150),
            height: px(50),
            border: UiRect::all(px(3)),
            justify_content: JustifyContent::Center,
            align_items: AlignItems::Center,
            border_radius: BorderRadius::MAX,
            ..default()
        },
        BorderColor::all(Color::WHITE),
        BackgroundColor(Color::BLACK),
    )
}
```

### Rounded rectangle

```rust
use bevy::prelude::*;

fn rounded_card() -> impl Bundle {
    (
        Node {
            width: px(300),
            height: px(200),
            border: UiRect::all(px(2)),
            border_radius: BorderRadius::all(px(12)),
            ..default()
        },
        BorderColor::all(Color::srgb(0.5, 0.5, 0.5)),
        BackgroundColor(Color::srgb(0.1, 0.1, 0.1)),
    )
}
```

### Per-corner radius (tab shape), struct literal form

```rust
use bevy::prelude::*;

fn tab_shape() -> impl Bundle {
    (
        Node {
            width: px(120),
            height: px(40),
            border: UiRect::all(px(1)),
            border_radius: BorderRadius {
                top_left: CornerRadius::circular(px(8)),
                top_right: px(8).into(),      // From<Val> for CornerRadius
                bottom_right: Val::ZERO.into(),
                bottom_left: Val::ZERO.into(),
            },
            ..default()
        },
        BorderColor::all(Color::srgb(0.6, 0.6, 0.6)),
        BackgroundColor(Color::srgb(0.2, 0.2, 0.2)),
    )
}
```

`BorderRadius::px(8.0, 8.0, 0.0, 0.0)` is the short form of the same shape.

## Pitfalls

- **`BorderRadius { top_left: px(8.), .. }` is the 0.19 form.** 0.20 needs `.into()` or `CornerRadius::circular`. Stale output fails with "expected `CornerRadius`, found `Val`".
- **`BorderRadius::resolve` takes two more arguments (0.20):** `em_size: EmSize`, `rem_size: RemSize`. `resolve_single_corner` is gone; use `CornerRadius::resolve`.
- **`BorderColor` needs a non-zero `border` on `Node`.** Otherwise nothing is drawn.
- **`BackgroundColor(Color::NONE)` vs no component.** Both look transparent; only the former gives the node a render item. Picking does not need either: hit-testing uses the `ComputedNode` rect.
- **Elliptical corners:** `CornerRadius::new(px(20), px(10))`. A circular corner sets `x` or `y` to `Val::Auto`.
