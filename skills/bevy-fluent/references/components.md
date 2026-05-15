# bevy-fluent — Components and Derives

## Two separate derives, two separate jobs

### `#[derive(EsFluent)]`

Makes a type a **typed Fluent message**. Each variant maps to a Fluent message
ID (derived from the variant name by converting `PascalCase` to `kebab-case`,
e.g. `StartGame` → `start-game`). Provides the `ToFluentString` implementation
used by the runtime lookup.

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

## The `Component` derive bound

`FluentText<T>` is bounded as follows (from
`es-fluent-manager-bevy-0.18.12/src/registration.rs:27`):

```rust
pub fn register_fluent_text<T>()
where
    T: ToFluentString + Clone + Component + Send + Sync + 'static,
```

This means your message enum `T` **must also derive `Component`**, even though
`T` is conceptually "just" a message key. The reason: `FluentText<T>` stores a
`T` internally, and the inventory machinery uses the `Component` bound to
satisfy Bevy's ECS type-system constraints when registering the refresh system.

```rust
// All four derives are required for types used with FluentText<T>:
#[derive(BevyFluentText, Clone, EsFluent, Component)]
#[fluent(namespace = "ui")]
pub enum UiMessage {
    StartGame,
}
```

Forgetting `Component` produces a trait-bound error at compile time from deep
inside the `BevyFluentText` expansion — the error message does not always point
at the missing derive.

---

## `Text::new("")` requirement

`FluentText<T>` writes translated text into a sibling `Text` component on the
same entity. You must spawn `Text::new("")` alongside it. If `Text` is absent,
the refresh system silently skips the entity (no panic, no warning).

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

If `I18nPlugin` fails to set up (invalid config, duplicate registration, missing
`.ftl` files), it inserts an `I18nPluginStartupError` resource. Check for it in
a startup system to implement graceful degradation or a user-visible error
screen:

```rust
fn check_i18n_errors(error: Option<Res<I18nPluginStartupError>>) {
    if let Some(err) = error {
        eprintln!("i18n setup failed: {:?}", *err);
    }
}
```

---

See also: [lib-target-layout.md](lib-target-layout.md),
[locale-events.md](locale-events.md).
