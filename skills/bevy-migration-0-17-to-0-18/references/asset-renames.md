# Asset Renames — Bevy 0.17 → 0.18

Cross-links: [ecs-renames](ecs-renames.md) | [render-renames](render-renames.md) | [schedule-renames](schedule-renames.md) | [cargo-feature-renames](cargo-feature-renames.md)

## `AssetLoader` must `#[derive(TypePath)]`

```rust
// 0.17
struct MyLoader;
impl AssetLoader for MyLoader { /* ... */ }

// 0.18 — TypePath derive required
#[derive(TypePath)]
struct MyLoader;
impl AssetLoader for MyLoader { /* ... */ }
```

## `LoadContext::path` → `LoadContext::asset_path`

```rust
// 0.17
let p = load_context.path();

// 0.18
let p = load_context.asset_path();
```

## `LoadContext::asset_bytes` removed — use reader

`asset_bytes()` was a synchronous helper that loaded bytes inline. In 0.18 use the async reader:

```rust
// 0.17
let bytes = load_context.asset_bytes()?;

// 0.18
let mut buf = Vec::new();
let reader = load_context.asset_reader();
reader.read_to_end(&mut buf).await?;
```

## `AssetSource` channel: crossbeam → async_channel

Internal `AssetSource` event channels switched from `crossbeam_channel` to `async_channel`. The change only surfaces if you implement a custom `AssetReader`/`AssetWriter` or interact with the raw sender:

```rust
// 0.17
sender.send(event)?; // crossbeam_channel::Sender

// 0.18
sender.send_blocking(event)?; // async_channel::Sender (blocking variant)
// or in an async context:
sender.send(event).await?;
```

## `Mesh::insert_attribute` is panicky — prefer `try_insert_attribute`

In 0.18 `insert_attribute` panics if the mesh has already been extracted to the render world (a real race in tools that mutate meshes post-spawn). Use the fallible form:

```rust
// 0.17 — always infallible
mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, positions);

// 0.18 — panics post-extract; prefer:
mesh.try_insert_attribute(Mesh::ATTRIBUTE_POSITION, positions)?;
// Returns Result<(), MeshAccessError>
```

`insert_attribute` is still available; it internally calls `.expect(...)`. Use it only when you are certain the mesh has not yet been extracted.

## `Image::reinterpret_size` now returns `Result`

```rust
// 0.17
image.reinterpret_size(new_size);

// 0.18
image.reinterpret_size(new_size)?; // returns Result<(), BevyError>
```
