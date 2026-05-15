---
name: bevy-porting
description: Use when porting a game project to Bevy 0.18 from another engine — Unity (Prefab, MonoBehaviour, Animator, UGUI), Unreal, Godot, Cocos, vanilla JavaScript / Phaser, Flash/SWF, Defold, Roblox, or GameMaker — and need a mapping of each engine's primitives to Bevy equivalents, plus inventory/extraction scripts to pull assets out of the source project.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "4"
  area: porting
  bevy_version: "0.18"
---

# Bevy 0.18 — Porting from other engines

## When to use this skill

- Starting a port of an existing game from Unity, Unreal, Godot, Cocos, vanilla JavaScript / Phaser, Flash/SWF, Defold, Roblox, or GameMaker into Bevy 0.18.
- Evaluating feasibility — does my engine's feature X have a Bevy equivalent in 0.18?
- Deciding which subsystem to port first (we recommend: rendering + a single playable slice).
- Extracting asset and scene data **from the source engine's project tree without needing the source engine installed** — see the `scripts/` policy below.
- Replacing engine-specific build pipelines (Unity Build Settings, Unreal Build Configuration, etc.) with `cargo` + `Cargo.toml` features.

## Engine coverage

| Engine | Coverage | Scripts |
|---|---|---|
| **Unity** | Deep (8 subsystem refs) — see § Unity below | 4 Python extractors in `scripts/unity/` |
| Unreal Engine 5 | _coming in PR B_ | — |
| Godot 4 | _coming in PR B_ | — |
| Cocos Creator | _coming in PR B_ | — |
| Vanilla JavaScript / Canvas / HTML5 | _coming in PR B_ | — |
| Phaser 3 | _coming in PR B_ | — |
| Flash / SWF | _coming in PR B_ | — |
| Defold | _coming in PR B_ | — |
| Roblox | _coming in PR B_ | — |
| GameMaker Studio 2 | _coming in PR B_ | — |

PR B (already planned) will ship the nine non-Unity engines and fill in this table.

## Unity (priority)

Unity is the deepest-covered engine. The eight subsystem references and four extraction scripts together cover an end-to-end port:

| Subsystem | Reference | Bevy primitives |
|---|---|---|
| Architecture (GameObject, MonoBehaviour, ScriptableObject, coroutines) | [references/unity-architecture.md](references/unity-architecture.md) | `Entity` + `ChildOf`, `Component` + `System`, `Asset`/`Resource`, async tasks |
| Asset pipeline (Prefab, Material, Addressables, GUIDs) | [references/unity-assets.md](references/unity-assets.md) | `Bundle`/spawn fn, `StandardMaterial`, `AssetServer` + `Handle<T>` |
| Scene → glTF extraction | [references/unity-scenes-gltf.md](references/unity-scenes-gltf.md) | `bevy_gltf`, `DynamicScene`, glTFast / Blender bridge |
| Animator / Mecanim | [references/unity-animation.md](references/unity-animation.md) | `AnimationGraph`, `AnimationTransitions::play`, `#[derive(AnimationEvent)]` |
| Input System | [references/unity-input.md](references/unity-input.md) | `ButtonInput`, `Axis`, `Touches`, `Gamepad*` |
| UGUI / UI Toolkit | [references/unity-ui.md](references/unity-ui.md) | `Node`, `BackgroundColor`, `BorderColor`, Taffy/flex |
| Audio (`AudioSource`, `AudioListener`, mixers) | [references/unity-audio.md](references/unity-audio.md) | `AudioPlayer`, `SpatialListener`, `bevy_audio` |
| Build / deploy (Build Settings, IL2CPP, WebGL) | [references/unity-build.md](references/unity-build.md) | `cargo build --target`, `Cargo.toml` features, WASM |

Extraction scripts (all stdlib-Python, no Unity install required):

| Script | What it does |
|---|---|
| [`scripts/unity/scene_inventory.py`](scripts/unity/scene_inventory.py) | Parse `.unity` YAML → JSON inventory of GameObjects + transforms + components |
| [`scripts/unity/prefab_inspector.py`](scripts/unity/prefab_inspector.py) | Parse `.prefab` YAML → component graph per prefab |
| [`scripts/unity/animation_extractor.py`](scripts/unity/animation_extractor.py) | Parse `.anim` YAML → keyframe JSON, formatted for `AnimatableKeyframeCurve::new([...])` |
| [`scripts/unity/asset_audit.py`](scripts/unity/asset_audit.py) | Walk `Assets/` → inventory by type, size, GUID, and (optionally) dependency graph |

Run each script with `--help` to see all flags. Each script's docstring points to the matching reference.

## General porting principles

These show up regardless of source engine:

1. **The ECS shift.** Engines other than Bevy mostly use a scene-graph + scripts model (one class = data + behaviour on one node). Bevy is data-oriented: data lives in `Component`s, behaviour in free `fn` `System`s. Don't try to recreate `MonoBehaviour` / `Actor` / `Node` as one Rust struct; split it.
2. **Port the smallest playable slice first.** A single character moving in a single scene with one input + one animation. Once that compiles and runs, the rest is iteration. Avoid trying to "port everything in parallel."
3. **Asset pipelines are the long pole.** Code ports faster than assets. Schedule asset extraction first; have a content pipeline producing glTF + KTX2 + audio formats before you start writing gameplay code.
4. **Fixed-timestep mindset.** Most engines hide the variable-vs-fixed timestep choice. Bevy makes it explicit: physics in `FixedUpdate`, rendering in `Update`, interpolation via `Time<Fixed>`. Decide early which systems live where — see `bevy-core-concepts` and `bevy-animation/references/procedural-animation.md`.
5. **Coordinate-system flips.** Unity is left-handed Y-up; Unreal is left-handed Z-up; Godot is right-handed Y-up; Bevy is right-handed Y-up (matches glTF). Most exporters handle the flip; spot-check by importing a scene with a known-asymmetric directional asset and confirming it isn't mirrored.

## Scripts policy

`scripts/<engine>/` contains runnable, single-file Python helpers that extract data from the source engine's project tree. The convention for this collection:

- **Stdlib-only when possible.** Unity's YAML is parsed with `re` not `pyyaml` — easier to install.
- **No source engine required.** All Unity scripts read text-format `.unity`/`.prefab`/`.anim`/`.meta` files directly. Engines whose files are binary (Roblox `.rbxl`, parts of GMS2) get a recipe in their reference instead.
- **Inventory + extraction, not auto-conversion.** None of these scripts produce a Bevy project. They give you JSON so you (or a downstream tool) know what to port. Treat them as `tree` + `file` + `stat` for game projects.
- **Reference-backed.** Each script names its matching reference in its top-of-file docstring.

## Gotchas

- **One-shot ports don't work.** Allocate time proportional to your project's content size, not its code size.
- **Prefab semantics don't transfer.** Unity's "Prefab + Variant + Nested Prefab" inheritance has no direct Bevy equivalent. Bake to glTF for visual prefabs; write spawn functions for data prefabs.
- **Animation retargeting is engine-specific.** Mecanim Humanoid retargeting in particular has no out-of-the-box Bevy equivalent — see `references/unity-animation.md`.
- **Coordinate-system flips silent-fail.** Most exporters handle them, but always spot-check.
- **Editor scripts are out of scope.** Unity `[CustomEditor]`, Unreal Blueprints' editor tooling, Godot tool scripts — none translate. Bevy's editor story is in flux; for porting, runtime-only.
- **Don't replicate engine-internal IDs.** Unity GUIDs, Unreal FNames, Godot RIDs, Roblox InstanceIDs — these are sidecar metadata only useful during extraction. Bevy uses path-based handles and ECS entity IDs.

## See also

- [`bevy`](../bevy/SKILL.md) — router; pins Bevy 0.18 and indexes every sibling skill.
- [`bevy-animation`](../bevy-animation/SKILL.md) — `AnimationGraph`, `AnimationTransitions`, `#[derive(AnimationEvent)]`. Cross-linked from `unity-animation.md`.
- [`bevy-ui`](../bevy-ui/SKILL.md) — `Node` + Taffy/flex model. Cross-linked from `unity-ui.md`.
- [`bevy-cargo-features`](../bevy-cargo-features/SKILL.md) — replaces Unity Build Settings / PlayerSettings.
- [`bevy-wasm-webgpu`](../bevy-wasm-webgpu/SKILL.md) — Unity WebGL → wasm32 / WebGPU port story.
- [`bevy-cameras`](../bevy-cameras/SKILL.md) — `RenderTarget` as a component (0.18), camera modes; close to Unity Camera component.
- [`bevy-migration-0-17-to-0-18`](../bevy-migration-0-17-to-0-18/SKILL.md) — useful if you find a tutorial pinned to a pre-0.18 release.
