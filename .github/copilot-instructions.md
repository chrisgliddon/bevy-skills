# GitHub Copilot — Bevy 0.20

Copilot does not load Agent Skills directly. This file mirrors the key rules so Copilot users in this repo still benefit.

## When writing Bevy code

1. **Bevy 0.20 only.** Do not suggest older APIs except while explaining a migration. Specifically:
   - Events use `MessageWriter` / `MessageReader` (not the older
     `EventWriter` / `EventReader`; double-check the migration skills when
     reviewing stale code).
   - Resources are components; scene serialization uses `WorldAsset` / `WorldAssetRoot` and the `bevy_world_serialization` feature.
   - Text styling uses `FontSource` and `FontSize` components; the default size is `FontSize::Rem(1.)` (0.20).
   - Lifecycle observers carry the bundle on the event: `On<Add<Player>>`, not `On<Add, Player>` (0.20).
   - Pointer events are flat: `On<PointerClick>`, not `On<Pointer<Click>>` (0.20).
   - `ui::Interaction` and `ui::widgets::Button` are deprecated; use `ui_widgets::Button` with `Hovered` and `Has<Pressed>` (0.20).
   - Custom shaders are WESL (`.wesl`, `import a::b;`, `@if(DEF)`), not naga_oil `#import` / `#ifdef` (0.20).
   - `NextState::set_if_different`, not `set_if_neq` (0.20).
   - Required components use `#[require(...)]` on `Component` derives.

2. **Feature collections.** When configuring `Cargo.toml`, pick the right Bevy feature set: `2d`, `3d`, `ui` (high-level) or mid-level `2d_api`, `3d_api`, `ui_api`. See `skills/bevy-cargo-features/SKILL.md`.

3. **Schedule placement.** Frame-driven game/presentation logic goes in `Update`;
   fixed-step physics and deterministic simulation go in `FixedUpdate`.
   Render-world systems belong in Bevy's render schedules, not `Update`.

4. **No `unwrap()` in systems.** Bevy systems run every frame. Use `let ... else` or proper error propagation.

5. **Bridge input into fixed ticks.** Translate physical input after `InputSystems`,
   queue button transitions, accumulate relative motion, and drain both once on the
   first fixed tick. Carry held buttons/absolute axes to every tick.

6. **Persist stable domain IDs.** Save versioned DTOs, not `Entity`, dense runtime
   palette indices, catalog order, asset handles, or reflected ECS layout by default.

## When editing skills in this repo

Read `CLAUDE.md`. The frontmatter rules, lint script, and tester-crate workflow apply to all agents, not just Claude.

## Where to look

| Topic | Skill |
|---|---|
| ECS basics | `skills/bevy-core-concepts/` |
| Rebindable input / gamepads / fixed bridge | `skills/bevy-input-actions/` |
| Deterministic and visual testing | `skills/bevy-testing/` |
| Components & required components | `skills/bevy-ecs-components/` |
| Queries & filters | `skills/bevy-ecs-queries/` |
| Systems, sets, run conditions | `skills/bevy-ecs-systems/` |
| 0.19 → 0.20 breaks | `skills/bevy-migration-0-19-to-0-20/` |
| 0.18 → 0.19 breaks | `skills/bevy-migration-0-18-to-0-19/` |
| 0.17 → 0.18 breaks | `skills/bevy-migration-0-17-to-0-18/` |
| Assets & custom loaders | `skills/bevy-assets/`, `skills/bevy-custom-assets/` |
| Save/load schemas and platform persistence | `skills/bevy-save-load/` |
| WASM + WebGPU | `skills/bevy-wasm-webgpu/` |
| Cameras | `skills/bevy-cameras/` |
| PBR / materials | `skills/bevy-pbr-materials/` |
| Renderer selection / custom passes | `skills/bevy-rendering/` |
| Diagnostics / tracing / render profiling | `skills/bevy-diagnostics-profiling/` |
| Physics / Rapier / collision queries | `skills/bevy-physics/` |
| Game accessibility / adaptive controllers | `skills/bevy-a11y/` |
| Audio / sinks / spatial / mixing | `skills/bevy-audio/` |
| Voxel data, meshing, and production runtime | `skills/bevy-voxel-data/`, `skills/bevy-voxel-pipeline/`, `skills/bevy-voxel-runtime/` |
