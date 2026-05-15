# Palette — Rust Types and Build Function

Runtime lookup table from `BlockId` (position in catalog) to `PaletteEntry`.
See [ron-schema.md](ron-schema.md) for the RON source and
[atlas-binding.md](atlas-binding.md) for how `face_tiles` feeds UV generation.

---

## Type Definitions

```rust
use bevy::prelude::*;
use bevy::reflect::TypePath;
use serde::Deserialize;
use std::collections::HashMap;

#[derive(Debug, Deserialize, Clone, Copy, Default)]
pub enum Visibility { #[default] Empty, Translucent, Opaque }

#[derive(Debug, Deserialize, Clone, Default)]
pub struct BlockFaces {
    #[serde(default)] pub top:    Option<String>,
    #[serde(default)] pub bottom: Option<String>,
    #[serde(default)] pub side:   Option<String>,
    #[serde(default)] pub all:    Option<String>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct BlockDef {
    pub name:       String,
    pub visibility: Visibility,
    #[serde(default)] pub faces: Option<BlockFaces>,
    #[serde(default)] pub flags: Vec<String>,
}

#[derive(Debug, Deserialize, Asset, TypePath)]
pub struct BlockCatalog {
    pub blocks: Vec<BlockDef>,
}

/// Compact runtime palette: catalog index == BlockId.
#[derive(Resource, Default)]
pub struct Palette {
    pub by_id:   Vec<PaletteEntry>,
    pub by_name: HashMap<String, u16>,
}

#[derive(Default, Clone)]
pub struct PaletteEntry {
    pub name:       String,
    pub visibility: Visibility,
    /// Atlas tile index for each of the six face directions.
    /// Index ordering matches block-mesh-rs face order (see table below).
    pub face_tiles: [u16; 6],
}
```

---

## `face_tiles` Slot Convention

`face_tiles[i]` stores the atlas tile index for the face at that slot.
The ordering matches `block_mesh::OrientedBlockFace` in `block-mesh-rs`:

| Slot | Direction | `BlockFaces` key |
|---|---|---|
| 0    | `-X`      | `side`           |
| 1    | `-Y`      | `bottom`         |
| 2    | `-Z`      | `side`           |
| 3    | `+X`      | `side`           |
| 4    | `+Y`      | `top`            |
| 5    | `+Z`      | `side`           |

Keeping this in sync with the meshing skill (`bevy-voxel-pipeline`) is critical:
the mesher reads `face_tiles[face_index]` to write per-vertex UV data.

---

## `build_palette` — Full Implementation

Call this once after the `BlockCatalog` asset loads and the `AtlasIndex` is
populated. `AtlasIndex` maps texture asset paths to atlas tile indices (produced
by the KTX2 baking step — see [ktx2-atlas.md](ktx2-atlas.md)).

```rust
use bevy::prelude::*;
use std::collections::HashMap;

/// Loaded from the JSON sidecar alongside the KTX2 atlas.
#[derive(Resource, Default)]
pub struct AtlasIndex(pub HashMap<String, u16>);

pub fn build_palette(
    catalog:  &BlockCatalog,
    atlas:    &AtlasIndex,
    mut palette: ResMut<Palette>,
) {
    palette.by_id.clear();
    palette.by_name.clear();

    for (id, def) in catalog.blocks.iter().enumerate() {
        let tile_of = |maybe: &Option<String>| -> u16 {
            maybe.as_ref()
                .and_then(|p| atlas.0.get(p).copied())
                .unwrap_or(0)   // tile 0 = "missing texture" sentinel
        };

        let face_tiles = match &def.faces {
            Some(f) => {
                let all  = tile_of(&f.all);
                let side = if f.side.is_some() { tile_of(&f.side)   } else { all };
                let top  = if f.top.is_some()  { tile_of(&f.top)    } else { all };
                let bot  = if f.bottom.is_some(){ tile_of(&f.bottom)} else { all };
                [
                    side, // 0 = -X
                    bot,  // 1 = -Y (bottom)
                    side, // 2 = -Z
                    side, // 3 = +X
                    top,  // 4 = +Y (top)
                    side, // 5 = +Z
                ]
            }
            None => [0; 6],
        };

        palette.by_id.push(PaletteEntry {
            name:       def.name.clone(),
            visibility: def.visibility,
            face_tiles,
        });
        palette.by_name.insert(def.name.clone(), id as u16);
    }
}
```

### Wiring in a system

```rust
fn on_catalog_loaded(
    catalog_assets: Res<Assets<BlockCatalog>>,
    catalog_handle: Res<CatalogHandle>,
    atlas:          Res<AtlasIndex>,
    palette:        ResMut<Palette>,
) {
    let Some(catalog) = catalog_assets.get(&catalog_handle.0) else { return };
    build_palette(catalog, &atlas, palette);
}
```

Run this system in `Update` gated on `AssetEvent<BlockCatalog>` or a
`State` transition — after both the catalog and atlas index are ready.
