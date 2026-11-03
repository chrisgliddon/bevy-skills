# Dirtying, halo fan-out, and revision tokens

## Define the mesher's read footprint first

Let a section contain coordinates `[0, N)` on each axis. A changed voxel always
dirties its owning section. For every axis on which the local coordinate is `0` or
`N - 1`, also dirty the adjacent section if the mesher reads across that face.

That six-neighbour rule is sufficient only for face visibility based on direct
neighbours. If ambient occlusion or lighting samples edge/corner voxels, derive the
fan-out from that stencil. A one-voxel halo in all directions can affect any of the
26 surrounding sections at a corner. Do not blindly remesh all 27 sections for every
edit: test which section meshes actually read the changed sample.

Useful representation:

```rust
#[derive(Clone, Copy)]
struct ReadHalo {
    negative: UVec3,
    positive: UVec3,
}
```

Given the changed world-space cell and each candidate section's expanded read AABB,
mark the candidate dirty when that AABB contains the cell. This generalises cleanly
to asymmetric lighting stencils and avoids hard-coded neighbour folklore.

Batch edits before fan-out. Union the affected section set, then increment each
section once for the batch. Revisions describe observable source changes, not the
number of individual voxel writes.

## Use two dimensions of validity

```rust
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct WorkToken {
    coord: SectionCoord,
    revision: u64,
    epoch: u64,
}
```

- `revision` changes whenever the section's mesh input changes, including relevant
  neighbour/halo data.
- `epoch` changes whenever the coordinate is unloaded, recreated, regenerated, or
  otherwise begins a new lifetime.

A result is acceptable only when the coordinate still exists and both fields equal
the current state. This closes the ABA bug where section `(4, 0, 9)` is unloaded and
later recreated at revision 1 while an old revision-1 job is still running.

Use checked increments in debug/test builds and define wrap behaviour. For practical
games a `u64` should never wrap, but silently relying on equality after wrap weakens
the contract. Persist epochs only if outstanding work can survive a loaded-world
transition; otherwise create a fresh session epoch on load.

## Snapshot consistently

The job token and all source/halo data must come from one logical revision. Order the
snapshot system after edit application and revision bumps. If copying multiple ECS
resources/components, use an exclusive system or an explicit staging structure so a
partial snapshot cannot mix revisions.

Never pass a raw pointer or lock guard into `AsyncComputeTaskPool`. Move owned arrays,
palette values needed by the mesher, and the token into the task. A worker should be
a pure function:

```text
(token, immutable section snapshot, immutable halo snapshot) -> MeshResult
```

This makes stale rejection, deterministic tests, and native/WASM fallbacks tractable.

## Tests that catch real failures

- Edit every face, edge, and corner cell and assert the exact affected set for each
  supported meshing/lighting mode.
- Generate result R1, edit to R2, apply R1, and assert presentation remains unchanged.
- Start a job, unload/reload the coordinate, then assert the old epoch is rejected.
- Batch repeated writes to one voxel and assert one revision bump and one queue intent.
