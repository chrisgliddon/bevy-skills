# bevy-porting — Unity Input → bevy_input (Bevy 0.18)

> Referenced from `bevy-porting/SKILL.md § Unity (priority)`.

## Ecosystem context

Unity ships two input APIs:

| Unity API | Shape | Bevy 0.18 equivalent |
|---|---|---|
| Legacy `Input.GetKey(KeyCode.Space)` | Polling, global static | `Res<ButtonInput<KeyCode>>` — polling, injected |
| New Input System (`InputAction`, `PlayerInput`) | Asset-driven binding map | No direct equivalent; build your own or use `leafwing-input-manager` |

Bevy's input layer is resource-based and injected as system parameters — there are no
global statics.

## Keyboard: `Input.GetKey` → `ButtonInput<KeyCode>`

```rust
fn jump_system(keys: Res<ButtonInput<KeyCode>>) {
    if keys.just_pressed(KeyCode::Space) { /* start jump */ }
    if keys.pressed(KeyCode::Space)      { /* hold jump */ }
    if keys.just_released(KeyCode::Space){ /* land */ }
}
```

| Unity | Bevy |
|---|---|
| `Input.GetKeyDown(k)` | `keys.just_pressed(k)` |
| `Input.GetKey(k)` | `keys.pressed(k)` |
| `Input.GetKeyUp(k)` | `keys.just_released(k)` |

## Action map → custom bindings resource

Unity Input System serialises an action map asset (`WASD` → `Move`, `Space` → `Jump`).
Bevy has no equivalent asset type. Pattern:

```rust
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
enum GameAction { Jump, MoveLeft, MoveRight, MoveForward, MoveBack }

#[derive(Resource)]
struct Bindings(std::collections::HashMap<KeyCode, GameAction>);

impl Default for Bindings {
    fn default() -> Self {
        let mut map = std::collections::HashMap::new();
        map.insert(KeyCode::Space, GameAction::Jump);
        map.insert(KeyCode::KeyA,  GameAction::MoveLeft);
        map.insert(KeyCode::KeyD,  GameAction::MoveRight);
        map.insert(KeyCode::KeyW,  GameAction::MoveForward);
        map.insert(KeyCode::KeyS,  GameAction::MoveBack);
        Self(map)
    }
}

fn read_actions(keys: Res<ButtonInput<KeyCode>>, bindings: Res<Bindings>) {
    for (key, action) in &bindings.0 {
        if keys.just_pressed(*key) {
            // dispatch action
            let _ = action;
        }
    }
}
```

For non-trivial setups (analog axes, chords, rebinding, gamepad + keyboard unification)
use [`leafwing-input-manager`](https://github.com/Leafwing-Studios/leafwing-input-manager).
It mirrors the Unity Input System's action-map model with a Bevy-native API.

## Gamepad

In Bevy 0.18, `Gamepad` is a **component** on an `Entity` (spawned automatically on connection).
`GamepadAxis` and `GamepadButton` are plain enums with direct variants — there are no `::new()`
constructors and no separate `GamepadAxisType`/`GamepadButtonType` enums.

```rust
use bevy::input::gamepad::{Gamepad, GamepadAxis, GamepadButton, GamepadConnectionEvent};

// Query the Gamepad component — one entity per connected controller.
fn gamepad_system(gamepads: Query<(Entity, &Gamepad)>) {
    for (entity, gamepad) in &gamepads {
        // Left stick X — equivalent to Gamepad.current.leftStick.ReadValue().x
        if let Some(x) = gamepad.get(GamepadAxis::LeftStickX) {
            let _ = x; // -1.0 … 1.0
        }
        // A / Cross — equivalent to Gamepad.current.buttonSouth.wasPressedThisFrame
        if gamepad.just_pressed(GamepadButton::South) {
            info!("{entity:?}: South pressed");
        }
    }
}

fn on_gamepad_connect(mut events: EventReader<GamepadConnectionEvent>) {
    for ev in events.read() {
        match &ev.connection {
            bevy::input::gamepad::GamepadConnection::Connected { name, .. } => {
                println!("Connected: {}", name);
            }
            bevy::input::gamepad::GamepadConnection::Disconnected => {
                println!("Disconnected: {:?}", ev.gamepad);
            }
        }
    }
}
```

Unity has `Gamepad.current` (implicit selection). Bevy has no "current" gamepad concept —
iterate `Query<(Entity, &Gamepad)>` and track which entity is "active" yourself, e.g. by
storing the `Entity` in a `Resource` when the first `GamepadConnectionEvent` fires.

## Touch & mobile

```rust
fn touch_system(touches: Res<Touches>) {
    for touch in touches.iter_just_pressed() {
        println!("touch id={} pos={:?}", touch.id(), touch.position());
    }
}
```

| Unity | Bevy |
|---|---|
| `Input.touchCount` | `touches.iter().count()` |
| `Input.GetTouch(i).phase == Began` | `touches.iter_just_pressed()` |
| `Input.GetTouch(i).phase == Ended` | `touches.iter_just_released()` |
| `touch.position` | `touch.position()` (logical pixels, Y-up) |

## Mouse / pointer

```rust
fn mouse_system(
    window: Single<&Window>,
    mouse_buttons: Res<ButtonInput<MouseButton>>,
) {
    if let Some(pos) = window.cursor_position() {
        // pos is in logical pixels, origin top-left (matches Unity's screen-space)
        let _ = pos;
    }
    if mouse_buttons.just_pressed(MouseButton::Left) { /* click */ }
}
```

Bevy 0.18: cursor position is **per-`Window`** — query `Single<&Window>` (one window)
or `Query<&Window>` (multi-window). There is no global `Input.mousePosition` equivalent.

## Rebinding

Unity Input System has built-in interactive rebinding (`InputAction.PerformInteractiveRebinding`).
Bevy has no equivalent. Options:

- Hand-roll: listen for `KeyboardInput` events during a "listening" state, write the new
  `KeyCode` back into your `Bindings` resource.
- Use `leafwing-input-manager` — it includes a rebinding API.

## See also

- [`../SKILL.md`](../SKILL.md) — bevy-porting dispatcher
- [`unity-animation.md`](unity-animation.md) — animation state machines driven by input state
- [`unity-ui.md`](unity-ui.md) — wiring input to UI button interaction
- [`bevy-ecs-systems/SKILL.md`](../../bevy-ecs-systems/SKILL.md) — `Res<T>`, `EventReader`, system ordering
