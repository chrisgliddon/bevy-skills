# Atlas Binding to StandardMaterial

Wiring the baked KTX2 atlas into `StandardMaterial` and computing per-vertex
UVs from tile indices during meshing. See [ktx2-atlas.md](ktx2-atlas.md) for
how the atlas is produced and [palette.md](palette.md) for the `face_tiles`
source data.

---

## Binding the Atlas

```rust
use bevy::prelude::*;

fn setup_material(
    mut materials: ResMut<Assets<StandardMaterial>>,
    asset_server:  Res<AssetServer>,
) -> Handle<StandardMaterial> {
    let atlas = asset_server.load("blocks_atlas.ktx2");
    materials.add(StandardMaterial {
        base_color_texture: Some(atlas),
        perceptual_roughness: 1.0,
        metallic: 0.0,
        reflectance: 0.0,
        // Opaque pass; translucent blocks use a separate material:
        alpha_mode: AlphaMode::Opaque,
        unlit: false,
        ..default()
    })
}
```

For translucent blocks (glass, water), create a second material with
`alpha_mode: AlphaMode::Blend`. Separate the opaque and translucent mesh
batches — they cannot share a draw call.

---

## UV Computation Formula

Given a 2D atlas, the tile UV corners are:

```text
// Atlas layout: atlas_cols columns, atlas_rows rows of equal-size tiles.

tile_x  = tile_index % atlas_cols          // column
tile_y  = tile_index / atlas_cols          // row

uv0     = ( tile_x      / atlas_cols,  tile_y      / atlas_rows )  // top-left
uv1     = ( (tile_x+1)  / atlas_cols,  (tile_y+1)  / atlas_rows )  // bottom-right
```

In Rust during the meshing pass:

```rust
/// Given a face's tile index, return the UV rectangle [min, max].
pub fn tile_uv(tile_index: u16, atlas_cols: u32, atlas_rows: u32) -> (Vec2, Vec2) {
    let cols = atlas_cols as f32;
    let rows = atlas_rows as f32;
    let tx   = (tile_index as u32 % atlas_cols) as f32;
    let ty   = (tile_index as u32 / atlas_cols) as f32;
    (
        Vec2::new(tx / cols,       ty / rows),       // uv_min
        Vec2::new((tx+1.0) / cols, (ty+1.0) / rows), // uv_max
    )
}
```

Look up `face_tiles[face_slot]` from `Palette.by_id[block_id]` to get the
`tile_index` for each quad face being meshed.

---

## Per-Vertex UV Emission

During the meshing pass (in `bevy-voxel-pipeline`), emit UVs per vertex:

```rust
// Four vertices of a quad (block-mesh-rs quad winding: 0,1,2,3 = BL,BR,TR,TL)
let (uv_min, uv_max) = tile_uv(tile_index, ATLAS_COLS, ATLAS_ROWS);
let uvs = [
    Vec2::new(uv_min.x, uv_max.y),  // bottom-left
    Vec2::new(uv_max.x, uv_max.y),  // bottom-right
    Vec2::new(uv_max.x, uv_min.y),  // top-right
    Vec2::new(uv_min.x, uv_min.y),  // top-left
];
```

Push these into the `Mesh::ATTRIBUTE_UV_0` buffer alongside positions and
normals.

---

## Sampler Configuration for Tile Arrays

If you use a **texture array** instead of a 2D atlas (one slice per tile),
configure the sampler to `clamp_to_edge` per slice to eliminate bleeding:

```rust
use bevy::render::texture::{ImageAddressMode, ImageSamplerDescriptor};

// Set on the Image before it reaches the GPU:
image.sampler = ImageSampler::Descriptor(ImageSamplerDescriptor {
    address_mode_u: ImageAddressMode::ClampToEdge,
    address_mode_v: ImageAddressMode::ClampToEdge,
    address_mode_w: ImageAddressMode::ClampToEdge,
    ..ImageSamplerDescriptor::default()
});
```

With a 2D atlas, `clamp_to_edge` on the whole atlas does not prevent
inter-tile bleeding at mip levels ≥ 1; use tile padding instead (see
[ktx2-atlas.md](ktx2-atlas.md)).

---

## Gotchas

- **`AlphaMode::Blend` blocks need a separate draw call.** Don't merge opaque
  and translucent quads into the same mesh. Maintain two `Mesh` + `Material`
  pairs per chunk: one opaque, one translucent.
- **UV precision.** At very high tile counts (> 4096), `f32` UV coordinates
  may lose sub-texel precision on large atlases. Consider a 4096×4096 atlas
  split into two 2048×2048 atlases rather than one giant one.
- **Mip generation must account for padding.** Most GPU-side mip generators
  do not know about your padding convention; bake mips manually in your atlas
  tool using only the interior tile pixels at each level.
