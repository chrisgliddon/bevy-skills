---
name: bevy-voxel-data
description: Use when defining voxel blocks in RON (`name`, `textures`, `flags`), building a runtime palette mapping `BlockId -> BlockDef`, baking per-block textures into a KTX2 atlas, or binding the atlas as `StandardMaterial.base_color_texture` so meshed quads sample by face index. Generic Bevy 0.18 voxel-data patterns — no game-specific data baked in.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "2"
  area: voxel
  bevy_version: "0.18"
---

# Bevy 0.18 — Voxel data (RON, palette, KTX2 atlas)

## When to use this skill

- Defining a moddable block catalog in a text format authors can edit.
- Building a runtime palette keyed by `BlockId` (`u16`/`u32`) for fast lookup during meshing.
- Packing per-block textures into a single atlas so all chunks can share one material.
- Switching the atlas to KTX2 for GPU-friendly compressed delivery.

## Block catalog in RON

```ron
// assets/blocks.ron
(
    blocks: [
        (
            name: "air",
            visibility: Empty,
        ),
        (
            name: "grass",
            visibility: Opaque,
            faces: (
                top:    "textures/grass_top.png",
                bottom: "textures/dirt.png",
                side:   "textures/grass_side.png",
            ),
        ),
        (
            name: "stone",
            visibility: Opaque,
            faces: ( all: "textures/stone.png" ),
        ),
    ],
)
```

## Data types and palette

```rust
use bevy::prelude::*;
use bevy::reflect::TypePath;
use serde::Deserialize;
use std::collections::HashMap;

#[derive(Debug, Deserialize, Clone, Copy)]
pub enum Visibility { Empty, Translucent, Opaque }

#[derive(Debug, Deserialize, Clone)]
pub struct BlockFaces {
    #[serde(default)] pub top: Option<String>,
    #[serde(default)] pub bottom: Option<String>,
    #[serde(default)] pub side: Option<String>,
    #[serde(default)] pub all: Option<String>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct BlockDef {
    pub name: String,
    pub visibility: Visibility,
    #[serde(default)] pub faces: Option<BlockFaces>,
}

#[derive(Debug, Deserialize, Asset, TypePath)]
pub struct BlockCatalog {
    pub blocks: Vec<BlockDef>,
}

/// Compact runtime palette: BlockId index -> (name, visibility, atlas tile indices per face).
#[derive(Resource, Default)]
pub struct Palette {
    pub by_id: Vec<PaletteEntry>,
    pub by_name: HashMap<String, u16>,
}

#[derive(Default, Clone)]
pub struct PaletteEntry {
    pub name: String,
    pub visibility: Visibility,
    /// Atlas tile index for each face direction:
    /// 0=-X, 1=-Y(bottom), 2=-Z, 3=+X, 4=+Y(top), 5=+Z. Match block-mesh face order.
    pub face_tiles: [u16; 6],
}

impl Default for Visibility { fn default() -> Self { Visibility::Empty } }
```

## Building the palette from the catalog

```rust
# use bevy::prelude::*;
# use std::collections::HashMap;
# #[derive(Resource, Default)] struct AtlasIndex(HashMap<String, u16>);
# #[derive(Resource, Default)] struct Palette { by_id: Vec<crate::PaletteEntry>, by_name: HashMap<String, u16> }
# fn build_palette(
#     catalog: &crate::BlockCatalog,
#     atlas: &AtlasIndex,
#     mut palette: ResMut<Palette>,
# ) {
//   - Walk the catalog, look up each face path in the atlas index,
//   - Emit a PaletteEntry per block in catalog order — that order *is* the BlockId space.
for (id, def) in catalog.blocks.iter().enumerate() {
    let tile_of = |maybe: &Option<String>| -> u16 {
        maybe.as_ref()
            .and_then(|p| atlas.0.get(p).copied())
            .unwrap_or(0)
    };
    let tiles = match &def.faces {
        Some(f) => {
            let all = tile_of(&f.all);
            let side = if f.side.is_some() { tile_of(&f.side) } else { all };
            [
                side,                              // -X
                if f.bottom.is_some() { tile_of(&f.bottom) } else { all }, // -Y
                side,                              // -Z
                side,                              // +X
                if f.top.is_some() { tile_of(&f.top) } else { all }, // +Y
                side,                              // +Z
            ]
        }
        None => [0; 6],
    };
    palette.by_id.push(crate::PaletteEntry {
        name: def.name.clone(),
        visibility: def.visibility,
        face_tiles: tiles,
    });
    palette.by_name.insert(def.name.clone(), id as u16);
}
# }
```

## Atlas binding

Bake all referenced textures into one image (KTX2 if you want compressed, PNG if you don't) and bind it as the material's base-colour texture:

```rust
use bevy::prelude::*;

# fn _bind(
mut materials: ResMut<Assets<StandardMaterial>>,
atlas_image: Handle<Image>,
# ) {
let material = materials.add(StandardMaterial {
    base_color_texture: Some(atlas_image),
    perceptual_roughness: 1.0,
    metallic: 0.0,
    unlit: false,
    ..default()
});
let _ = material;
# }
```

The mesh's UVs reference tile indices encoded as offsets into the atlas. Tile index → UV is:

```text
tile_x = tile_index % atlas_cols
tile_y = tile_index / atlas_cols
uv0    = (tile_x / atlas_cols,        tile_y / atlas_rows)
uv1    = ((tile_x + 1) / atlas_cols,  (tile_y + 1) / atlas_rows)
```

Compute per-vertex UVs in the meshing pass using the `face_tiles` lookup from the palette.

## Gotchas

- **KTX2 is opt-in.** Bevy supports KTX2 via the `ktx2` Cargo feature (on by default in the high-level `3d` collection). For trimmed WASM builds add it explicitly. Use BC7 (desktop) or ETC2/ASTC (mobile) compression depending on target.
- **Atlas size budget.** A 2048×2048 atlas with 32×32 tiles holds 4096 unique tile slots — usually plenty. Larger atlases can be expensive on older GPUs; consider splitting into multiple materials by texture type (opaque, alpha-tested, translucent).
- **Texture bleeding.** When the camera looks at quads at glancing angles, mipmapping samples across tile boundaries and shows the neighbour. Fix: 2-pixel padding around each tile, plus clamp-to-edge sampling per-tile (requires a texture array, not a 2D atlas).
- **Don't bake the atlas at runtime in shipped builds.** Bake at content-build time (a sidecar script), commit the atlas + a JSON index, and load both at runtime. The block-catalog loader resolves block face paths through the index.
- **Palette ordering is the BlockId space.** Reordering the catalog after a save file ships will break that save. Always append; never reorder.
- **Visibility `Translucent` needs alpha blending in the material.** `StandardMaterial { alpha_mode: AlphaMode::Blend, .. }` — and a different mesh batch from opaque blocks, since translucent quads can't be merged into the same draw call.

## See also

- `bevy-voxel-pipeline` — the meshing step that consumes the palette's `face_tiles`.
- `bevy-custom-assets` — implementing the RON catalog loader.
- `bevy-pbr-materials` — wiring the atlas into `StandardMaterial`.
