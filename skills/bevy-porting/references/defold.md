# bevy-porting — Defold → Bevy 0.18

> Referenced from `bevy-porting/SKILL.md § Engine coverage`.

Defold is a Lua-scripted 2D-first engine (limited 3D). Game objects (`.go`) carry components; collections (`.collection`) are scene hierarchies. Both are text-based protobuf-flavoured key/value files — readable without a Defold install. The mental shift to Bevy ECS is gentler than for class-OOP engines: Defold components are already data attachments, not deep class trees.

## Concept map

| Defold | Bevy 0.18 |
|---|---|
| Game object (`.go`) | `Entity` + `Bundle` |
| `script` component (Lua behaviour) | `System` functions |
| `sprite` component | `Sprite` + `Handle<Image>` |
| `tilemap` component | `bevy_ecs_tilemap` (community crate) |
| `factory` component (spawner) | spawn function called from a system |
| `collisionobject` | `bevy_rapier2d` collider or `avian2d` |
| `.collection` (scene hierarchy) | spawn function or `DynamicScene` |
| `go.property("speed", 100)` | `#[derive(Component)] struct Speed(pub f32)` |
| Camera (orthographic 2D) | `Camera2d` |

## Game object components → Bundles

Defold attaches typed components to a game object in the `.go` text file. In Bevy, `Bundle` groups the same components for one `commands.spawn(...)` call:

```rust
#[derive(Component)] struct Speed(pub f32);
#[derive(Component)] struct Player;

fn spawn_player(mut commands: Commands, asset_server: Res<AssetServer>) {
    commands.spawn((
        Player,
        Speed(100.0),
        Sprite::from_image(asset_server.load("player.png")),
        Transform::from_xyz(0.0, 0.0, 0.0),
    ));
}
// app.add_systems(Startup, spawn_player);
```

## Lua lifecycle → Bevy schedules

| Defold (Lua) | Bevy 0.18 |
|---|---|
| `init(self)` | `Startup` system |
| `update(self, dt)` | `Update` system + `Res<Time>` |
| `on_message(self, msg_id, msg, sender)` | message handler system (see below) |
| `final(self)` | `On<Remove<C>>` observer |

```rust
// Defold: function update(self, dt)  self.pos.x = self.pos.x + self.speed * dt  end
fn move_player(mut query: Query<(&Speed, &mut Transform), With<Player>>, time: Res<Time>) {
    for (speed, mut tf) in &mut query {
        tf.translation.x += speed.0 * time.delta_secs();
    }
}
```

## Message passing → Bevy messages / events

Defold's `msg.post` / `on_message` is similar to Bevy 0.18's typed message system. Map each Defold message hash to a Rust type:

```rust
// Defold: msg.post(".", hash("walk"), { dir = 1 })
#[derive(Event)]
struct WalkRequest { dir: f32 }

fn send_walk(mut writer: EventWriter<WalkRequest>, input: Res<ButtonInput<KeyCode>>) {
    if input.pressed(KeyCode::ArrowRight) {
        writer.send(WalkRequest { dir: 1.0 });
    }
}
fn handle_walk(mut events: EventReader<WalkRequest>, mut query: Query<&mut Transform, With<Player>>) {
    for ev in events.read() {
        for mut tf in &mut query { tf.translation.x += ev.dir * 4.0; }
    }
}
```

Cross-link: **`bevy-ecs-systems`** (event and observer patterns).

## Collections → scene composition

Defold collections nest game objects and sub-collections. Bevy equivalents:

- **Spawn function** — a regular Rust `fn` that calls `commands.spawn(...)` for each object; cleanest for code-first ports.
- **glTF** — export visual geometry from Defold (via FBX/OBJ intermediate); load with `bevy_gltf`.
- **`DynamicScene`** — serialisable ECS snapshot; use when you want round-trippable scene data.

## Sprite atlases (`.atlas`)

Defold `.atlas` files are protobuf-text manifests listing image paths and animation frame groups. Port path:

1. Extract image paths from the `.atlas` text file (each `images { image: "/path.png" }` block).
2. Load images via `asset_server.load("sprites/sheet.png")`.
3. Build a `TextureAtlas` and drive frame advancement with a `Timer` — same pattern as Phaser sprite-sheet animation (cross-link `phaser.md`).

## Tile sources + tilemaps

Defold tilemaps are purely 2D. The recommended Bevy equivalent is **`bevy_ecs_tilemap`** — the community de facto standard for tile-based worlds. Import the tileset image as a `Handle<Image>` and rebuild the tile layout in Bevy's coordinate space.

## `go.property` → component field

```rust
// Defold .go:  go.property("speed", 100)  go.property("jump_force", 400)
#[derive(Component)]
struct ActorProps { speed: f32, jump_force: f32 }

commands.spawn((ActorProps { speed: 100.0, jump_force: 400.0 }, ...));
```

## Input

Defold input-binding files map device inputs to action hashes. Bevy equivalent: `Res<ButtonInput<KeyCode>>` + `Res<ButtonInput<GamepadButton>>`. For rebindable actions consider **`leafwing-input-manager`** (community crate — also mentioned in `unity-input.md`).

## Parsing `.go` / `.collection` files (inline recipe)

`.go` and `.collection` files are protobuf-text — parseable with stdlib:

```python
import pathlib, re
text = pathlib.Path("player.go").read_text()
for m in re.finditer(r'components\s*\{\s*([^}]*)\}', text, re.S):
    print(m.group(1).strip())
```

No script is bundled for Defold because the workflow is mostly editing rather than bulk extraction. For atlas image enumeration use the same `re.findall(r'image:\s*"([^"]+)"', text)` pattern.

## Build / deploy

| Defold | Bevy 0.18 |
|---|---|
| `bob.jar` build CLI | `cargo build --release --target <triple>` |
| HTML5 export | `wasm32-unknown-unknown` + `wasm-bindgen` |
| Android / iOS export | cross-compilation targets in `Cargo.toml` |

Cross-link: **`bevy-cargo-features`**, **`bevy-wasm-webgpu`**.

## Gotchas

- Defold's coordinate origin is top-left for screen space but world-space cameras can vary — confirm Y-axis direction when porting positions.
- Defold factories have built-in pooling; Bevy has no built-in pool. Use explicit `despawn` + re-spawn, or a community object-pool crate.
- `.collection` files embed child collection references by file path, not inline — you may need to walk multiple files to fully reconstruct a scene hierarchy.
- `go.animate` (built-in tweening) has no direct Bevy core equivalent; port to the easing curve pattern (see `phaser.md § Tweens`).
- Defold's `physics.ray_cast` → `bevy_rapier2d::prelude::RapierContext::cast_ray`.

## See also

- [`../SKILL.md`](../SKILL.md) — bevy-porting dispatcher
- [`phaser.md`](phaser.md) — sibling 2D-engine context; sprite-sheet animation + tween patterns
- `bevy-ecs-systems` — event writers/readers, observers, `On<E>` pattern
- `bevy-wasm-webgpu` — Defold HTML5 export → `wasm32-unknown-unknown`
