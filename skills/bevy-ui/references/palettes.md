# Bevy 0.18 UI — Color Palettes

Bevy 0.18 ships three pre-defined color palettes under `bevy::color::palettes`.
Import the module you need and use the constants directly — no hex strings required.

## Quick reference

| Module | Style | Example constant |
|---|---|---|
| `bevy::color::palettes::basic` | 16 HTML basic colors | `basic::WHITE`, `basic::RED` |
| `bevy::color::palettes::css` | ~150 CSS named colors | `css::CORNFLOWER_BLUE`, `css::TOMATO` |
| `bevy::color::palettes::tailwind` | Tailwind CSS v3 palette (900 shades) | `tailwind::GREEN_300`, `tailwind::SLATE_800` |

All constants are `Srgba` values. They implement `Into<Color>`, so they work
everywhere a `Color` is expected.

## Common patterns

### Import statement

```rust
// Pick the palette(s) you need — avoid glob-importing all three.
use bevy::color::palettes::basic;
use bevy::color::palettes::css;
use bevy::color::palettes::tailwind;
use bevy::prelude::*;
```

### Using basic palette for standard UI colors

```rust
use bevy::color::palettes::basic::*;
use bevy::prelude::*;

fn danger_button() -> impl Bundle {
    (
        Button,
        Node { width: px(120), height: px(44), border_radius: BorderRadius::MAX, ..default() },
        BackgroundColor(RED.into()),
        BorderColor::all(WHITE.into()),
    )
}
```

### Using Tailwind for design-system colors

```rust
use bevy::color::palettes::tailwind;
use bevy::prelude::*;

const BRAND_PRIMARY: Color = Color::Srgba(tailwind::INDIGO_600);
const BRAND_HOVER: Color   = Color::Srgba(tailwind::INDIGO_500);
const BRAND_TEXT: Color    = Color::Srgba(tailwind::SLATE_50);

fn branded_button() -> impl Bundle {
    (
        Button,
        Node {
            width: px(160),
            height: px(48),
            border_radius: BorderRadius::all(Val::Px(6.0)),
            justify_content: JustifyContent::Center,
            align_items: AlignItems::Center,
            ..default()
        },
        BackgroundColor(BRAND_PRIMARY),
    )
}
```

### Choosing which palette to reach for

| Situation | Recommended palette |
|---|---|
| "I want standard red / green / white / black" | `basic` — minimal import, well-known names. |
| "I want a specific CSS color by its web name" | `css` — matches MDN color keywords exactly. |
| "I'm following a Tailwind design system" | `tailwind` — matches Tailwind v3 shade names. |
| "I need a fully custom color" | `Color::srgb(r, g, b)` — no palette needed. |

## Pitfalls

- **`Srgba` vs `Color`.** Palette constants are `Srgba` (the linear-sRGB newtype),
  not `Color`. Use `.into()` or wrap with `Color::Srgba(...)` when the API
  requires `Color` rather than `impl Into<Color>`.

- **Tailwind constant names use underscores, not hyphens.**
  `tailwind::GREEN_300`, not `tailwind::green-300` or `tailwind::GREEN300`.

- **Glob imports from `tailwind::*` export ~900 symbols.** Import the module
  rather than glob-importing to keep auto-complete manageable.

- **`basic::NONE` does not exist.** For transparent, use
  `Color::srgba(0.0, 0.0, 0.0, 0.0)` or `Color::NONE` from the prelude.
