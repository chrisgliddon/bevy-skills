---
name: bevy-voxel-pipeline
description: Use when meshing voxel chunks with `block-mesh-rs` (`greedy_quads` / `visible_block_faces`), translating a `GreedyQuadsBuffer` into a Bevy 0.20 `Mesh` via `try_insert_attribute`, choosing between greedy and simple meshing, or scheduling chunk meshing on `AsyncComputeTaskPool` with `poll_once` so the main thread doesn't stall. Covers Bevy 0.20 voxel meshing.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "2"
  area: voxel
  bevy_version: "0.20"
---

# Bevy 0.20 — Voxel meshing pipeline

## When to use this skill

- Building a Minecraft-style voxel world with chunked meshing.
- Choosing between `greedy_quads` (fewer, larger quads — best for static terrain) and `visible_block_faces` (one quad per face — best for fast remesh on edits).
- Wiring `block-mesh-rs` output into a Bevy 0.20 `Mesh`.
- Avoiding main-thread stalls on remesh by spawning the work on `AsyncComputeTaskPool`.

## Canonical pattern

```rust
use bevy::asset::RenderAssetUsages;
use bevy::mesh::{Indices, PrimitiveTopology};
use bevy::prelude::*;
use block_mesh::ndshape::{ConstShape, ConstShape3u32};
use block_mesh::{
    greedy_quads, GreedyQuadsBuffer, MergeVoxel, Voxel, VoxelVisibility,
    RIGHT_HANDED_Y_UP_CONFIG,
};

// 18^3 — the standard "chunk plus padding" block-mesh expects.
// Each axis gets 1 cell of padding on each side so neighbour lookups are
// in-bounds. The user-visible chunk is 16^3.
type ChunkShape = ConstShape3u32<18, 18, 18>;

#[derive(Clone, Copy, Eq, PartialEq, Default)]
pub struct BlockId(pub u16);

impl Voxel for BlockId {
    fn get_visibility(&self) -> VoxelVisibility {
        if self.0 == 0 {
            VoxelVisibility::Empty
        } else {
            VoxelVisibility::Opaque
        }
    }
}

impl MergeVoxel for BlockId {
    type MergeValue = u16;
    fn merge_value(&self) -> Self::MergeValue { self.0 }
}

/// Build a Bevy 0.20 Mesh from a padded chunk of blocks.
/// Returns `None` for an entirely empty chunk so callers can skip spawning.
pub fn mesh_chunk(blocks: &[BlockId]) -> Option<Mesh> {
    assert_eq!(blocks.len(), ChunkShape::SIZE as usize);

    let mut buffer = GreedyQuadsBuffer::new(blocks.len());
    greedy_quads(
        blocks,
        &ChunkShape {},
        [0; 3],
        [17, 17, 17],
        &RIGHT_HANDED_Y_UP_CONFIG.faces,
        &mut buffer,
    );

    if buffer.quads.num_quads() == 0 {
        return None;
    }

    let num_indices = buffer.quads.num_quads() * 6;
    let num_vertices = buffer.quads.num_quads() * 4;
    let mut indices = Vec::with_capacity(num_indices);
    let mut positions = Vec::with_capacity(num_vertices);
    let mut normals = Vec::with_capacity(num_vertices);

    for (group, face) in buffer.quads.groups.iter().zip(RIGHT_HANDED_Y_UP_CONFIG.faces.iter()) {
        for quad in group.iter() {
            indices.extend_from_slice(&face.quad_mesh_indices(positions.len() as u32));
            positions.extend_from_slice(&face.quad_mesh_positions(quad, 1.0));
            normals.extend_from_slice(&face.quad_mesh_normals());
        }
    }

    let mut mesh = Mesh::new(PrimitiveTopology::TriangleList, RenderAssetUsages::default());
    mesh.try_insert_attribute(Mesh::ATTRIBUTE_POSITION, positions).ok()?;
    mesh.try_insert_attribute(Mesh::ATTRIBUTE_NORMAL, normals).ok()?;
    mesh.insert_indices(Indices::U32(indices));
    Some(mesh)
}
```

## Threading: get it off the main thread

```rust
use bevy::prelude::*;
use bevy::tasks::{block_on, poll_once, AsyncComputeTaskPool, Task};

#[derive(Component)]
struct MeshTask(Task<Option<Mesh>>);

fn kick(mut commands: Commands) {
    let pool = AsyncComputeTaskPool::get();
    let blocks: Vec<BlockId> = Vec::new(); // load from chunk store
    let task = pool.spawn(async move { mesh_chunk(&blocks) });
    commands.spawn(MeshTask(task));
}

fn poll(mut commands: Commands, mut meshes: ResMut<Assets<Mesh>>, mut q: Query<(Entity, &mut MeshTask)>) {
    for (entity, mut task) in &mut q {
        if let Some(maybe_mesh) = block_on(poll_once(&mut task.0)) {
            commands.entity(entity).remove::<MeshTask>();
            if let Some(mesh) = maybe_mesh {
                let handle = meshes.add(mesh);
                commands.entity(entity).insert(Mesh3d(handle));
            }
        }
    }
}
```

`block_on` and `poll_once` are re-exported from `bevy::tasks`; no `futures_lite` dependency is needed.

## Gotchas

- **Padding is non-optional.** `block-mesh` needs one cell of padding on each axis so cross-chunk neighbour visibility computes correctly. A "16-cube" chunk is stored as 18×18×18; edits in a chunk also touch the padding of its six neighbours.
- **Greedy vs simple.** `greedy_quads` produces 1/3 the quads of `visible_block_faces` but takes 3× longer. Use simple for chunks players are editing right now, greedy for chunks that have been stable for a while.
- **UVs are not free.** `block-mesh` doesn't emit UVs — you compute them yourself from quad face direction and block ID. A texture atlas + per-quad offset is the standard approach (see `bevy-voxel-data`).
- **`block-mesh` 0.2.0 (crate `block-mesh`, repo `block-mesh-rs`) is Bevy-independent** (last published 2022-04). It depends on `ilattice` and `ndshape`, both pure-Rust. It compiles with Bevy 0.20 because it never imports Bevy; only the `Mesh`-building glue above is Bevy code.
- **Don't reach for `par_iter` inside a single chunk mesh** — block-mesh is already fast. The parallelism wins are across chunks, not within one. Spawn N chunk-mesh tasks on `AsyncComputeTaskPool`.
- **`try_insert_attribute` still returns `Result<(), MeshAccessError>`** in 0.20 — the error case is "mesh already extracted to render world", which won't happen for a freshly-`new`-d mesh. Still, handle the `Result` so the API doesn't regress on you.
- **`RenderAssetUsages` lives in `bevy::asset`.** `bevy::mesh::{Indices, PrimitiveTopology}` is the mesh path; `bevy::render::mesh::*` is stale 0.15-era output.
- **Dropping a `Task` cancels it on web (0.19).** If you drop `MeshTask` before polling it (chunk unloaded mid-mesh), call `task.0.detach()` first only if you still want the work to finish; otherwise the cancel is what you want.
- **`MeshAabb::compute_aabb` is `get_aabb` (0.20).** Stale snippets that compute a chunk bounding box via `mesh.compute_aabb()` fail to compile; use `mesh.get_aabb()` with `use bevy::camera::primitives::MeshAabb;` (the trait is not in `bevy::mesh`).
- **`MeshTag(x)` is `MeshTag::new(x)` (0.20)** and the value is `tag.value`, not `tag.0`. Useful if you tag chunk meshes for a custom shader.
- **Shapes moved to `bevy_shape` (0.20).** `Cuboid` and friends are still in `bevy::prelude`; only direct `bevy::math::primitives::*` imports break.
- **Lifecycle `Replace` is `Discard` (0.19).** Hooks that reacted to a `Mesh3d` swap on the chunk entity use `On<Discard<Mesh3d>>` and `#[component(on_discard = ...)]`.
- **`Query::iter_many` yields `Result` (0.20).** Batch-polling tasks by entity list needs `.iter_many(ids).matched()` for the old silent-skip behaviour.

## See also

- `bevy-voxel-data` — RON block definitions, palette, UV atlas baking.
- `bevy-voxel-runtime` — dirty/halo fan-out, revision tokens, bounded uploads around `mesh_chunk`.
- `bevy-assets` — loading chunk data and managing the resulting Mesh handles.
- `bevy-migration-0-19-to-0-20` — `get_aabb`, `MeshTag::new`, `bevy_shape`, `iter_many` changes.
