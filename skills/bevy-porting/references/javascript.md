# bevy-porting — Vanilla JS / Canvas / HTML5 → Bevy 0.18

> Referenced from `bevy-porting/SKILL.md § Engine coverage`.

Vanilla JS games typically share one shape: a `<canvas>` element, a `requestAnimationFrame` loop, and a set of classes that each own their own draw + update logic. This reference covers porting that pattern — and simpler HTML5 game patterns built on the same ideas — to Bevy 0.18.

## Concept map

| Vanilla JS / Canvas | Bevy 0.18 |
|---|---|
| `requestAnimationFrame(loop)` | `Update` schedule (Bevy owns the loop) |
| `setInterval(tick, 16)` for fixed logic | `FixedUpdate` schedule |
| `class Player { update(dt) {} draw(ctx) {} }` | `Player` component + `update_players` system + `Sprite` for rendering |
| `ctx.drawImage(img, x, y)` | `Sprite::from_image(handle)` + `Transform::from_xyz` |
| `ctx.fillRect(x, y, w, h, color)` | 1×1 white `Sprite` scaled via `Transform`, tinted via `Sprite::color` |
| `ctx.fillText("score", x, y)` | `Text` + `TextFont` component bundle |
| `new Image(); img.src = "hero.png"` | `asset_server.load::<Image>("hero.png")` |
| `AudioContext` + buffer source | `AudioPlayer` component on an entity |
| `addEventListener("keydown", fn)` | `Res<ButtonInput<KeyCode>>` polled each frame |
| `mousemove` / `mousedown` listeners | `Res<ButtonInput<MouseButton>>` + window cursor position |
| `localStorage.setItem(key, val)` | `bevy_persistent` (community) or direct file IO / WASM shim |

## The render loop

You do **not** write a loop in Bevy. Systems registered on `Update` run every frame; Bevy calls `requestAnimationFrame` internally in WASM builds. The only decision is which schedule:

```rust
// Variable-timestep: rendering, input reading, UI updates
app.add_systems(Update, (read_input, update_camera, animate_sprites));

// Fixed-timestep: physics, deterministic game logic (default 64 Hz)
app.add_systems(FixedUpdate, (apply_velocity, check_collisions));
```

See `bevy-core-concepts` for schedule ordering and `Time<Fixed>`.

## Class → Component + System

Don't port JS classes 1:1 into Rust structs. Split data from behaviour.

**JS:**
```js
class Player {
  constructor(x, y) { this.x = x; this.y = y; this.speed = 200; }
  update(dt, keys) { if (keys["ArrowRight"]) this.x += this.speed * dt; }
  draw(ctx, img) { ctx.drawImage(img, this.x, this.y); }
}
```

**Bevy:**
```rust
#[derive(Component)]
struct Player { speed: f32 }

fn move_player(
    mut query: Query<(&Player, &mut Transform)>,
    input: Res<ButtonInput<KeyCode>>,
    time: Res<Time>,
) {
    for (player, mut transform) in &mut query {
        if input.pressed(KeyCode::ArrowRight) {
            transform.translation.x += player.speed * time.delta_secs();
        }
    }
}

// Spawn:
commands.spawn((
    Player { speed: 200.0 },
    Sprite::from_image(asset_server.load("player.png")),
    Transform::from_xyz(x, y, 0.0),
));
```

## Canvas drawing → Bevy 2D primitives

| Canvas call | Bevy equivalent |
|---|---|
| `ctx.drawImage(img, x, y)` | `Sprite::from_image(handle)` + `Transform` |
| `ctx.fillRect(...)` colored box | 1×1 white sprite, `Transform::with_scale(Vec3::new(w, h, 1.))`, `Sprite { color: Color::srgb(r, g, b), .. }` |
| `ctx.fillText(s, x, y)` | `commands.spawn((Text::new(s), TextFont { font_size: 24., .. }, Transform::from_xyz(x, y, 0.)))` |

Bevy 2D does not have a built-in filled-rectangle primitive. The scaled white-sprite pattern is idiomatic for solid color rectangles.

## Image loading

Both worlds are async; the difference is the API:

```rust
// Bevy: load returns immediately with a handle; asset is ready later
let handle: Handle<Image> = asset_server.load("sprites/hero.png");

// Optionally gate on readiness
fn use_when_loaded(
    handle: Res<MyImageHandle>,
    images: Res<Assets<Image>>,
) {
    if let Some(img) = images.get(&handle.0) { /* use img */ }
}
```

## Audio

Replace Web Audio API with `bevy_audio`. Spawn an entity with `AudioPlayer`:

```rust
commands.spawn(AudioPlayer::new(asset_server.load("sounds/jump.ogg")));
```

See `unity-audio.md` for the broader Bevy audio mapping (same `AudioPlayer` API regardless of source engine).

## Input

```rust
// Keyboard
fn handle_input(input: Res<ButtonInput<KeyCode>>) {
    if input.just_pressed(KeyCode::Space) { /* jump */ }
}

// Mouse position
fn cursor_pos(window: Single<&Window>) {
    if let Some(pos) = window.cursor_position() { /* pos is Vec2 */ }
}
```

## Storage

- **Native:** use `std::fs` or the `bevy_persistent` community crate for typed, auto-persisted resources.
- **WASM:** `bevy_persistent` can target `LocalStorage`/`IndexedDB` via a feature flag. See `bevy-wasm-webgpu` for WASM-specific constraints.

## Networking

`fetch()` and `WebSocket` have no core Bevy equivalent. Use `reqwest` for native HTTP, and `web_sys::WebSocket` (via `wasm-bindgen`) for WASM. Wrap calls in `IoTaskPool` tasks and send results back via channels.

## Game loop pacing in WASM

WASM Bevy still drives rendering through `requestAnimationFrame` — but you never touch it. `FixedUpdate` logic runs inside each frame callback at the configured Hz. See `bevy-wasm-webgpu` for WASM build setup and browser constraints.

## No extraction script

Vanilla JS source is plain text. There is no binary project format to unpack. Porting is a rewrite of logic, not an extraction of data — read the JS, map each class to the table above, and rewrite.

## See also

- [`../SKILL.md`](../SKILL.md) — bevy-porting dispatcher and general porting principles
- [`phaser.md`](phaser.md) — Phaser 3 → Bevy 0.18 (same rendering targets, adds physics and scene system)
- `bevy-core-concepts` — schedules, `Update` vs `FixedUpdate`, `Time<Fixed>`
- `bevy-wasm-webgpu` — WASM build setup, browser constraints, `requestAnimationFrame` internals
- `bevy-ui` — `Text`, `Node`, Taffy/flex for UI elements previously drawn with Canvas text/boxes
