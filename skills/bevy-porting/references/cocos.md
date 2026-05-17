# bevy-porting — Cocos Creator 3.x → Bevy 0.18

> Referenced from `bevy-porting/SKILL.md § Engine coverage`.

## Ecosystem context

"Cocos" refers to two engines: legacy **Cocos2d-x** (C++, mostly maintenance mode) and **Cocos Creator 3.x** (JavaScript/TypeScript, the current active product). This reference covers **Cocos Creator 3.x** — that's what most active projects use. Cocos Creator 2.x used a 2D-only model; 3.x supports both 2D and 3D with a unified TypeScript scripting API.

## Architectural shift

Cocos Creator uses a **node-tree with component scripts** (TypeScript classes extending `cc.Component`). Bevy is **ECS**. The split to make:

| Cocos Creator 3.x | Bevy 0.18 |
|---|---|
| `Node` | `Entity` + `Transform` |
| `cc.Component` (script) | Split: `#[derive(Component)]` data struct + `fn` system |
| `cc.director` (singleton) | `Resource` |
| `cc.game` / scene manager | `App` + scene loading via `AssetServer` |
| `cc.Node.on(event, cb)` | `EventWriter`/`EventReader` or `On<E>` observer |

## Lifecycle

| Cocos Creator | Bevy 0.18 |
|---|---|
| `onLoad()` | `Startup` schedule system or `Added<C>` query filter |
| `start()` | `Startup` (after `onLoad`) or first-frame check via `Local<bool>` |
| `update(dt: number)` | `Update` system with `time: Res<Time>` → `time.delta_secs()` |
| `lateUpdate(dt)` | `PostUpdate` system |
| `onDestroy()` | `On<Remove<C>>` observer |

```rust
// Cocos: update(dt: number) { this.node.position.x += this.speed * dt; }
// Bevy:
fn move_entities(mut query: Query<(&Speed, &mut Transform)>, time: Res<Time>) {
    for (speed, mut tf) in &mut query {
        tf.translation.x += speed.0 * time.delta_secs();
    }
}
```

## 2D and 3D primitives

| Cocos Creator 3.x | Bevy 0.18 |
|---|---|
| `Sprite` (2D) | `Sprite` component, texture via `Handle<Image>` |
| `MeshRenderer` (3D) | `Mesh3d` + `MeshMaterial3d<StandardMaterial>` |
| Built-in Chipmunk physics (2D) | `bevy_rapier2d` or `avian2d` |
| Built-in Bullet physics (3D) | `bevy_rapier3d` or `avian3d` |
| `Camera` component | `Camera2d` or `Camera3d` component |
| `DirectionalLight` | `DirectionalLight` component |

## Scenes and prefabs — JSON, no engine needed

Cocos Creator `.scene` and `.prefab` files are JSON. Parse them directly with stdlib — no script needed:

```python
import json, pathlib

data = json.loads(pathlib.Path("scene.scene").read_text())
for node in data.get("_objects", []):
    print(node.get("_name"), node.get("_position"))
```

The `_objects` array contains all nodes in the scene. Each entry includes `_name`, `_position`, `_rotation`, `_scale`, and a `__type__` key identifying the component class.

## Asset references — UUIDs and `.meta` files

Cocos Creator tracks assets via UUIDs stored in `.meta` JSON sidecar files — similar to Unity GUIDs. Bevy uses path-based `Handle<T>`s loaded via `AssetServer`. During a port, build a UUID → file-path lookup from the `.meta` files, then replace UUID references with `AssetServer::load("path/to/asset")` calls.

## TypeScript → Rust

The Cocos Creator scripting model is high-level (decorators, `async`/`await`, prototype-based OOP). Key translation patterns:

| TypeScript / Cocos pattern | Rust / Bevy pattern |
|---|---|
| `class PlayerCtrl extends cc.Component` | `#[derive(Component)] struct PlayerCtrl` + system fn |
| `@property` decorator fields | Plain fields on the component struct |
| `async/await` coroutines | `bevy_tasks::IoTaskPool` or `AsyncComputeTaskPool` |
| `cc.tween(...)` | `AnimatableCurve` + `bevy-animation` keyframes |
| `cc.Node.emit(event, data)` | `EventWriter<E>` |
| `cc.find("Path/To/Node")` | `Query` by component marker or `ChildOf` traversal |

Cross-link: **`bevy-core-concepts`** for schedules, `Time`, and the ECS mental model.

## Animation

| Cocos Creator 3.x | Bevy 0.18 |
|---|---|
| `AnimationClip` (keyframe tracks) | `AnimationClip` + `AnimationGraph` |
| `AnimationState` playback | `AnimationPlayer` + `AnimationTransitions::play` |
| `SkeletalAnimation` | Skeletal animation via glTF import |

Export skeletal models to glTF from Cocos Creator (or from DCC tools), then load with `bevy_gltf`. Cross-link: **`bevy-animation`**.

## UI

| Cocos Creator 3.x | Bevy 0.18 |
|---|---|
| `Canvas` (root UI node) | `Node` with `TargetCamera` |
| `Label` | `Text` component |
| `Sprite` (UI image) | `ImageNode` |
| `Button` | `Button` + `Interaction` |
| `Layout` (H/V/Grid) | `Node` + Taffy `FlexDirection` / `display: Grid` |
| `Widget` (anchors) | Taffy margin / align-self / position |

Cross-link: **`bevy-ui`**.

## Build and publish

| Cocos Creator 3.x | Bevy 0.18 |
|---|---|
| Build panel → Web Desktop/Mobile | `cargo build --target wasm32-unknown-unknown` |
| Build panel → Windows/macOS/Linux | `cargo build --release --target <triple>` |
| Build panel → Android/iOS | `cargo build` + platform SDK; cross-link `bevy-cargo-features` |

Cross-link: **`bevy-cargo-features`** for feature flags and target selection; **`bevy-wasm-webgpu`** for the WebAssembly build story.

## Gotchas

- Cocos Creator's scene JSON format changed between 2.x and 3.x — the `_objects` structure above applies to 3.x; 2.x uses a different key layout.
- `cc.game.addPersistRootNode` (cross-scene persistence) has no Bevy equivalent; use a `Resource` that persists across scene loads.
- Cocos Creator's built-in physics cannot be extracted; reconstruct physics bodies from the JSON `_components` arrays (look for `cc.RigidBody`, `cc.Collider` entries).
- TypeScript decorators like `@ccclass` are metadata only — they don't survive porting. The data they annotate becomes plain Rust struct fields.

## See also

- [`../SKILL.md`](../SKILL.md) — bevy-porting dispatcher
- `bevy-animation` — `AnimationGraph`, `AnimationTransitions`, glTF clip loading
- `bevy-ui` — `Node` + Taffy/flex, replacing Cocos UI components
- `bevy-wasm-webgpu` — Cocos web export → `wasm32-unknown-unknown`
