# Bevy 0.18 UI — Text

Bevy 0.18 uses a **split-component model** for text. There is no `TextBundle`.
Instead, a text entity is a bundle of separate components, each with a single
responsibility.

## Quick reference

| Component | Purpose |
|---|---|
| `Text::new("hello")` | The string content of a text entity. |
| `TextFont { font, font_size, .. }` | Font handle + size (in logical pixels). |
| `TextColor(Color)` | Foreground colour. |
| `TextShadow::default()` | Adds a subtle drop shadow (offset `(1,1)` in 0.18). |
| `TextLayout` | Wrapping and alignment; optional. |

`Text`, `TextFont`, `TextColor`, and `TextShadow` are all in `bevy::prelude`.

## Common patterns

### Inline text child (the canonical pattern)

```rust
use bevy::prelude::*;

fn text_label(asset_server: &AssetServer) -> impl Bundle {
    (
        Text::new("Hello, Bevy!"),
        TextFont {
            font: asset_server.load("fonts/FiraSans-Bold.ttf"),
            font_size: 24.0,
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
use bevy::text::{Justify, TextLayout};

fn wrapped_text(asset_server: &AssetServer) -> impl Bundle {
    (
        Text::new("A longer paragraph that wraps across lines."),
        TextFont {
            font: asset_server.load("fonts/FiraSans-Bold.ttf"),
            font_size: 18.0,
            ..default()
        },
        TextColor(Color::srgb(0.8, 0.8, 0.8)),
        TextLayout::new_with_justify(Justify::Left),
    )
}
```

Note: `Justify` (not `JustifyText`) is the 0.18 enum. The `JustifyText` name was retired in an earlier release — stale-training-data alert.

### Replacing the default font (diplopod idiom)

This pattern lets every `TextFont { ..default() }` entity in the app automatically
use a custom font, without threading an `AssetServer` handle everywhere.

```rust
use bevy::prelude::*;

/// Stored until the font asset has loaded.
#[derive(Resource)]
struct DefaultFontHandle(Handle<Font>);

fn setup(mut commands: Commands, asset_server: Res<AssetServer>) {
    let font = asset_server.load("fonts/MyFont-Regular.ttf");
    commands.insert_resource(DefaultFontHandle(font));
}

/// Runs every frame while `DefaultFontHandle` exists; removes itself when done.
fn set_default_font(
    mut commands: Commands,
    mut fonts: ResMut<Assets<Font>>,
    handle: Res<DefaultFontHandle>,
) {
    // `fonts.remove` returns `None` if the asset hasn't loaded yet — safe to
    // call every frame until it succeeds.
    if let Some(font) = fonts.remove(&handle.0)
        && fonts.insert(&TextFont::default().font, font).is_ok()
    {
        commands.remove_resource::<DefaultFontHandle>();
    }
}

// In App::new():
//   .add_systems(Update, set_default_font.run_if(resource_exists::<DefaultFontHandle>))
```

The key insight: `TextFont::default().font` is the handle Bevy uses for its
built-in font. Inserting your font at that handle ID replaces it globally.

## Pitfalls

- **No `TextBundle` in 0.18.** Pre-0.17 tutorials use `TextBundle { style, text, .. }`.
  This type does not exist in 0.18. Spawn the components individually or as a tuple bundle.

- **`Text` deref.** `Text` derefs to `String` via `Deref` / `DerefMut`. To update
  the text in a system: `**text = "New string".to_string();`.

- **Font size units.** `font_size` is logical pixels. On HiDPI displays the
  engine scales automatically via `UiScale`.

- **`TextShadow` is a unit-like default.** `TextShadow::default()` gives a `(1.0, 1.0)`
  pixel shadow in dark grey. To customise, construct `TextShadow { offset: Vec2::new(2.0, 2.0), color: Color::BLACK }`.
