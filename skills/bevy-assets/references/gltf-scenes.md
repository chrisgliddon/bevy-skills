# glTF scenes in Bevy 0.19

Bevy 0.19 loads a glTF scene sub-asset as `Handle<WorldAsset>` and instantiates it
with `WorldAssetRoot`. Classic glTF scenes still use `bevy_world_serialization`; they
did not become BSN scenes merely because `bevy_scene` now hosts BSN.

## Load the intended asset type

```rust
use bevy::prelude::*;

fn spawn_model(mut commands: Commands, assets: Res<AssetServer>) {
    let scene: Handle<WorldAsset> = assets.load(
        GltfAssetLabel::Scene(0).from_asset("models/level.glb"),
    );

    commands.spawn((
        Name::new("Level instance"),
        WorldAssetRoot(scene),
        Transform::default(),
    ));
}
```

`GltfAssetLabel` also addresses nodes, meshes, primitives, textures, materials,
animations, skins, and inverse bind matrices. Prefer it over hand-built `#Scene0`
strings. Loading the bare `.glb` as `Handle<Gltf>` gives the root index asset, whose
fields include scenes/named scenes, meshes/named meshes, materials/named materials,
nodes/named nodes, skins, and—when animation is enabled—animations.

Scene indices and author names can change when the source file is edited. Use them to
select authored data, but use explicit semantic IDs for durable save/gameplay links.

## Observe instance readiness

Asset `LoadState::Loaded` says the asset and dependencies loaded; it does not give an
instance's spawned entity graph. Observe `WorldInstanceReady`, which targets the root
and carries the `InstanceId`:

```rust
use bevy::{prelude::*, world_serialization::{WorldInstanceReady, WorldInstanceSpawner}};

fn on_world_ready(
    ready: On<WorldInstanceReady>,
    spawner: Res<WorldInstanceSpawner>,
    metadata: Query<(Option<&Name>, Option<&bevy::gltf::GltfExtras>)>,
) {
    for entity in spawner.iter_instance_entities(ready.instance_id) {
        if let Ok((name, extras)) = metadata.get(entity) {
            let _authored_data = (name.map(Name::as_str), extras.map(|x| x.value.as_str()));
        }
    }
}
```

Install this with `.add_observer(on_world_ready)`. `iter_instance_entities` follows
instance ownership even if an entity was moved out of the root hierarchy; walking
`Children::iter_descendants(ready.entity)` is simpler when hierarchy membership is
the intended contract.

Observers can run again after root replacement/hot reload. Make extraction
idempotent, remove old derived state, and key caches by instance/lifetime rather than
assuming readiness fires once for a path.

## Names, extras, and semantic metadata

Spawned glTF entities may carry:

- Bevy `Name` and glTF-specific `GltfSceneName`/`GltfMeshName`/
  `GltfMaterialName` components;
- `GltfExtras`, `GltfSceneExtras`, `GltfMeshExtras`, and `GltfMaterialExtras`, whose
  `value` is JSON text from glTF `extras`.

Names are excellent for debugging and artist workflows but brittle as gameplay IDs.
Put namespaced, versioned semantic data in extras, for example:

```json
{
  "game": {
    "schema": 1,
    "id": "base:level/atrium/door-west",
    "kind": "door",
    "collider": "box"
  }
}
```

Parse extras into a typed DTO, validate schema/IDs/limits, then add product-owned
components. Reject duplicate semantic IDs in an instance. Keep the source JSON only
as authoring input; gameplay systems query typed components.

## Extract authored proxies safely

At `WorldInstanceReady`:

1. iterate instance entities and parse typed metadata;
2. collect/validate all IDs and references before mutation;
3. create colliders, interaction points, spawn markers, nav volumes, or sockets;
4. hide/remove proxy render components if they are authoring-only;
5. mark the root/instance with the extraction schema and outcome.

Account for full `GlobalTransform` and primitive scale when generating colliders.
Prefer simple authored primitives over runtime triangle-mesh colliders for dynamic
objects. If derived entities are spawned separately, parent them under an owned root
or record an explicit `OwnedByWorldInstance` relationship so unload cannot leak them.

glTF materials are assets and can be shared across instances. Clone a material before
an instance-specific mutation; changing the shared asset recolours every user. The
official Bevy example follows this pattern.

## Clean despawning and ownership

`WorldAssetRoot` receives `WorldInstance` after spawning. If every spawned entity
stays in its hierarchy, despawning the root removes that hierarchy. If entities were
reparented/moved, use the instance registry to remove every associated entity:

```rust
use bevy::{prelude::*, world_serialization::{WorldInstance, WorldInstanceSpawner}};

fn unload_world(
    mut commands: Commands,
    roots: Query<(Entity, &WorldInstance), With<UnloadRequested>>,
    mut spawner: ResMut<WorldInstanceSpawner>,
) {
    for (root, instance) in &roots {
        spawner.despawn_instance(**instance);
        commands.entity(root).despawn();
    }
}

#[derive(Component)]
struct UnloadRequested;
```

`despawn_instance` is deferred and removes all registered instance entities, including
ones no longer under the root. Product-spawned derived entities are not automatically
in that map; keep their ownership explicit. Do not retain raw spawned `Entity` IDs in
save files or across instance replacement.

## Readiness and lifecycle tests

- load two instances of one glTF and verify instance-specific material/proxy state;
- verify duplicate/malformed/unknown extras fail without partial extraction;
- replace/hot-reload the root and ensure extraction is idempotent;
- reparent a spawned entity, unload through `InstanceId`, and assert no leak;
- unload before readiness and verify no late observer resurrects derived state;
- test missing optional names/extras and authoring-order changes.

Primary references:

- [Bevy glTF module](https://docs.rs/bevy/0.19.0/bevy/gltf/index.html)
- [Material editing example](https://github.com/bevyengine/bevy/blob/v0.19.0/examples/gltf/edit_material_on_gltf.rs)
- [glTF extras example](https://github.com/bevyengine/bevy/blob/v0.19.0/examples/gltf/load_gltf_extras.rs)
- [glTF loading example](https://github.com/bevyengine/bevy/blob/v0.19.0/examples/gltf/load_gltf.rs)
