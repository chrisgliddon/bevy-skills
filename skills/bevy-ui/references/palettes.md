# Bevy 0.20 UI — Color Palettes

Bevy ships three palettes under `bevy::color::palettes`. The constants are `Srgba`; they convert into `Color` with `.into()` or `Color::Srgba(..)`.

## Quick reference

| Module | Style | Example constant |
|---|---|---|
| `bevy::color::palettes::basic` | 16 HTML basic colors | `basic::WHITE`, `basic::RED` |
| `bevy::color::palettes::css` | ~150 CSS named colors | `css::CORNFLOWER_BLUE`, `css::TOMATO` |
| `bevy::color::palettes::tailwind` | Tailwind v3 palette | `tailwind::GREEN_300`, `tailwind::SLATE_800` |

## Common patterns

### Basic palette for standard UI colors

```rust
use bevy::{color::palettes::basic::*, prelude::*, ui_widgets::Button};

fn danger_button() -> impl Bundle {
    (
        Button,
        Node { width: px(120), height: px(44), border_radius: BorderRadius::MAX, ..default() },
        BackgroundColor(RED.into()),
        BorderColor::all(WHITE),
    )
}
```

`BorderColor::all` and `BorderColor::set_all` take `impl Into<Color>`, so palette constants pass straight through.

### Tailwind for design-system colors

```rust
use bevy::{color::palettes::tailwind, prelude::*, ui_widgets::Button};

const BRAND_PRIMARY: Color = Color::Srgba(tailwind::INDIGO_600);
const BRAND_HOVER: Color = Color::Srgba(tailwind::INDIGO_500);

fn branded_button() -> impl Bundle {
    (
        Button,
        Node {
            width: px(160),
            height: px(48),
            border_radius: BorderRadius::all(px(6)),
            justify_content: JustifyContent::Center,
            align_items: AlignItems::Center,
            ..default()
        },
        BackgroundColor(BRAND_PRIMARY),
    )
}

fn hover_tint() -> BackgroundColor {
    BackgroundColor(BRAND_HOVER)
}
```

### Which palette

| Situation | Palette |
|---|---|
| Standard red / green / white / black | `basic` |
| A CSS color by web name | `css` |
| Following a Tailwind design system | `tailwind` |
| Fully custom | `Color::srgb(r, g, b)` |

## Pitfalls

- **`Srgba` vs `Color`.** `BackgroundColor` wraps a `Color`, so write `RED.into()`. `Color::Srgba(..)` is the `const` form.
- **Tailwind names use underscores:** `tailwind::GREEN_300`.
- **Avoid `tailwind::*` globs** (~900 symbols).
- **`basic::NONE` does not exist.** Use `Color::NONE`.
- **`with_luminance` no longer clamps (0.20).** `LinearRgba::with_luminance` scales rather than clamps; tinted palettes may exceed 1.0 before conversion.
