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
- Reading the current locale from `RequestedLanguageId`.

## Canonical pattern — 5-file minimum shape

`Cargo.toml`:

```toml
[dependencies]
bevy                   = "0.18"
es-fluent              = { version = "0.15", features = ["derive"] }
es-fluent-manager-bevy = { version = "0.18", features = ["macros"] }
unic-langid            = "0.9"
```

`i18n.toml` (crate root, read at compile time):

```toml
fallback_language = "en"
assets_dir = "assets/locales"
```

`src/i18n.rs`:

```rust
es_fluent_manager_bevy::define_i18n_module!();
```

`src/lib.rs` — **message types must live here** (see Gotchas):

```rust
use bevy::prelude::*;
use es_fluent::EsFluent;
use es_fluent_manager_bevy::{
    BevyFluentText, FluentText, I18nPlugin, LocaleChangeEvent, RequestedLanguageId,
};
use unic_langid::langid;

pub mod i18n;

#[derive(BevyFluentText, Clone, EsFluent, Component)]
#[fluent(namespace = "ui")]
pub enum UiMessage { StartGame, Settings, QuitGame }

pub fn build_i18n_plugin() -> I18nPlugin {
    I18nPlugin::with_language(langid!("en"))
}

pub fn setup_ui(mut commands: Commands) {
    commands.spawn(Camera2d);
    // FluentText<T> writes translations into a sibling Text component.
    commands.spawn((FluentText::new(UiMessage::StartGame), Text::new("")));
}

pub fn switch_locale_on_keypress(
    keys: Res<ButtonInput<KeyCode>>,
    requested: Res<RequestedLanguageId>,
    mut locale_events: MessageWriter<LocaleChangeEvent>,
) {
    if keys.just_pressed(KeyCode::KeyL) {
        let next = if requested.0.to_string() == "en" { langid!("fr") } else { langid!("en") };
        locale_events.write(LocaleChangeEvent(next));
    }
}
```

`src/main.rs` — thin binary entry point:

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

Replace `my_game` with your package name (hyphens become underscores). The full
walkthrough — including the lib-vs-binary rationale, package-name placeholder,
and pure-binary-crate workarounds — is in
[references/lib-target-layout.md](references/lib-target-layout.md).

## Topics

| Topic | Reference |
|-------|-----------|
| Why types must live in the lib target; `cargo es-fluent generate` invisibility footgun; full layout | [references/lib-target-layout.md](references/lib-target-layout.md) |
| `BevyFluentText` derive vs `FluentText<T>` component; `Component` bound; `Text::new("")` | [references/components.md](references/components.md) |
| `LocaleChangeEvent` (request) vs `LocaleChangedEvent` (confirmation); `RequestedLanguageId`; Messages vs Events | [references/locale-events.md](references/locale-events.md) |
| `i18n.toml` full schema, `assets_dir`, `I18nPluginConfig` runtime override | [references/i18n-toml.md](references/i18n-toml.md) |
| `generate`, `watch`, `check`, `clean`, `sync`, `tree`, `format` — dev and CI workflows | [references/cli.md](references/cli.md) |
| rustc 1.95+ requirement; `rust-toolchain.toml` pin; failure modes on older toolchains | [references/toolchain.md](references/toolchain.md) |

## Gotchas

1. **`cargo es-fluent generate` only sees the lib target.** Message enums
   declared only in `src/main.rs` are invisible to the CLI and produce empty
   `.ftl` output with no error. Move every `BevyFluentText` / `EsFluent`-derived
   type to `src/lib.rs` (or a module reachable from it). See
   [references/lib-target-layout.md](references/lib-target-layout.md).

2. **`BevyFluentText` is a derive macro; `FluentText<T>` is the component.** The
   derive registers refresh systems via `inventory`. The component is what you
   spawn on UI entities. Your message enum `T` must also derive `Component`
   because `FluentTextRegistration::register_fluent_text` requires
   `T: ToFluentString + Clone + Component + Send + Sync + 'static`. Missing
   `Component` gives a confusing trait-bound error. See
   [references/components.md](references/components.md).

3. **Minimum rustc 1.95.** Older toolchains fail with cryptic trait-resolution
   errors that do not mention the version requirement. Pin with
   `rust-toolchain.toml` (`[toolchain]` / `channel = "1.95"`). See
   [references/toolchain.md](references/toolchain.md).

4. **Events are Messages.** Use `MessageWriter<LocaleChangeEvent>` and
   `MessageReader<LocaleChangedEvent>` — not `EventWriter`/`EventReader`
   (renamed in Bevy 0.17). See [references/locale-events.md](references/locale-events.md).

## See also

- `bevy-ui` — `FluentText<T>` is used alongside `Text`, `Node`, and `Button`.
- `bevy-ecs-components` — `#[derive(Component)]` patterns required by `FluentText<T>`.
- `bevy-assets` — how Bevy's `AssetServer` loads `.ftl` files; relevant for hot-reload.
