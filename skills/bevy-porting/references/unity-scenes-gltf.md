# bevy-porting — Unity scenes → glTF → Bevy 0.18

> Referenced from `bevy-porting/SKILL.md § Unity (priority)`.

## Why glTF is the recommended pivot

Unity's `.unity` scene format is YAML but encodes engine-internal instance IDs (`fileID`, `guid`) that are meaningless outside Unity. Attempting to parse `.unity` files directly is fragile and produces stale references the moment assets are renamed.

The cleanest port path: **export to glTF 2.0, load natively in Bevy.**

Bevy's `bevy_gltf` crate (included in `DefaultPlugins`) loads `.glb` / `.gltf` files directly. The loaded asset is a `Handle<Scene>` spawnable with `SceneRoot`. Animations, PBR materials, bone hierarchies, and mesh LODs all survive the roundtrip if the exporter is correct.

## Tooling options

| Method | When to use |
|---|---|
| **Unity glTFast** (recommended) | Unity 2020.3 LTS+, produces glTF 2.0 + PBR + animations |
| **FBX → Blender → glTF** | Older Unity versions; also useful for mesh cleanup before porting |
| **Manual rebuild** | Tiny scenes, or when automated export drops critical data |

**glTFast** is free and open source (`com.unity.cloud.gltfast` in Package Manager). It handles the left-hand to right-hand axis flip, PBR material conversion, and bone export automatically.

For the FBX path: export FBX from Unity, import into Blender, verify the axis and materials, export as glTF 2.0 with "Apply Modifiers" checked.

## Loading the exported scene in Bevy

```rust
fn setup(mut commands: Commands, asset_server: Res<AssetServer>) {
    // Load the root scene from a .glb
    let scene: Handle<Scene> = asset_server.load("scenes/main.glb#Scene0");
    commands.spawn(SceneRoot(scene));
}
```

`#Scene0` selects the first scene in the file. Multi-scene `.glb` files use `#Scene1`, `#Scene2`, etc.

## Using `scene_inventory.py` before and after export

Before exporting, dump the Unity scene's object list to confirm what's in scope:

```bash
python3 skills/bevy-porting/scripts/unity/scene_inventory.py \
  /path/to/Assets/Scenes/Main.unity --out scene.json
```

The script parses the `.unity` YAML and emits a JSON array of `{ name, type, fileID, components[] }` for every `GameObject`. Run it again after export on the glTF side to diff what was dropped (lights, particle systems, audio sources, custom scripts — all non-transferable). This diff is your porting checklist.

## Bones and `Name` — Mecanim Humanoid rig gotcha

Bevy resolves animation targets by name:

```rust
let hips = AnimationTargetId::from_name(&Name::new("Hips"));
```

Unity's **Mecanim Humanoid** retargeting renames bones to a normalised set (`Hips`, `Spine`, `Head`, `LeftUpperArm`, ...). When glTFast exports a Humanoid rig, it uses the **source skeleton's original bone names**, not the Mecanim names. Check the actual bone names in the exported `.glb` using a viewer (e.g. [gltf.report](https://gltf.report)) and update your `AnimationTargetId::from_name` calls accordingly.

Cross-link: `bevy-animation/references/gltf-import.md` covers `AnimationTargetId` matching in detail.

## Axis flip

Unity is **left-handed Y-up**; glTF is **right-handed Y-up**. The difference is a sign flip on the X axis.

glTFast applies this correction automatically. If you use any other exporter, spot-check by importing a Unity scene with a known asymmetric asset (e.g. a character facing +Z in Unity) and confirming it isn't mirrored in Bevy. A correct export: the character still faces +Z. A broken export: the character faces -Z or is inside-out.

If you see mirroring, apply `Transform { scale: Vec3::new(-1.0, 1.0, 1.0), .. }` to the scene root as a workaround, then fix the exporter setting.

## Lighting

Unity baked lightmaps (Enlighten / Progressive Lightmapper) are stored in a proprietary format that does not transfer to Bevy.

Bevy 0.18 supports baked lightmaps via the `Lightmap` component, but the bake format is incompatible — you cannot reuse Unity's `.exr` lightmap atlases directly.

**Recommendation for porting:** start with real-time lighting (`DirectionalLight`, `PointLight`) to unblock development. Schedule a Bevy-native lightmap bake later once the scene geometry is stable.

## What the glTF export drops (expect these gaps)

| Unity feature | glTF / Bevy status |
|---|---|
| Particle Systems | Not in glTF — rebuild with Bevy particles |
| Audio Sources | Not in glTF — re-add via Bevy audio systems |
| Colliders (Physics) | Not in glTF — add `bevy_rapier3d` / `avian` colliders in code |
| Custom MonoBehaviours | Not in glTF — re-implement as Bevy components |
| Baked lightmaps | Not transferable — rebake or use real-time |
| Canvas / UI | Not in glTF — rebuild with `bevy-ui` |
| Terrain | Not exportable — rebuild as mesh or voxel data |

## See also

- [`../SKILL.md`](../SKILL.md) — bevy-porting dispatcher
- [`unity-assets.md`](unity-assets.md) — asset pipeline, material channel mapping, KTX2
- [`unity-animation.md`](unity-animation.md) — Mecanim → `AnimationGraph` porting (parallel reference)
- `bevy-animation` — `AnimationTargetId::from_name`, `AnimationGraph`, glTF clip loading
- `bevy-pbr-materials` — `StandardMaterial` setup after import, lightmap component
- `bevy-cameras` — camera setup after dropping Unity's `Camera` component on the scene root
