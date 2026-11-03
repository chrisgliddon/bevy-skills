# bevy-fluent — Toolchain Requirements

## Minimum Rust version: 1.99

`es-fluent 0.21.x` and `es-fluent-manager-bevy 0.21.x` declare `rust-version = "1.99"`. Older
toolchains fail with cryptic trait-resolution or proc-macro errors that do not
point at the actual cause.

Common symptom on older toolchains:

```
error[E0277]: the trait bound `UiMessage: FluentMessage` is not satisfied
  --> src/lib.rs:8:10
   |
8  | #[derive(BevyFluentText, Clone, EsFluent)]
   |          ^^^^^^^^^^^^^^ the trait `FluentMessage` is not implemented for `UiMessage`
```

This error appears even when `EsFluent` is derived correctly — it is caused by
the proc-macro failing silently on a pre-1.99 compiler, leaving the trait
unimplemented.

---

## Version matrix

| `es-fluent-manager-bevy` | Bevy | rustc |
|---|---|---|
| 0.21.x | 0.20.1+ | 1.99 |
| 0.20.x | 0.19 | see crate `rust-version` |
| 0.18.x | 0.18 | 1.95 |

---

## Pinning the toolchain

Add a `rust-toolchain.toml` at the crate root:

```toml
[toolchain]
channel = "1.99"
```

Rustup reads this file and automatically downloads and uses the pinned version
for all `cargo` and `rustc` invocations in that directory tree.

### Why pin instead of using `stable`?

`stable` advances over time. A future stable release may introduce a breaking
change to a proc-macro dependency (rare, but it happens). Pinning ensures
reproducible builds across developer machines and CI.

### Keeping the pin current

When `es-fluent` releases a version that requires a newer compiler, update
`channel` to the new minimum. You can find the MSRV in `es-fluent`'s
`Cargo.toml` under `rust-version`.

---

## Ad-hoc toolchain override

To check compilation on a specific version without changing `rust-toolchain.toml`:

```sh
cargo +1.99 check
cargo +1.99 build
```

This is useful when bisecting a toolchain regression.

---

## CI example

```yaml
# .github/workflows/ci.yml
- name: Install Rust 1.99
  uses: dtolnay/rust-toolchain@1.99

- name: Build
  run: cargo build

- name: Check i18n
  run: cargo es-fluent check
```

Or, if you have `rust-toolchain.toml` in the repo, `dtolnay/rust-toolchain@stable`
will be overridden by the file automatically — no explicit version needed in CI.

---

## `macros` feature required for `BevyFluentText` and `define_i18n_module!()`

The `macros` feature is required for `BevyFluentText` and
`define_i18n_module!()`. Defaults in 0.21 are `macros` and `file_watcher`
(enables Bevy's `file_watcher` + `embedded_watcher` for `.ftl` hot-reload).
Opt out only with `default-features = false`.

If you set `default-features = false` (common in size-sensitive game projects),
you must re-add `macros` explicitly:

```toml
es-fluent-manager-bevy = { version = "0.21", default-features = false, features = ["macros"] }
```

Without the `macros` feature the proc-macro crate is not compiled and
`BevyFluentText` / `define_i18n_module!()` are not available, producing a
"cannot find derive macro" or "unresolved import" compile error.

---

See also: [cli.md](cli.md), [lib-target-layout.md](lib-target-layout.md).
