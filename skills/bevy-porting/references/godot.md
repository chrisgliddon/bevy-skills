# bevy-porting — Godot 4 → Bevy 0.18

> Referenced from `bevy-porting/SKILL.md § Engine coverage`.

## Architectural shift

Godot 4 is a **scene-tree engine**: every `Node` has a parent and may have children; behaviour is attached via GDScript, C#, or C++ subclasses on those nodes.

Bevy is **ECS**: entities are flat (parent-child via the `ChildOf` component) and behaviour lives in free system functions. Don't recreate the Node class hierarchy — split each Node into a `Component` (data) + one or more systems (behaviour).

Coordinate system: Godot is **right-handed Y-up** — same as Bevy and glTF. Axis conventions match; no flip needed for most exports.

## Node type map

| Godot 4 | Bevy 0.18 |
|---|---|
| `Node2D` | `Entity` + `Transform` (2D: `Camera2d` + 2D mesh) |
| `Node3D` | `Entity` + `Transform` |
| `Sprite2D` | `Sprite` component, texture via `Handle<Image>` |
| `MeshInstance3D` | `Mesh3d` + `MeshMaterial3d<StandardMaterial>` |
| `Camera3D` | `Camera3d` component |
| `DirectionalLight3D` | `DirectionalLight` component |
| `CharacterBody3D` | No built-in; use `bevy_rapier3d` or `avian3d` |
| `Area3D` | Collider sensor in `bevy_rapier3d` / `avian3d` |
| `AnimationPlayer` | `AnimationPlayer` (Bevy — same name, different API) |
| `AnimationTree` | `AnimationGraph` + blend nodes |

## `.tscn` and `.tres` — text formats, no engine needed

Godot scene (`.tscn`) and resource (`.tres`) files are plain text. Use **`scripts/godot/tscn_inventory.py`** to parse them without a Godot install:

```
python3 tscn_inventory.py levels/World.tscn --out world.json
python3 tscn_inventory.py levels/World.tscn --resolve-resources --out world_resolved.json
```

## GDScript → Rust

| Godot 4 | Bevy 0.18 |
|---|---|
| `_process(delta: float)` | `Update` system with `time: Res<Time>` |
| `_physics_process(delta)` | `FixedUpdate` system with `Time<Fixed>` |
| `_ready()` | `Startup` schedule or `Added<C>` query filter |
| `_exit_tree()` | `On<Remove<C>>` observer |
| `@onready var n = $Path/To/Node` | `Query` filter / `entity` lookup by component |
| `get_node("../Sibling")` | Hierarchy traversal via `ChildOf` + `Children` |

```rust
// Godot: func _process(delta): position.x += speed * delta
// Bevy:
fn move_entities(mut query: Query<(&Speed, &mut Transform)>, time: Res<Time>) {
    for (speed, mut tf) in &mut query {
        tf.translation.x += speed.0 * time.delta_secs();
    }
}
```

## Signals → Bevy events / observers

Godot signals are typed pub/sub. Bevy 0.18 equivalents:

- **One-to-many fire-and-forget** → `EventWriter<E>` / `EventReader<E>`.
- **Entity-targeted reactions** → `On<E>` observer triggered via `commands.trigger_targets(e, entity)`.

Cross-link: **`bevy-ecs-systems`** (event and observer patterns).

```rust
// Godot: signal health_depleted(); emit_signal("health_depleted")
// Bevy:
#[derive(Event)] struct HealthDepleted { entity: Entity }

fn check_health(
    query: Query<(Entity, &Health)>,
    mut writer: EventWriter<HealthDepleted>,
) {
    for (entity, health) in &query {
        if health.current <= 0.0 { writer.send(HealthDepleted { entity }); }
    }
}
```

## Animation

Both engines use a component named `AnimationPlayer`, but the APIs differ:

| Godot 4 | Bevy 0.18 |
|---|---|
| `AnimationPlayer` runs tracks on node properties | `AnimationPlayer` drives curves on `Entity` components |
| `AnimationTree` blend tree | `AnimationGraph` with blend nodes |
| State machine layer | `AnimationTransitions` + state-driving system |

**Migration path:** export to glTF via Godot's built-in **File → Export → glTF 2.0** exporter, then load with `bevy_gltf`. Animation clips are preserved in the glTF. Cross-link: **`bevy-animation`**.

## Resources (`.tres`) → Bevy `Asset`

Godot custom `Resource` subclasses map to Bevy `Asset<T>` types loaded via `AssetServer`. Implement `AssetLoader` for custom binary resources; for the text `.tres` format, parse to a struct and use a custom loader or `AssetServer::load` with a `.ron` sidecar.

Cross-link: **`bevy-custom-assets`**.

## UI: Control nodes → `bevy_ui`

Godot's Container/Control system already uses a CSS-like model (size flags, anchor presets, minimum size). The mapping to Bevy's `Node` + Taffy flexbox is closer than Unity's UGUI:

| Godot 4 | Bevy 0.18 |
|---|---|
| `VBoxContainer` | `Node` with `FlexDirection::Column` |
| `HBoxContainer` | `Node` with `FlexDirection::Row` |
| `Label` | `Text` component |
| `TextureRect` | `ImageNode` |
| `Button` | `Button` + `Interaction` component |

Cross-link: **`bevy-ui`**.

## Project export

| Godot 4 | Bevy 0.18 |
|---|---|
| Export presets (Desktop) | `cargo build --release --target <triple>` |
| `--headless` export | CI `cargo build` with env vars |
| Web export | `wasm32-unknown-unknown` + `wasm-bindgen` |

WebAssembly: cross-link **`bevy-wasm-webgpu`**.

## Gotchas

- Godot's `NodePath` and `RID` are internal runtime IDs — do not port them. Use `Entity` IDs and Bevy path handles.
- GDScript duck typing has no Rust equivalent; plan for a strict typing pass during port.
- `CharacterBody3D`'s `move_and_slide` is built into Godot's physics; replicate with a physics plugin + a custom move system.
- `@export` variables (inspector-editable fields) have no direct Bevy runtime equivalent; store in a `Resource` or component with `Reflect` for `bevy_editor` inspection.
- Godot 4's GDExtension C++ API is not relevant to a Bevy port — focus on the GDScript/scene logic.

## See also

- [`../SKILL.md`](../SKILL.md) — bevy-porting dispatcher
- `bevy-animation` — `AnimationGraph`, `AnimationTransitions`, clip loading from glTF
- `bevy-ui` — `Node` + Taffy/flex, replacing Control nodes
- `bevy-custom-assets` — `AssetLoader` pattern, replacing Godot custom `Resource`
- `bevy-wasm-webgpu` — Godot web export → `wasm32-unknown-unknown`
