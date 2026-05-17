# bevy-vfx — Gaussian splats with `bevy_spark`

> Referenced from `bevy-vfx/SKILL.md § Topics`.

## What Gaussian splatting is

A Gaussian splat scene represents the world as a cloud of millions of 3D Gaussian
primitives — each with a position, 3D covariance (size and orientation), colour, and
opacity. At render time, each Gaussian is projected onto the screen as a soft ellipse
and composited front-to-back. The result is photorealistic scene reconstruction from
photogrammetry captures, with no triangle mesh, UV maps, or PBR materials.

The "scene" is the asset. You import it; you do not build it in-engine.

## `bevy_spark 0.2.0` — Bevy 0.18 Gaussian splat renderer

`bevy_spark` (crates.io, repo: `htdt/bevy_spark`) pins `bevy = "0.18"` cleanly.
It loads `.spz` files (Niantic / NGSP Gaussian splat format) and renders them via a
dedicated render pipeline.

```toml
[dependencies]
bevy = "0.18"
bevy_spark = "0.2.0"
```

### Plugin registration

```rust
use bevy::prelude::*;
use bevy_spark::SparkPlugin;

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_plugins(SparkPlugin)   // registers loaders, render pipeline, diagnostics
        .add_systems(Startup, setup)
        .run();
}
```

### Loading and spawning a splat cloud

```rust
use bevy_spark::{SplatCloud, SplatCoordinateConvention, Splats};

fn setup(mut commands: Commands, asset_server: Res<AssetServer>) {
    // Load a .spz file — SpzLoader is registered automatically by SparkPlugin
    let cloud: Handle<Splats> = asset_server.load("scenes/capture.spz");

    // Splat cloud entity: handle + coordinate convention + transform
    commands.spawn((
        SplatCloud { handle: cloud },
        SplatCoordinateConvention::YDown,  // photogrammetry outputs are often Y-down
        Transform::from_xyz(0.0, 0.0, -3.0),
    ));

    // Camera — splat rendering is camera-centric; position it to frame the scene
    commands.spawn((
        Camera3d::default(),
        Transform::from_xyz(0.0, 1.5, 5.0).looking_at(Vec3::ZERO, Vec3::Y),
    ));
}
```

### Per-cloud quality overrides

```rust
use bevy_spark::SplatCloudSettings;

// Attach alongside SplatCloud to override global SparkSettings defaults
commands.spawn((
    SplatCloud { handle: cloud },
    SplatCloudSettings::default(), // customise sort mode, LOD, upload quality here
    SplatCoordinateConvention::YDown,
    Transform::default(),
));
```

Key resource for global defaults: `SparkSettings` (insert as a `Resource` before
startup, or mutate at runtime). Performance diagnostics: `SparkDiagnostics`.

**File format:** `.spz` only (SPZ / NGSP format, as produced by Niantic's tooling and
Polycam's SPZ export). There is no `.ply` or `.splat` loader in `bevy_spark 0.2.0`.

## When to use vs traditional mesh rendering

| Situation | Splats win | Mesh rendering wins |
|---|---|---|
| Scene source | Photogrammetry capture | Hand-authored in Blender/Maya |
| Lighting | Baked colour (no dynamic lights) | Full PBR, dynamic shadows |
| Physics | Not needed | Collision, raycast, character nav |
| Authoring iteration | Scan-once, import | Continuous edit cycles |
| Runtime mutation | Static backdrop | Deformable, destructible geometry |

Splats are not a replacement for mesh-rendered gameplay objects. The typical pattern
is: splat scene as photoreal backdrop, mesh entities for anything interactive.

## Performance characteristics

- **GPU memory:** scales with splat count. A high-quality capture is commonly 1–6 M
  splats; at ~40–60 bytes per splat that is 40–360 MB of GPU memory before any
  atlas/LOD compression.
- **Bandwidth-bound rasterisation:** compositing millions of soft quads is fill-rate
  heavy. Reduce splat count or enable LOD (`SplatLodSettings`) for mobile / lower-end
  targets.
- **Sort per frame:** splats must be sorted by depth each frame for correct
  alpha-compositing order. `SparkSettings` exposes `SplatSortSettings` to choose
  sort mode (`SplatSortMode`) and backend (`SplatSortBackend`).
- **WebGPU only.** `bevy_spark` uses compute shaders for sorting. It will not compile
  or run with the Bevy `webgl2` feature. See `bevy-wasm-webgpu` for the target setup.

## Authoring / capture pipeline

Typical toolchain (no specific vendor endorsement):

1. **Capture** — multi-view photos or video of the subject.
2. **Reconstruction** — photogrammetry software (Postshot, Polycam, gsplat CLI, etc.)
   trains a 3DGS model and exports a `.spz` file.
3. **Import** — drop the `.spz` into `assets/`, load with `asset_server.load`.
4. **Iterate** — adjust `Transform` + `SplatCoordinateConvention` to align with your
   scene's coordinate space.

You cannot edit Gaussian splat geometry inside Bevy. Splat authoring happens entirely
in external tools; Bevy only plays them back.

## Combining with traditional rendering

Splat entities and mesh entities coexist in the same scene. Guidelines:

- Place the splat scene on a distant `Transform` Z-offset to act as a backdrop; keep
  gameplay objects as meshes in front.
- Transparent mesh entities (particle effects, UI planes) sort against splat quads in
  the same transparent pass — keep transparent mesh count low when a splat scene is
  active.
- Splat colour is baked; it will not respond to Bevy `DirectionalLight` or
  `PointLight`. Do not expect lighting consistency between splat backdrop and
  mesh-rendered characters.

## Out of scope for this reference

Gaussian splat training and optimisation — this is an offline research / tooling
problem. `bevy_spark` is a *renderer*, not a trainer.

## See also

- [`../SKILL.md`](../SKILL.md) — top-level bevy-vfx dispatcher
- [`performance.md`](performance.md) — GPU budget table and transparent-pass cost
- `bevy-cameras` — splat scenes are strongly camera-centric; camera placement and FOV
  affect splat quality and sort order noticeably
- `bevy-wasm-webgpu` — WebGPU-only constraint; compute-shader sort backend
