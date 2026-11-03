# bevy-porting — Unreal Engine 5 → Bevy 0.20

> Referenced from `bevy-porting/SKILL.md § Engine coverage`.

## Concept map

| Unreal Engine 5 | Bevy 0.20 |
|---|---|
| `AActor` | `Entity` + a bundle of `Component`s |
| `UActorComponent` | Single `#[derive(Component)]` struct |
| `UWorld` | `World` (Bevy ECS) |
| `GameMode` / `GameState` | `Resource`s + systems |
| `PlayerController` | Input systems + a player `Entity` |
| Blueprint graph | Plain Rust `fn` systems — no direct equivalent |
| `FName` / asset path | Path-based `Handle<T>` via `AssetServer` |
| `USubsystem` | `Resource` + a `Plugin` that inserts it |

Coordinate system: Unreal is **left-handed Z-up**; Bevy is **right-handed Y-up** (matches glTF).
Most exporters handle the conversion — spot-check with an asymmetric asset.

## Lifecycle hooks

| Unreal | Bevy 0.20 |
|---|---|
| `BeginPlay()` | `Startup` schedule system or `Added<C>` query filter |
| `Tick(float DeltaTime)` | `Update` system with `time: Res<Time>` → `time.delta_secs()` |
| `EndPlay(EEndPlayReason)` | `On<Remove<C>>` observer (0.20 form: bundle generic on the event, not on `On`) |

```rust
// BeginPlay equivalent — runs once when the component is added.
// Stale output: `Trigger<OnAdd, MyActor>` (≤0.16) or `On<Add, MyActor>` (0.17–0.19).
fn on_actor_added(add: On<Add<MyActor>>, mut commands: Commands) {
    let _ = (add.entity, &mut commands); // initialise state
}

// Tick equivalent
fn tick_actors(mut query: Query<(&MyActor, &mut Transform)>, time: Res<Time>) {
    for (actor, mut tf) in &mut query {
        tf.translation.x += actor.speed * time.delta_secs();
    }
}
```

## Subsystems → `Resource` + `Plugin`

`UGameInstanceSubsystem` and `ULocalPlayerSubsystem` are singletons scoped to a game instance or player. In Bevy, model them as a `Resource` registered by a `Plugin`:

```rust
#[derive(Resource, Default)]
pub struct SaveSystem { pub slot: u32 }

pub struct SavePlugin;
impl Plugin for SavePlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<SaveSystem>()
           .add_systems(Update, autosave_system);
    }
}
```

## Blueprints → Rust systems

Blueprints compile to bytecode and have no Bevy equivalent. Port gameplay logic as free Rust `fn`s added to a schedule. Editor tooling from Blueprints is out of scope — Bevy 0.20 has no shipped scene editor (only Feathers widgets and `PanOrbitCamera` building blocks).

## UMG UI → `bevy_ui`

Unreal Motion Graphics widgets map to Bevy's `Node`-based UI backed by Taffy (flexbox). The mental model is the same as Unity UGUI → `bevy_ui`. See the **`bevy-ui`** skill.

## Materials

Unreal's Material Editor compiles node graphs to HLSL. Bevy equivalents:

- **PBR basics** → `StandardMaterial` (metallic/roughness workflow, same as UE5 defaults).
- **Custom node graph** → write a custom `Material` impl (trait now in `bevy_material`, 0.19) with WESL shaders (`.wesl`, `import …;`, `@if(..)` — the naga_oil `#import` preprocessor is gone in 0.20).
- **Clearcoat, anisotropy, specular tint** — `StandardMaterial` fields in 0.20; **subsurface** still needs a custom material.

Cross-link: **`bevy-pbr-materials`**.

## Animation Blueprint / State Machine → `AnimationGraph`

| Unreal | Bevy 0.20 |
|---|---|
| `Animation Blueprint` | `AnimationGraph` asset |
| State machine layer | `AnimationTransitions` + state-driving system |
| Blend space | `AnimationGraph` blend node |
| `Notify` events | `#[derive(AnimationEvent)]` + `On<E>` observer |

Export skeletal meshes to glTF (via Datasmith or the built-in glTF Exporter plugin), then load with `bevy_gltf`. Cross-link: **`bevy-animation`**.

## Niagara / Cascade VFX

Bevy 0.20 has no built-in GPU particle system equivalent to Niagara. The community crate **`bevy_hanabi`** (0.20.0 targets Bevy 0.20) provides GPU particle graphs and covers most Cascade / Niagara use cases.

## Level export (`.umap`)

`.umap` is a binary Unreal format — do not parse directly. Recommended pipeline:

1. Install the **glTF Exporter** plugin (or Datasmith) in the UE5 editor.
2. Export each level to glTF.
3. Load in Bevy via `AssetServer::load` + `bevy_gltf`.

Level streaming has no direct Bevy equivalent. Implement via `AssetServer` loading of `WorldAssetRoot` scenes with boundary triggers driving `spawn` / `despawn`.

Use **`scripts/unreal/ue5_python_export.py`** (drop into `<Project>/Content/Python/`, run from UE5's Output Log Python console) to extract actor and asset metadata to JSON before the glTF export step.

## Build pipeline

| Unreal | Bevy 0.20 |
|---|---|
| Package Project (per-platform) | `cargo build --target <triple>` |
| `DefaultEngine.ini` feature switches | `Cargo.toml` `[features]` |
| PS5 / Xbox / Switch | Not supported in Bevy 0.20 |

Cross-link: **`bevy-cargo-features`**.

## Gotchas

- Bevy uses **right-handed Y-up**; UE5 uses left-handed Z-up. Verify your exporter flips axes.
- Unreal's FName string pool has no Bevy equivalent — use path handles or marker components.
- `PlayerController` possession / unpossession is a pure design pattern in Bevy; implement with a marker component + a query filter.
- Blueprint-only projects have zero direct code to port; budget extra time for logic reconstruction.
- Subsurface scattering requires a custom material in WESL — not available out-of-the-box in 0.20.

## See also

- [`../SKILL.md`](../SKILL.md) — bevy-porting dispatcher
- `bevy-animation` — `AnimationGraph`, `AnimationTransitions`, `#[derive(AnimationEvent)]`
- `bevy-pbr-materials` — `StandardMaterial`, custom `Material` with WESL
- `bevy-ui` — `Node` + Taffy/flex, replacing UMG widgets
- `bevy-cargo-features` — replaces Unreal's per-platform packaging pipeline
