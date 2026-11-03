# Coalescing, priorities, and bounded queues

## One intent per section

Track a state machine rather than spawning a task at every edit:

| Current state | Dirty request | Worker starts/finishes | Main-thread apply |
|---|---|---|---|
| `Idle` | enqueue latest token → `Queued` | — | — |
| `Queued` | update latest token/priority | start: snapshot → `Running` | — |
| `Running` | newer token → `RunningAndDirty` | finish: stage result → `Ready` | — |
| `RunningAndDirty` | update latest token/priority | finish: reject old result → `Queued` | — |
| `Ready` | discard pending result; latest → `Queued` | — | revalidate; accept → `Idle` |

Every source-data edit bumps the section revision immediately. Therefore a result
from a job that moved to `RunningAndDirty` is stale by definition and must not be
applied. A duplicate dirty notification for the current revision may update priority,
but it does not create a newer token or force another job.

`Ready` means CPU output is waiting for the bounded main-thread apply stage; it does
not mean the token is permanently accepted. Re-check existence, epoch, and revision
at apply. A global completed queue may retain lazily invalidated entries, but only the
result matching the section's current `Ready` token may mutate presentation.
Transition `Running -> Ready` only after result storage admits the payload. If that
stage is full, keep ownership in the completed task or apply an explicit latest-only
drop policy; never lose the scheduler state while dropping an output implicitly.

Unload/lifecycle replacement removes the intent instead of requeueing it; a late
completion then fails epoch/existence validation. Treat worker failure separately:
return to `Idle`, retry with an explicit bounded policy, or queue a newer dirty token.

## Priority heap with lazy invalidation

`BinaryHeap` has no cheap update-in-place. Keep a `latest` map keyed by section and
push a new heap entry when priority or token changes. On pop, discard the entry unless
it equals the map's current queue generation/token. This makes reprioritisation cheap
and bounded by periodic heap compaction.

A practical priority tuple, highest first:

1. collision-critical hole near the controlled actor;
2. currently visible section;
3. distance bucket from relevant cameras/players;
4. age since first dirtied;
5. stable coordinate tie-breaker for reproducible tests.

Do not use Euclidean distance alone. Behind-camera chunks can crowd out visible work,
and a constantly moving camera can starve older sections. Recompute priorities at a
bounded cadence or when visibility/distance buckets change, not for every section on
every frame.

## Budget every stage

Keep separate limits because each stage consumes a different resource:

```rust
struct RemeshBudgets {
    max_in_flight_tasks: usize,
    max_task_starts_per_frame: usize,
    max_completed_results: usize,
    max_applies_per_frame: usize,
    max_upload_bytes_per_frame: usize,
    max_apply_time: std::time::Duration,
}
```

- `max_in_flight_tasks` prevents worker saturation and snapshot memory spikes.
- `max_task_starts_per_frame` limits snapshot/copy bursts.
- `max_completed_results` provides backpressure. If the channel cannot block safely,
  retain only the latest result per section and drop superseded results with metrics.
- apply count controls entity/asset churn; byte/time limits cover a few giant meshes.

Tune from observed frame budgets. A nominal count is not portable across section
sizes, vertex formats, desktop GPUs, Steam Deck, and WebGPU.

## Worker and platform rules

- Use `AsyncComputeTaskPool` for CPU-heavy meshing, but treat it as an executor, not a
  scheduler. Your queue owns priority and admission.
- Poll tasks without blocking the main thread: `block_on(poll_once(&mut task))`
  returns immediately when the task is not finished. Never await one specific
  section's task from a frame system.
- On targets without effective worker threads, the same bounded state machine must
  make forward progress incrementally or through a synchronous fallback budget.
- Cancelled/dropped tasks still need state cleanup. Prefer completion messages that
  always carry their token, including errors/panics converted at the task boundary.
- Include snapshot bytes and result bytes in memory telemetry; task count alone hides
  the dominant cost.

## Deterministic scheduler tests

Extract priority and state transitions into ordinary Rust functions. Feed a fake
clock and fake completions; assert ordering, aging, stale heap entry rejection,
coalescing, result-cap behaviour, and recovery after task failure. No sleeps or real
thread pool are required for these tests.
