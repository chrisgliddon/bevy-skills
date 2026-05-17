# bevy-porting — Phaser 3 → Bevy 0.18

> Referenced from `bevy-porting/SKILL.md § Engine coverage`.

Phaser 3 is a scene-based 2D framework: each `Phaser.Scene` subclass has `preload()`, `create()`, and `update()` methods, a built-in physics engine (Arcade or Matter.js), tweens, a sprite-sheet animation manager, and a managed input system. This reference maps each of those subsystems to Bevy 0.18 equivalents.

## Concept map

| Phaser 3 | Bevy 0.18 |
|---|---|
| `Phaser.Scene` subclass | Plugin + a set of systems |
| `preload()` | `Startup` system + `AssetServer::load(...)` |
| `create()` | `Startup` system (spawning initial entities) |
| `update(time, delta)` | One or more `Update` systems per gameplay concern |
| `this.add.sprite(x, y, key)` | `commands.spawn((Sprite::from_image(h), Transform::from_xyz(x, y, 0.)))` |
| `setDepth(n)` | `Transform.translation.z` (higher = drawn on top in Bevy 2D) |
| `Phaser.GameObjects.Group` | Marker component + query filter |
| Container / parent sprite | `ChildOf` component |
| Arcade Physics body | `bevy_rapier2d` or `avian2d` (community crates) |
| `this.tweens.add(...)` | Easing curve sampled in a system (see below) |
| `scene.anims.create(...)` | `TextureAtlas` + `Timer` + frame-advance system |
| `this.input.keyboard.on("keydown-LEFT", ...)` | `Res<ButtonInput<KeyCode>>` polled in a system |
| Pointer / mouse click | `Res<ButtonInput<MouseButton>>` + `Window::cursor_position()` |

## `preload()` → `AssetServer::load`

Phaser blocks in `preload()` until all assets are ready, then calls `create()`. Bevy's loading is always async — `load` returns a `Handle<T>` immediately, and the asset becomes ready in a later frame.

```rust
#[derive(Resource)]
struct GameAssets { player: Handle<Image>, tileset: Handle<Image> }

fn load_assets(mut commands: Commands, asset_server: Res<AssetServer>) {
    commands.insert_resource(GameAssets {
        player: asset_server.load("sprites/player.png"),
        tileset: asset_server.load("sprites/tiles.png"),
    });
}
// app.add_systems(Startup, load_assets);
```

Gate gameplay systems on readiness with `AssetServer::is_loaded_with_dependencies` or the `LoadingState` pattern from `bevy_asset_loader` (community crate).

## `create()` → startup system

```rust
fn spawn_world(mut commands: Commands, assets: Res<GameAssets>) {
    // Phaser: this.add.sprite(100, 200, "player")
    commands.spawn((
        Sprite::from_image(assets.player.clone()),
        Transform::from_xyz(100.0, 200.0, 0.0),
        Player { speed: 150.0 },
    ));
}
// app.add_systems(Startup, spawn_world.after(load_assets));
```

## `update()` → per-concern systems

Don't translate `update()` line by line. Split it into one system per responsibility:

```rust
app.add_systems(Update, (read_player_input, move_player, update_camera).chain());
app.add_systems(FixedUpdate, apply_physics);
```

## Arcade Physics → `bevy_rapier2d` / `avian2d`

Bevy 0.18 core has no physics engine. Two community crates provide 2D physics:

- **`bevy_rapier2d`** — wraps the Rapier physics engine; mature, feature-rich, comparable to Arcade + Matter combined.
- **`avian2d`** — Bevy-native, ECS-first design; slightly less mature but idiomatic.

Both provide velocity, collision events, and sensor bodies equivalent to Phaser's Arcade physics API. Add the chosen crate's plugin and replace `setVelocityX` / `body.touching` with the crate's components and events.

## Tweens → easing curves

Phaser: `this.tweens.add({ targets: obj, x: 400, duration: 800, ease: "Sine.easeInOut" })`

Bevy: sample an `EasingCurve` each frame and write to `Transform`:

```rust
#[derive(Component)]
struct Tween { start_x: f32, end_x: f32, duration: f32, elapsed: f32 }

fn drive_tweens(mut query: Query<(&mut Tween, &mut Transform)>, time: Res<Time>) {
    for (mut tw, mut transform) in &mut query {
        tw.elapsed = (tw.elapsed + time.delta_secs()).min(tw.duration);
        let t = tw.elapsed / tw.duration;
        // Use EaseFunction::SineInOut from bevy::math
        let eased = EasingCurve::new(tw.start_x, tw.end_x, EaseFunction::SineInOut)
            .sample_clamped(t);
        transform.translation.x = eased;
    }
}
```

See `bevy-animation/references/curves-and-tweening.md` for the full `AnimatableCurve` + `EaseFunction` catalogue.

## Sprite-sheet animation

Phaser's `scene.anims.create({ key, frames, frameRate })` maps to a `TextureAtlas` + a `Timer` that advances the atlas index:

```rust
#[derive(Component)]
struct SpriteAnim { frames: Vec<usize>, fps: f32, current: usize, timer: f32 }

fn advance_anims(mut query: Query<(&mut SpriteAnim, &mut Sprite)>, time: Res<Time>) {
    for (mut anim, mut sprite) in &mut query {
        anim.timer += time.delta_secs();
        if anim.timer >= 1.0 / anim.fps {
            anim.timer = 0.0;
            anim.current = (anim.current + 1) % anim.frames.len();
            if let Some(atlas) = &mut sprite.texture_atlas {
                atlas.index = anim.frames[anim.current];
            }
        }
    }
}
```

## Groups → marker components; Containers → `ChildOf`

```rust
// Phaser: group.add(sprite) — tag instead:
#[derive(Component)] struct EnemyGroup;
commands.entity(enemy_entity).insert(EnemyGroup);

// Query the group:
fn damage_enemies(query: Query<Entity, With<EnemyGroup>>) { ... }

// Phaser Container (parented sprites) → ChildOf:
commands.entity(child_sprite).insert(ChildOf(parent_entity));
```

## Input

```rust
fn player_input(
    input: Res<ButtonInput<KeyCode>>,
    mut query: Query<&mut Transform, With<Player>>,
) {
    let mut dir = Vec2::ZERO;
    if input.pressed(KeyCode::ArrowLeft)  { dir.x -= 1.0; }
    if input.pressed(KeyCode::ArrowRight) { dir.x += 1.0; }
    for mut transform in &mut query {
        transform.translation += dir.extend(0.0) * 150.0 * /* delta */ 0.016;
    }
}
```

## Build

Phaser ships a bundled JS/WASM file. Bevy targets `wasm32-unknown-unknown` via `cargo build --target wasm32-unknown-unknown`, then `wasm-bindgen`. See `bevy-wasm-webgpu` for the full WASM build recipe.

## See also

- [`../SKILL.md`](../SKILL.md) — bevy-porting dispatcher and general porting principles
- [`javascript.md`](javascript.md) — vanilla JS / Canvas → Bevy (lower-level; same rendering targets)
- `bevy-animation` — `AnimatableCurve`, `EaseFunction`, full animation graph
- `bevy-wasm-webgpu` — WASM build setup, asset serving, browser constraints
- `bevy-ui` — UI elements (Phaser DOM/HTML UI or Scene-based UI → Bevy `Node`)
