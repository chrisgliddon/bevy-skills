# Cargo Feature Renames — Bevy 0.17 → 0.18

Cross-links: [ecs-renames](ecs-renames.md) | [render-renames](render-renames.md) | [asset-renames](asset-renames.md) | [schedule-renames](schedule-renames.md)

## Feature rename table

| 0.17 feature | 0.18 feature |
|---|---|
| `animation` | `gltf_animation` |
| `bevy_sprite_picking_backend` | `sprite_picking` |
| `bevy_ui_picking_backend` | `ui_picking` |
| `bevy_mesh_picking_backend` | `mesh_picking` |
| `documentation` | `reflect_documentation` |

Update your `Cargo.toml` features list after bumping to `bevy = "0.18"`.

## Input features no longer in `default-features = false`

In 0.17, `default-features = false` still pulled in a unified `input` feature. In 0.18, input devices are opt-in individually:

```toml
# Cargo.toml
[dependencies]
# 0.17 — one flag covered all input
# bevy = { version = "0.17", default-features = false, features = ["input"] }

# 0.18 — add only the devices you need
bevy = { version = "0.18", default-features = false, features = [
    "mouse",
    "keyboard",
    "gamepad",  # optional
    "touch",    # optional
    "gestures", # optional
] }
```

Omitting these in a `default-features = false` setup causes `Input<MouseButton>`, `Input<KeyCode>`, etc. to be absent at compile time with no clear error — the resources simply don't exist.

## `gltf_animation` replaces `animation`

If your crate only used `animation` for GLTF clips (the common case), rename it:

```toml
# 0.17
bevy = { version = "0.17", features = ["animation"] }

# 0.18
bevy = { version = "0.18", features = ["gltf_animation"] }
```

There is no standalone `animation` feature in 0.18 — the rename is complete. For non-GLTF animation (`AnimationPlayer` + `AnimationGraph` driven from custom clips or `bevy_scene`), enable the `bevy_animation` subcrate selector when running with `default-features = false`:

```toml
# 0.18 — non-GLTF animation, minimal feature set
bevy = { version = "0.18", default-features = false, features = ["bevy_animation"] }
```

`gltf_animation` is the GLTF-binding layer on top of `bevy_animation`; enable both if you need GLTF clips plus custom-built clips in the same crate.

## Picking backend names shortened

The `bevy_` prefix was dropped from the picking backend features to match the rest of the optional-module naming convention:

```toml
# 0.17
features = ["bevy_sprite_picking_backend", "bevy_ui_picking_backend"]

# 0.18
features = ["sprite_picking", "ui_picking"]
```
