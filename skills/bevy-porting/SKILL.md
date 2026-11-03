---
name: bevy-porting
description: Use when porting a game project to Bevy 0.20 from another engine — Unity (Prefab, MonoBehaviour, Animator, UGUI), Unreal, Godot, Cocos, vanilla JavaScript / Phaser, Flash/SWF, Defold, Roblox, or GameMaker — and need a mapping of each engine's primitives to Bevy equivalents (`WorldAssetRoot`, `MessageWriter`, `ui_widgets::Button` + `Hovered`/`Pressed`, `AnimationGraph`, `AudioPlayer`), plus inventory/extraction scripts to pull assets out of the source project.
license: MIT
compatibility: opencode,claude-code,cursor
metadata:
  tier: "4"
  area: porting
  bevy_version: "0.20"
---

# Bevy 0.20 — Porting from other engines

## When to use this skill

- Starting a port of an existing game from Unity, Unreal, Godot, Cocos, vanilla JavaScript / Phaser, Flash/SWF, Defold, Roblox, or GameMaker into Bevy 0.20.
- Evaluating feasibility — does my engine's feature X have a Bevy equivalent in 0.20?
- Deciding which subsystem to port first (we recommend: rendering + a single playable slice).
- Extracting asset and scene data **from the source engine's project tree without needing the source engine installed** — see the `scripts/` policy below.
- Replacing engine-specific build pipelines (Unity Build Settings, Unreal Build Configuration, etc.) with `cargo` + `Cargo.toml` features.

## Engine coverage

| Engine | Coverage | Scripts |
|---|---|---|
| **Unity** | Deep (8 subsystem refs) — see § Unity below | 4 Python extractors in [`scripts/unity/`](scripts/unity/) |
| Unreal Engine 5 | [references/unreal.md](references/unreal.md) — Actor/Component → ECS, UMG → bevy_ui, Niagara/animation gaps | [`scripts/unreal/ue5_python_export.py`](scripts/unreal/ue5_python_export.py) (drops into UE5 editor) |
| Godot 4 | [references/godot.md](references/godot.md) — node-tree → ECS, `.tscn` text format, GDScript → Rust | [`scripts/godot/tscn_inventory.py`](scripts/godot/tscn_inventory.py) (stdlib, no Godot needed) |
| Cocos Creator 3 | [references/cocos.md](references/cocos.md) — TypeScript node-tree → ECS, JSON `.scene`/`.prefab` | inline Python recipe in the reference |
| Vanilla JavaScript / Canvas / HTML5 | [references/javascript.md](references/javascript.md) — class+rAF loops → ECS systems, Canvas 2D → `Sprite` | — (port is a rewrite, not extraction) |
| Phaser 3 | [references/phaser.md](references/phaser.md) — Scene/preload/update → systems, Arcade physics, tweens | — |
| Flash / SWF | [references/flash-swf.md](references/flash-swf.md) — `ffdec`-based extraction, AS3 → Rust rewrite | [`scripts/flash/swf_assets.py`](scripts/flash/swf_assets.py) (requires `ffdec` on PATH) |
| Defold | [references/defold.md](references/defold.md) — message-passing → Bevy `Message`s, Lua → Rust, 2D-first | inline Python recipe in the reference |
| Roblox | [references/roblox.md](references/roblox.md) — Instance tree → ECS, asset-ID extraction, Luau → Rust | [`scripts/roblox/rbxlx_inventory.py`](scripts/roblox/rbxlx_inventory.py) (XML `.rbxlx` only) |
| GameMaker Studio 2 | [references/gamemaker.md](references/gamemaker.md) — Object events → systems, JSON project files | [`scripts/gamemaker/gms2_inventory.py`](scripts/gamemaker/gms2_inventory.py) (stdlib, walks `.yyp`) |

## Unity (priority)

Unity is the deepest-covered engine. The eight subsystem references and four extraction scripts together cover an end-to-end port:

| Subsystem | Reference | Bevy primitives |
|---|---|---|
| Architecture (GameObject, MonoBehaviour, ScriptableObject, coroutines) | [references/unity-architecture.md](references/unity-architecture.md) | `Entity` + `ChildOf`, `Component` + `System`, `Asset`/`Resource`, async tasks |
| Asset pipeline (Prefab, Material, Addressables, GUIDs) | [references/unity-assets.md](references/unity-assets.md) | `Bundle`/spawn fn, `StandardMaterial`, `AssetServer` + `Handle<T>` |
| Scene → glTF extraction | [references/unity-scenes-gltf.md](references/unity-scenes-gltf.md) | `bevy_gltf`, `WorldAssetRoot`, `DynamicWorld`, glTFast / Blender bridge |
| Animator / Mecanim | [references/unity-animation.md](references/unity-animation.md) | `AnimationGraph`, `AnimationTransitions::play`, `#[derive(AnimationEvent)]` |
| Input System | [references/unity-input.md](references/unity-input.md) | `ButtonInput`, `Axis`, `Touches`, `Gamepad*`, `MessageReader` |
| UGUI / UI Toolkit | [references/unity-ui.md](references/unity-ui.md) | `Node`, `ui_widgets::Button` + `Hovered`/`Pressed`, `TextFont`/`FontSize`, Taffy/flex |
| Audio (`AudioSource`, `AudioListener`, mixers) | [references/unity-audio.md](references/unity-audio.md) | `AudioPlayer`, `SpatialListener`, `AudioSink` (`&mut`), `bevy_audio` |
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

## Names that changed since 0.18 (what stale LLM output looks like)

Every engine-mapping row in `references/` uses the right-hand column. If a tutorial or model emits the left-hand name, translate before porting.

| Stale (≤0.18) | Bevy 0.20 | Since |
|---|---|---|
| `SceneRoot(Handle<Scene>)`, `DynamicScene`, `bevy::scene::*` (old) | `WorldAssetRoot(Handle<WorldAsset>)`, `DynamicWorld`, `bevy::world_serialization::*`; `bevy::scene` is BSN (`bsn!`, `@` refs) | 0.19 / 0.20 |
| `EventWriter`/`EventReader`, `#[derive(Event)]` for buffered events | `MessageWriter::write` / `MessageReader`, `#[derive(Message)]` | 0.17 |
| `Trigger<OnAdd, C>`, `On<Add, C>`, `commands.trigger_targets(e, entity)` | `On<Add<C>>`, `#[derive(EntityEvent)]` + `commands.trigger(E { entity })` | 0.17 / 0.20 |
| `Replace` lifecycle, `on_replace` | `Discard`, `on_discard` | 0.19 |
| `Button` + `Interaction` (`Changed<Interaction>`) | `ui_widgets::Button` + `Hovered(bool)` + `Has<Pressed>`, `On<Activate>` | 0.20 |
| `TextFont { font: Handle<Font>, font_size: f32 }` | `TextFont { font: FontSource, font_size: FontSize::Px(..) }` | 0.19 |
| `TargetCamera` | `UiTargetCamera` | pre-0.19 |
| `On<Pointer<Click>>` | `On<PointerClick>` (flat pointer events) | 0.20 |
| `AmbientLight` resource | `GlobalAmbientLight` resource; `AmbientLight` is a per-camera component | 0.19 |
| `sink.set_volume(..)` on `&AudioSink` | needs `&mut AudioSink`; `Volume::Linear(x)` / `Volume::Decibels(x)` | pre-0.19 |
| `#import bevy_pbr::…` / `#ifdef` in `.wgsl` | WESL: `import bevy_pbr::render::…;`, `@if(..)`, `.wesl` | 0.20 |
| `Sprite` on its own batcher | `Sprite` renders through `Mesh2d` + `SpriteMaterial`; new `alpha_mode` field | 0.20 |
| `NextState::set_if_neq` | `NextState::set_if_different` | 0.20 |

## Scripts policy

`scripts/<engine>/` contains runnable, single-file Python helpers that extract data from the source engine's project tree. The convention for this collection:

- **Stdlib-only when possible.** Unity's YAML is parsed with `re` not `pyyaml` — easier to install.
- **No source engine required.** All Unity scripts read text-format `.unity`/`.prefab`/`.anim`/`.meta` files directly. Engines whose files are binary (Roblox `.rbxl`, parts of GMS2) get a recipe in their reference instead.
- **Inventory + extraction, not auto-conversion.** None of these scripts produce a Bevy project. They give you JSON so you (or a downstream tool) know what to port. Treat them as `tree` + `file` + `stat` for game projects.
- **Reference-backed.** Each script names its matching reference in its top-of-file docstring.

## Gotchas

- **One-shot ports don't work.** Allocate time proportional to your project's content size, not its code size.
- **Prefab semantics don't transfer.** Unity's "Prefab + Variant + Nested Prefab" inheritance has no direct Bevy equivalent. Bake to glTF for visual prefabs (`WorldAssetRoot`); write spawn functions or `bsn!` templates for data prefabs.
- **Animation retargeting is engine-specific.** Mecanim Humanoid retargeting in particular has no out-of-the-box Bevy equivalent — see `references/unity-animation.md`.
- **Coordinate-system flips silent-fail.** Most exporters handle them, but always spot-check.
- **Editor scripts are out of scope.** Unity `[CustomEditor]`, Unreal Blueprints' editor tooling, Godot tool scripts — none translate. Bevy 0.20 ships Feathers widgets and `PanOrbitCamera` for editor-style tools, but no shipped scene editor; for porting, runtime-only.
- **Don't replicate engine-internal IDs.** Unity GUIDs, Unreal FNames, Godot RIDs, Roblox InstanceIDs — these are sidecar metadata only useful during extraction. Bevy uses path-based handles and ECS entity IDs.
- **`ui` and `audio` are not implied by `3d`/`2d` (0.19).** A port that trims `default-features` must add `ui` and `audio` explicitly or buttons and `AudioPlayer` silently never run.
- **Community crate versions move with Bevy.** Verified for 0.20 (2026-11): `bevy_rapier3d` 0.37, `avian3d` 0.8, `bevy_hanabi` 0.20, `leafwing-input-manager` 0.22, `bevy_asset_loader` 0.28, `bevy_ecs_tilemap` 0.20, `bevy_kira_audio` 0.27, `bevy-persistent` 0.12, `bevy_hui` 0.8. Still on older Bevy: `bevy_prototype_lyon` 0.17 (0.19), `bevy_cobweb_ui` 0.22 (0.17).

## See also

- [`bevy`](../bevy/SKILL.md) — router; pins Bevy 0.20 and indexes every sibling skill.
- [`bevy-animation`](../bevy-animation/SKILL.md) — `AnimationGraph`, `AnimationTransitions`, `#[derive(AnimationEvent)]`. Cross-linked from `unity-animation.md`.
- [`bevy-ui`](../bevy-ui/SKILL.md) — `Node` + Taffy/flex model, `ui_widgets::Button`. Cross-linked from `unity-ui.md`.
- [`bevy-cargo-features`](../bevy-cargo-features/SKILL.md) — replaces Unity Build Settings / PlayerSettings.
- [`bevy-wasm-webgpu`](../bevy-wasm-webgpu/SKILL.md) — Unity WebGL → wasm32 / WebGPU port story.
- [`bevy-cameras`](../bevy-cameras/SKILL.md) — `RenderTarget` as a component, camera modes; close to Unity Camera component.
- [`bevy-migration-0-19-to-0-20`](../bevy-migration-0-19-to-0-20/SKILL.md) and [`bevy-migration-0-18-to-0-19`](../bevy-migration-0-18-to-0-19/SKILL.md) — full rename lists behind the table above.
