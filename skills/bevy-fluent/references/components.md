# bevy-fluent — Components and Derives

## Two separate derives, two separate jobs

### `#[derive(EsFluent)]`

Makes a type a **typed Fluent message**. Each variant maps to a Fluent message
ID (derived from the variant name by converting `PascalCase` to `kebab-case`,
e.g. `StartGame` → `start-game`). Provides the `FluentMessage` implementation
(`to_fluent_string_with`) used by the runtime lookup. (`ToFluentString` was the
pre-0.20 trait name.)

```rust
#[derive(EsFluent)]
#[fluent(namespace = "ui")]
pub enum UiMessage {
    StartGame,    // → fluent ID: "start-game" in namespace "ui"
    Settings,
    QuitGame,
}
```

### `#[derive(BevyFluentText)]`

**Registers the type with `I18nPlugin`** so that every entity carrying
`FluentText<UiMessage>` gets its `Text` component refreshed whenever the active
locale changes. The registration happens via `inventory` at startup — no manual
plugin call is needed, but `I18nPlugin` must be present in the app.

`BevyFluentText` is a derive macro, **not a component**. It generates an
`inventory::submit!` call that adds a `FluentTextRegistration<T>` to a global
registry. `I18nPlugin::build()` iterates that registry and adds the refresh
systems.

### `FluentText<T>` — the component you spawn

`FluentText<T>` is the actual **ECS component** that you attach to UI entities.
It stores a `T` value (your message enum variant) and tells the refresh system
which Fluent message to display on that entity.

```rust
// Spawn a UI text entity with a FluentText component.
// Text::new("") is required — the plugin writes the translation into it.
commands.spawn((
    FluentText::new(UiMessage::StartGame),
    Text::new(""),
));
```

---

## Trait bounds on `T` (0.21)

`FluentText<T>` and its registration are bounded as follows (from
`es-fluent-manager-bevy-0.21.2/src/components.rs` and `src/registration.rs`):

```rust
pub struct FluentText<T: FluentMessage> { pub value: T }

fn register_fluent_text<T: es_fluent::FluentMessage + Send + Sync + 'static>(&mut self) -> &mut Self;
```

`FluentText<T>` is the `Component`; `T` is not. The 0.18 bound
(`ToFluentString + Clone + Component`) is gone, so `#[derive(Component)]` on the
message enum is optional. `Clone` is still needed because `FluentText<T>` derives
`Clone`.

```rust
// Sufficient in 0.21:
#[derive(BevyFluentText, Clone, EsFluent)]
#[fluent(namespace = "ui")]
pub enum UiMessage {
    StartGame,
}
```

A missing `EsFluent` derive surfaces as "the trait `FluentMessage` is not
implemented" from inside the `BevyFluentText` expansion.

---

## `Text::new("")` requirement

`FluentText<T>` writes translated text into the `Text` component on the same
entity and into `Text` components on its direct children (0.21
`update_fluent_text_system`). Spawn `Text::new("")` alongside it, or give it a
`Text` child. With neither, the refresh system silently skips the entity.
Unchanged output does not mark `Text` as changed (`set_if_neq`), so change
detection stays quiet between locale switches.

```rust
// Correct: Text::new("") paired with FluentText
commands.spawn((
    FluentText::new(UiMessage::StartGame),
    Text::new(""),
));

// Broken: translation never appears — no Text component
commands.spawn(FluentText::new(UiMessage::StartGame));
```

---

## `I18nPluginStartupError`

`#[locale]` fields (0.21): mark a field whose value should be rebuilt from the
new locale; `BevyFluentText` then registers through
`register_fluent_text_from_locale`. The field type must implement
`TryFrom<&LanguageIdentifier>`.



If `I18nPlugin` fails to set up (invalid config, duplicate registration, missing
`.ftl` files), it inserts an `I18nPluginStartupError` resource. Check for it in
a startup system to implement graceful degradation or a user-visible error
screen:

```rust
fn check_i18n_errors(error: Option<Res<I18nPluginStartupError>>) {
    if let Some(err) = error {
        eprintln!("i18n setup failed: {}", err.message());
    }
}
```

---

See also: [lib-target-layout.md](lib-target-layout.md),
[locale-events.md](locale-events.md).
