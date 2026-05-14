# bevy-fluent — Locale Events and State

## Two events, one direction

| Name | Direction | Meaning |
|------|-----------|---------|
| `LocaleChangeEvent` | **request** — you write it | Ask the plugin to switch to a new locale |
| `LocaleChangedEvent` | **confirmation** — you read it | The new locale's bundles have loaded and are active |

These are Bevy 0.17+ **Messages**, not the old `Event` / `EventWriter` /
`EventReader` API. Use `MessageWriter` and `MessageReader`:

```rust
use es_fluent_manager_bevy::{LocaleChangeEvent, LocaleChangedEvent};

// Writing a request:
fn request_locale_switch(mut writer: MessageWriter<LocaleChangeEvent>) {
    writer.write(LocaleChangeEvent(langid!("fr")));
}

// Reading the confirmation:
fn on_locale_changed(mut reader: MessageReader<LocaleChangedEvent>) {
    for event in reader.read() {
        println!("Locale is now: {}", event.0);
    }
}
```

Using `EventWriter<LocaleChangeEvent>` or `EventReader<LocaleChangedEvent>`
compiles on Bevy 0.16 but not on 0.17+. The rename is at the Bevy level, not
`es-fluent-manager-bevy`'s API.

---

## `RequestedLanguageId` — what you asked for

`RequestedLanguageId` is a resource inserted by `I18nPlugin` that reflects the
**most recently requested** locale — i.e. the argument last passed to
`LocaleChangeEvent`. It updates immediately when the event is written, before
the `.ftl` bundles for that locale have finished loading.

```rust
fn show_requested_locale(requested: Res<RequestedLanguageId>) {
    println!("User wants: {}", requested.0);
}
```

Use `RequestedLanguageId` to drive UI (e.g. highlight the active language in a
settings menu) without waiting for asset loading.

---

## `ActiveLanguageId` — what is actually loaded

`ActiveLanguageId` (if exported in the version you are using) reflects the
locale whose bundles are **currently active and ready**. It lags behind
`RequestedLanguageId` by the time it takes Bevy's `AssetServer` to load the
`.ftl` files for the new locale.

If `ActiveLanguageId` is not exported in your version of
`es-fluent-manager-bevy`, react to `LocaleChangedEvent` instead — it fires
exactly once when the new locale is ready.

---

## Switching locale on a keypress

```rust
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

The `RequestedLanguageId` resource is read (not mutated) here — `I18nPlugin`
owns the write side. Attempting to `ResMut<RequestedLanguageId>` directly and
set it yourself will not trigger bundle loading.

---

## Startup locale

Pass the initial locale to `I18nPlugin::with_language`:

```rust
I18nPlugin::with_language(langid!("en"))
```

The plugin inserts `RequestedLanguageId` with this value before any systems run.

---

## Pitfalls

### `BevyI18n` system param not exported in crates.io release

`BevyI18n` system param (imperative localization) exists in the GitHub source
but is **not exported in crates.io `0.18.12`**. If you need imperative lookup
in a system, query `I18nBundle` and `I18nResource` directly, or wait for a
later release.

---

See also: [components.md](components.md),
[lib-target-layout.md](lib-target-layout.md).
