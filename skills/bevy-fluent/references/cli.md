# bevy-fluent — CLI Cookbook (`es-fluent-cli`)

## Installation

```sh
cargo install es-fluent-cli
```

Run all commands from the **crate root** (the directory containing `Cargo.toml`
and `i18n.toml`). The CLI reads `i18n.toml` to locate asset directories and
walks the library target's module tree to discover registered types.

---

## Commands

| Command | One-line description |
|---------|---------------------|
| `cargo es-fluent generate` | Walk the lib target; emit `.ftl` skeleton files for all discovered `EsFluent`-derived types |
| `cargo es-fluent watch` | Continuous `generate` — re-runs on every source change. Use during development. |
| `cargo es-fluent check` | Verify that generated `.ftl` files are up-to-date and all message IDs are present. Exits non-zero on mismatch. Use in CI. |
| `cargo es-fluent clean` | Delete all CLI-generated output from the asset directories |
| `cargo es-fluent sync` | Bring secondary locale `.ftl` files in sync with the fallback locale's keys (adds missing keys as comments) |
| `cargo es-fluent tree` | Print a tree of discovered namespaces, types, and message IDs |
| `cargo es-fluent format` | Reformat `.ftl` files according to Fluent style conventions |

---

## Common workflows

### Development

```sh
# Terminal 1 — keep .ftl files updated as you add/rename message variants
cargo es-fluent watch

# Terminal 2 — normal cargo workflow
cargo run
```

`watch` re-runs `generate` automatically. Changes to the `.ftl` files are
picked up by Bevy's hot-reload if `watch_for_changes_override` is enabled in
your `AssetPlugin` config.

### CI gate

```sh
# Fails if .ftl files are missing or stale — run after cargo build
cargo es-fluent check
```

Add this to your CI pipeline after the build step to catch cases where a
developer added a new message variant but forgot to run `generate`.

### Sync translations after adding new keys

```sh
# After adding new variants to your message enum:
cargo es-fluent generate   # regenerates fallback locale .ftl
cargo es-fluent sync       # propagates skeleton entries to other locales
```

`sync` adds missing keys as commented-out placeholders, making it easy for
translators to see what needs work.

---

## The CLI only sees the library target

`cargo es-fluent generate` discovers types by compiling the library target. If
your message enums are only in `src/main.rs`, they are invisible and the
generated `.ftl` files will be empty. See
[lib-target-layout.md](lib-target-layout.md) for the fix.

---

See also: [lib-target-layout.md](lib-target-layout.md),
[i18n-toml.md](i18n-toml.md), [toolchain.md](toolchain.md).
