```text
               ++
             +++++++
            ++++ +++++
            ++++ ++++            +++++++++    ++++++++++ +++       +++  +++      +++
            ++++++++ ++         +++++++++++   ++++++++++ ++++      ++++ ++++     ++++
     ++++++++++++++ ++++        ++++++++++++ +++++++++++ ++++     +++++ +++++   +++++
     +++++++++++++++ +  +       ++++   +++++ ++++++++++  +++++    +++++ +++++   +++++
      ++++++++++++++ +  ++      ++++    ++++ +++++       +++++    +++++  +++++ +++++
        +++++++++++++ +++++     ++++    ++++ +++++        ++++    ++++    ++++ +++++
     ++++++++++++++++ ++        ++++++++++++ ++++++++++   +++++  +++++    +++++++++
   +++++++++++++++++++ +        +++++++++++  ++++++++++   +++++  +++++     +++++++
  ++++++++++++++++++++          ++++++++++++ ++++++++++    ++++  ++++      +++++++
 +++++++++++++++++++++          ++++++++++++ ++++++++++    ++++  ++++       +++++
+++++++++++++++++++++ +         ++++    ++++++++++         ++++++++++       +++++
           ++++++++++ +         ++++    ++++++++++          ++++++++         ++++
            ++++++++            +++++  +++++++++++++++++    ++++++++         ++++
             +++++++ +          ++++++++++++ +++++++++++     +++++++        +++++
            +++++++             ++++++++++++  ++++++++++     ++++++          ++++
           +++++++               +++++++++    ++++++++++      ++++           ++++
        ++++++++
    +++++++++
     +++
```

# Bevy Skills

AI agent skills with a **Bevy 0.19 general baseline**, a staged **Bevy 0.20 migration and Rapier 0.37 physics update**, and **Rust maintainability tooling**. Teach Claude Code, OpenCode, Cursor, Codex, and Pi the right Bevy ECS, asset, rendering, physics, input, audio, accessibility, persistence, testing, profiling, and migration patterns — plus how to keep the codebase clean as it grows — without re-prompting them every session.

> **For AI agents:** Load `skills/bevy/SKILL.md` first and inspect the project’s Bevy version before choosing guidance. Do not treat every skill in this collection as Bevy 0.20-compatible.

Inspired by [pixijs/pixijs-skills](https://github.com/pixijs/pixijs-skills). MIT-licensed so any agent or project can consume the skills.

## What this is

Each skill is a folder under `skills/<skill-name>/` containing a `SKILL.md` with YAML frontmatter the agent uses to auto-load it on relevant tasks. The body is a tight, version-pinned reference for that one concept.

The repository ships strict frontmatter linting and focused Python tests for bundled
scripts. Rust compilation is a separate verification layer: the documented companion
[`bevy-skills-tester`](https://github.com/chrisgliddon/bevy-skills-tester) is not vendored
here, and no blanket snippet-compile or runtime guarantee is made by these checks.

## Version coverage

| Project version | Guidance to use | Status |
|---|---|---|
| Bevy 0.19 | General implementation skills; version-pinned 0.19 physics baseline linked from the router | Existing baseline; not revalidated wholesale by the 0.20 update |
| Bevy 0.20 | [0.19→0.20 migration](skills/bevy-migration-0-19-to-0-20/SKILL.md) and [Rapier 0.37 physics](skills/bevy-physics/SKILL.md) | Staged, source-reviewed guidance; not full-collection compile/runtime certification |
| Bevy 0.17 / 0.18 | The matching historical migration skill, one hop at a time | Historical target pins are preserved |
| Unknown, inherited, mixed, or other versions | Resolve `Cargo.toml`, workspace dependencies, and `Cargo.lock` first | Do not guess a target or silently apply another version’s APIs |

Other implementation skills, including rendering and cameras, still target 0.19.
A cross-link from a 0.20 skill does not certify the linked examples for 0.20.
See [0.20 readiness and remaining gates](docs/bevy-020-readiness.md) for evidence and
limits. Plugin release metadata remains on the 0.19 line until broader validation.

## Install

| Agent | Skill directory | Setup |
|---|---|---|
| Claude Code | `~/.claude/skills/` | `/plugin marketplace add chrisgliddon/bevy-skills` |
| OpenCode | `~/.config/opencode/skills/` *or* `~/.claude/skills/` | Clone and symlink `skills/` → one of those paths |
| Cursor | `~/.cursor/skills/` | Mirror the `.cursor-plugin/` files or copy `skills/` |
| OpenAI Codex | `~/.codex/skills/` | Copy `skills/` |
| Pi | `~/.pi/agent/skills/` | Copy `skills/` |

Universal route (auto-detects your agent):

```bash
npx skills add https://github.com/chrisgliddon/bevy-skills
```

OpenCode reads `~/.claude/skills/` natively — no duplication needed if both agents are installed.

## The collection

> **Where to start.** Read the router first. For the Bevy 0.19 general baseline, these are the foundation:
>
> 1. **[`bevy`](skills/bevy/SKILL.md)** — router. Tells you which sibling skill applies to your task.
> 2. **[`bevy-core-concepts`](skills/bevy-core-concepts/SKILL.md)** — `App`, `Plugin`, schedules. Without this, the rest won't make sense.
> 3. **[`bevy-ecs-components`](skills/bevy-ecs-components/SKILL.md)** + **[`bevy-ecs-queries`](skills/bevy-ecs-queries/SKILL.md)** + **[`bevy-ecs-systems`](skills/bevy-ecs-systems/SKILL.md)** — the ECS triangle. Read all three before writing your first system.
>
> Migrating? Read [`bevy-migration-0-19-to-0-20`](skills/bevy-migration-0-19-to-0-20/SKILL.md) for the latest hop, or the preserved [0.18→0.19](skills/bevy-migration-0-18-to-0-19/SKILL.md) / [0.17→0.18](skills/bevy-migration-0-17-to-0-18/SKILL.md) guide for your starting version.

| Skill | One-line trigger |
|---|---|
| [`bevy`](skills/bevy/SKILL.md) | Version-aware router for the 0.19 baseline and staged 0.20 guidance. Read first. |
| [`bevy-core-concepts`](skills/bevy-core-concepts/SKILL.md) | App, Plugin, Schedule, World, `Update` vs `FixedUpdate`, exclusive systems. |
| [`bevy-input-actions`](skills/bevy-input-actions/SKILL.md) | Rebindable logical actions, entity gamepads, hot-plug, deadzones, Steam Deck, and frame-to-fixed buffering. |
| [`bevy-testing`](skills/bevy-testing/SKILL.md) | Deterministic `App`/time stepping, fixed schedules, messages/observers, async draining, headless and visual tests. |
| [`bevy-ecs-components`](skills/bevy-ecs-components/SKILL.md) | `#[derive(Component)]`, `#[require(...)]`, observers (`On<E>`), hooks, storage. |
| [`bevy-ecs-queries`](skills/bevy-ecs-queries/SKILL.md) | `Query<D, F>`, filters, change detection, `par_iter`, lenses, and 0.19 generic bounds. |
| [`bevy-ecs-systems`](skills/bevy-ecs-systems/SKILL.md) | `SystemParam`, `SystemSet`, run conditions, ordering, state schedules, and runtime removal. |
| [`bevy-cargo-features`](skills/bevy-cargo-features/SKILL.md) | `2d`/`3d`/`ui` collections, `2d_api`/`3d_api`/`ui_api`, feature renames, WASM trim. |
| [`bevy-migration-0-19-to-0-20`](skills/bevy-migration-0-19-to-0-20/SKILL.md) | Bevy 0.20 migration, API/behavior checks, and the published Rapier 0.37 dependency path. |
| [`bevy-migration-0-18-to-0-19`](skills/bevy-migration-0-18-to-0-19/SKILL.md) | High-impact 0.18 → 0.19 changes: text/font (`FontSource`/`FontSize`), `bevy_world_serialization`, resources-as-components. |
| [`bevy-migration-0-17-to-0-18`](skills/bevy-migration-0-17-to-0-18/SKILL.md) | High-impact 0.17 → 0.18 changes and rename catalogue. |
| [`bevy-wasm-webgpu`](skills/bevy-wasm-webgpu/SKILL.md) | WASM build pipeline, WebGL2 vs WebGPU, bundle trimming. |
| [`bevy-assets`](skills/bevy-assets/SKILL.md) | `AssetServer`, `Handle`, hot-reload, `AssetPath`, `SeekableReader`, and glTF world instances. |
| [`bevy-custom-assets`](skills/bevy-custom-assets/SKILL.md) | `AssetLoader`, `load_builder`, dependency tracking, and required `Reader::seekable`. |
| [`bevy-save-load`](skills/bevy-save-load/SKILL.md) | Stable IDs, versioned DTOs/migrations, atomic native/browser writes, snapshots and sparse deltas. |
| [`bevy-cameras`](skills/bevy-cameras/SKILL.md) | `Camera3d`, render targets, free/pan controls, and third-person orbit/obstruction. |
| [`bevy-rendering`](skills/bevy-rendering/SKILL.md) | Built-in vs external/headless rendering, forward/deferred, render systems, and the Rapier physics boundary. |
| [`bevy-diagnostics-profiling`](skills/bevy-diagnostics-profiling/SKILL.md) | Custom diagnostics, tracing, render CPU/GPU timings, async telemetry, and platform acceptance budgets. |
| [`bevy-physics`](skills/bevy-physics/SKILL.md) | Bevy 0.20 / Rapier 0.37 bodies, colliders, fixed-step ordering, messages, queries, controllers, and migration gotchas. |
| [`bevy-pbr-materials`](skills/bevy-pbr-materials/SKILL.md) | `StandardMaterial`, custom `Material`, meshes, lights, shadows, and atmosphere. |
| [`bevy-animation`](skills/bevy-animation/SKILL.md) | glTF clips, `AnimationGraph`, transitions, masks, events, tweening, and procedural animation. |
| [`bevy-vfx`](skills/bevy-vfx/SKILL.md) | Hanabi 0.19 particles, shaders, Gaussian splats, and compatible non-Hanabi effects. |
| [`bevy-audio`](skills/bevy-audio/SKILL.md) | `AudioPlayer`, sinks, spatial listeners, mix/transition policy, browser unlock, and Seedling 0.8 boundary. |
| [`bevy-voxel-data`](skills/bevy-voxel-data/SKILL.md) | Immutable serialized block IDs, dense runtime palettes, KTX2 atlas baking, and explicit storage estimates. |
| [`bevy-voxel-pipeline`](skills/bevy-voxel-pipeline/SKILL.md) | `block-mesh-rs` integration, greedy quads, and pure worker-side mesh generation. |
| [`bevy-voxel-runtime`](skills/bevy-voxel-runtime/SKILL.md) | Dirty/halo fan-out, revision tokens, stale rejection, coalesced priority queues, bounded mesh/collider swaps. |
| [`bevy-capture`](skills/bevy-capture/SKILL.md) | Record cameras to MP4 (`Mp4Openh264Encoder`, ffmpeg-CLI) or PNG sequences (`FramesEncoder`). |
| [`bevy-fluent`](skills/bevy-fluent/SKILL.md) | `es-fluent-manager-bevy` i18n: `FluentText<T>`, `BevyFluentText`, `LocaleChangeEvent`, `i18n.toml`. |
| [`bevy-ui`](skills/bevy-ui/SKILL.md) | `Node`, `Button`, `Interaction`, `children![]`, `TextFont`, `InputFocus`, `BorderRadius`, `BackgroundColor`. |
| [`bevy-a11y`](skills/bevy-a11y/SKILL.md) | High-standard game accessibility: screen readers, adaptive controllers, remapping, captions, contrast, motion safety, and evidence. |
| [`bevy-porting`](skills/bevy-porting/SKILL.md) | Port Unity, Unreal, Godot, Cocos, Phaser/JS, Flash, Defold, Roblox, or GameMaker projects to Bevy. |
| [`similarity-rs`](skills/similarity-rs/SKILL.md) | Detect copy-paste and near-duplicate Rust code before committing. `--cross-file`, `--threshold`, CI recipes. |

## Quick reference — smallest valid Bevy 0.19 app

```rust
use bevy::prelude::*;

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_systems(Startup, setup)
        .run();
}

fn setup(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
) {
    commands.spawn((
        Mesh3d(meshes.add(Cuboid::new(1.0, 1.0, 1.0))),
        MeshMaterial3d(materials.add(StandardMaterial {
            base_color: Color::srgb(0.4, 0.7, 0.9),
            ..default()
        })),
    ));
    commands.spawn((
        Camera3d::default(),
        Transform::from_xyz(0.0, 2.0, 4.0).looking_at(Vec3::ZERO, Vec3::Y),
    ));
    commands.spawn((
        DirectionalLight::default(),
        Transform::from_xyz(2.0, 4.0, 2.0).looking_at(Vec3::ZERO, Vec3::Y),
    ));
}
```

`Cargo.toml`:

```toml
[dependencies]
bevy = "0.19"
```

## Repo structure

```
bevy-skills/
├── .claude-plugin/        # Claude Code marketplace + plugin manifest
├── .cursor-plugin/        # Cursor mirror
├── .github/
│   └── copilot-instructions.md
├── skills/
│   ├── bevy/              # router (read first)
│   ├── bevy-core-concepts/
│   ├── bevy-input-actions/
│   ├── bevy-testing/
│   ├── bevy-ecs-components/
│   ├── bevy-ecs-queries/
│   ├── bevy-ecs-systems/
│   ├── bevy-cargo-features/
│   ├── bevy-migration-0-19-to-0-20/
│   ├── bevy-migration-0-18-to-0-19/
│   ├── bevy-migration-0-17-to-0-18/
│   ├── bevy-wasm-webgpu/
│   ├── bevy-assets/
│   ├── bevy-custom-assets/
│   ├── bevy-save-load/
│   ├── bevy-cameras/
│   ├── bevy-rendering/
│   ├── bevy-diagnostics-profiling/
│   ├── bevy-physics/
│   ├── bevy-pbr-materials/
│   ├── bevy-animation/
│   ├── bevy-vfx/
│   ├── bevy-audio/
│   ├── bevy-ui/
│   ├── bevy-a11y/
│   ├── bevy-capture/
│   ├── bevy-fluent/
│   ├── bevy-porting/
│   ├── bevy-voxel-pipeline/
│   ├── bevy-voxel-data/
│   ├── bevy-voxel-runtime/
│   └── similarity-rs/
├── docs/
│   └── bevy-020-readiness.md # staged coverage and remaining validation gates
├── scripts/
│   └── lint-skills.py     # validates SKILL.md frontmatter
├── AGENTS.md              # if you landed here as an AI agent
├── CLAUDE.md              # editor guidance: how to add or change a skill
├── LICENSE                # MIT
└── README.md              # you are here
```

## Editing or adding a skill

Read [`CLAUDE.md`](CLAUDE.md). The hard rules:

1. Every skill description names its actual target. The general baseline is
   `Bevy 0.19`; staged 0.20 and historical skills use `metadata.target_version`.
2. New or changed Rust snippets require a matching fixture compiled against that
   target and its plugin versions before claiming compile coverage. Use the documented
   `bevy-skills-tester/examples/<skill_name>.rs` layout (hyphens → underscores).
3. `python3 scripts/lint-skills.py --strict` is clean; run affected Python tests.

If the Rust toolchain or companion is unavailable, record that verification gap and
keep the PR in draft. Lint and Python tests are not Rust compile evidence.

## Maintenance cadence

- **Quarterly Bevy release:** Add the migration hop, verify dependency compatibility, and migrate skills in validated slices. Preserve historical pins; change the general baseline and plugin metadata only after the intended compile/runtime matrix passes.
- **Continuous:** When a real-world Bevy gotcha hits, add it to the most relevant skill's Gotchas section. The collection grows from friction, not anticipation.

## License

MIT. See [`LICENSE`](LICENSE).
