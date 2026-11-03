---
name: bevy-migration-0-18-to-0-19
description: "Use when upgrading from Bevy 0.18 to Bevy 0.19, when `TextLayout::new_with_justify` or `TextFont { font_size: 24.0, font: handle }` stops compiling (now `TextLayout::justify`, `FontSize::Px`, `FontSource`), when `bevy_scene`/`DynamicScene` serialization moved to `bevy_world_serialization` (`WorldAsset`/`DynamicWorld`), when a `#[derive(Resource)]` type now also matches `&T` component queries, or when `init_non_send_resource`/`FeathersPlugin`/`EasyScreenRecordPlugin` changed. Index of every breaking Bevy 0.19 change."
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "1"
  area: migration
  bevy_version: "0.19"
  target_version: "Bevy 0.19"
---

# Bevy 0.18 → 0.19 — Migration cheat sheet

**Released 2026-06-18.** Apply top-down — earlier items break later builds if skipped. Going all the way to 0.20? Finish this sheet, then `bevy-migration-0-19-to-0-20`.

## When to use this skill

- Compiler errors after a `bevy = "0.18"` → `bevy = "0.19"` bump.
- LLM emits 0.18-era text/font/scene API names from training data.
- A `#[derive(Resource)]` type suddenly behaves like a component.
- A third-party crate (`bevy_capture`, etc.) hasn't shipped 0.19 yet.

## The renames you'll hit first

### Text layout: drop the `new_with_` prefix

```rust
// 0.19
TextLayout::justify(Justify::Left)   // was new_with_justify
TextLayout::linebreak(/* … */)       // was new_with_linebreak
TextLayout::no_wrap()                // was new_with_no_wrap
```

### `TextFont` fields changed type: `FontSource` + `FontSize`

```rust
// 0.19 — font is FontSource (handle OR family), font_size is FontSize
TextFont {
    font: asset_server.load("fonts/FiraSans-Bold.ttf").into(), // Handle → FontSource via .into()
    font_size: FontSize::Px(24.0),                             // f32 → FontSize::Px / ::Vh / ::Rem
    ..default()
}
// Select by family (needs the `bevy/system_font_discovery` feature for installed fonts):
TextFont { font: FontSource::family("Fira Sans"), ..default() }
```

0.19 swapped the cosmic-text layout backend for **Parley**, which does font fallback
automatically via `fontique`. The old "insert a `DefaultFontHandle` so `..default()`
entities inherit a font" trick is obsolete — see [references/text-and-fonts.md](references/text-and-fonts.md).

### Scene serialization crate was renamed (silent wrong-crate trap)

`bevy_scene` is **reused** for the new BSN system. Classic `DynamicScene` round-trip
serialization moved to **`bevy_world_serialization`**:

```rust
// 0.18  → 0.19
// bevy_scene::DynamicScene          → bevy_world_serialization::DynamicWorld
// bevy::scene::SceneRoot            → bevy::world_serialization::WorldAssetRoot
// DynamicSceneBuilder               → DynamicWorldBuilder
// SceneSpawner                      → WorldInstanceSpawner
```

glTF scene spawning still uses the old (now `world_serialization`) system. Full table:
[references/scene-serialization.md](references/scene-serialization.md).

### Resources are now Components (mostly a mental-model change)

`Res<T>`, `ResMut<T>`, `#[derive(Resource)]`, and `insert_resource` **all still work.**
The narrow breakages:

```rust
// ILLEGAL in 0.19 — a type can no longer be both:
#[derive(Component, Resource)] struct Health(u32);
```

Plus: a resource type now also matches `Query<&T>`, and inserting it as a *component*
can despawn other copies. Non-send resource methods were renamed (deprecated, not removed):

```rust
world.init_non_send::<T>();    // was init_non_send_resource
world.get_non_send::<T>();     // was get_non_send_resource
```

Details + the query/despawn footgun: [references/resources-as-components.md](references/resources-as-components.md).

## Cargo feature implications tightened

```toml
# 0.19: audio is NO LONGER implied by 2d / 3d / ui — add it explicitly:
bevy = { version = "0.19", features = ["3d", "bevy_audio", "vorbis"] }
# ui is NO LONGER implied by 2d / 3d either — add "ui" if you build UI.
```

## Feathers UI stabilized

`experimental_` dropped. `FeathersPlugin` → `FeathersCorePlugin`, and widget components
lost their `Core` prefix (`CoreScrollbarThumb` → `ScrollbarThumb`,
`CoreSliderDragState` → `SliderDragState`, etc.). Only relevant if you use Feathers.

## Third-party crates lag the release

`bevy_capture` (the crate behind `bevy-capture`) tracks Bevy and may not have a 0.19
release yet — **verify a 0.19-compatible version exists before bumping.** When it does,
`EasyScreenRecordPlugin` gained a required `output_dir: Option<PathBuf>` field
(only breaks manual struct construction; `..default()` is fine).

## Gotchas

- **`#[reflect(Resource)]`** reflection access now also needs `ReflectComponent` in some paths.
- **`TextFont::default().font` is a `FontSource`, not a `Handle<Font>`** — code that read it as a handle won't compile.
- **System font discovery** needs the `bevy/system_font_discovery` feature; on Linux also `libfontconfig1-dev`.
- The fallback setters (`set_serif_family`, etc.) now return `Result` — and you mostly shouldn't need them under Parley.

## See also

- `bevy-migration-0-19-to-0-20` — the next release's catalogue.
- `bevy-migration-0-17-to-0-18` — the previous release's rename catalogue.
- `bevy-ui` — `TextFont`/`FontSize`/`FontSource` in everyday UI code.
- `bevy-cargo-features` — feature-implication table and renames.
- `bevy-ecs-components` — the Component model the new Resource subtrait plugs into.
