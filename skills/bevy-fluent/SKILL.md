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

`src/i18n.rs` — module file holding the compile-time discovery macro:

```rust
// Reads i18n.toml at compile time, discovers asset languages, emits metadata.
es_fluent_manager_bevy::define_i18n_module!();
```

`src/lib.rs` — **required** so the macro module and every `BevyFluentText` /
`EsFluent`-derived type live in the library target. `cargo es-fluent generate`
discovers types by walking the lib's module tree; anything declared only in
`src/main.rs` is invisible to the CLI.

```rust
use bevy::prelude::*;
use es_fluent::EsFluent;
use es_fluent_manager_bevy::{
    BevyFluentText, FluentText, I18nPlugin, LocaleChangeEvent, RequestedLanguageId,
};
use unic_langid::langid;

pub mod i18n;

// EsFluent      → typed Fluent key lookup (message ID derived from variant name).
// BevyFluentText → registers locale-refresh systems with I18nPlugin via inventory.
#[derive(BevyFluentText, Clone, EsFluent)]
#[fluent(namespace = "ui")]
pub enum UiMessage {
    StartGame,
    Settings,
    QuitGame,
}

pub fn build_i18n_plugin() -> I18nPlugin {
    // Loads .ftl files from assets/locales/<lang>/*.ftl
    I18nPlugin::with_language(langid!("en"))
}

pub fn setup_ui(mut commands: Commands) {
    commands.spawn(Camera2d);

    // Pair FluentText<T> with Text::new("") — the plugin fills in the
    // translated string when bundles load and on every LocaleChangedEvent.
    commands.spawn((
        FluentText::new(UiMessage::StartGame),
        Text::new(""),
    ));
}

pub fn switch_locale_on_keypress(
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

`src/main.rs` — thin binary entry point that pulls everything from the lib:

```rust
use bevy::prelude::*;
use my_game::{build_i18n_plugin, setup_ui, switch_locale_on_keypress};

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_plugins(build_i18n_plugin())
        .add_systems(Startup, setup_ui)
        .add_systems(Update, switch_locale_on_keypress)
        .run();
}
```

Replace `my_game` with your package name (the `name` field in `Cargo.toml`). Cargo implicitly links `src/lib.rs` into the binary when they share a package, which is what wires the `inventory` registrations into the running app.

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
- **Put `define_i18n_module!()` in a file that is part of the library target** — i.e., `src/lib.rs` directly, or a module declared from it (e.g. `pub mod i18n;` in `src/lib.rs` with `define_i18n_module!()` in `src/i18n.rs`). Placing it only in the binary target (`src/main.rs` or any module only reachable from there) hides registered types from `cargo es-fluent generate`. The same rule applies to every `BevyFluentText` / `EsFluent`-derived type — keep them in the lib, expose them to the binary via `use my_game::*;`.
- **`FluentText<T>` needs a sibling `Text::new("")`** on the same entity (or a child). The plugin writes the localized string into the Bevy `Text` component.
- **Events are Messages.** Use `MessageWriter<LocaleChangeEvent>` and `MessageReader<LocaleChangedEvent>` — not `EventWriter`/`EventReader` (renamed in Bevy 0.17).
- **`I18nPluginStartupError`** is a resource inserted when setup fails (invalid config, duplicate registration). Check for it in a startup system to handle graceful degradation.
- **`macros` feature required** for `BevyFluentText` and `define_i18n_module!()`. The default feature set enables it; opt out only with `default-features = false`.
- **`es-fluent` CLI** (`cargo es-fluent generate|watch|check|clean|sync|tree|format`) operates on the library target. Install via `cargo install es-fluent-cli` and run from the crate root alongside `i18n.toml`.
- **`BevyI18n` system param** (imperative localization) exists in the GitHub source but is **not exported in crates.io `0.18.12`**. If you need imperative lookup in a system, query `I18nBundle` and `I18nResource` directly, or wait for a later release.
- **`BevyFluentText` is a derive macro, not a component.** It registers refresh systems with `I18nPlugin` via `inventory`. The component that wraps UI text is `FluentText<T>`. The message enum `T` still needs `#[derive(Component)]` because `es-fluent-manager-bevy`'s `FluentTextRegistration::register_fluent_text` is bounded `T: ToFluentString + Clone + Component + Send + Sync + 'static` — `T` is stored inside `FluentText<T>` but the inventory machinery treats it as an ECS component for its own bookkeeping.
- **Minimum rustc version: 1.95.** `es-fluent` 0.15.x uses language features stabilized in Rust 1.95. Older toolchains fail with cryptic trait-resolution errors. Pin via `rust-toolchain.toml` at the crate root (`[toolchain]` / `channel = "1.95"`), or run `cargo +1.95 check` ad-hoc.

## See also

- `bevy-assets` — how Bevy's `AssetServer` loads `.ftl` files; relevant to `watch_for_changes_override` for hot-reload during development.
- `bevy-ecs-components` — `#[derive(Component)]` patterns; `FluentText<T>` is itself a Bevy component and must be combined with ECS entity spawning.
