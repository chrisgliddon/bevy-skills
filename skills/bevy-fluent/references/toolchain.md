# bevy-fluent — Toolchain Requirements

## Minimum Rust version: 1.95

`es-fluent 0.15.x` uses language features stabilized in **Rust 1.95**. Older
toolchains fail with cryptic trait-resolution or proc-macro errors that do not
point at the actual cause.

Common symptom on older toolchains:

```
error[E0277]: the trait bound `UiMessage: ToFluentString` is not satisfied
  --> src/lib.rs:8:10
   |
8  | #[derive(BevyFluentText, Clone, EsFluent, Component)]
   |          ^^^^^^^^^^^^^^ the trait `ToFluentString` is not implemented for `UiMessage`
```

This error appears even when `EsFluent` is derived correctly — it is caused by
the proc-macro failing silently on a pre-1.95 compiler, leaving the trait
unimplemented.

---

## Pinning the toolchain

Add a `rust-toolchain.toml` at the crate root:

```toml
[toolchain]
channel = "1.95"
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
cargo +1.95 check
cargo +1.95 build
```

This is useful when bisecting a toolchain regression.

---

## CI example

```yaml
# .github/workflows/ci.yml
- name: Install Rust 1.95
  uses: dtolnay/rust-toolchain@1.95

- name: Build
  run: cargo build

- name: Check i18n
  run: cargo es-fluent check
```

Or, if you have `rust-toolchain.toml` in the repo, `dtolnay/rust-toolchain@stable`
will be overridden by the file automatically — no explicit version needed in CI.

---

See also: [cli.md](cli.md), [lib-target-layout.md](lib-target-layout.md).
