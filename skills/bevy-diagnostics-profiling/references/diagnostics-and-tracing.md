# Diagnostics and tracing

## Design the measurement before the API call

Classify every signal:

- **gauge:** current queue depth, visible section count, resident bytes;
- **counter:** accepted jobs, stale results, coalesced requests, uploaded bytes total;
- **duration/sample:** task latency, apply time, frame time;
- **ratio:** stale/finished jobs, budget misses/frames.

Bevy's `Diagnostic` stores `f64` samples and can smooth/history them. It does not turn
a cumulative counter into a rate or a stream of task-duration samples into a full
percentile distribution automatically. Export raw samples or maintain a bounded
histogram when acceptance criteria require p95/p99.

`Diagnostics` buffers measurements by path until deferred application. Repeatedly
recording the same path from one system invocation retains only that system buffer's
last value, so do not call it once per completed job and expect a latency sample for
every job. Aggregate in an application-owned histogram/export queue and publish a
defined summary sample instead.

Use stable paths such as `voxel/task_latency_ms`; do not put section coordinates,
entity IDs, filenames, or player IDs in the path. That creates unbounded metric
cardinality. Put targeted identifiers in trace fields instead.

## Registration and reading

Register a `Diagnostic` once during plugin construction. Record through the
`Diagnostics` system parameter. Read through `Res<DiagnosticsStore>`:

```rust
use bevy::{diagnostic::{DiagnosticPath, DiagnosticsStore}, prelude::*};

const APPLY_TIME: DiagnosticPath =
    DiagnosticPath::const_new("voxel/apply_time_ms");

fn inspect(store: Res<DiagnosticsStore>) {
    let latest = store
        .get(&APPLY_TIME)
        .and_then(|diagnostic| diagnostic.value());
    let _ = latest;
}
```

Choose history length and smoothing to match the signal. Smoothing a queue gauge can
hide a dangerous spike; raw latest plus a peak/high-water mark may be more useful.
For totals larger than exactly representable `f64` integers, retain the authoritative
integer counter in your resource and publish a windowed delta/rate.

## Trace causal phases

Name spans by operation, not object identity. `tracing` is re-exported as
`bevy::log::tracing`; do not add it as a separate dependency with a different version:

```rust
let span = info_span!(
    "voxel_remesh",
    queue_wait_ms = bevy::log::tracing::field::Empty,
    revision = revision,
);
let _entered = span.enter();
```

Instrument these boundaries separately when applicable:

```text
dirty/coalesce -> queue wait -> snapshot -> worker compute -> result wait
               -> validation -> asset upload -> collider build -> entity swap
```

An outer span alone cannot distinguish queue pressure from compute cost. Conversely,
thousands of tiny spans distort scheduling and capture size. Use diagnostics for the
continuous overview and temporarily richer spans for a reproducible capture.

## Built-in system information limitations

`SystemInformationDiagnosticsPlugin` samples asynchronously because system queries
are relatively expensive. It supports Linux, Windows, Android, and macOS in suitable
standard builds. It is unsupported with Bevy dynamic linking, on iOS, and on Wasm.
Treat absent data as “not available.” Browser memory/CPU evidence must come from
browser/platform tools and application-owned counters.
