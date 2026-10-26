# Bevy 0.20 readiness — staged update

Evidence date: **26 October 2026**. This record updates the dependency status in
[draft migration-plan PR #24](https://github.com/chrisgliddon/bevy-skills/pull/24).
It does not rewrite that 9 October assessment or claim its game-project snapshots
are current. No game project or companion repository is changed by this update.

## What is now unblocked

The published [`bevy_rapier3d` 0.37.0 manifest][manifest] explicitly depends on Bevy
`0.20` (Cargo's `^0.20` requirement). The corresponding 2D release has the same engine
requirement. The **Rapier release-availability gate is resolved**: no fork, Git
branch, or wait for publication is needed for that dependency pair.

This is not a blanket 0.20 release of the collection:

| Area | Status |
|---|---|
| General implementation skills | Remain pinned to Bevy 0.19; not recertified for 0.20 |
| 0.19→0.20 migration skill | Added, source-reviewed checklist |
| Physics skill and its current references | Updated to Bevy 0.20 / Rapier 0.37.0; compile/runtime gate **pending** |
| Existing 0.19 physics consumers | [Commit-pinned 0.19 path](../../bevy-physics/references/bevy-019-compatibility.md) preserved |
| 0.17→0.18 and 0.18→0.19 migration skills | Historical targets unchanged |
| Renderer feature auditor | Detects known 0.36/0.37 mismatches and removed `headless` feature; static check only |
| Plugin release metadata | Stays at 0.19.0; no new supported-default release advertised |

## Source review completed

- Published manifests for both `bevy_rapier3d` and `bevy_rapier2d` 0.37.0, including
  Bevy requirement, default features, removed `headless`, and determinism/SIMD limits.
- Published 3D source: plugin scheduling, `TimestepMode`, `Velocity`, collider
  constructors, messages, groups, context queries, controller fields, and joint builders.
- [Rapier changelog][changelog]: query callback changes, hook defaults, context
  inheritance, additional public fields, joint metadata, and relevant lifecycle changes.
- [Official Bevy migration guide][guide], release notes, and the
  [v0.20.0 manifest][bevy-manifest]. The latter declares Rust **1.97.1** as its MSRV;
  this resolves the old plan's unknown tagged-manifest/toolchain requirement, not the
  question of which toolchain a future validation run actually used.

The published crate's VCS record names commit
`475caa3ff4646fd9a796b67d14116256f4962bc7` with `dirty: true`. Therefore the registry
crate, not just a moving `master` branch, was inspected. Its `src/` tree matched that
upstream commit. The downloaded 3D crate archive SHA-256 was
`549d1806101690b7b3076189dfaa6e2aec392d601dfea3249c6c18fb1105dafa`.

## Validation and the open compile gate

**Do not mark this draft ready on source review alone.** Repository policy requires
changed examples to compile in the companion tester. The authenticated lookup of
`chrisgliddon/bevy-skills-tester` returned **404** on the evidence date; that does not
prove the repository is absent. This executor has no `cargo`, `rustc`, or `rustup`.
No Rust build, dependency resolution, shader validation, or runtime test was run.
`dex` is also unavailable here, so no Dex completion or synchronized issue is claimed.

Lightweight repository checks are run locally and recorded in the update PR:

```sh
python3 scripts/lint-skills.py --strict
python3 -m unittest discover -s skills/bevy-rendering/tests -v
python3 -m unittest discover -s skills/bevy-a11y/tests -v
git diff --check
```

These checks establish frontmatter/Python behavior/whitespace only, not Rust
compatibility. No GitHub Actions workflow was added, enabled, or manually dispatched.

### Snippet verification inventory

Use `examples/bevy_physics.rs` in the resolved companion tester for the canonical
example. The remaining fixture names below are **proposed**, not existing files or
passing builds. Record the exact tester revision, Rust version, lockfile, target,
features, and result when the gate is completed.

| Source | Proposed fixture / check | Current result |
|---|---|---|
| `skills/bevy-physics/SKILL.md` Cargo + Rust fences | `examples/bevy_physics.rs`; Bevy 0.20.0 / Rapier 0.37.0 default game features | Published API review only; compile/run pending |
| `references/setup-and-scheduling.md` | Game + lean manifests; timestep fixture | Manifest feature/source review only; Cargo check pending |
| `references/bodies-and-colliders.md` | `examples/bevy_physics_bodies.rs` | Constructor source review only; compile pending |
| `references/events-queries-and-filtering.md` | `examples/bevy_physics_queries.rs` with `Player` and app registration | Message/group/query source review only; compile/run pending |
| `references/controllers-and-joints.md` | `examples/bevy_physics_controllers.rs` | Controller/joint source review only; compile/run pending |
| `skills/bevy-migration-0-19-to-0-20/SKILL.md` | Resolve dependency checkpoint and apply migration checks to affected fixtures | Manifest/source review only; Cargo check pending |

The `references/` rows above are relative to `skills/bevy-physics/`. Excerpt fences
need harness imports/setup; they are not standalone Rust files. The preserved 0.19
dependency fence is historical guidance, not freshly compiled evidence.

## Remaining gates before a collection-wide 0.20 default

1. **Restore tester access and run the inventory above.** Use Rust 1.97.1 or newer,
   pin the actual patch/toolchain/lockfile, and test default and lean profiles.
2. **Audit the other Bevy-facing plugins individually.** Avian, Hanabi, capture,
   Seedling, localization, spritesheet/vector rendering, and Gaussian splatting
   compatibility were not established in this slice. Existing 0.19 pins are not 0.20
   recommendations. Check optional and target-specific features, not just defaults.
3. **Migrate and verify remaining implementation skills/references.** Prioritize
   observers/queries/scheduling, render extraction/shaders/materials, UI/picking/text,
   assets/scenes, and Cargo/web features. Keep historical guides pinned.
4. **Prove behavior.** Physics contacts/controllers/hooks/context inheritance;
   fixed-step/input timing; camera isolation/shader visuals; UI focus/Escape/controller
   navigation; scene lifecycle and saves all require runtime evidence.
5. **Only then change published-default/version metadata.** Keep project upgrades in
   separate authorized branches; no PPW, Variant, or older-project migration is claimed.

The previous plan's proposed CI workflow remains a proposal, not an instruction to
enable Actions in this update. Local checks and future authorized tester evidence
can be recorded without creating billed CI work.

[manifest]: https://docs.rs/crate/bevy_rapier3d/0.37.0/source/Cargo.toml
[changelog]: https://github.com/dimforge/rapier/blob/475caa3ff4646fd9a796b67d14116256f4962bc7/bindings/bevy_rapier/CHANGELOG.md
[guide]: https://bevy.org/learn/migration-guides/0-19-to-0-20/
[bevy-manifest]: https://github.com/bevyengine/bevy/blob/v0.20.0/Cargo.toml
