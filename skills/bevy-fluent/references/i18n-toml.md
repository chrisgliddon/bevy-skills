# bevy-fluent — `i18n.toml` Schema

## Purpose

`i18n.toml` is read **at compile time** by the `define_i18n_module!()` macro.
It tells the macro where `.ftl` asset files live and which language to use as
the fallback. A missing or malformed `i18n.toml` is a **compile error**, not a
runtime panic.

Place `i18n.toml` in the crate root — the same directory as `Cargo.toml`.

---

## Full schema

```toml
# Language tag to use when no translation is found for the active locale.
# Must be a valid BCP 47 language tag.
# Required — there is no default.
fallback_language = "en"

# Path (relative to the crate root) where locale asset directories live.
# Each subdirectory is treated as a language tag.
# Default: "assets/locales"
assets_dir = "assets/locales"
```

No other top-level keys are defined in `es-fluent-manager-bevy 0.18.x`.

---

## `assets_dir` layout

Given `assets_dir = "assets/locales"`, the expected directory structure is:

```
assets/
└── locales/
    ├── en/
    │   ├── ui.ftl
    │   └── menu.ftl
    └── fr/
        ├── ui.ftl
        └── menu.ftl
```

Each immediate subdirectory of `assets_dir` must be a valid BCP 47 language
tag. `define_i18n_module!()` enumerates these directories at compile time to
build the list of available locales.

### Custom asset path example

```toml
assets_dir = "assets/i18n"
```

Or, when running an embedded plugin crate where assets live one directory up:

```toml
assets_dir = "../assets/locales"
```

The path is relative to the crate root, not the workspace root.

---

## `I18nPluginConfig` (runtime override)

If you need to override the asset path at runtime (e.g. for testing or
distribution), use `I18nPluginConfig` instead of relying solely on `i18n.toml`:

```rust
use es_fluent_manager_bevy::{I18nPlugin, I18nPluginConfig};
use unic_langid::langid;

I18nPlugin::with_config(
    I18nPluginConfig::new(langid!("en")).with_asset_path("i18n"),
)
```

`with_asset_path` takes a path **relative to the Bevy asset directory** (not
the crate root). By default the Bevy asset directory is `assets/`, so
`with_asset_path("i18n")` loads from `assets/i18n/`.

---

## Compile-time vs runtime errors

| Scenario | Error type |
|----------|-----------|
| `i18n.toml` missing | Compile error inside `define_i18n_module!()` |
| `i18n.toml` malformed TOML | Compile error |
| `fallback_language` is an invalid language tag | Compile error |
| `.ftl` file missing at runtime | `I18nPluginStartupError` resource inserted |
| `.ftl` parse error at runtime | `I18nPluginStartupError` resource inserted |

---

See also: [lib-target-layout.md](lib-target-layout.md),
[components.md](components.md), [cli.md](cli.md).
