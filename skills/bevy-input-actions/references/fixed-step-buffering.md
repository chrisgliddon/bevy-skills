# Carrying frame input into fixed simulation

## Why direct reads fail

Bevy refreshes raw input once per rendered frame. `FixedUpdate` can execute zero times
or multiple times before the next refresh. Directly reading frame-scoped edges and
relative mouse motion inside every fixed iteration causes three classes of bug:

- zero ticks: a short press or mouse delta disappears before simulation sees it;
- multiple ticks: the same edge/delta is applied repeatedly;
- press and release in one frame: a boolean held state loses the tap entirely.

## Persistent bridge

Translate physical messages after `InputSystems` and append action transitions in
their observed order. Keep the bridge resource alive across frames:

```rust
use bevy::prelude::*;
use std::collections::VecDeque;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ActionEdge {
    JumpPressed,
    JumpReleased,
}

#[derive(Resource, Default)]
struct FrameToFixedInput {
    edges: VecDeque<ActionEdge>,
    look_delta: Vec2,
    move_axis: Vec2,
    jump_held: bool,
}

#[derive(Resource, Default)]
struct FixedInputFrame {
    edges: Vec<ActionEdge>,
    look_delta: Vec2,
    move_axis: Vec2,
    jump_held: bool,
}

fn begin_fixed_tick(
    mut bridge: ResMut<FrameToFixedInput>,
    mut tick: ResMut<FixedInputFrame>,
) {
    tick.edges.clear();
    tick.edges.extend(bridge.edges.drain(..));
    tick.look_delta = std::mem::take(&mut bridge.look_delta);
    tick.move_axis = bridge.move_axis;
    tick.jump_held = bridge.jump_held;
}
```

Run `begin_fixed_tick` first in the simulation's `FixedUpdate` ordering. The first
fixed tick drains pending edges and relative motion. Later catch-up ticks see empty
edges/zero delta but the same current held and absolute-axis state. If no tick runs,
the pending data remains for next time.

Do not clear the bridge in `Last` or at the end of the render frame. Consumption, not
render-frame lifetime, owns clearing.

## Preserve transition order

`ButtonInput::just_pressed`/`just_released` are convenient summaries but do not form
an ordered transition log. Use underlying input messages when a fast tap or repeated
transition must survive. Translate each physical transition through the bindings that
were active at that moment and queue the resulting action edge.

Each Bevy message stream preserves its own reader order; separate keyboard, mouse,
and gamepad streams do not provide a shared total order. If gameplay needs a
deterministic merge, define stream precedence and assign a monotonically increasing
sequence at one ingestion boundary. If actual cross-device chronology matters, the
platform adapter must timestamp/sequence transitions before Bevy splits them; it
cannot be reconstructed from the separate streams afterward.

Define how binding/context changes interact with held inputs. A safe default is to
synthesize releases for actions leaving the active context, then require a fresh
physical transition before newly bound actions press. This prevents opening a menu
from also activating the focused menu item.

## Mouse and other relative axes

Add each frame's `AccumulatedMouseMotion.delta` once to the bridge. Do the same for
wheel/gyro deltas if they are treated as relative quantities. Absolute sticks and
cursor positions overwrite the latest value instead of accumulating.

Clamp or subdivide extreme accumulated motion after a stall according to game
semantics; never silently drop it just to hide a hitch. Focus loss should explicitly
clear relative deltas and synthesize releases as part of the action policy.

## Rollback and deterministic commands

The bridge is a local real-time adapter, not a rollback history. At the fixed-tick
boundary, quantize values into a serializable `InputCommand { tick, buttons, axes }`,
store it in a ring buffer, and make simulation consume that command. Record the
quantization rules and action-map version. Replays and network peers should not need
access to Bevy's live `ButtonInput` or `Gamepad` components.

## Deterministic tests

Drive the bridge and fixed schedule manually:

- enqueue press+release, run no fixed tick, assert both remain;
- run one tick, assert both arrive in order exactly once;
- run three more ticks, assert no repeated edges/delta but held/axes persist;
- enqueue motion across two zero-tick frames, assert the sum arrives once;
- focus-loss transition clears holds and creates the required release edge.

Use [`bevy-testing`](../../bevy-testing/SKILL.md) for manual time and fixed-schedule
stepping.
