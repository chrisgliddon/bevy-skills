# Bevy 0.20 UI — Gotchas

Cross-cutting traps. Most describe what stale (0.18-era) LLM output looks like and the 0.20 form.

## 1. The prelude `Button` is the deprecated one

`use bevy::prelude::*; commands.spawn(Button)` compiles with a deprecation warning and gives you the old `Interaction`-driven widget. Write `use bevy::ui_widgets::Button;` so the import shadows the prelude. Stale code also pairs it with `Changed<Interaction>`; the 0.20 form is `&Hovered` + `Has<Pressed>` and an `On<Activate>` observer. See [interaction.md](interaction.md).

## 2. The frame-0 `Changed<Interaction>` invariant is gone

0.18 skills warned that `Changed<Interaction>` never fires on frame 0, so the button showed spawn-time colours until the first hover. With polling on `Hovered` / `Has<Pressed>` the system runs every frame and converges immediately. Only the spawn-time `BorderColor` / `BackgroundColor` on the first rendered frame can still differ; the 0.20.1 example spawns the idle colours to avoid that.

## 3. `TextFont { font: handle, font_size: 33.0 }` does not compile

Since 0.19 `font` is `FontSource` and `font_size` is `FontSize`:

```rust
TextFont {
    font: asset_server.load("fonts/FiraSans-Bold.ttf").into(),
    font_size: FontSize::Px(33.0),
    ..default()
}
```

`TextFont::default()` is `FontSize::Rem(1.)` in 0.20 (20 px with the default `RemSize`). Set `FontSize::Px(20.)` if the size must not follow `RemSize`.

## 4. `BorderRadius { top_left: px(8.), .. }` does not compile

Fields are `CornerRadius` in 0.20. Write `px(8.).into()` or `CornerRadius::circular(px(8.))`. Constructors (`BorderRadius::all`, `::top_left`, `::px`, `::MAX`) still work; they are no longer `const`.

## 5. `InputFocus` must not be initialised by hand

`DefaultPlugins` includes `InputFocusPlugin` (0.19+). `input_focus.0` is private; use `get()` / `set(entity, FocusCause)` / `clear()`.

## 6. `On<Pointer<Click>>` is `On<PointerClick>`

Flat pointer events (0.20). Fields moved: `event.pointer_location.position` → `event.pointer.position`; `event.pointer_id` → `event.pointer.id`. Generic code uses the `PointerEvent` trait.

## 7. `On<Insert, Pressed>` is `On<Insert<Pressed>>`

The observer bundle generic moved onto the lifecycle event in 0.20.

## 8. `children![]` bundle grouping

```rust
// CORRECT — one child entity with three components
children![(Button, Node { ..default() }, BackgroundColor(Color::BLACK))]

// WRONG — three separate child entities
children![Button, Node { ..default() }, BackgroundColor(Color::BLACK)]
```

## 9. Missing UI after `default-features = false`

Since 0.19 the `ui` collection is not implied by `2d` / `3d`. Add `ui` explicitly; it brings `bevy_ui_widgets`, `ui_picking`, and `bevy_input_focus`.

## 10. Text widgets split in 0.20

A working text field needs both `EditableText` (state) and `TextInput` (behaviour). `TextScroll` is gone; read `EditableText::viewport.offset`. `TextReader::iter` yields `TextLayoutItem`, not plain spans.

## 11. Internal types that changed shape

Only matters for custom layout or render code: `ComputedNode::stack_index` → `ComputedStackIndex` component (0.19); `CalculatedClip` is an enum (0.20); `ViewportNode.camera` is `Option<Entity>` (0.19); UI rendering is retained in 0.20 (`ExtractedUiNodes::changed`).
