---
name: bevy-fluent
description: Use when adding localization to a Bevy 0.18 app with `es-fluent-manager-bevy`, defining typed messages with `#[derive(EsFluent)]`, wrapping UI text in `FluentText<T>`, auto-registering locale updates with `#[derive(BevyFluentText)]`, or reacting to locale switches via `LocaleChangeEvent`. Covers `I18nPlugin`, `RequestedLanguageId`, `i18n.toml` config, and hot-reload of `.ftl` assets.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "2"
  area: i18n
  bevy_version: "0.18"
---

# Bevy 0.18 — Localization (es-fluent)

## When to use this skill

- Adding Fluent-based i18n to a Bevy app (`es-fluent-manager-bevy = "0.18"`).
- Defining typed UI messages with `#[derive(EsFluent)]` and `#[derive(BevyFluentText)]`.
- Wrapping a UI text entity with `FluentText<T>` for automatic locale-driven refresh.
- Switching locales at runtime via `LocaleChangeEvent`.
- Reading the current locale from `RequestedLanguageId` or `ActiveLanguageId`.
- Checking startup failures through `I18nPluginStartupError`.

## Canonical pattern

`Cargo.toml`:

```toml
[dependencies]
bevy = "0.18"
es-fluent = { version = "0.15", features = ["derive"] }
es-fluent-manager-bevy = { version = "0.18", features = ["macros"] }
unic-langid = "0.9"
```

`i18n.toml` (crate root, read at compile time by `define_i18n_module!()`):

```toml
fallback_language = "en"
assets_dir = "assets/locales"
```

`src/i18n.rs` — declare the module macro in a library-reachable file:

```rust
// Reads i18n.toml at compile time, discovers asset languages, emits metadata.
es_fluent_manager_bevy::define_i18n_module!();
```

`src/main.rs`:

```rust
use bevy::prelude::*;
use es_fluent::EsFluent;
use es_fluent_manager_bevy::{
    BevyFluentText, FluentText, I18nPlugin, LocaleChangeEvent, RequestedLanguageId,
};
use unic_langid::langid;

mod i18n;

// EsFluent  → typed Fluent key lookup (message ID derived from variant name).
// BevyFluentText → registers locale-refresh systems with I18nPlugin via inventory.
#[derive(BevyFluentText, Clone, Component, EsFluent)]
#[fluent(namespace = "ui")]
pub enum UiMessage {
    StartGame,
    Settings,
    QuitGame,
}

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        // Loads .ftl files from assets/locales/<lang>/*.ftl
        .add_plugins(I18nPlugin::with_language(langid!("en")))
        .add_systems(Startup, setup_ui)
        .add_systems(Update, switch_locale_on_keypress)
        .run();
}

fn setup_ui(mut commands: Commands) {
    commands.spawn(Camera2d);

    // Pair FluentText<T> with Text::new("") — the plugin fills in the
    // translated string when bundles load and on every LocaleChangedEvent.
    commands.spawn((
        FluentText::new(UiMessage::StartGame),
        Text::new(""),
    ));
}

fn switch_locale_on_keypress(
    keys: Res<ButtonInput<KeyCode>>,
    requested: Res<RequestedLanguageId>,
    mut locale_events: MessageWriter<LocaleChangeEvent>,
) {
    if keys.just_pressed(KeyCode::KeyL) {
        let next = if requested.0.to_string() == "en" {
            langid!("fr")
        } else {
            langid!("en")
        };
        // LocaleChangeEvent requests a switch; LocaleChangedEvent fires once
        // the new locale's bundles are ready.
        locale_events.write(LocaleChangeEvent(next));
    }
}
```

### Custom asset path

```rust
use es_fluent_manager_bevy::{I18nPlugin, I18nPluginConfig};
use unic_langid::langid;

// When translations live in assets/i18n instead of assets/locales:
I18nPlugin::with_config(
    I18nPluginConfig::new(langid!("en")).with_asset_path("i18n"),
);
```

## Gotchas

- **`BevyFluentText` vs `EsFluent` are separate derives.** `EsFluent` makes a type a typed Fluent message. `BevyFluentText` registers it with `I18nPlugin` for automatic `FluentText<T>` refresh. You need both on types used in UI.
- **`define_i18n_module!()` reads `i18n.toml` at compile time.** Place `i18n.toml` in the crate root. Missing or malformed config is a compile error, not a runtime panic.
- **Put `define_i18n_module!()` in a library target** (`src/lib.rs` or `src/i18n.rs`). Placing it only in `src/main.rs` hides registered types from `cargo es-fluent generate`.
- **`FluentText<T>` needs a sibling `Text::new("")`** on the same entity (or a child). The plugin writes the localized string into the Bevy `Text` component.
- **Events are Messages.** Use `MessageWriter<LocaleChangeEvent>` and `MessageReader<LocaleChangedEvent>` — not `EventWriter`/`EventReader` (renamed in Bevy 0.17).
- **`I18nPluginStartupError`** is a resource inserted when setup fails (invalid config, duplicate registration). Check for it in a startup system to handle graceful degradation.
- **`macros` feature required** for `BevyFluentText` and `define_i18n_module!()`. The default feature set enables it; opt out only with `default-features = false`.
- **`es-fluent` CLI** (`cargo es-fluent generate|watch|check|clean|sync|tree|format`) operates on the library target. Install via `cargo install es-fluent-cli` and run from the crate root alongside `i18n.toml`.
- **`BevyI18n` system param** (imperative localization) exists in the GitHub source but is **not exported in crates.io `0.18.12`**. If you need imperative lookup in a system, query `I18nBundle` and `I18nResource` directly, or wait for a later release.
- **Stated API claim** that `BevyFluentText` is "a UI text component" is inaccurate. `BevyFluentText` is a **derive macro**; the component that wraps UI text is `FluentText<T>`.

## See also

- `bevy-assets` — how Bevy's `AssetServer` loads `.ftl` files; relevant to `watch_for_changes_override` for hot-reload during development.
- `bevy-ecs-components` — `#[derive(Component)]` patterns; `FluentText<T>` is itself a Bevy component and must be combined with ECS entity spawning.
