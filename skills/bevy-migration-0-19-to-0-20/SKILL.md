---
name: bevy-migration-0-19-to-0-20
description: Use when upgrading from Bevy 0.19 to Bevy 0.20, migrating `On<Add, T>` to `On<Add<T>>`, replacing `Pointer<Press>` with `PointerPress`, converting naga_oil shaders to WESL, handling `Query::iter_many` results, or selecting the Bevy-compatible `bevy_rapier3d` release.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "1"
  area: migration
  bevy_version: "0.20"
  source_version: "Bevy 0.19"
  target_version: "Bevy 0.20"
---

# Bevy 0.19 → 0.20 migration

## When to use this skill

- A project already builds on 0.19 and is taking the next engine-version hop.
- Observer, pointer, query, shader, or plugin APIs break after the dependency update.
- Rapier availability was blocking a 0.20 upgrade.

This is a source-reviewed migration checklist, not certification that every sibling
skill or project has migrated. Check each sibling's version pin before copying code.
For older projects, use the preceding migration skills first.

## Canonical dependency checkpoint

```toml
[dependencies]
bevy = "0.20"
bevy_rapier3d = "0.37"
```

The reviewed releases are Bevy **0.20.0** and `bevy_rapier3d` **0.37.0**. The published
Rapier manifest requires Bevy `^0.20`, so a Git fork or unreleased branch is not
needed for this pair. Bevy 0.19 projects must keep their matching Rapier 0.36 line;
do not mix the two engine generations. Other plugins need their own dependency audit.
See the [published Rapier manifest][rapier-manifest].

Bevy 0.20.0 declares Rust **1.97.1** as its minimum version in the
[tagged manifest][bevy-manifest]. Record the actual toolchain, resolved versions,
feature profile, and lockfile used for validation; a compatible version declaration
alone is not a passing build. The manifest above retains convenient rendering defaults,
not a server profile; see [`bevy-physics`](../bevy-physics/SKILL.md) for lean features.

## Ordered migration pass

1. Capture a working 0.19 checkpoint: builds, tests, saved-data fixtures, and screenshots
   for behavior the project depends on. Preserve unrelated work and plugin patches.
2. Resolve every Bevy-facing dependency for 0.20. Inspect default, optional, workspace,
   renamed, and target-specific dependencies rather than checking only one manifest.
3. Apply the [complete official migration guide][guide] to the APIs actually used.
   The targeted checks below are priorities, not an exhaustive replacement.
4. Compile the real native/web and feature matrix before removing compatibility code.
5. Exercise physics, input, rendering, assets, and saved data; compare against the
   baseline. Adopt optional new engine features only after existing behavior is stable.

## Gotchas: source changes

| Affected surface | 0.20 action |
|---|---|
| Lifecycle observers | Put the component/bundle inside the pattern: `On<Add<T>>`, not `On<Add, T>`. Apply the same shape to `Insert`, `Discard`, `Remove`, and `Despawn`. Dynamic component observers use `Add<()>`. [Observer change][observers] |
| Custom events | Ordinary `On<MyEvent>` remains valid through blanket event-pattern support. Do not add lifecycle generics to every observer. [Observer change][observers] |
| Picking handlers | Use concrete types such as `PointerPress`; read pointer identity/position through `.pointer.id` and `.pointer.position`. Generic handlers use `PointerEvent`. [Pointer change][pointer] |
| Multi-entity queries | `iter_many` and related variants expose per-entity `Result`s. Handle failures deliberately; `.matched()` restores skip-unmatched behavior where available. Do not hide missing-entity bugs with an automatic unwrap. [Query change][queries] |
| Custom shaders | Translate naga_oil directives to WESL and use `.wesl`; directive-free WGSL still works. Remove `shader_format_wesl`; WESL no longer needs that feature. GLSL is removed. [Shader section][shaders] |
| Manual `AsBindGroup` | Audit `BindGroupBuilder` and `build_bind_group`, not only a type rename. Derived implementations are handled by the derive. [Migration guide][guide] |
| Render extraction | Add the target app to extraction traits/derives, including `#[extract_app(RenderApp)]` where required. [Migration guide][guide] |

## Gotchas: behavior and data

- **Ordering:** built-in weak edges may disappear for nonconflicting tracked access.
  Channels, atomics, or interior mutability can hide a real dependency. Keep explicit
  strong `.before()`, `.after()`, or `.chain()` constraints when behavior needs them;
  weak ordering does not overlap separate schedules. [Scheduling change][ordering]
- **UI:** `Button`/`Interaction` old aliases are deprecated, not universally removed.
  Plan widget/interaction migration and check warning-as-error policies.
  [Deprecation change][ui]
- **Text input:** supply both `EditableText` and `TextInput`; test Escape because it
  now blurs and bubbles. Audit generic `FontSource` family constructors. [Guide][guide]
- **Rendering:** opt in to `ScreenSpaceTransmission`; check `Tonemapping::None` versus
  `Linear` for visual parity and update persisted reflected type paths. [Guide][guide]
- **Scenes:** BSN scene references use `@`; component-value `template_value` wrappers
  are no longer needed. Test authored templates separately from serialized-world
  fixtures rather than treating all scene formats as one migration. [Release notes][release]
- **Optional additions:** `PanOrbitCamera`, sprite materials, and extended 2D materials
  are available, but none is a prerequisite for updating the physics dependency.
  [Release notes][release]

## Validate before declaring support

```sh
cargo check --all-targets --locked
cargo test --locked
cargo tree -d
```

Run after intentionally resolving and reviewing the upgraded lockfile. Repeat for the
project's actual feature profiles and supported target triples; blindly enabling every
feature can combine mutually exclusive backends. Inspect duplicate Bevy crate versions
and prove that plugins exchange the same ECS/assets/render types.

Compilation does not validate collision behavior, fixed-step timing, camera isolation,
shader output, focus/navigation, controller input, scene lifetime, or save compatibility.
Record those checks separately. Publishing Rapier 0.37 resolves the **release-availability
gate only**, not the project's compile/runtime acceptance gates.

**Evidence status (2026-10-26):** upstream release, manifests, and migration sources
reviewed. This checklist's dependency snippet has not been Cargo-checked in this
repository; Rust toolchain/companion-tester validation remains a separate gate.

## See also

- [`bevy`](../bevy/SKILL.md) — version-aware entry point.
- [`bevy-physics`](../bevy-physics/SKILL.md) — Rapier setup and migration boundaries.
- [`bevy-migration-0-18-to-0-19`](../bevy-migration-0-18-to-0-19/SKILL.md) — prior hop.
- [Official migration guide][guide] — full breaking-change inventory.
- [Bevy 0.20.0 release tag](https://github.com/bevyengine/bevy/releases/tag/v0.20.0).

[guide]: https://bevy.org/learn/migration-guides/0-19-to-0-20/
[release]: https://bevy.org/news/bevy-0-20/
[bevy-manifest]: https://github.com/bevyengine/bevy/blob/v0.20.0/Cargo.toml
[rapier-manifest]: https://docs.rs/crate/bevy_rapier3d/0.37.0/source/Cargo.toml
[observers]: https://github.com/bevyengine/bevy/pull/24013
[pointer]: https://github.com/bevyengine/bevy/pull/25337
[queries]: https://github.com/bevyengine/bevy/pull/25200
[shaders]: https://bevy.org/learn/migration-guides/0-19-to-0-20/#wesl-shaders
[ordering]: https://github.com/bevyengine/bevy/pull/25128
[ui]: https://github.com/bevyengine/bevy/pull/25197
