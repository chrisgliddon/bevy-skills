# bevy-animation — Straight-Ahead vs Pose-to-Pose, Solid Drawing & Appeal

> Referenced from `bevy-animation/SKILL.md § The 12 Basic Principles`.

These three principles aren't engine concerns — they're decisions you make in
Blender / Maya / your animation pipeline before the asset ever reaches Bevy. This
reference is about what they mean and how to spot-check your imports.

---

## Straight-Ahead vs Pose-to-Pose

These are the two fundamental animation workflows:

**Straight-ahead:** the animator works frame-by-frame from start to finish, discovering
the motion as they go. This produces fluid, spontaneous-feeling motion but can drift
from the intended path. Results in **dense keyframe data** — many closely spaced keys.

**Pose-to-pose:** the animator sets key poses first (start, end, breakdowns), then
fills in the in-betweens. More structured and predictable; easier to hit precise
timing. Results in **sparse keyframe data** — a handful of keys, relying on
interpolation for the in-between frames.

**Bevy doesn't care which workflow produced the clip** — it samples keyframes at the
current playback time. The difference surfaces in asset size and motion quality:

- Dense (straight-ahead) clips are larger files but play smoothly with linear
  interpolation between tightly spaced keys.
- Sparse (pose-to-pose) clips are smaller but may feel mechanical if Bevy's linear
  interpolation between the few keys doesn't match the animator's intended curve.
  Fix this by adding more breakdown keys in the DCC tool, or by replacing
  `AnimatableKeyframeCurve` (for procedural clips) with `UnevenSampleAutoCurve`
  from `bevy::math::curve`, which fits a smoother interpolant through sparse samples.

---

## Solid Drawing (Solid Construction in 3D)

"Solid drawing" in classical animation means forms that have weight, volume, and a
clear sense of three-dimensionality even in 2D. In 3D animation it becomes **solid
construction**: the rig and mesh must read convincingly from any camera angle, hold
volume through deformation, and respond to light in a way that reinforces mass.

**Spot-checks at import:**

- **Volume during extreme poses:** during a deep squat or punch extension, does the
  mesh pinch or collapse around joints? If so, review skinning weights in the DCC tool.
  Bevy applies whatever skinning the `.glb` asset contains; it does not fix poor weight
  painting.

- **Silhouette from camera:** does the character read clearly in silhouette? Stiff
  T-poses import fine but may read as rigid once animated. Test with a solid-color
  unlit material to isolate silhouette from shading.

- **Normals integrity:** extreme joint rotations can flip normals or create shading
  seams. Check this in Bevy by spinning the camera around the character during a
  full-body motion. Bevy's PBR shading will reveal normal discontinuities that look
  fine in a DCC preview with a fixed light.

There are no Bevy API calls to fix solid construction — it is fully an authoring
concern resolved before export.

---

## Appeal

Appeal is the quality that makes a character compelling to watch — charm, clarity of
read, and a design that the eye is drawn to. It is not the same as beauty: a
compelling villain has appeal. In 3D, appeal comes from character design, pose
hierarchy, and how light wraps the surface.

**Not a Bevy runtime concern.** Appeal is authored in the design and rigging phase.
Bevy faithfully renders what you give it. However, the rendering setup does matter:

- **Emissive accents** (glowing eyes, bioluminescent markings) can dramatically
  increase silhouette readability against dark backgrounds. Configure via
  `StandardMaterial::emissive` — see the `bevy-pbr-materials` skill for material
  setup.
- **Subsurface scattering** (skin, foliage) affects how light wraps around a character.
  In Bevy 0.18, SSS is approximated; check `bevy-pbr-materials` for the available
  shading model parameters.
- **Pose hierarchy:** the most appealing poses have a clear primary line of action
  running through the whole body, with secondary curves counterpointing it. Author
  this in the DCC tool; it survives into Bevy unchanged.

---

## Gotchas

- **Scale factor mismatch on import.** Blender's default unit is meters, but its
  export scale can produce a 100× mismatch in Bevy scenes. Check that the character
  is the expected size after spawning. The canonical fix is to apply all transforms
  in Blender before export (`Ctrl+A → All Transforms`) and use Bevy's
  `SceneRoot` / `Transform::from_scale` to adjust if needed.
- **`Name` component is required for `AnimationTargetId::from_name`.** The glTF
  loader sets `Name` on bone entities automatically from the node names in the file.
  If you rename bones after export (e.g. in a post-process step), the
  `AnimationTargetId` will no longer match the clip's target IDs and animations will
  silently not apply to those bones.
- **Broken normals after "Apply Transform" in Blender.** Applying transforms sometimes
  flips normals if the original scale included a negative axis. Always check normals
  (`Overlay → Face Orientation`) in Blender after applying and before exporting.
- **`UnevenSampleAutoCurve` is in `bevy::math::curve`**, not the animation module.
  Import it explicitly when using it to smooth sparse pose-to-pose keyframe data in
  procedural clips.

---

## See also

- [`../SKILL.md`](../SKILL.md) — canonical pattern and full trigger list
- [`gltf-import.md`](gltf-import.md) — loading `.glb`/`.gltf` assets, `Name`-based
  target resolution, and scale factor handling
- `bevy-pbr-materials` (sibling skill) — `StandardMaterial` emissive, roughness,
  and shading model parameters that affect character visual appeal
