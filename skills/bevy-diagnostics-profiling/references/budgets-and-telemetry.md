# Acceptance budgets and runtime telemetry

## A budget is a testable contract

Write the target and replay before choosing thresholds:

```yaml
scenario: edit_burst_near_camera_v2
build: release + shipping features
warmup_seconds: 30
sample_seconds: 120
targets:
  native_min_spec:
    frame_time_p99_ms: <project value>
    queue_recovery_seconds: <project value>
  steam_deck_15w:
    frame_time_p99_ms: <project value>
    queue_recovery_seconds: <project value>
  chrome_webgpu_min_spec:
    frame_time_p99_ms: <project value>
    queue_recovery_seconds: <project value>
```

Pin resolution, renderer/backend, target frame rate, Deck power/refresh profile,
browser version, world seed, camera route, edit stream, and asset state. Record
thermal state where it matters. Thresholds copied from a different game are not
acceptance criteria.

## Minimum async-pipeline signals

For each queue/task/upload pipeline, record:

- valid queued count and oldest-item age;
- in-flight work and configured concurrency;
- starts, completions, failures, cancellations, coalesced requests, stale rejections;
- queue wait, compute duration, result wait, and main-thread apply duration;
- input snapshot bytes, completed-result bytes, uploaded bytes, and high-water marks;
- visible/near/critical work counts and work completed by priority class;
- budget misses and time/bytes deferred to later frames.

Queue depth without age can hide starvation. Average latency can hide p99 stalls.
Task duration without queue wait can blame workers for admission pressure. Uploaded
mesh count without bytes can hide a single pathological asset.

## Measurement hygiene

- Use one monotonic clock for latency timestamps.
- Define whether a duration includes queue wait, copying, validation, and upload.
- Separate cumulative totals from per-frame samples and rolling rates.
- Reset scenario counters at a controlled marker, not during arbitrary gameplay.
- Export enough raw/windowed data to calculate percentiles outside the frame loop.
- Include instrumentation version in captures so path/semantics changes are visible.

## Pass/fail interpretation

A run fails if a hard threshold is exceeded after allowed warm-up, if the queue does
not recover in the specified interval, or if required evidence is absent. Do not pass
a WebGPU run because GPU timings were unsupported; use the target's alternative
evidence. Compare distributions over repeated runs and keep the raw artifacts needed
to explain a regression.

When optimisation changes quality—render distance, collider fidelity, update cadence,
or input latency—record that as a separate product tradeoff. It is not a free
performance win.
