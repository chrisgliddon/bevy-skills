# Bevy 0.18 — Mesh Primitives Reference

Built-in `bevy_math` shapes and how to spawn them as meshes. See also
[lighting](lighting.md) and [custom-material](custom-material.md).

---

## Plane3d

```rust
// Plane3d::new(normal: Vec3, half_size: Vec2)
//
// KEY GOTCHA: half_size is a Vec2 (half-width, half-height),
// NOT a scalar. This caught the card_pickup rebuild off-guard.
let plane = meshes.add(Plane3d::new(Vec3::Y, Vec2::new(5.0, 5.0)));
//                                              ^^^^^^^^^^^^^^^^^^
//                                    width=10, height=10 in world units
```

- `normal`: the surface normal, given as a `Vec3` (converted to `Dir3` internally).
- `half_size`: `Vec2` — `x` = half-width along the plane's X axis, `y` = half-height
  along the plane's Z axis (when normal is Y-up). **Not a scalar.**
- Default orientation: normal = `Vec3::Y`, i.e. the plane lies in the XZ plane
  (horizontal ground). No rotation needed for a flat floor.

**Struct fields (if constructing directly):**
```rust
Plane3d {
    normal: Dir3::Y,             // surface normal
    half_size: Vec2::new(0.5, 0.5),  // default: 1×1 unit plane
}
```

---

## Cuboid

```rust
// Three constructors — all take full lengths, not half-sizes:
let cube   = meshes.add(Cuboid::new(1.0, 1.0, 1.0));          // x, y, z lengths
let box_   = meshes.add(Cuboid::from_size(Vec3::new(2.0, 0.5, 1.0)));
let corner = meshes.add(Cuboid::from_corners(
    Vec3::new(-1.0, 0.0, -1.0),
    Vec3::new( 1.0, 2.0,  1.0),
));
```

The underlying field is `half_size: Vec3`, but the constructors take full lengths —
`Cuboid::new(1, 1, 1)` stores `half_size = Vec3::splat(0.5)`.

**Default:** `Cuboid::default()` = 1×1×1 cube.

---

## Sphere

```rust
let sphere = meshes.add(Sphere::new(0.5));   // radius
// or direct struct:
let sphere = meshes.add(Sphere { radius: 0.5 });
```

For control over subdivision style, use `Sphere::mesh()` (from the `Meshable`
trait) which returns a `SphereMeshBuilder`:

```rust
// UV sphere (longitude × latitude grid). Good defaults: 32 sectors, 18 stacks.
let uv_sphere = meshes.add(Sphere::new(0.5).mesh().uv(32, 18));

// Icosphere (uniform-area triangles). Subdivision 5 is a good default;
// returns Result because too-deep subdivision overflows the index buffer.
let ico_sphere = meshes.add(Sphere::new(0.5).mesh().ico(5).unwrap());

// Or build via SphereKind explicitly.
use bevy::math::primitives::SphereKind;
let builder = SphereMeshBuilder::new(0.5, SphereKind::Ico { subdivisions: 5 });
```

**Default:** `Sphere::default()` = radius `0.5`.
Centered at origin, poles along Y.

---

## Circle

`Circle` is a 2D primitive but is commonly used as a flat disc in 3D.

```rust
let disc = meshes.add(Circle::new(1.0)); // radius
```

**Default orientation gotcha:** `Circle` is built in the **XY plane** (the mesh
normal is +Z). For a flat ground disc lying on XZ, rotate it:

```rust
use std::f32::consts::FRAC_PI_2;

commands.spawn((
    Mesh3d(meshes.add(Circle::new(1.0))),
    MeshMaterial3d(materials.add(StandardMaterial::default())),
    Transform::from_rotation(Quat::from_rotation_x(-FRAC_PI_2)),
));
```

This was documented as a discovery in the `3d_scene` rebuild. Forgetting this
rotation leaves the disc standing upright like a coin.

---

## Cylinder

```rust
let cyl = meshes.add(Cylinder::new(0.5, 2.0));  // radius, height (full, not half)
// or:
let cyl = meshes.add(Cylinder { radius: 0.5, half_height: 1.0 });
```

- Axis along Y, centered at origin.
- `Cylinder::new(radius, height)` stores `half_height = height / 2`.
- Default: radius `0.5`, half-height `0.5` (= height 1.0).

---

## Capsule3d

```rust
let cap = meshes.add(Capsule3d::new(0.5, 1.0)); // radius, length of the cylinder segment
// or:
let cap = meshes.add(Capsule3d { radius: 0.5, half_length: 0.5 });
```

- `half_length` is the half-height of the cylinder *between* the two hemispheres —
  **not** the total height. Total height = `2 * half_length + 2 * radius`.
- Default: radius `0.5`, half-length `0.5` → total height `2.0`.

---

## Torus

```rust
// Torus::new(inner_radius, outer_radius)
// inner = hole radius, outer = overall object radius
let torus = meshes.add(Torus::new(0.5, 1.0));
// or direct:
let torus = meshes.add(Torus { minor_radius: 0.25, major_radius: 0.75 });
```

- `minor_radius` = tube cross-section radius.
- `major_radius` = distance from torus center to tube center.
- `Torus::new(inner, outer)` computes `minor = (outer - inner) / 2`,
  `major = outer - minor`.
- Default: minor `0.25`, major `0.75`.

---

## Pitfalls

### Default mesh orientations

| Primitive   | "Up" axis | Lies in plane | Notes                                        |
|-------------|-----------|---------------|----------------------------------------------|
| `Plane3d`   | +Y        | XZ            | No rotation needed for a horizontal floor     |
| `Cuboid`    | Y         | —             | Centered at origin                            |
| `Sphere`    | Y         | —             | Poles on ±Y                                  |
| `Circle`    | +Z        | XY            | Rotate `-FRAC_PI_2` around X for XZ ground   |
| `Cylinder`  | Y         | —             | Axis along Y                                  |
| `Capsule3d` | Y         | —             | Axis along Y                                  |
| `Torus`     | Y         | XZ            | Ring lies in XZ plane                        |

### Using meshes.add()

```rust
// meshes.add(Primitive) returns Handle<Mesh>
// Wrap it in Mesh3d for spawning:
let handle: Handle<Mesh> = meshes.add(Cuboid::new(1.0, 1.0, 1.0));
commands.spawn((Mesh3d(handle), MeshMaterial3d(mat)));

// This works because From<Cuboid> for Mesh is implemented — meshes.add()
// accepts anything that implements Into<Mesh>.
```

`meshes.add(Plane3d::new(...))` returns `Handle<Mesh>`; `Mesh3d` wraps the handle.
**Do not** pass the primitive directly to `Mesh3d` — it takes a `Handle<Mesh>`.
