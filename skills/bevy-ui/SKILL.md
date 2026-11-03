---
name: bevy-ui
description: Use when building Bevy 0.20 UI with `Node`, `ui_widgets::Button`, `Hovered` / `Pressed` / `Activate`, `children![]`, `TextFont` with `FontSource` and `FontSize`, `BorderRadius` / `CornerRadius`, `BackgroundColor`, `BorderColor`, `InputFocus`, or `AccessibleLabel`, or when `ui::Interaction` and `Changed<Interaction>` show deprecation warnings.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "2"
  area: ui
  bevy_version: "0.20"
---

# Bevy 0.20 — UI

## When to use this skill

- Spawning any `Node`-based UI element (panels, buttons, text labels, overlays).
- Reacting to a button: `Hovered`, `Has<Pressed>`, and the `Activate` event.
- Styling text with `TextFont { font: FontSource, font_size: FontSize, .. }`, `TextColor`, `TextShadow`.
- Setting `BackgroundColor`, `BorderColor`, or `Node::border_radius` (`BorderRadius` of `CornerRadius`).
- Using palette constants from `bevy::color::palettes`.
- Wiring `InputFocus`, `TabIndex`, or `AccessibleLabel` for keyboard and screen-reader support.
- Nesting child entities with `children![]` or `.with_children(...)`.
- Migrating code that used `ui::Interaction`, `Changed<Interaction>`, `font_size: 33.0`, or `font: handle` (0.18 forms).

## Canonical pattern

Headless `ui_widgets::Button`, styled by polling `Hovered` and `Pressed`, clicked via `Activate`. Mirrors `examples/ui/widgets/button.rs` in Bevy 0.20.1.

```rust
use bevy::{
    color::palettes::basic::*,
    picking::hover::Hovered,
    prelude::*,
    ui::Pressed,
    ui_widgets::{observe, Activate, Button},
};

fn main() {
    App::new()
        // DefaultPlugins already includes UiWidgetsPlugins and InputFocusPlugin.
        .add_plugins(DefaultPlugins)
        .add_systems(Startup, setup)
        .add_systems(Update, update_button_appearance)
        .run();
}

const NORMAL_BUTTON: Color = Color::srgb(0.15, 0.15, 0.15);
const HOVERED_BUTTON: Color = Color::srgb(0.25, 0.25, 0.25);
const PRESSED_BUTTON: Color = Color::srgb(0.35, 0.75, 0.35);

fn setup(mut commands: Commands, assets: Res<AssetServer>) {
    commands.spawn(Camera2d);
    commands.spawn((
        // Full-screen flex container that centres the button.
        Node {
            width: percent(100),
            height: percent(100),
            align_items: AlignItems::Center,
            justify_content: JustifyContent::Center,
            ..default()
        },
        children![(
            button(&assets),
            // `Button` fires `Activate` on a completed click (or Enter/Space when focused).
            observe(|_activate: On<Activate>| {
                info!("Button clicked!");
            }),
        )],
    ));
}

fn button(asset_server: &AssetServer) -> impl Bundle {
    (
        Button,             // headless widget: tracks `Pressed`, emits `Activate`
        Hovered::default(), // picking backend keeps this up to date
        Node {
            width: px(150),
            height: px(65),
            border: UiRect::all(px(5)),
            justify_content: JustifyContent::Center,
            align_items: AlignItems::Center,
            border_radius: BorderRadius::MAX, // pill
            ..default()
        },
        BorderColor::all(Color::BLACK),
        BackgroundColor(NORMAL_BUTTON),
        children![(
            Text::new("Button"),
            TextFont {
                font: asset_server.load("fonts/FiraSans-Bold.ttf").into(), // Handle -> FontSource
                font_size: FontSize::Px(33.0),
                ..default()
            },
            TextColor(Color::srgb(0.9, 0.9, 0.9)),
            TextShadow::default(),
        )],
    )
}

/// Poll `Hovered` + `Has<Pressed>` every frame and pick a look.
fn update_button_appearance(
    mut buttons: Query<
        (&Hovered, Has<Pressed>, &mut BackgroundColor, &mut BorderColor, &Children),
        With<Button>,
    >,
    mut text_query: Query<&mut Text>,
) {
    for (hovered, pressed, mut color, mut border_color, children) in &mut buttons {
        let Ok(mut text) = text_query.get_mut(children[0]) else { continue };
        match (hovered.get(), pressed) {
            (_, true) => {
                **text = "Press".to_string();
                *color = PRESSED_BUTTON.into();
                border_color.set_all(RED);
            }
            (true, false) => {
                **text = "Hover".to_string();
                *color = HOVERED_BUTTON.into();
                border_color.set_all(WHITE);
            }
            (false, false) => {
                **text = "Button".to_string();
                *color = NORMAL_BUTTON.into();
                border_color.set_all(BLACK);
            }
        }
    }
}
```

## Topics

| Topic | Reference |
|---|---|
| `Node`, `Val` (`px`, `percent`, `em`, `rem`, `vw`, `vh`), flex recipes | [references/layout.md](references/layout.md) |
| `Text::new`, `TextFont`, `FontSource`, `FontSize`, `TextLayout::justify` | [references/text.md](references/text.md) |
| `ui_widgets::Button`, `Hovered`, `Pressed`, `Activate`, observers vs polling | [references/interaction.md](references/interaction.md) |
| `BackgroundColor`, `BorderColor`, `BorderRadius` / `CornerRadius` | [references/colors-and-borders.md](references/colors-and-borders.md) |
| `bevy::color::palettes::{basic,css,tailwind}` | [references/palettes.md](references/palettes.md) |
| `InputFocus`, `FocusCause`, `TabIndex`, `AccessibleLabel` | [references/accessibility.md](references/accessibility.md) |
| `children![]` vs `.with_children(...)` | [references/children-macro.md](references/children-macro.md) |
| Cross-cutting traps and stale-LLM output | [references/gotchas.md](references/gotchas.md) |

## Gotchas

1. **`ui::Interaction` and `ui::widget::Button` are deprecated in 0.20.** Both still sit in `bevy::prelude`, so `Button` from the prelude is the *old* one. Import `bevy::ui_widgets::Button` explicitly. Replace `Changed<Interaction>` matches with `&Hovered` + `Has<Pressed>` (both are *not* in the prelude: `bevy::picking::hover::Hovered`, `bevy::ui::Pressed`).
2. **Clicks are an event, not a state.** `Activate` fires once per completed click; `Pressed` is only present while the pointer is held. Attach `observe(|_: On<Activate>| ..)` in the bundle or `commands.entity(e).observe(..)`.
3. **`button.set_changed()` is gone with the old button.** `ui_widgets::Button` requires `AccessibilityNode(Role::Button)`; add `AccessibleLabel("...")` for the spoken name. No manual dirty-marking.
4. **`InputFocus` is inserted by `DefaultPlugins` (0.19+).** Do not `init_resource` it. Fields are private: `get()`, `set(entity, FocusCause::Pressed)`, `clear()`. `FocusCause` gained `Auto` in 0.20; exhaustive matches must add it.
5. **`TextFont` fields changed in 0.19.** `font: Handle<Font>` became `FontSource` (`handle.into()`, `FontSource::family("Fira Sans")`, `FontSource::sans_serif()`); `font_size: f32` became `FontSize::Px(f32)`. `TextFont::default()` is `FontSize::Rem(1.)` in 0.20 (20 px via `RemSize`), so set `FontSize::Px(20.)` for a fixed size. `FontSource::SansSerif` (0.19) is `FontSource::sans_serif()` in 0.20.
6. **`BorderRadius` fields are `CornerRadius` in 0.20.** `BorderRadius::MAX` and `BorderRadius::px(..)` are unchanged; `BorderRadius::all(px(6))` works via `Into<CornerRadius>`; literal structs need `CornerRadius::circular(px(10.))`.
7. **`Val::Em` / `Val::Rem` are new in 0.20.** `Val::resolve` takes `EmSize` and `RemSize` as two extra arguments.
8. **Flat pointer events in 0.20.** `On<Pointer<Click>>` is `On<PointerClick>`; `press.pointer_location.position` is `press.pointer.position`.
9. **`ui` is not implied by `2d` / `3d` since 0.19.** With `default-features = false`, add the `ui` feature collection (it also carries `bevy_ui_widgets` and `ui_picking`).
10. **`TextLayout::new_with_justify` is `TextLayout::justify` (0.19).** `Justify` is in the prelude.

## See also

- `bevy-migration-0-19-to-0-20` — full list of the button, pointer-event, and `Val` changes.
- `bevy-cameras` — spawn a `Camera2d` alongside any UI scene.
- `bevy-ecs-queries` — `Has<T>`, `Changed<T>`, and query filters used above.
- `bevy-fluent` — localized UI text via `FluentText<T>`.
- `bevy-cargo-features` — the `ui` collection and what it enables.
