# bevy-porting — UGUI + UI Toolkit → bevy_ui (Bevy 0.20)

> Referenced from `bevy-porting/SKILL.md § Unity (priority)`.

## Two Unity UI worlds

| Unity system | Shape | Bevy 0.20 mental model |
|---|---|---|
| **UGUI** (legacy) | Canvas → RectTransform hierarchy, prefab-driven | `Node` tree; anchors/pivots → `PositionType` + flex |
| **UI Toolkit** (newer) | UXML templates + USS stylesheets, retained mode | `Node` tree; USS rules → field values on spawn |

Both map to the same Bevy `Node` entity model. The flex (Taffy/CSS) mental model is closer
to UI Toolkit than to UGUI's anchor/pivot system.

See [`bevy-ui/SKILL.md`](../../bevy-ui/SKILL.md) for the full Bevy 0.20 UI API.

## UGUI Canvas → root `Node`

A `Canvas` GameObject with `ScreenSpace - Overlay` render mode maps to a `Node` entity
at the root of the UI tree that Bevy's `UiPlugin` manages automatically. You do not spawn
a canvas explicitly — any `Node` entity without a `ChildOf` parent is a UI root.

```rust
commands.spawn(Node {
    width: Val::Percent(100.0),
    height: Val::Percent(100.0),
    ..default()
});
```

## RectTransform anchors / pivots → `Node` layout

This is the trickiest single area. UGUI's anchor/pivot/size-delta model has no direct
counterpart. Translate to Bevy's Taffy/flex properties:

| UGUI pattern | Bevy 0.20 |
|---|---|
| Stretch to fill parent | `width: Percent(100), height: Percent(100)` |
| Anchored bottom-right, size (200, 100) | `position_type: Absolute, bottom: Px(0), right: Px(0), width: Px(200), height: Px(100)` |
| Centered, fixed size | `align_self: Center` + fixed `width`/`height` on the `Node` |
| Anchored top-left with offset | `position_type: Absolute, top: Px(offset_y), left: Px(offset_x)` |
| `VerticalLayoutGroup` | `flex_direction: Column, row_gap: Px(spacing)` |
| `HorizontalLayoutGroup` | `flex_direction: Row, column_gap: Px(spacing)` |
| `GridLayoutGroup` | `display: Grid` + `grid_template_columns` |

Pivot (0.5, 0.5) — Bevy has no pivot concept for UI; transforms rotate around the
top-left corner by default. For centered rotation, offset the child or use a wrapper node.

## UI Toolkit (USS/UXML) → `Node` tree

UXML templates → spawn entity trees in code (`children![]` or `.with_children`).
USS class selectors do not exist in Bevy 0.20 `bevy_ui` — there is no runtime style
sheet resolver. Map USS rule blocks directly to `Node` field values at spawn time.

Community crates exist for class-based/reactive styling (search crates.io for
`bevy_hui`, `belly`, or `bevy_cobweb_ui`) but none are first-party.

## Buttons + interaction

Unity `Button` component → `bevy::ui_widgets::Button` (headless) + the `Hovered(bool)`
and `Pressed` marker components. `onClick` → an `On<Activate>` observer. The 0.18
`ui::widgets::Button` + `Interaction` pair is deprecated in 0.20.

```rust
use bevy::picking::hover::Hovered;
use bevy::ui::Pressed;
use bevy::ui_widgets::{Activate, Button};

fn spawn_button(mut commands: Commands) {
    commands
        .spawn((Button, Node::default(), Hovered::default(), BackgroundColor(Color::BLACK)))
        .observe(|activate: On<Activate>| info!("clicked {}", activate.entity));
}

fn button_colors(
    mut q: Query<
        (&Hovered, Has<Pressed>, &mut BackgroundColor),
        (With<Button>, Or<(Changed<Hovered>, Changed<Pressed>)>),
    >,
) {
    for (hovered, pressed, mut bg) in &mut q {
        *bg = match (pressed, hovered.0) {
            (true, _) => BackgroundColor(Color::srgb(0.35, 0.75, 0.35)),
            (false, true) => BackgroundColor(Color::srgb(0.25, 0.25, 0.25)),
            (false, false) => BackgroundColor(Color::BLACK),
        };
    }
}
```

**Frame-0 invariant:** `Changed<Hovered>` does NOT fire at frame 0. The button shows
its spawn-time `BackgroundColor` on the first rendered frame. This matches Unity's
behaviour (OnPointerEnter fires after the first frame). See `bevy-ui/SKILL.md § Gotchas`.

## Text (TextMeshPro → `Text` + `TextFont`)

| Unity | Bevy 0.20 |
|---|---|
| `TextMeshPro` component | `Text::new("...")` |
| TMP font asset (`.asset`) | `TextFont { font: asset_server.load("fonts/Roboto.ttf").into(), .. }` — `font` is a `FontSource` since 0.19 (`FontSource::sans_serif()` for a system family) |
| `fontSize` | `TextFont { font_size: FontSize::Px(32.0), .. }` — `FontSize`, not `f32`, since 0.19 |
| `color` | `TextColor(Color::WHITE)` |
| `outlineWidth` / `shadowOffset` | `TextShadow { offset: Vec2::new(2.0, -2.0), .. }` |

TMP `.asset` files are not loadable by Bevy. Export the source TTF/OTF from your Unity
project and load that directly.

## Layout groups → flex / grid

```rust
// VerticalLayoutGroup equivalent
Node {
    flex_direction: FlexDirection::Column,
    row_gap: Val::Px(8.0),
    ..default()
}

// HorizontalLayoutGroup equivalent
Node {
    flex_direction: FlexDirection::Row,
    column_gap: Val::Px(8.0),
    ..default()
}
```

Bevy 0.20 uses [Taffy](https://github.com/DioxusLabs/taffy) for layout — the same
engine as web CSS flexbox/grid. Flex is the default `Display`. `Val::Em` / `Val::Rem`
(0.20) map USS `em`/`rem` units directly.

## Animation / tweens (DOTween → curves)

DOTween sequences and UI Animator clips → procedural systems that sample
`EasingCurve` or `EaseFunction` each frame and write back to `Node` fields
(e.g. `width`, `height`, `top`, `left`, `BackgroundColor`).

```rust
// Fade-in: write opacity via BackgroundColor alpha each frame
fn fade_in(time: Res<Time>, mut q: Query<&mut BackgroundColor, With<FadeTarget>>) {
    let t = (time.elapsed_secs() / 0.3).clamp(0.0, 1.0);
    for mut bg in &mut q {
        bg.0.set_alpha(t);
    }
}
```

For curve utilities see
[`bevy-animation/references/curves-and-tweening.md`](../../bevy-animation/references/curves-and-tweening.md).

## See also

- [`../SKILL.md`](../SKILL.md) — bevy-porting dispatcher
- [`unity-input.md`](unity-input.md) — wiring input to UI buttons
- [`bevy-ui/SKILL.md`](../../bevy-ui/SKILL.md) — full Bevy 0.20 UI reference
- [`bevy-animation/references/curves-and-tweening.md`](../../bevy-animation/references/curves-and-tweening.md) — `EaseFunction`, `EasingCurve` for UI tweens
