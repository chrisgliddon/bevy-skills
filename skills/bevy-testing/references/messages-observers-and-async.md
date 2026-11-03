# Messages, observers, commands, and async work

## Read messages with a test-owned cursor

```rust
use bevy::{ecs::message::MessageCursor, prelude::*};

#[derive(Message)]
struct Scored(u32);

let mut app = App::new();
app.add_message::<Scored>();

let mut cursor = MessageCursor::<Scored>::default();
app.world_mut()
    .resource_mut::<Messages<Scored>>()
    .write(Scored(7));

let messages = app.world().resource::<Messages<Scored>>();
let values: Vec<u32> = cursor.read(messages).map(|event| event.0).collect();
assert_eq!(values, [7]);
```

`Messages::get_cursor()` includes currently retained messages;
`get_cursor_current()` starts after them. Choose intentionally. When testing a
scheduled writer, create the cursor at the appropriate boundary, call `app.update()`,
then read before retention removes the data. Do not add a production reader solely so
a test can inspect output.

## Observer semantics

```rust
use bevy::prelude::*;

#[derive(Event)]
struct Hit(u32);

#[derive(Component)]
struct Health(u32);

#[derive(Resource, Default)]
struct HitLog(Vec<u32>);

let mut app = App::new();
app.init_resource::<HitLog>();
// 0.20: no bundle generic on `On`; lifecycle events carry it instead.
app.add_observer(|hit: On<Hit>, mut log: ResMut<HitLog>| log.0.push(hit.event().0));
app.add_observer(|add: On<Add<Health>>, mut log: ResMut<HitLog>| {
    let _entity = add.entity;
    log.0.push(0);
});

app.world_mut().spawn(Health(3));
app.world_mut().trigger(Hit(2));
assert_eq!(app.world().resource::<HitLog>().0, [0, 2]);
```

`world.trigger(event)` runs matching observers immediately. `commands.trigger(event)`
is deferred until commands apply. Test whichever path production uses. Observer
side-effects can trigger nested observers synchronously, so assert the final causal
contract. Ordering among observers reacting to the same event is not guaranteed;
if order matters, redesign around explicit systems/sets or a single orchestrator.

Entity events can propagate through configured relationships. Tests should cover
source, target, propagation stopping, despawned targets, and mutations performed by
observers—not only that “an observer ran.”

## Deferred commands

Spawns/inserts/despawns issued through `Commands` become visible at a synchronization
point. `.chain()` inserts the necessary boundary between dependent systems. A test
that calls only one system function directly may accidentally skip this semantic.
Use an `App` and the real schedule when command visibility is part of the behaviour.

## Async production polling

Bevy 0.20 offers two cheap, non-blocking polls:

```rust
use bevy::tasks::{block_on, futures::check_ready, poll_once, Task};

fn drain(task: &mut Task<u32>) -> Option<u32> {
    block_on(poll_once(task)) // or: check_ready(task)
}
```

When either returns `Some(output)`, consume the output and remove the task
component/owner exactly once. Do not repeatedly await a completed `Task`.

For deterministic tests, inject one of these boundaries:

- an executor trait/resource whose test version returns a controlled completion;
- a result inbox that tests can fill directly;
- a pure scheduler state machine tested without a real thread;
- a task factory returning a pre-resolved task/future.

Then test queued, running, completed, failed, cancelled, superseded, and stale states
without scheduling races.

## Bounded integration drain

When a real task-pool smoke test is necessary, define an observable predicate and a
hard bound:

```rust
fn update_until(
    app: &mut App,
    max_updates: usize,
    done: impl Fn(&World) -> bool,
) {
    for _ in 0..max_updates {
        app.update();
        if done(app.world()) {
            return;
        }
        std::thread::yield_now();
    }
    panic!("async work did not complete within {max_updates} app updates");
}
```

Include queue depth, task state, and last error in the real helper's panic. A yielded,
bounded loop is still a scheduler-dependent smoke test, so do not use it where the
injected deterministic test can prove the behaviour. Never use an arbitrary sleep as
a correctness boundary.
