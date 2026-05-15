# bevy-porting — Unity → Bevy 0.18 asset pipeline

> Referenced from `bevy-porting/SKILL.md § Unity (priority)`.

## Concept map

| Unity | Bevy 0.18 |
|---|---|
| Prefab (visual hierarchy) | glTF scene loaded via `AssetServer` |
| Prefab (data / spawner) | Rust fn that spawns a `Bundle` |
| `Standard Shader` material | `StandardMaterial` |
| Texture import settings (BC7/ASTC) | KTX2 with matching block compression |
| Addressables `Handle<T>` | `Handle<T>` via `AssetServer` (lazy + refcounted) |
| Addressables groups | Asset subdirectories / glTF bundle files |
| AssetBundle | No equivalent — ship glTF + KTX2 files |
| `.meta` GUID | File-path-based `Handle` |

## Prefabs → spawnable entity templates

Unity prefabs are serialised entity hierarchies. Bevy 0.18 has no native "prefab" type. Two idioms:

**Visual prefab** — bake to glTF (see `unity-scenes-gltf.md`), then load the scene:

```rust
let prefab: Handle<Scene> = asset_server.load("prefabs/enemy.glb#Scene0");
commands.spawn(SceneRoot(prefab));
```

**Data prefab / spawner** — a Rust function that builds and returns an entity with the right components:

```rust
fn spawn_enemy(commands: &mut Commands, pos: Vec3) -> Entity {
    commands.spawn((
        Enemy,
        Health(100),
        Transform::from_translation(pos),
    )).id()
}
```

Prefer the spawner function for entities that need logic-driven variation; prefer glTF scenes for authored geometry and rigs.

## Materials — Unity Standard Shader → `StandardMaterial`

| Unity Standard Shader field | `StandardMaterial` field | Notes |
|---|---|---|
| Albedo / Base Color | `base_color` + `base_color_texture` | Direct |
| Metallic (slider) | `metallic` (f32) | Direct |
| Metallic Map (R=metallic) | `metallic_roughness_texture` | **Channel swap needed** — see below |
| Smoothness (1 - roughness) | `perceptual_roughness` | Invert: `roughness = 1.0 - smoothness` |
| Normal Map | `normal_map_texture` | Must be Linear, not sRGB |
| Emission | `emissive` + `emissive_texture` | |
| Transparency (Fade/Transparent) | `alpha_mode: AlphaMode::Blend` | |

**Channel swap gotcha:** Unity's Standard Shader packs `Metallic` in the R channel of the Metallic Map and derives roughness from the Glossiness slider, not a texture. Bevy (and glTF) expect a **packed metallic-roughness texture** with Metallic in B and Roughness in G. You need a channel-repack step at export time — glTFast handles this automatically; FBX/manual exports do not.

## Textures + compression

| Unity compression preset | Bevy / KTX2 equivalent |
|---|---|
| BC7 (colour, high quality) | KTX2 + BC7 (`transcoder_format: Bc7Rgba`) |
| BC5 (normal maps, RG) | KTX2 + BC5 |
| ASTC 6×6 (mobile) | KTX2 + ASTC 6×6 |

Enable the `ktx2` and `zstd` Cargo features:

```toml
bevy = { version = "0.18", features = ["ktx2", "zstd"] }
```

**sRGB vs Linear:** Unity's "sRGB (Color Texture)" maps to Bevy's default sRGB image format. Normal maps **must be imported as Linear** — Unity marks them automatically; in Bevy you must ensure the asset isn't tagged sRGB. glTFast handles this correctly when exporting from Unity. See `bevy-voxel-data` for KTX2 atlas workflows.

## Addressables → `AssetServer` + `Handle<T>`

`Handle<T>` in Bevy is already lazy and refcounted — the core value proposition of Addressables is built in.

```rust
// Load (lazy — actual IO starts here)
let tex: Handle<Image> = asset_server.load("textures/enemy_albedo.ktx2");

// Check load state
if asset_server.is_loaded_with_dependencies(&tex) { ... }
```

Addressables **groups** (batching assets for download chunks) map loosely to:
- Splitting assets across subdirectories and loading a folder.
- Shipping a self-contained `.glb` that bundles geometry + textures + animations.

Hot-reload of changed assets is enabled by adding the `file_watcher` feature:

```toml
bevy = { version = "0.18", features = ["file_watcher"] }
```

## AssetBundle / SceneAssetBundle

Bevy has no equivalent bundling format. Recommended approach:
- Ship a flat or hierarchical directory of `.glb` / `.gltf` + `.ktx2` files.
- For distribution builds, run `bevy_asset_processing` or a custom content-build script to compress and pack assets.

## Per-asset `.meta` files (GUIDs)

Unity identifies every asset by a GUID stored in a `.meta` sidecar. Bevy uses **file-path-based handles** — no GUIDs.

During a port, use `scripts/unity/asset_audit.py` to walk `Assets/` and emit a JSON map of GUIDs to file types and paths, so you can track which Unity assets map to which new Bevy paths:

```bash
python3 skills/bevy-porting/scripts/unity/asset_audit.py \
  /path/to/UnityProject/Assets --out asset_audit.json
```

The output JSON has the shape:
```json
{
  "root": "Assets/",
  "totals": { "files": 1234, "bytes": 56789012, "by_type": { "Texture2D": 200, ... } },
  "assets": [
    { "path": "Assets/Textures/hero.png", "guid": "abc123...", "type": "Texture2D", "bytes": 12345 }
  ]
}
```

With `--graph`, each asset entry also includes `"depends_on": ["guid1", ...]`.

Cross-reference the `assets` array against your new `assets/` tree during the port to spot missing or renamed files early.

## See also

- [`../SKILL.md`](../SKILL.md) — bevy-porting dispatcher
- [`unity-scenes-gltf.md`](unity-scenes-gltf.md) — scene extraction and glTF export details
- `bevy-pbr-materials` — `StandardMaterial` fields, `AlphaMode`, emissive, depth bias
- `bevy-voxel-data` — KTX2 atlas authoring and block compression workflow
- `bevy-custom-assets` — writing a custom `AssetLoader` for proprietary formats
