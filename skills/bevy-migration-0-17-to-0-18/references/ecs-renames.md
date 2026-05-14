# ECS Renames — Bevy 0.17 → 0.18

Cross-links: [render-renames](render-renames.md) | [asset-renames](asset-renames.md) | [schedule-renames](schedule-renames.md) | [cargo-feature-renames](cargo-feature-renames.md)

## `Trigger<E>` → `On<E>`

```rust
// 0.17 (also in LLM training data as 0.16)
fn on_hit(trigger: Trigger<Damage>) { let _e = trigger.event(); }

// 0.18
fn on_hit(on: On<Damage>) { let _e = on.event(); }
```

## Buffered events: `Event`/`EventReader`/`EventWriter` → `Message`/`MessageReader`/`MessageWriter`

```rust
// 0.17
#[derive(Event)] struct Tick;
fn read(mut r: EventReader<Tick>) { for _ in r.read() {} }
fn write(mut w: EventWriter<Tick>) { w.send(Tick); }

// 0.18
#[derive(Message)] struct Tick;
// app.add_message::<Tick>();
fn read(mut r: MessageReader<Tick>) { for _ in r.read() {} }
fn write(mut w: MessageWriter<Tick>) { w.write(Tick); }
```

`Event` is now reserved for **observed**, entity-targeted events. Use `#[derive(EntityEvent)]` for those.

## `EntityEvent` and target-mutation

`EntityEvent` is a trait in 0.18 (not just a derive), at `bevy::ecs::event::EntityEvent`:

```rust
pub trait EntityEvent: Event {
    fn event_target(&self) -> Entity;
}
```

There is **no `EntityEvent::set_target` method**. The trait only exposes the `event_target()` getter. To mutate the target during propagation, use the separate `SetEntityEventTarget` extension trait — auto-implemented when you derive with `#[entity_event(propagate)]`:

```rust
#[derive(EntityEvent)]
#[entity_event(propagate)]  // auto-impls SetEntityEventTarget for you
struct BubbleClick { entity: Entity }
```

The method is `set_event_target(&mut self, Entity)` (not `set_target`). You almost never call it manually — `#[entity_event(propagate)]` plus Bevy's observer machinery handles it for you.

## `FunctionSystem` new `In` generic

```rust
// 0.17
FunctionSystem<M, O, F>

// 0.18 — new `I` (In) generic inserted between M and O
FunctionSystem<M, I, O, F>
```

This only affects code that explicitly names the type (rare in application code; common in plugin/macro crates).

## `Entity::row` / `Entity::from_row` → `Entity::index` / `Entity::from_index`

```rust
// 0.17
let idx = entity.row();
let e = Entity::from_row(42);

// 0.18
let idx = entity.index();
let e = Entity::from_index(42);
```

## Tick-type module moves

| 0.17 | 0.18 |
|---|---|
| `bevy::ecs::component::Tick` | `bevy::ecs::change_detection::Tick` |
| `bevy::ecs::component::ComponentTicks` | `bevy::ecs::change_detection::ComponentTicks` |
| `bevy::ecs::component::TickCells` | `bevy::ecs::change_detection::ComponentTickCells` |

Note the rename: `TickCells` → `ComponentTickCells`.

## `Resource` requires `'static`

`Resource` no longer allows non-`'static` lifetimes. A struct with a borrowed field will fail to compile:

```rust
// 0.18 compile error
#[derive(Resource)]
struct Ref<'a>(&'a str); // ERROR: Resource requires 'static

// Fix: own the data or use Arc<str> / String
#[derive(Resource)]
struct Owned(String);
```

## Reflect attribute syntax tightened

Only parentheses are accepted; brace or bracket forms are rejected:

```rust
// 0.17 — other forms accepted
// #[reflect[Clone]]
// #[reflect{Clone}]

// 0.18 — only parens
#[reflect(Clone)]
```

## Hierarchy helpers renamed

| 0.17 | 0.18 |
|---|---|
| `clear_children()` | `detach_all_children()` |
| `remove_children(...)` | `detach_children(...)` |

## HashMap change

```rust
// 0.17
map.get_many_mut([k1, k2])

// 0.18
map.get_disjoint_mut([k1, k2])
```

## `AnimationTarget` split

What was one component is now two:

```rust
// 0.17
commands.spawn(AnimationTarget { id, player });

// 0.18
commands.spawn((AnimationTargetId(id), AnimatedBy(player)));
```
