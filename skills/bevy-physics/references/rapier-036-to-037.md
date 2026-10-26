# Bevy 0.20: bevy_rapier 0.36 → 0.37

Reviewed against the **published `bevy_rapier3d` 0.37.0 source** on 2026-10-26.
This is an integration checklist, not a local Cargo or runtime pass.

## Dependency and source checkpoint

- Use Bevy `0.20` with `bevy_rapier3d = "0.37"` (or the corresponding 2D crate).
  Published 0.37.0 manifests declare Bevy `^0.20` and underlying Rapier `0.36.1`.
  The binding and underlying engine version numbers are different.
- The active source moved to
  [`dimforge/rapier/bindings/bevy_rapier`](https://github.com/dimforge/rapier/tree/master/bindings/bevy_rapier).
  The former [`dimforge/bevy_rapier`](https://github.com/dimforge/bevy_rapier) is archived.
  Use the registry release; the move is not a reason to add a Git dependency.
- Remove the unused `headless` feature. A lean 3D profile disables defaults and enables
  `dim3`; see [setup](setup-and-scheduling.md). Defaults still include asset, debug
  rendering, picking, and mesh-conversion helpers.
- `enhanced-determinism` is reported fixed upstream, but still cannot be combined
  with `simd8`. Do not equate a successful build with deterministic game behavior.

## API changes to audit

| Surface | Required check |
|---|---|
| `QueryFilter::predicate` | Accept `(Entity, &RapierCollider)`, not only an entity. |
| `intersect_*` callbacks | Accept the collider argument as well as the entity. |
| `project_point_and_get_feature` | Supply the new `max_dist` argument. |
| `RapierContextMut::move_shape` | Pass `QueryFilter` instead of a mutable query pipeline. |
| Direct `step_simulation` calls | Supply `SimulationMode`; ordinary plugin users need not call this directly. |
| Struct literals/exhaustive matches | Audit added fields/variants on configuration, groups, sleeping, contact-force messages, controllers, query hits, combine rules, joints, and shape views. Use constructors/defaults when appropriate. |
| Collision/solver groups | `::new` retains `And`; `Or` applies only when both groups choose it. |
| Shape casts | `AsShape` accepts a `Collider` directly; old shape-trait objects are still accepted. Do not rewrite working casts unnecessarily. |

The existing canonical fixed-step pattern still uses `Velocity::linear`,
`velocity.linear`, `MessageReader<CollisionEvent>`, `ReadRapierContext::single()`,
`PhysicsSet::{SyncBackend, StepSimulation, Writeback}`, and
`.in_fixed_schedule()`. These names were checked in the published source, not guessed
from older examples. That source review does not satisfy the compile gate.

## Behavior that compilation will not prove

- Default contact/intersection hook implementations now **keep** pairs rather than
  discard them. Test custom hooks relying on inherited defaults.
- Unlinked entities inherit the nearest linked ancestor's physics context before
  falling back to the default. Re-test reparenting and multiple contexts.
- Joint `user_data` is overwritten with the owning entity. Store application metadata
  in ECS components instead.
- Debug-render style lengths now use meters scaled by the context's `length_unit`.
  Recheck 2D pixel-scale diagnostics; this is not a physics/rendering engine merger.
- Zero-duration steps are skipped. Ensure paused/first-frame tests do not expect a step.
- Removing physics components now resets backend properties; reparenting joints
  reattaches them; waking a sleeping body wakes its island. Test those lifecycle flows.
- Check collision messages, controller slopes/stairs, fixed-step pacing, and any
  application-specific ray/shape queries against recorded 0.19 behavior.

New soft bodies, vehicle/PID controllers, robotics loaders, FEM, and diagnostics are
optional additions. Do not introduce them merely to complete this dependency migration.

## Evidence

- [Published manifest](https://docs.rs/crate/bevy_rapier3d/0.37.0/source/Cargo.toml)
- [Published query filter](https://docs.rs/crate/bevy_rapier3d/0.37.0/source/src/pipeline/query_filter.rs)
- [Published context API](https://docs.rs/crate/bevy_rapier3d/0.37.0/source/src/plugin/context/systemparams/rapier_context_systemparam.rs)
- [Published groups](https://docs.rs/crate/bevy_rapier3d/0.37.0/source/src/geometry/collider.rs)
- [Binding changelog at reviewed upstream commit](https://github.com/dimforge/rapier/blob/475caa3ff4646fd9a796b67d14116256f4962bc7/bindings/bevy_rapier/CHANGELOG.md)
- [Collection validation and remaining gates](../../bevy/references/bevy-020-readiness.md)
