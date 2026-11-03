# Bevy 0.20 UI — Text

Bevy uses a split-component model for text. There is no `TextBundle`. Since 0.19 layout runs on Parley (not cosmic-text); the public component API changed in two places: `TextFont::font` and `TextFont::font_size`.

## Quick reference

| Component | Purpose |
|---|---|
| `Text::new("hello")` | String content. Derefs to `String` (`**text = "x".into()`). |
| `TextFont { font: FontSource, font_size: FontSize, .. }` | Font selection and size. |
| `FontSource::Handle(h)` / `handle.into()` | Font by asset handle. |
| `FontSource::family("Fira Sans")` | Font by family name. Loaded fonts register their embedded family name (0.20). |
| `FontSource::sans_serif()`, `::serif()`, `::monospace()` | Generic families (`GenericFontFamily`). 0.19's `FontSource::SansSerif` variants are gone. |
| `FontSize::Px(f32)`, `::Rem(f32)`, `::Vw`, `::Vh`, `::VMin`, `::VMax` | Size units. Default is `Rem(1.)` (0.20). |
| `TextColor(Color)` | Foreground colour. |
| `TextShadow { offset, color }` | Drop shadow; `default()` is a 1 px offset. |
| `TextLayout::justify(Justify::Center)` | Alignment / wrapping. Was `new_with_justify` before 0.19. |
| `RemSize(pub f32)` resource | Base for `FontSize::Rem` and `Val::Rem`. Default 20. |

All of these are in `bevy::prelude`.

## Common patterns

### Inline text child

```rust
use bevy::prelude::*;

fn text_label(asset_server: &AssetServer) -> impl Bundle {
    (
        Text::new("Hello, Bevy!"),
        TextFont {
            font: asset_server.load("fonts/FiraSans-Bold.ttf").into(),
            font_size: FontSize::Px(24.0),
            ..default()
        },
        TextColor(Color::WHITE),
        TextShadow::default(),
    )
}
```

### Text with layout control

```rust
use bevy::prelude::*;

fn wrapped_text() -> impl Bundle {
    (
        Text::new("A longer paragraph that wraps across lines."),
        TextFont { font_size: FontSize::Px(18.0), ..default() },
        TextColor(Color::srgb(0.8, 0.8, 0.8)),
        TextLayout::justify(Justify::Left),
    )
}
```

### Generic and named families

```rust
use bevy::prelude::*;

fn monospace_readout() -> impl Bundle {
    (
        Text::new("fps: 60"),
        TextFont { font: FontSource::monospace(), font_size: FontSize::Rem(0.8), ..default() },
    )
}

fn brand_heading() -> impl Bundle {
    (
        Text::new("Title"),
        // Works once any font asset whose embedded family is "Fira Sans" has loaded.
        TextFont { font: FontSource::family("Fira Sans"), font_size: FontSize::Px(40.0), ..default() },
    )
}
```

### Scaling all default-size text at once

```rust
use bevy::prelude::*;

fn bump_text_scale(mut rem: ResMut<RemSize>) {
    rem.0 = 24.0; // every TextFont left at FontSize::Rem(1.) now renders at 24 px
}
```

## Pitfalls

- **`font: handle` and `font_size: 33.0` are 0.18 syntax.** 0.19+ needs `handle.into()` and `FontSize::Px(33.0)`. This is the most common stale-LLM error in UI code.
- **`FontSource::SansSerif` is 0.19-only.** 0.20 uses `FontSource::sans_serif()` or `GenericFontFamily::SansSerif.into()`.
- **Default size follows `RemSize` (0.20).** `TextFont::default()` is `Rem(1.)`, not `Px(20.)`. Pin `FontSize::Px(..)` when a size must stay fixed.
- **System fonts need `system_font_discovery`.** Enable the Bevy feature (Linux also needs `libfontconfig`). Without it only bundled font assets and the built-in default resolve.
- **`Font::try_from_bytes` → `Font::from_bytes(bytes)` (0.19), and it no longer takes a family name (0.20).**
- **Span traits consolidated (0.19).** `TextRoot`, `TextSpanAccess`, `TextSpanComponent` are one trait, `TextSection`; `read_span` / `write_span` are `get_text` / `get_text_mut`.
- **No `TextBundle`.** Spawn the components as a tuple.
- **The 0.18 "replace the default font" idiom (`fonts.insert(&TextFont::default().font, font)`) is not verified on 0.20.** `TextFont::default().font` is now `FontSource::Handle(Handle::default())`. Prefer passing a handle or using `FontSource::family`.
