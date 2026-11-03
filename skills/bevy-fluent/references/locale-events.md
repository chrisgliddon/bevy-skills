# bevy-fluent — Locale Events and State

## Two events, one direction

| Name | Direction | Meaning |
|------|-----------|---------|
| `LocaleChangeMessage` | **request** — you write it | Ask the plugin to switch to a new locale |
| `LocaleChangedMessage` | **confirmation** — you read it | The new locale's bundles have loaded and are active |

These are Bevy 0.17+ **Messages**, not the old `Event` / `EventWriter` /
`EventReader` API. Use `MessageWriter` and `MessageReader`:

```rust
use es_fluent_manager_bevy::{LocaleChangeMessage, LocaleChangedMessage};

// Writing a request:
fn request_locale_switch(mut writer: MessageWriter<LocaleChangeMessage>) {
    writer.write(LocaleChangeMessage(langid!("fr")));
}

// Reading the confirmation:
fn on_locale_changed(mut reader: MessageReader<LocaleChangedMessage>) {
    for event in reader.read() {
        println!("Locale is now: {}", event.0);
    }
}
```

Using `EventWriter<LocaleChangeMessage>` or `EventReader<LocaleChangedMessage>`
compiles on Bevy 0.16 but not on 0.17+. The rename is at the Bevy level, not
`es-fluent-manager-bevy`'s API.

---

## `RequestedLanguageId` — what you asked for

`RequestedLanguageId` is a resource inserted by `I18nPlugin` that reflects the
**most recently requested** locale — i.e. the argument last passed to
`LocaleChangeMessage`. It updates immediately when the event is written, before
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

`ActiveLanguageId` (exported since 0.21) reflects the locale whose bundles are
**currently active and ready**. It lags behind `RequestedLanguageId` by the time
it takes Bevy's `AssetServer` to load the `.ftl` files for the new locale.
`LocaleChangedMessage` fires once when it updates.

---

## Switching locale on a keypress

```rust
pub fn switch_locale_on_keypress(
    keys: Res<ButtonInput<KeyCode>>,
    requested: Res<RequestedLanguageId>,
    mut locale_messages: MessageWriter<LocaleChangeMessage>,
) {
    if keys.just_pressed(KeyCode::KeyL) {
        let next = if requested.0.to_string() == "en" {
            langid!("fr")
        } else {
            langid!("en")
        };
        locale_messages.write(LocaleChangeMessage(next));
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

### Names changed in 0.21

`LocaleChangeEvent` / `LocaleChangedEvent` (0.18–0.20 crate lines) are
`LocaleChangeMessage` / `LocaleChangedMessage` in 0.21. Stale snippets fail
with "cannot find type `LocaleChangeEvent`".

### `BevyI18n` is exported since 0.21

Use the `BevyI18n` system param for imperative lookups instead of querying
bundle resources directly (the 0.18 workaround).

---

See also: [components.md](components.md),
[lib-target-layout.md](lib-target-layout.md).
