# bevy-porting — Unity → Bevy 0.18 architecture

> Referenced from `bevy-porting/SKILL.md § Unity (priority)`.

## Concept map

| Unity | Bevy 0.18 |
|---|---|
| `GameObject` | `Entity` |
| `Transform` (with parent link) | `Transform` + `ChildOf` component |
| `MonoBehaviour` | `#[derive(Component)]` struct + system fn |
| `ScriptableObject` | `Asset<T>` or `Resource` (see below) |
| `Coroutine` | `Local<Timer>` or `AsyncComputeTaskPool` task |
| Tag string / Layer int | Marker component / physics collision groups |
| Singleton `MonoBehaviour` | `Resource` |
| `[ExecuteInEditMode]` / `[CustomEditor]` | Out of scope — see note |

## GameObject + Transform hierarchy → Entity + `ChildOf`

In Bevy 0.18, parent-child relationships are expressed by inserting the `ChildOf` component on the child entity. There is no separate "hierarchy field" on `Transform`.

```rust
commands.entity(child).insert(ChildOf(parent));
```

`Transform` is always **local to its parent**. The engine propagates it to `GlobalTransform` automatically in `PostUpdate` via `TransformSystems::Propagate`. Reading `GlobalTransform` before `PostUpdate` yields last frame's value — account for this if you're doing collision checks in `Update`.

## MonoBehaviour → Component + System

Unity bundles data and behaviour in one class. Bevy splits them:

- **Data** → a `#[derive(Component)]` struct.
- **Behaviour** → a system function registered on a schedule.

**Unity:**
```csharp
public class PlayerController : MonoBehaviour {
    public float speed = 5f;
    void Update() { transform.Translate(Input.GetAxis("Horizontal") * speed * Time.deltaTime, 0, 0); }
}
```

**Bevy:**
```rust
#[derive(Component)]
struct Player { speed: f32 }

fn move_players(
    mut query: Query<(&Player, &mut Transform)>,
    input: Res<ButtonInput<KeyCode>>,
    time: Res<Time>,
) {
    for (player, mut transform) in &mut query {
        let dir = if input.pressed(KeyCode::ArrowRight) { 1.0 } else { -1.0 };
        transform.translation.x += dir * player.speed * time.delta_secs();
    }
}

// In your plugin / main:
app.add_systems(Update, move_players);
```

`Start()` maps to a `Startup` system or an `Added<Player>` query filter. `OnDestroy()` maps to `ComponentHooks::on_remove`.

## Update() / FixedUpdate() → Bevy schedules

The semantic split is identical:

- `Update` — every frame, variable timestep. Use `time.delta_secs()`.
- `FixedUpdate` — fixed timestep (default 64 Hz). Use `Time<Fixed>` for interpolation.

```rust
app.add_systems(FixedUpdate, apply_physics);
app.add_systems(Update, interpolate_visuals);
```

See `bevy-core-concepts` for schedule ordering and `Time<Fixed>` usage.

## ScriptableObject → `Asset` or `Resource`

Two Bevy idioms depending on how you used the SO:

| ScriptableObject pattern | Bevy idiom |
|---|---|
| Shared config loaded from a file, hot-reloadable | `Asset<T>` via `AssetServer` |
| Runtime singleton / global state | `Resource` |

Decision rubric: **"Do you want hot-reload or load from disk?"** → `Asset`. **"Is it the global authoritative runtime state?"** → `Resource`.

```rust
// Asset path: implement AssetLoader, load with AssetServer
let config: Handle<WeaponConfig> = asset_server.load("config/weapons.ron");

// Resource path: insert directly
app.insert_resource(GameSettings { difficulty: 3 });
```

See `bevy-custom-assets` for the `AssetLoader` pattern.

## Coroutines → `Local<Timer>` or task pools

Unity coroutines cover two distinct use cases in Bevy:

**Frame-paced delays / timers** — use `Local<Timer>`. This is the idiomatic path for `yield return new WaitForSeconds(...)`.

```rust
fn spawn_waves(mut timer: Local<Timer>, time: Res<Time>, mut commands: Commands) {
    timer.tick(time.delta());
    if timer.just_finished() {
        commands.spawn(EnemyBundle::default());
        *timer = Timer::from_seconds(5.0, TimerMode::Once);
    }
}
```

**IO-bound async work** (file reads, network) → `IoTaskPool::get().spawn(...)`. Results are sent back via a `Sender`/`Receiver` pair polled in a system.

**CPU-bound async work** (pathfinding, chunk gen) → `AsyncComputeTaskPool::get().spawn(...)`.

There is no `yield return null` equivalent — Bevy runs systems as plain functions each frame. For multi-frame sequencing, track state in a `Component` or `Resource` and use `if` / `match` branches.

## Tags / Layers → marker components / collision groups

```rust
// Unity: gameObject.tag = "Enemy"
// Bevy:
#[derive(Component)] struct Enemy;
commands.entity(e).insert(Enemy);

// Query by marker
fn despawn_enemies(mut commands: Commands, query: Query<Entity, With<Enemy>>) { ... }
```

Unity's layer collision matrix → your physics plugin's collision groups. With `bevy_rapier3d`:

```rust
CollisionGroups::new(Group::GROUP_2, Group::GROUP_1)
```

Consult the `bevy_rapier3d` or `avian` docs for exact group APIs.

## Singleton MonoBehaviour → `Resource`

`static T Instance` does not translate to Bevy. Use `Resource`:

```rust
#[derive(Resource)] struct AudioManager { ... }
app.insert_resource(AudioManager::new());

// Access in any system:
fn play_sfx(audio: Res<AudioManager>) { ... }
```

## Editor scripts (`[ExecuteInEditMode]`, `[CustomEditor]`)

Bevy's editor story (`bevy_editor`) is under active development and not stable in 0.18. Skip porting editor-only code for now; implement runtime equivalents where needed.

## See also

- [`../SKILL.md`](../SKILL.md) — bevy-porting dispatcher
- [`unity-assets.md`](unity-assets.md) — asset pipeline mapping
- [`unity-scenes-gltf.md`](unity-scenes-gltf.md) — scene extraction and glTF bridge
- `bevy-core-concepts` — schedules, `Time<Fixed>`, `Update` vs `FixedUpdate`
- `bevy-ecs-components` — `#[derive(Component)]`, required components, hooks
- `bevy-ecs-systems` — system registration, ordering, observers
