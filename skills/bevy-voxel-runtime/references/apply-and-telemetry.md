# Applying results and measuring the runtime

## Validate at the last responsible moment

Receiving a result is not validation. Keep it staged until the main-world apply step,
then check all of the following immediately before mutation:

- the section coordinate still resolves to the expected entity/lifetime;
- result epoch equals current epoch;
- result revision equals current content revision;
- the section still expects that result token;
- mesh and collider payloads passed structural validation and size limits.

Increment a stale-result diagnostic for token mismatch. A stale result must not clear
the dirty flag or change the scheduler state for the newer token.

## Treat mesh and collider as one presentation revision

Build the CPU payloads off-thread. In one immediate/exclusive main-world apply step,
validate the token, create the Bevy `Mesh` asset and Rapier `Collider`, and replace
their components together. Because no other system can mutate the section during
that exclusive step, the validation remains current through insertion. Record the
accepted token alongside them:

```rust
#[derive(Component, Clone, Copy)]
struct PresentedVoxelRevision {
    revision: u64,
    epoch: u64,
}

// 0.20: `&mut World` is an ordinary `SystemParam`, so this is just a system.
fn apply_results(world: &mut World) {
    let Some(result) = world.resource_mut::<RemeshRuntime>().completed.pop_front() else {
        return;
    };
    let current = world.resource::<RemeshRuntime>().latest.get(&result.token.coord).copied();
    if current != Some(result.token) {
        return; // stale: count it, do not touch presentation
    }
    let new_mesh_handle = world.resource_mut::<Assets<Mesh>>().add(build_mesh(&result.mesh));
    let new_collider = build_collider(&result.collider);
    let mut section_entity = world.entity_mut(section_entity_for(&result.token));
    section_entity.insert((
        Mesh3d(new_mesh_handle),
        new_collider,
        PresentedVoxelRevision {
            revision: result.token.revision,
            epoch: result.token.epoch,
        },
    ));
}
```

If collider cooking must also happen on the main thread, include it in the same apply
budget. If a collider is intentionally lower fidelity or lower cadence, model that as
a separate accepted revision and expose the mismatch explicitly; do not call it an
atomic swap.

Retire old unique mesh assets only after their handles are no longer used. Never
remove an asset merely because one section replaced a handle if assets can be shared.
If payload validation or asset construction can fail after allocating a unique asset,
remove that staged asset before returning so rejected results do not leak handles.

## Measure the whole latency path

Register Bevy diagnostics for at least:

| Path | Meaning |
|---|---|
| `voxel/dirty_sections` | Sections awaiting current geometry |
| `voxel/remesh_queue_depth` | Valid queued intents, excluding stale heap entries |
| `voxel/remesh_in_flight` | Active worker jobs |
| `voxel/results_pending` | Completed results awaiting validation/apply |
| `voxel/coalesced_total` | Dirty requests folded into existing intent |
| `voxel/stale_results_total` | Results rejected by token validation |
| `voxel/task_latency_ms` | Snapshot-to-completion latency |
| `voxel/queue_age_ms` | Oldest valid queued intent age |
| `voxel/upload_bytes` | Bytes accepted this frame |
| `voxel/apply_time_ms` | Main-thread validation/upload/swap cost |
| `voxel/visible_sections` | Visible section count used by prioritisation |

Counters and gauges need different interpretation. A cumulative stale count is useful
for totals; a per-second rate or ratio is better for alerting. Include section size,
mesher mode, vertex format, platform, and build profile in benchmark metadata.

Wrap snapshot, mesh, queue wait, upload, and collider construction with tracing spans.
Avoid a span per voxel in production; the instrumentation would become the workload.

## Acceptance budgets

Specify budgets per target instead of claiming one universal threshold:

| Target | Frame percentile | Queue recovery | Upload cap | Memory cap |
|---|---|---|---|---|
| Native minimum spec | p95/p99 | after scripted edit burst | bytes + ms/frame | snapshots + results |
| Steam Deck | p95/p99 at target power profile | same replay | bytes + ms/frame | same definition |
| Browser WebGPU | browser/device matrix | same replay | bytes + ms/frame | include JS/WASM heap |

Keep the replay deterministic: camera path, edit locations, edit rate, world seed, and
warm-up are fixed. Record both steady state and burst recovery. A bounded queue that
never drains is still a failed budget.

See [`bevy-diagnostics-profiling`](../../bevy-diagnostics-profiling/SKILL.md) for the
Bevy diagnostic and tracing APIs and render-backend limitations.
