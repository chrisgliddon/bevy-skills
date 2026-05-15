# bevy-fluent — Lib-Target Layout

## Why types must live in the library target

`cargo es-fluent generate` discovers `BevyFluentText` / `EsFluent`-derived types
by walking the **library** target's module tree (i.e. everything reachable from
`src/lib.rs`). Types declared only in `src/main.rs` — or in modules that are
reachable only from `main.rs` — are invisible to the CLI and will not appear in
the generated `.ftl` files.

### The `cargo es-fluent generate` invisibility footgun

If you put your message enum inside `src/main.rs`:

```rust
// src/main.rs  ← WRONG
#[derive(BevyFluentText, Clone, EsFluent)]
#[fluent(namespace = "ui")]
pub enum UiMessage { StartGame }
```

Running `cargo es-fluent generate` produces no output for `UiMessage`. There is
no error — the CLI silently skips it. The `.ftl` files it emits will be empty
(or contain only types from the lib target). This is the single most common
setup mistake.

**Fix:** move every `BevyFluentText` / `EsFluent` type to `src/lib.rs` or a
module declared from it.

---

## Full 5-file canonical layout

```
my-game/
├── Cargo.toml
├── i18n.toml
├── assets/
│   └── locales/
│       ├── en/
│       │   └── ui.ftl
│       └── fr/
│           └── ui.ftl
└── src/
    ├── lib.rs     ← types + plugin builder live here
    ├── i18n.rs    ← define_i18n_module!() macro
    └── main.rs    ← thin binary; pulls from the lib
```

### `Cargo.toml`

```toml
[package]
name = "my-game"          # <-- used as the crate identifier in the lib

[lib]
name = "my_game"          # optional explicit lib name

[[bin]]
name = "my-game"
path = "src/main.rs"

[dependencies]
bevy                   = "0.18"
es-fluent              = { version = "0.15", features = ["derive"] }
es-fluent-manager-bevy = { version = "0.18", features = ["macros"] }
unic-langid            = "0.9"
```

### `i18n.toml`

```toml
fallback_language = "en"
assets_dir = "assets/locales"
```

Place this at the crate root (next to `Cargo.toml`). It is read at **compile
time** by `define_i18n_module!()`. A missing or malformed file is a compile
error, not a runtime panic. See [i18n-toml.md](i18n-toml.md) for the full
schema.

### `src/i18n.rs`

```rust
// Reads i18n.toml at compile time; discovers language assets; emits metadata.
es_fluent_manager_bevy::define_i18n_module!();
```

### `src/lib.rs`

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
pub enum UiMessage {
    StartGame,
    Settings,
    QuitGame,
}

pub fn build_i18n_plugin() -> I18nPlugin {
    I18nPlugin::with_language(langid!("en"))
}

pub fn setup_ui(mut commands: Commands) {
    commands.spawn(Camera2d);
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
        locale_events.write(LocaleChangeEvent(next));
    }
}
```

### `src/main.rs`

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

Replace `my_game` with your package name's snake-case form (the `name` field in
`Cargo.toml` with hyphens replaced by underscores). Cargo implicitly links
`src/lib.rs` into the binary when they share a package, which is what wires the
`inventory` registrations from `BevyFluentText` into the running app.

---

## What if you only have a binary crate?

If your project has no `src/lib.rs`, you have two options:

1. **Add one.** Move your message enums there. This is the idiomatic approach
   and the one `cargo es-fluent` expects.

2. **Convert to a workspace.** Put shared types in a `shared` crate and depend
   on it from the binary. `cargo es-fluent generate` must be run from the
   `shared` crate root.

There is no supported way to use `cargo es-fluent generate` with a pure-binary
crate — the type-walking step requires a lib target.

---

See also: [components.md](components.md), [cli.md](cli.md),
[i18n-toml.md](i18n-toml.md).
