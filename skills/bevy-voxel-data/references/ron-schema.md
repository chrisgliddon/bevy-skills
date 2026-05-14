# Block Catalog RON Schema

Full field reference for `assets/blocks.ron`. See also
[palette.md](palette.md) for the Rust types this deserializes into.

---

## Full Example

```ron
// assets/blocks.ron
(
    blocks: [
        (
            name: "air",
            visibility: Empty,
            // faces omitted — no textures needed for empty blocks
        ),
        (
            name: "grass",
            visibility: Opaque,
            faces: (
                top:    "textures/grass_top.png",
                bottom: "textures/dirt.png",
                side:   "textures/grass_side.png",
                // `all` is unused when individual face keys are present
            ),
        ),
        (
            name: "stone",
            visibility: Opaque,
            faces: ( all: "textures/stone.png" ),
        ),
        (
            name: "glass",
            visibility: Translucent,
            faces: ( all: "textures/glass.png" ),
            flags: ["no_ao"],
        ),
        (
            name: "water",
            visibility: Translucent,
            faces: (
                top:  "textures/water_top.png",
                side: "textures/water_side.png",
                all:  "textures/water_side.png",  // fallback if top/bottom absent
            ),
            flags: ["no_ao", "animated"],
        ),
    ],
)
```

---

## Field Reference

### `BlockEntry` (each element of `blocks`)

| Field        | Type              | Required | Default   | Description |
|---|---|---|---|---|
| `name`       | `String`          | yes      | —         | Unique identifier; also the key in `Palette.by_name`. |
| `visibility` | `Visibility` enum | yes      | —         | Controls face culling and draw-call batching. |
| `faces`      | `BlockFaces`      | no       | `None`    | Texture paths per face. Omit for fully invisible blocks (air). |
| `flags`      | `Vec<String>`     | no       | `[]`      | Freeform tags consumed by game logic; serde defaults to empty vec. |

### `Visibility` enum

| Variant       | Effect |
|---|---|
| `Empty`       | Block occupies no visual space; skip all face quads. |
| `Opaque`      | All six faces cull neighbours; contributes to ambient-occlusion. |
| `Translucent` | Faces are kept even when neighbours are opaque; requires alpha blend. |

### `BlockFaces`

All four fields are `Option<String>` with `#[serde(default)]`.

| Key      | Maps to face slots |
|---|---|
| `top`    | `+Y` (slot 4 in block-mesh order) |
| `bottom` | `-Y` (slot 1) |
| `side`   | `-X`, `-Z`, `+X`, `+Z` (slots 0, 2, 3, 5) |
| `all`    | Fallback when a specific key is absent. |

Resolution priority per face: specific key → `side` (horizontal faces) → `all` → tile 0.

---

## Serde Defaults and Parser Notes

- Use `#[serde(default)]` on `faces` and `flags` so blocks that omit them
  still deserialize correctly.
- RON is strict about trailing commas — add them; omit them; both are valid.
- The `name` string is used as a HashMap key in `Palette.by_name`; duplicate
  names will silently overwrite earlier entries at palette build time.
- Catalog order is the `BlockId` space — **never reorder entries** after a
  save file ships. Append only.
- `visibility` has no serde default; omitting it is a parse error. This is
  intentional: forgetting `Empty` on air would produce a block that fully
  occludes its neighbours.
