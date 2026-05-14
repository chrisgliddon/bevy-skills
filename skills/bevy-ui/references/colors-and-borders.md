# Bevy 0.18 UI — Colors and Borders

## Quick reference

| Component / Constructor | Purpose |
|---|---|
| `BackgroundColor(Color)` | Fill colour for a `Node` entity. |
| `BorderColor::all(Color)` | Same border colour on all four sides. |
| `BorderColor::new(top, right, bottom, left)` | Per-side border colours. |
| `BorderRadius::MAX` | Maximum corner radius → pill / circle shape. |
| `BorderRadius::all(Val)` | Same radius on all four corners. |
| `BorderRadius::px(tl, tr, br, bl)` | Per-corner radius in pixels. |

All four are in `bevy::prelude`.

## Common patterns

### Solid coloured panel

```rust
use bevy::prelude::*;

fn coloured_panel() -> impl Bundle {
    (
        Node {
            width: px(200),
            height: px(100),
            ..default()
        },
        BackgroundColor(Color::srgb(0.2, 0.2, 0.8)),
    )
}
```

### Rounded pill button

```rust
use bevy::prelude::*;

fn pill_button() -> impl Bundle {
    (
        Button,
        Node {
            width: px(150),
            height: px(50),
            border: UiRect::all(px(3)),
            justify_content: JustifyContent::Center,
            align_items: AlignItems::Center,
            border_radius: BorderRadius::MAX,  // full pill
            ..default()
        },
        BorderColor::all(Color::WHITE),
        BackgroundColor(Color::BLACK),
    )
}
```

### Rounded rectangle (specific radius)

```rust
use bevy::prelude::*;

fn rounded_card() -> impl Bundle {
    (
        Node {
            width: px(300),
            height: px(200),
            border: UiRect::all(px(2)),
            border_radius: BorderRadius::all(Val::Px(12.0)),
            ..default()
        },
        BorderColor::all(Color::srgb(0.5, 0.5, 0.5)),
        BackgroundColor(Color::srgb(0.1, 0.1, 0.1)),
    )
}
```

### Per-corner radius (e.g. tab shape)

```rust
use bevy::prelude::*;

fn tab_shape() -> impl Bundle {
    (
        Node {
            width: px(120),
            height: px(40),
            border: UiRect::all(px(1)),
            // Rounded top corners only
            border_radius: BorderRadius::px(8.0, 8.0, 0.0, 0.0),
            ..default()
        },
        BorderColor::all(Color::srgb(0.6, 0.6, 0.6)),
        BackgroundColor(Color::srgb(0.2, 0.2, 0.2)),
    )
}
```

## Constructor intent

| Constructor | When to use |
|---|---|
| `BorderRadius::MAX` | When you want the maximum possible rounding — a pill for rectangles, a circle for squares. |
| `BorderRadius::all(Val::Px(r))` | Consistent rounding; `r` in pixels. |
| `BorderRadius::px(tl, tr, br, bl)` | Different corner radii (tabs, speech bubbles, asymmetric cards). |

## Pitfalls

- **`BorderColor` requires a non-zero `border` on `Node`.** Setting `BorderColor`
  without `border: UiRect::all(px(N))` on `Node` renders no visible border.

- **`BackgroundColor(Color::NONE)` vs omitting `BackgroundColor`.** Both appear
  transparent, but an entity with `BackgroundColor(Color::NONE)` still participates
  in hit-testing via `Button`. If you want a transparent, clickable region, set
  `BackgroundColor(Color::srgba(0.0, 0.0, 0.0, 0.0))` rather than omitting the component.

- **`BorderRadius` clamps at `BorderRadius::MAX`.** Values above `MAX` are clamped,
  not wrapped. Use `MAX` for a pill; don't compute `f32::MAX` manually.

- **`BorderColor::all` vs per-arm mutation.** When the `Interaction::None` arm
  sets `BorderColor::all(Color::BLACK)` but the spawn-time value was
  `BorderColor::all(Color::WHITE)`, the button shows white at frame 0 (before
  `Changed<Interaction>` fires). See [gotchas](gotchas.md).
