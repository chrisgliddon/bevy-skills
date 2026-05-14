# GitHub Copilot — Bevy 0.18

Copilot does not load Agent Skills directly. This file mirrors the key rules so Copilot users in this repo still benefit.

## When writing Bevy code

1. **Bevy 0.18 only.** Do not suggest 0.17 or earlier APIs. Specifically:
   - Events use `MessageWriter` / `MessageReader` (not `EventWriter` / `EventReader` — those were renamed in the 0.17→0.18 migration; double-check the relevant skill in `skills/bevy-migration-0-17-to-0-18/`).
   - Asset paths support `short-type-path` in 0.18.
   - Required components use `#[require(...)]` on `Component` derives.

2. **Feature collections.** When configuring `Cargo.toml`, pick the right Bevy feature set: `2d`, `3d`, `ui` (high-level) or mid-level `2d_api`, `3d_api`, `ui_api`. See `skills/bevy-cargo-features/SKILL.md`.

3. **Schedule placement.** Game logic in `Update`; physics, networking, deterministic sims in `FixedUpdate`. Render-world systems are extracted automatically — don't add them to `Update`.

4. **No `unwrap()` in systems.** Bevy systems run every frame. Use `let ... else` or proper error propagation.

## When editing skills in this repo

Read `CLAUDE.md`. The frontmatter rules, lint script, and tester-crate workflow apply to all agents, not just Claude.

## Where to look

| Topic | Skill |
|---|---|
| ECS basics | `skills/bevy-core-concepts/` |
| Components & required components | `skills/bevy-ecs-components/` |
| Queries & filters | `skills/bevy-ecs-queries/` |
| Systems, sets, run conditions | `skills/bevy-ecs-systems/` |
| 0.17 → 0.18 breaks | `skills/bevy-migration-0-17-to-0-18/` |
| Assets & custom loaders | `skills/bevy-assets/`, `skills/bevy-custom-assets/` |
| WASM + WebGPU | `skills/bevy-wasm-webgpu/` |
| Cameras | `skills/bevy-cameras/` |
| PBR / materials | `skills/bevy-pbr-materials/` |
