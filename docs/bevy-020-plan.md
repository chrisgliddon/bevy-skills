# Bevy 0.20 migration plan

Prepared for Chris Gliddon · 9 October 2026

## Recommendation

Bevy 0.20.0 is released. Start a version-aware `bevy-skills` migration branch now, then upgrade the games in separate, tested branches. The highest risks in the inspected projects are custom rendering, plugin compatibility, multi-camera behavior, and UI/input regressions. A dependency-number change alone is insufficient.

The immediate priorities are:

1. Establish reproducible `bevy-skills` snippet coverage and add the missing 0.19→0.20 migration skill.
2. Prove PPW’s physics and rendering dependency path, then validate its solo/split-screen effects across native and browser builds.
3. Migrate the active Variant game in `variant-club`; assess `variant-hunter`’s separate 0.18 Rust client independently.
4. Keep older projects on explicit migration paths. Advance one minor release at a time, with a working checkpoint at each step.

This report is a source-level impact assessment and implementation plan. No project builds, tests, repository edits, or pushes were performed. Dependency versions below are verified current pins; their compatibility with Bevy 0.20 remains a release gate.

## Verified baseline

[Bevy 0.20.0][release] was published on 8 October 2026 at 21:41 UTC. The [official announcement][announcement] is dated 8 October. The direct release page is authoritative here; a cached releases index still showed an earlier release candidate during research.

| Repository and branch | Inspected baseline | Planning consequence |
|---|---|---|
| `ppw-blocks`, `main` | Manifest and lockfile: Bevy 0.19.1; Rapier 0.36.0. Avian 0.7.0 is optional behind the Avian spike. | A direct 0.19→0.20 candidate, gated first on physics and custom rendering. |
| `variant-club`, `dev` | Active Variant game client: Bevy 0.19.1. | A direct 0.19→0.20 candidate with substantial UI, input, audio, and material coverage. |
| `variant-hunter`, `dev` | Separate minimal Rust client: manifest 0.18, lockfile 0.18.1. | Assess 0.18→0.19 before the final hop; do not confuse it with the active game client. |
| `prefabuland`, `main` | Bevy 0.18, water 0.18, Rapier 0.33, and a vendored capture fork patched for 0.18. | A multi-hop upgrade with fork and plugin work. |
| `voxelforge`, `dev` | `voxelforge-bevy` adapter pins `=0.19.0`. | Assess the Bevy adapter and downstream consumers together. |
| `bevy-skills`, `main` | 31 skills; current implementation guidance targets 0.19. Existing migration skills cover 0.17→0.18 and 0.18→0.19. | Add the missing hop and validate examples before declaring 0.20 support. |

Sources: [PPW manifest][ppw-cargo] and [lockfile][ppw-lock]; [Variant Club manifest][variant-cargo] and [lockfile][variant-lock]; [Variant Hunter manifest][hunter-cargo] and [entry point][hunter-main]; [Prefabuland manifest][prefab-cargo]; [VoxelForge adapter manifest][voxel-cargo]; [skills router][skills-router]. The skills audit is pinned to commit `b1b4da5744ebbd5c526342b2351967411cd5ca61`; project links reflect the inspected branches.

## What changes in 0.20

These categories determine the response: **breaking** requires source or configuration work when the affected API is used; **behavioral** requires regression tests even if compilation succeeds; **deprecated** allows a transition period; **additive** can be adopted separately.

### Confirmed changes with direct upstream evidence

| Change | Type | Required response when applicable |
|---|---|---|
| Lifecycle observer patterns move the bundle parameter into the event pattern: `On<Add, A>` becomes `On<Add<A>>`. Ordinary custom events receive blanket event-pattern support. | Breaking API | Audit lifecycle observers and shared handler signatures. This is a targeted rewrite, not evidence that every observer must change. [PR 24013][pr-observers] |
| Picking uses concrete pointer-event types such as `PointerPress`; pointer details live under `.pointer`. | Breaking API | Update affected handlers and field access; use the generic `PointerEvent` abstraction only where needed. [PR 25337][pr-pointer] |
| Built-in scheduling adopts weak dependency edges that can be omitted when tracked accesses do not conflict. This does not merge `Update` with `PostUpdate`, or `Render` with `RenderGraph`. | Behavioral | Test systems with ordering assumptions and document genuine ordering requirements. [PR 25128][pr-ordering] |
| The sprite backend is unified; ordinary `Sprite` use is largely transparent, with the old backend retained for `Text2d`. | Behavioral and internal API | Recheck rendering and custom backend integrations. Do not replace ordinary sprites with meshes merely because the backend changed. [PR 25432][pr-sprites] |
| `AtmosphereBuffer` becomes a per-camera component; `init_atmosphere_buffer` is removed. | Breaking for custom render integration; behavioral fix | Update custom atmosphere systems that accessed the resource. Ordinary atmosphere users mainly need multi-camera visual checks. [PR 23113][pr-atmosphere] |
| The older UI `Button` and `Interaction` names remain as deprecated aliases. | Deprecated | Plan the replacement deliberately. Warning-as-error policies can make the cleanup a build gate. [PR 25197][pr-ui] |
| Custom sprite materials become available. | Additive | Consider after migration passes; there is no general requirement to redesign materials around the new feature. [PR 25415][pr-sprite-material] |

### Additional conditional checks

The following compact checklist comes from the [official 0.19→0.20 migration guide][guide20]. It is intentionally selective; use the guide and affected APIs when implementing each change.

- **Shaders:** `naga_oil` directives migrate to WESL and `.wesl`; plain directive-free WGSL remains valid. WESL support is unconditional, the `shader_format_wesl` feature is removed, GLSL is removed, and SPIR-V remains supported.
- **Transmission:** add `ScreenSpaceTransmission` explicitly where its former `Camera3d` requirement supplied the effect.
- **Text editing:** `EditableText` needs `TextInput`; Escape now blurs and bubbles, potentially also closing a dialog.
- **Tonemapping:** `None` becomes true passthrough; `Linear` preserves the previous grading/dither/clamp behavior. Reflected type paths also change.
- **Queries and reflection:** `iter_many` variants yield `Result`; `.matched()` skips unmatched entities. `PartialReflect::to_dynamic` also returns `Result`.
- **Crate splits:** audit explicit imports, features, and dependencies for `bevy_shape` and `bevy_curve`.
- **State:** deprecated `NextState` method wrappers and the `PendingIfNeq` enum-variant rename need separate treatment.
- **Rendering and ordering:** test overlapping same-depth sprites and hidden scheduling dependencies through channels, atomics, or interior mutability.

### Optional additions

The release also adds facilities such as a ready-scene event, `PanOrbitCamera`, `ExtendedMaterial2d`, richer text/UI features, and early mesh-shader infrastructure. Evaluate them after restoring the existing behavior. Mesh shaders are unavailable on the web. Solari adds Metal support, but macOS lacks a built-in denoiser; its ReSTIR default changes can alter visuals. DLSS users need the updated SDK. These are conditional capabilities and checks, not reasons to enable new rendering features in every project. [Official announcement][announcement]

## Impact on the actual projects

### PPW Blocks

**Risk assessment: high rendering exposure; dependency-gated upgrade.** The current workspace enables Bevy 3D, UI, and audio. Its documented targets include native, browser WebGPU with a WebGL2 fallback, and Steam Deck. Rapier is part of the current dependency graph; Avian belongs to an optional spike. [Manifest][ppw-cargo] · [README][ppw-readme]

Start with these surfaces:

- Custom `Material` and `MaterialExtension` implementations in `apps/ppw-blocks/src/water.rs`, `lava.rs`, `sky.rs`, and `prop_fade.rs`; `crates/ppw-avatar/src/material.rs`; and `crates/ppw-blocks-bevy/src/surface_material.rs`. Inspect their shader files, imports, specialization, and feature assumptions together. [Water source][ppw-water] · [Sky source][ppw-sky] · [Surface material][ppw-surface]
- `apps/ppw-blocks/src/screen_pass.rs` explicitly documents a 0.19 fullscreen-material pipeline collision workaround combining rain and iris, plus four fixed uniform slots to avoid cached bind-group buffer moves. It targets world and second-view cameras while excluding thumbnails. Preserve these safeguards until a focused test demonstrates a safe replacement. A new engine release does not establish that either workaround is obsolete. [Screen pass][ppw-screen]
- Avatar, resident, and downtown presentation uses animation graphs/players and world assets; terrain sections stream meshes and colliders. Exercise spawn/despawn, scene readiness, animation, and streaming across camera changes. [PPW repository][ppw-repo]
- Solo and split UI crates should share migration fixtures and controller checks rather than drifting into separate API fixes. [Workspace manifest][ppw-cargo]

A useful isolation boundary already exists: `ppw-blocks-core` has no Bevy dependency. Keep engine adaptation in the Bevy-facing crates and avoid combining the upgrade with core world-format or algorithm changes. [Core manifest][ppw-core]

**Acceptance focus:** solo/split/thumbnail camera separation; rain and iris independently and together; sky, water, lava, fade, and avatar materials; tonemapping parity; section streaming and collider lifetime; keyboard/controller play; native, WebGPU, and WebGL2. Capture a baseline before modifying the render path.

The inspected authored sky uses a custom material. Built-in `Atmosphere` usage was not established, so the atmosphere change above is a conditional audit item rather than a confirmed PPW break.

### Variant Club

**Risk assessment: broad UI/input and rendering exposure.** This is the current Variant game client. Its Bevy 0.19.1 manifest includes PBR, postprocessing, glTF/animation, world serialization, UI/text, focus, and gamepad support. Current plugins include text input 0.15.0, optional Seedling 0.8.0, optional Bevy developer tools 0.19.1 for capture, and AccessKit 0.24.1. Verify each combination independently. [Client manifest][variant-cargo] · [Lockfile][variant-lock]

Audit these groups:

- `client/src/voxel_overworld/materials.rs`, `sky.rs`, and `visibility/distant_material.rs`, plus the `UiMaterial` in `client/src/variant_hunter/interface/visuals.rs`. Pair API compilation with shader validation and screenshots. [Materials][variant-materials] · [Interface visuals][variant-visuals]
- `client/src/variant_hunter/wild_grails/presentation.rs` for world assets and animation graphs. [Presentation source][variant-presentation]
- Chat text input, AccessKit/scroll handling, focus navigation, gamepad input, and second-controller seating. Test typing, focus transfer, Escape, D-pad navigation, and the controller joining/leaving flow. [Client source tree][variant-src]
- Optional audio and capture paths. A successful default build does not certify them. [Client manifest][variant-cargo]

Use the existing accessibility gates and 1280×720/1280×800 capture conventions as regression baselines. The inspected browser feature uses WebGL2; older descriptions mentioning a different UI or browser backend should not drive this plan. Native Linux includes X11/Wayland and gamepad support, with a Deck release profile. [README][variant-readme] · [Manifest][variant-cargo]

The current client manifest does not declare Rapier or Avian. Preserve its custom minigame physics tests without importing PPW’s physics assumptions into this migration.

### Variant Hunter and older projects

`variant-hunter`’s Rust client uses `MinimalPlugins`, domain ECS plugins, and a startup Nakama health check followed by application exit. Its immediate surface is much smaller than the game renderer’s, but it starts from 0.18. Backend and TypeScript services are outside the direct Bevy API migration. [Entry point][hunter-main] · [Manifest][hunter-cargo]

For `prefabuland`, inventory the water plugin, vendored capture changes, Rapier, and direct `wgpu`/`winit` dependencies before selecting an upgrade path. Preserve fork patches explicitly instead of assuming a newer crate release contains them. [Manifest][prefab-cargo]

For VoxelForge, test the `voxelforge-bevy` adapter’s assets, glTF, scene, animation, rendering, PBR, and reflection features, plus any generated content/contracts that consume it. [Adapter manifest][voxel-cargo]

Additional manifests show Bevy exposure in `ppw-paint` 0.18, `prefabuland-cards` 0.18, `bevy-go` 0.18, and `inindo_bevy` 0.16. Confirm which still need active support before expanding the work. These are discovered dependencies, not a claim that every project is currently shipping. [Paint][paint-cargo] · [Cards][cards-cargo] · [Bevy Go][go-cargo] · [Inindo][inindo-cargo]

## File level plan for bevy skills

### Phase 1 Establish a trustworthy baseline

The current [README][skills-readme] claims compiled snippets in a companion tester. That repository returned 404 through authenticated access, so its coverage could not be independently verified. This does not establish that it does not exist. Documentation also names conflicting fixture layouts. Resolve the repository, revision, and canonical path before advertising compile coverage.

[CLAUDE.md][skills-claude] says PR lint CI runs, but the inspected recursive tree contains no `.github/workflows` directory. Local Python tests cover accessibility scripts and the renderer-feature auditor; there are no Rust fixtures in this repository. Treat those checks as separate layers of evidence.

Create a snippet inventory with source file/fence, target Bevy version, features, third-party dependencies, fixture path, and compile/runtime result. Include linked reference documents. Pin the exact engine patch, toolchain, and lockfile used by the tester.

### Phase 2 Add the missing migration path

Proposed new file:

- `skills/bevy-migration-0-19-to-0-20/SKILL.md`

Use source/target version metadata, official citations, and an ordered checklist. Keep the main skill within the repository’s 200-line convention. Separate mechanical fixes, behavioral/data checks, deprecations, and optional adoption.

Add reference files only where the actual coverage justifies them; suggested subjects are ECS/scheduling, rendering/materials, assets/scenes, UI/input/audio, and Cargo/platforms. These are proposed additions, not existing repository files.

Preserve `skills/bevy-migration-0-17-to-0-18/` and `skills/bevy-migration-0-18-to-0-19/`, including their historical target pins. Add next-hop routing instead of rewriting their examples to 0.20. [Existing migration skills][skills-hop17] · [0.18→0.19][skills-hop18]

### Phase 3 Update routing and published guidance

| Files | Planned change | Completion evidence |
|---|---|---|
| `skills/bevy/SKILL.md` | Read the project version and select the correct implementation or migration path. Replace the current blanket 0.19 assumption with explicit version-aware routing. | Tests for current, older, unsupported, and ambiguous manifests. |
| `README.md`, `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md` | Align supported versions, fixture locations, validation claims, and editor guidance. | Every claim names a runnable check or recorded result. |
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.cursor-plugin/plugin.json` | Update release metadata after the validation gate passes. Current plugin versions are 0.19.0. | Consistent published metadata and documented exceptions. |
| `.cursor-plugin/marketplace.json` | Check the mirror pointer; change only if its target needs updating. | Pointer resolves to the intended artifact. |
| Current implementation skills and references | Update descriptions, metadata, headings, examples, and documentation links after validating each subsystem. | Exact snippet/fixture coverage at the selected 0.20 patch. |

Retain a clearly labeled 0.19 release or branch for existing projects. Avoid global replacement of version strings: historical guides and third-party crate numbers have different meanings. [Router][skills-router] · [Editing rules][skills-claude] · [Repository snapshot][skills-tree]

### Phase 4 Strengthen checks before changing the default

- `scripts/lint-skills.py`: replace the hardcoded default target with one explicit source of truth; check agreement between metadata, description, and headings while preserving historical and non-Bevy overrides. Add proposed `tests/test_lint_skills.py` cases for current/historical targets, overrides, invalid pins, and missing metadata. The current linter does not establish compilation or ecosystem compatibility. [Linter][skills-lint]
- Proposed `.github/workflows/validate.yml`: run strict lint and existing Python tests. If Rust compilation stays in a companion repository, publish its exact revision and fixture coverage rather than implying the local workflow tests every example.
- `skills/bevy-rendering/scripts/audit_renderer_features.py` and its test file: make engine-version handling explicit. The current script applies 0.19 assumptions, rejects workspace inheritance, and recognizes only direct Bevy and Rapier declarations. Test inherited/renamed dependencies, target tables, and 0.18/0.19/0.20 manifests. Use resolved Cargo metadata/tree where a static manifest cannot establish feature unification. [Auditor][skills-auditor] · [Tests][skills-auditor-tests]

### Phase 5 Migrate the highest exposure content

Review these current skill groups first, using the change list above as a checklist rather than assuming every skill is broken:

1. ECS components, queries, systems, and core concepts.
2. Rendering, `references/render-systems.md`, PBR/materials, assets, `references/gltf-scenes.md`, and custom assets.
3. UI and its text/interaction/colors-and-borders references; input actions; animation; save/load.
4. Cargo features and browser targets.
5. Physics, camera/orbit, voxel runtime, VFX, audio, capture, and localization integrations after dependency verification.

Update canonical examples, linked references, router triggers, and mirrored Copilot guidance together. Preserve sound project-level patterns such as stable IDs, DTO migrations, stale-task rejection, and action buffering unless a test or upstream change shows a reason to alter them.

The repository’s existing 0.19 ecosystem examples include Rapier 0.36, Avian 0.7, Hanabi 0.19, capture 0.6, Seedling 0.8, fluent manager 0.19.2 with fluent 0.18.1, spritesheet animation 7.0.1, vector shapes 0.13.1, and Gaussian splatting 8.0.1. These are an audit queue, not a 0.20 compatibility matrix. Verify the declared Bevy dependency and compile the relevant feature set before recommending a replacement version. [Skills snapshot][skills-tree]

## Staged migration from older versions

Sequential minor-version checkpoints are a recommended risk-control workflow, not an upstream requirement.

1. Record the starting manifest, lockfile, toolchain, targets, plugin versions, fork patches, and representative saved data. Produce baseline builds and screenshots where applicable.
2. Select the next official migration guide. Apply that hop’s required changes while keeping feature adoption and unrelated refactors separate.
3. Compile all relevant targets and features; run behavior/data checks; record remaining warnings and exceptions. Commit a working checkpoint before advancing.
4. Continue until 0.19 is stable, then apply this report’s 0.20 plan.
5. Re-run the complete supported-platform matrix at the final version before switching the skills default or merging a game upgrade.

Routes for the inspected projects:

- **0.19 projects:** [0.19→0.20][guide20].
- **0.18 projects:** [0.18→0.19][guide19], then 0.19→0.20. The skills repository already contains the first hop.
- **0.17 projects:** [0.17→0.18][guide18], then the route above. Both historical skills should remain available.
- **0.16 projects:** [0.16→0.17][guide17], then the route above. The repository does not currently provide its own skill for the first hop.
- **0.15 or earlier:** begin with the matching [official migration guides][guides]; [0.15→0.16][guide16] is the next step for a 0.15 project. Do not claim tested repository-specific coverage for these older starting points.

Maintain source/target fixtures for each supported hop. Where useful, retain an old-API compile-failure fixture beside the corrected target example so future edits cannot silently erase the migration lesson.

## Acceptance gates

### Skills and documentation

Run and retain the results of:

```sh
python3 scripts/lint-skills.py --strict
python3 skills/bevy-a11y/tests/test_scripts.py
python3 skills/bevy-rendering/tests/test_audit_renderer_features.py
```

After the proposed linter tests exist, include them in CI. Check sibling/reference links, version consistency, fixture paths, historical routing, and the published plugin metadata. These commands are planned validation, not results from this assessment.

### Rust and dependency compatibility

For each project and the confirmed tester layout:

```sh
cargo check --all-targets
cargo test
cargo tree -d
```

Inspect duplicate Bevy release lines and the resolved dependency graph. These commands are a starting point; they do not cover every optional feature or cross-compilation target by themselves.

Run explicit supported combinations for desktop/default, minimal headless, 2D, 3D/UI/audio, custom-renderer configurations, and separate browser WebGL2/WebGPU paths where the project actually supports them. Add each allowed third-party combination and optional physics/audio/capture path. Verify exact 0.20 feature names against its manifest before encoding the matrix.

### Runtime and data

- Shader validation and representative screenshots, including camera separation and transparency/effects.
- Controller, focus, typing, dialog/Escape behavior, accessibility, and audio.
- glTF/world loading, animation startup, hierarchy lifecycle, and streamed entity cleanup.
- Golden saved-data/world fixtures and reflected-type compatibility where those formats are persisted.
- Native and browser smoke tests; Steam Deck checks for projects that claim that target.

Compilation is necessary, but it cannot certify these behaviors. Record the tested commit, toolchain, target, feature set, and result. Mark 0.20 support only when the intended matrix passes or exclusions are clearly documented.

## Decisions and unresolved evidence

- **Exact 0.20 toolchain and dependency requirements:** the new tagged manifest could not be retrieved during this assessment. Confirm its MSRV, features, and resolved dependencies before pinning CI. No exact new MSRV is asserted here.
- **Plugin availability:** compatible 0.20 releases for the project and skills dependency lists were not established. This is the first implementation gate.
- **Tester access and coverage:** resolve the companion repository and conflicting fixture paths; preserve the distinction between linted, compiled, and runtime-tested examples.
- **Project scope:** confirm which older repositories still need maintained support. No native mobile build was established by the audited manifests.
- **Runtime confidence:** current findings are static inspection. Shader output, saves, controller behavior, browser behavior, and hardware-specific performance require the acceptance checks above.

A sensible first implementation slice is the skills baseline plus migration router and new hop, followed by one PPW rendering/physics spike and one Variant UI/input spike. Use their actual failures to refine examples before declaring broad support.

## Sources

Links below resolve to official Bevy sources or the inspected repositories. Repository sources are linked close to the relevant claims; the skills links are commit-pinned for reproducibility.

[release]: https://github.com/bevyengine/bevy/releases/tag/v0.20.0
[announcement]: https://bevy.org/news/bevy-0-20/
[guide20]: https://bevy.org/learn/migration-guides/0-19-to-0-20/
[guide19]: https://bevy.org/learn/migration-guides/0-18-to-0-19/
[guide18]: https://bevy.org/learn/migration-guides/0-17-to-0-18/
[guide17]: https://bevy.org/learn/migration-guides/0-16-to-0-17/
[guide16]: https://bevy.org/learn/migration-guides/0-15-to-0-16/
[guides]: https://bevy.org/learn/migration-guides/
[pr-observers]: https://github.com/bevyengine/bevy/pull/24013
[pr-pointer]: https://github.com/bevyengine/bevy/pull/25337
[pr-ordering]: https://github.com/bevyengine/bevy/pull/25128
[pr-sprites]: https://github.com/bevyengine/bevy/pull/25432
[pr-atmosphere]: https://github.com/bevyengine/bevy/pull/23113
[pr-ui]: https://github.com/bevyengine/bevy/pull/25197
[pr-sprite-material]: https://github.com/bevyengine/bevy/pull/25415
[ppw-repo]: https://github.com/chrisgliddon/ppw-blocks
[ppw-cargo]: https://github.com/chrisgliddon/ppw-blocks/blob/main/Cargo.toml
[ppw-lock]: https://github.com/chrisgliddon/ppw-blocks/blob/main/Cargo.lock
[ppw-readme]: https://github.com/chrisgliddon/ppw-blocks/blob/main/README.md
[ppw-core]: https://github.com/chrisgliddon/ppw-blocks/blob/main/crates/ppw-blocks-core/Cargo.toml
[ppw-water]: https://github.com/chrisgliddon/ppw-blocks/blob/main/apps/ppw-blocks/src/water.rs
[ppw-sky]: https://github.com/chrisgliddon/ppw-blocks/blob/main/apps/ppw-blocks/src/sky.rs
[ppw-surface]: https://github.com/chrisgliddon/ppw-blocks/blob/main/crates/ppw-blocks-bevy/src/surface_material.rs
[ppw-screen]: https://github.com/chrisgliddon/ppw-blocks/blob/main/apps/ppw-blocks/src/screen_pass.rs
[variant-cargo]: https://github.com/chrisgliddon/variant-club/blob/dev/client/Cargo.toml
[variant-lock]: https://github.com/chrisgliddon/variant-club/blob/dev/Cargo.lock
[variant-readme]: https://github.com/chrisgliddon/variant-club/blob/dev/README.md
[variant-src]: https://github.com/chrisgliddon/variant-club/tree/dev/client/src
[variant-materials]: https://github.com/chrisgliddon/variant-club/blob/dev/client/src/voxel_overworld/materials.rs
[variant-visuals]: https://github.com/chrisgliddon/variant-club/blob/dev/client/src/variant_hunter/interface/visuals.rs
[variant-presentation]: https://github.com/chrisgliddon/variant-club/blob/dev/client/src/variant_hunter/wild_grails/presentation.rs
[hunter-cargo]: https://github.com/chrisgliddon/variant-hunter/blob/dev/src/client/Cargo.toml
[hunter-main]: https://github.com/chrisgliddon/variant-hunter/blob/dev/src/client/src/main.rs
[prefab-cargo]: https://github.com/chrisgliddon/prefabuland/blob/main/Cargo.toml
[voxel-cargo]: https://github.com/chrisgliddon/voxelforge/blob/dev/crates/voxelforge-bevy/Cargo.toml
[paint-cargo]: https://github.com/chrisgliddon/ppw-paint/blob/main/Cargo.toml
[cards-cargo]: https://github.com/chrisgliddon/prefabuland-cards/blob/main/Cargo.toml
[go-cargo]: https://github.com/chrisgliddon/bevy-go/blob/main/Cargo.toml
[inindo-cargo]: https://github.com/chrisgliddon/inindo/blob/main/crates/inindo_bevy/Cargo.toml
[skills-tree]: https://github.com/chrisgliddon/bevy-skills/tree/b1b4da5744ebbd5c526342b2351967411cd5ca61
[skills-readme]: https://github.com/chrisgliddon/bevy-skills/blob/b1b4da5744ebbd5c526342b2351967411cd5ca61/README.md
[skills-claude]: https://github.com/chrisgliddon/bevy-skills/blob/b1b4da5744ebbd5c526342b2351967411cd5ca61/CLAUDE.md
[skills-router]: https://github.com/chrisgliddon/bevy-skills/blob/b1b4da5744ebbd5c526342b2351967411cd5ca61/skills/bevy/SKILL.md
[skills-hop17]: https://github.com/chrisgliddon/bevy-skills/blob/b1b4da5744ebbd5c526342b2351967411cd5ca61/skills/bevy-migration-0-17-to-0-18/SKILL.md
[skills-hop18]: https://github.com/chrisgliddon/bevy-skills/blob/b1b4da5744ebbd5c526342b2351967411cd5ca61/skills/bevy-migration-0-18-to-0-19/SKILL.md
[skills-lint]: https://github.com/chrisgliddon/bevy-skills/blob/b1b4da5744ebbd5c526342b2351967411cd5ca61/scripts/lint-skills.py
[skills-auditor]: https://github.com/chrisgliddon/bevy-skills/blob/b1b4da5744ebbd5c526342b2351967411cd5ca61/skills/bevy-rendering/scripts/audit_renderer_features.py
[skills-auditor-tests]: https://github.com/chrisgliddon/bevy-skills/blob/b1b4da5744ebbd5c526342b2351967411cd5ca61/skills/bevy-rendering/tests/test_audit_renderer_features.py
