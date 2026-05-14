# KTX2 Atlas Baking

Packing per-block tile textures into a single compressed KTX2 atlas for
GPU-friendly delivery. See [ron-schema.md](ron-schema.md) for the source
paths and [atlas-binding.md](atlas-binding.md) for how to bind the result.

---

## Why Bake at Content-Build Time

Baking at runtime is slow, adds build dependencies to shipped code, and
produces different results on different machines. Instead:

1. Run a sidecar script (e.g. `tools/bake_atlas.py`) during the content build.
2. Commit the `.ktx2` atlas and a JSON sidecar index to `assets/`.
3. At runtime, load both; populate `AtlasIndex` from the JSON.

The JSON index maps each source path to its tile slot:

```json
{
  "textures/grass_top.png":  0,
  "textures/dirt.png":       1,
  "textures/grass_side.png": 2,
  "textures/stone.png":      3,
  "textures/glass.png":      4,
  "textures/water_top.png":  5,
  "textures/water_side.png": 6
}
```

Load it with a custom asset loader or a startup system that reads the JSON
via `std::fs` / `bevy::asset::AssetReader`.

---

## Tile Size Budget

| Atlas size | Tile size | Capacity |
|---|---|---|
| 2048 × 2048 | 32 × 32 | 4096 tiles |
| 2048 × 2048 | 64 × 64 | 1024 tiles |
| 4096 × 4096 | 32 × 32 | 16 384 tiles |

4096 unique tile slots at 32 × 32 covers most block-based games comfortably.
Larger atlases can be expensive on low-end and mobile GPUs; split by material
type (opaque / alpha-tested / translucent) rather than going wider.

---

## Padding for Mip Safety

Without padding, bilinear sampling at mip levels ≥ 1 bleeds texels from
adjacent tiles ("texture bleeding" at glancing angles).

Add **2 pixels of padding** on every edge of every tile before packing:

```
┌─────────────────────────┐
│  P P P P P P P P P P   │
│  P ┌───────────────┐ P  │
│  P │  tile pixels  │ P  │
│  P └───────────────┘ P  │
│  P P P P P P P P P P   │
└─────────────────────────┘
```

Replicate (not mirror) the edge pixels into the padding zone so that
out-of-tile samples see the correct colour. The padded tile size is then
`tile_px + 4` per dimension; factor this into your layout stride.

Alternatively, use a **texture array** (`image_type: Array2d`) where each
slice is one tile — arrays eliminate bleeding entirely because `clamp_to_edge`
operates per-slice. See [atlas-binding.md](atlas-binding.md) for the
`AsBindGroup` configuration.

---

## Compression Formats by Platform

| Target platform     | Format | Notes |
|---|---|---|
| Desktop (PC / Mac)  | BC7    | Best quality; universally supported on DX12/Vulkan/Metal. |
| Android             | ETC2   | Guaranteed on OpenGL ES 3.0+. Use RGBA ETC2 for alpha tiles. |
| iOS / Apple Silicon | ASTC   | Supported on all Apple GPU families; very high quality. |
| WASM (WebGPU)       | BC7 or ASTC | WebGPU exposes both on most hardware; prefer BC7 as safer fallback. |
| Universal fallback  | RGBA8  | Uncompressed; always works; 4× larger on GPU. |

Bevy's `ktx2` feature (on by default in the `3d` bundle) loads KTX2 with
supercompression (Zstandard). Enable it explicitly in trimmed WASM builds:

```toml
# Cargo.toml
[dependencies]
bevy = { version = "0.18", features = ["ktx2", "zstd"] }
```

---

## Baking Script Outline

A minimal Python bake script using `Pillow` and `ktx-software` bindings:

```python
# tools/bake_atlas.py  (pseudocode outline)
import json
from pathlib import Path
from PIL import Image

TILE_PX   = 32
PADDING   = 2
STRIDE    = TILE_PX + PADDING * 2
ATLAS_COLS = 64          # 64 * stride ≈ 2304; crop to 2048 after packing
atlas     = Image.new("RGBA", (ATLAS_COLS * STRIDE, ATLAS_COLS * STRIDE))
index     = {}
tile_id   = 0

for src_path in sorted(Path("assets").rglob("*.png")):
    tile  = Image.open(src_path).resize((TILE_PX, TILE_PX))
    col   = tile_id % ATLAS_COLS
    row   = tile_id // ATLAS_COLS
    x     = col * STRIDE + PADDING
    y     = row * STRIDE + PADDING
    # paste tile + replicate border into padding
    atlas.paste(tile, (x, y))
    index[str(src_path)] = tile_id
    tile_id += 1

atlas.save("assets/blocks_atlas.png")
Path("assets/blocks_atlas_index.json").write_text(json.dumps(index, indent=2))
# Then invoke `toktx` or `basisu` to convert PNG → KTX2 with BC7/ETC2/ASTC.
```
