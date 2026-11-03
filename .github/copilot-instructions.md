# GitHub Copilot — Bevy 0.20

Copilot does not load Agent Skills directly. This file mirrors the key rules so Copilot users in this repo still benefit.

## When writing Bevy code

1. **Bevy 0.20 only.** Do not suggest 0.19 or earlier APIs. Specifically:
   - Events use `MessageWriter` / `MessageReader` (not `EventWriter` / `EventReader`, renamed in 0.17).
   - Observers are `On<E>`; lifecycle observers carry the bundle on the event: `On<Add<Player>>`, not `On<Add, Player>` (changed in 0.20).
   - `ui::Interaction` and `ui::widgets::Button` are deprecated; use `ui_widgets::Button` with `Hovered` and `Pressed` (0.20).
   - Pointer events are flat: `On<PointerClick>`, not `On<Pointer<Click>>` (0.20).
   - `TextFont` takes `font: FontSource` and `font_size: FontSize::Px(..)` (0.19); the default size is `FontSize::Rem(1.)` (0.20).
   - Custom shaders are WESL (`.wesl`, `import a::b;`, `@if(DEF)`), not naga_oil `#import` / `#ifdef` (0.20).
   - Scene files use `WorldAssetRoot` from `bevy_world_serialization`; `bevy_scene` is BSN (0.19).
   - `NextState::set_if_different`, not `set_if_neq` (0.20).
   - Required components use `#[require(...)]` on `Component` derives.

2. **Feature collections.** When configuring `Cargo.toml`, pick the right Bevy feature set: `2d`, `3d`, `ui` (high-level) or mid-level `2d_api`, `3d_api`, `ui_api`. `audio` and `ui` are no longer implied by `2d`/`3d` (0.19). See `skills/bevy-cargo-features/SKILL.md`.

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
| 0.19 → 0.20 breaks | `skills/bevy-migration-0-19-to-0-20/` |
| 0.18 → 0.19 breaks | `skills/bevy-migration-0-18-to-0-19/` |
| 0.17 → 0.18 breaks | `skills/bevy-migration-0-17-to-0-18/` |
| Assets & custom loaders | `skills/bevy-assets/`, `skills/bevy-custom-assets/` |
| WASM + WebGPU | `skills/bevy-wasm-webgpu/` |
| Cameras | `skills/bevy-cameras/` |
| PBR / materials / shaders | `skills/bevy-pbr-materials/` |
| UI, text, buttons | `skills/bevy-ui/` |
