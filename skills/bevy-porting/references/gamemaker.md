# bevy-porting — GameMaker Studio 2 → Bevy 0.18

> Referenced from `bevy-porting/SKILL.md § Engine coverage`.

GameMaker Studio 2 (GMS2) organises content into Objects (with event-driven code), Sprites, Rooms (scenes), Sounds, Fonts, and Shaders. Scripting is in GML (GameMaker Language — C-like). Project files (`.yyp` root manifest + per-asset `.yy`) are plain JSON — easy to parse without a GMS2 install.

## Object events → Bevy systems

| GMS2 event | Bevy 0.18 |
|---|---|
| Create | `Startup` system, or an `Added<C>` observer on first spawn |
| Step | `Update` system |
| Begin Step | `PreUpdate` system |
| End Step | `PostUpdate` system |
| Draw | Bevy renders automatically; spawn `Mesh2d` entities for custom draw |
| Destroy | `On<Remove<C>>` observer, or detect `RemovedComponents<C>` in a system |
| Collision | `bevy_rapier2d` `CollisionEvent` reader |
| Alarm[n] | `Timer` component + a system that fires on expiry |

```rust
// GMS2: Step event — x += speed * delta_time
fn move_objects(mut query: Query<(&Speed, &mut Transform), With<MyObj>>, time: Res<Time>) {
    for (speed, mut tf) in &mut query {
        tf.translation.x += speed.0 * time.delta_secs();
    }
}
// app.add_systems(Update, move_objects);
```

## Object instances → entities

```rust
// GMS2: instance_create_layer(x, y, "Instances", obj_enemy)
// Bevy:
#[derive(Component)] struct Enemy;

fn spawn_enemy(mut commands: Commands, x: f32, y: f32) {
    commands.spawn((
        Enemy,
        Speed(80.0),
        Sprite::from_image(/* handle */),
        Transform::from_xyz(x, y, 0.0),
    ));
}
```

## GML idioms → Rust

| GML | Bevy 0.18 |
|---|---|
| `global.score` | `#[derive(Resource)] struct Score(pub i32)` |
| `with(obj_enemy) { ... }` | `Query<&mut Enemy>` + iterate |
| `instance_find(obj, n)` | iterate a `Query`; index n is usually a design smell — refactor |
| `instance_exists(obj)` | `Query<(), With<Enemy>>.is_empty()` (inverted) |
| `instance_destroy()` | `commands.entity(e).despawn()` |
| `var x = ...` | local `let x = ...` in a system fn |
| `draw_sprite(spr, img, x, y)` | spawn a `Sprite` entity (or update an existing one's `Transform`) |

## Sprites (`.yy`)

GMS2 sprites carry frame data, origin point (pivot), and a collision mask. Port steps:

1. Export sprite sheet PNGs from GMS2 (Sprite editor → Export).
2. Load in Bevy: `asset_server.load("spr_player.png")`.
3. For animated sprites: build a `TextureAtlas` + add a `Timer` + write a frame-advance system.

Cross-link: `phaser.md § Sprite-sheet animation` for the `TextureAtlas` + `Timer` pattern.

```rust
#[derive(Component)]
struct FrameTimer { timer: Timer, frames: u32, current: u32 }

fn advance_frames(mut query: Query<(&mut FrameTimer, &mut Sprite)>, time: Res<Time>) {
    for (mut ft, mut sprite) in &mut query {
        ft.timer.tick(time.delta());
        if ft.timer.just_finished() {
            ft.current = (ft.current + 1) % ft.frames;
            if let Some(atlas) = &mut sprite.texture_atlas {
                atlas.index = ft.current as usize;
            }
        }
    }
}
```

## Rooms (`.yy`)

GMS2 rooms are 2D scenes with layers (Background, Instance, Tile, Asset, etc.). Bevy equivalents:

- **Spawn function** — a `Startup` (or state-enter) system that spawns room contents; cleanest approach.
- **`DynamicScene`** — serialisable ECS snapshot; useful if you need round-trippable room state.

Use `scripts/gamemaker/gms2_inventory.py` to list all instances in a room before writing the spawn function.

## Tilesets

GMS2 tilesets → **`bevy_ecs_tilemap`** (community crate). Import the tileset image as a `Handle<Image>` and reconstruct tile layout in Bevy coordinates. Note that GMS2 uses a top-left origin; Bevy 2D uses bottom-left by default — flip Y when converting tile positions.

## Input

```rust
// GMS2: if keyboard_check_pressed(vk_space) { jump() }
fn read_input(input: Res<ButtonInput<KeyCode>>, mut query: Query<&mut Velocity, With<Player>>) {
    if input.just_pressed(KeyCode::Space) {
        for mut vel in &mut query { vel.linvel.y = 400.0; }
    }
}
```

## Audio

```rust
// GMS2: audio_play_sound(snd_jump, 10, false)
commands.spawn((
    AudioPlayer(asset_server.load("sounds/jump.ogg")),
    PlaybackSettings::DESPAWN,
));
```

## Using `gms2_inventory.py`

```
python3 gms2_inventory.py /path/to/Project.yyp
python3 gms2_inventory.py /path/to/Project.yyp --out project.json
python3 gms2_inventory.py /path/to/Project.yyp --by-type
python3 gms2_inventory.py /path/to/Project.yyp --include-events
```

Output groups resources by type (GMObject, GMSprite, GMRoom, GMSound, GMScript, …) with per-asset metadata. `--include-events` lists which GMS2 events each Object has defined (decoded from integer event-type codes — see script docstring for the full mapping).

## Build / publish

| GMS2 | Bevy 0.18 |
|---|---|
| Windows/macOS/Linux (IDE export) | `cargo build --release --target <triple>` |
| HTML5 export | `wasm32-unknown-unknown` + `wasm-bindgen` |
| Android / iOS | cross-compilation via `cargo` + NDK/Xcode |

Cross-link: **`bevy-cargo-features`**, **`bevy-wasm-webgpu`**.

## Gotchas

- GMS2's `with(obj)` block runs code in the scope of every matching instance. The direct Bevy translation is a `Query` iteration — but heavy use of `with` often signals that the design needs refactoring into components and systems.
- GMS2 uses `delta_time` (seconds per step) automatically in Step events. Bevy `time.delta_secs()` is equivalent but must be passed explicitly to systems.
- GMS2 room origin is top-left; Bevy 2D world origin is centre-screen, Y-up. Convert room positions: `bevy_x = room_x - room_width/2`, `bevy_y = room_height/2 - room_y`.
- GML dynamic typing (arrays are 1D or 2D, strings and numbers auto-coerce) has no Rust equivalent. Audit all data structures before porting.
- GMS2 `draw_*` functions run in the Draw event; Bevy rendering is automatic — only port Draw event code that constructs or transforms mesh data.

## See also

- [`../SKILL.md`](../SKILL.md) — bevy-porting dispatcher
- [`phaser.md`](phaser.md) — similar 2D context; sprite-sheet animation and tween patterns
- `bevy-wasm-webgpu` — GMS2 HTML5 export → `wasm32-unknown-unknown`
