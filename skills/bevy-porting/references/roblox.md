# bevy-porting — Roblox → Bevy 0.18

> Referenced from `bevy-porting/SKILL.md § Engine coverage`.

Roblox is a closed-platform engine: `.rbxl` (binary) or `.rbxlx` (XML) place files, Lua/Luau scripting, Roblox Studio editor. Porting **off** Roblox to Bevy is unusual — most Roblox content is platform-locked. This reference focuses on the **data-extraction** side: getting asset metadata and scene structure out of a place file so you can recreate the game in Bevy.

## `.rbxl` vs `.rbxlx`

| Format | Parseable without Roblox? | How |
|---|---|---|
| `.rbxlx` | Yes — it's XML | stdlib `xml.etree.ElementTree`; use `scripts/roblox/rbxlx_inventory.py` |
| `.rbxl` | No — binary | Use `rbx-dom` (Rust crate) or `rojo` (Go CLI) to convert to `.rbxlx` first, then run the script |

Always save a copy as `.rbxlx` in Roblox Studio before attempting a non-Studio workflow.

## Instance model → Bevy mapping

Every Roblox `Instance` is a named, class-typed object that can have children. The model is tree-structured; Bevy flattens to ECS with `ChildOf` for hierarchy.

| Roblox | Bevy 0.18 |
|---|---|
| `Workspace` (root container) | root `Entity`; no direct equivalent — just spawn into the world |
| `Part` (box/sphere/cylinder primitive) | `Mesh3d` + `MeshMaterial3d<StandardMaterial>` + matching primitive mesh |
| `MeshPart` (custom mesh) | `Mesh3d`; extract source FBX/OBJ and convert to glTF |
| `Model` (group) | parent `Entity`; children use `ChildOf` |
| `Script` / `LocalScript` / `ModuleScript` | rewrite in Rust — Luau has no runtime bridge to Bevy |
| `Humanoid` | custom Bevy state machine; no built-in equivalent |
| `Camera` | `Camera3d` |
| `Lighting` service | `AmbientLight` + `DirectionalLight` |
| `ScreenGui` / `Frame` / `TextLabel` | Bevy `Node` tree — see **`bevy-ui`** |
| `Sound` (in workspace) | `AudioPlayer` + `PlaybackSettings` |

```rust
// Roblox: Instance.new("Part") placed in Workspace
// Bevy:
fn spawn_part(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
) {
    commands.spawn((
        Mesh3d(meshes.add(Cuboid::new(4.0, 1.0, 4.0))),
        MeshMaterial3d(materials.add(StandardMaterial {
            base_color: Color::srgb(0.5, 0.5, 0.5),
            ..default()
        })),
        Transform::from_xyz(0.0, -0.5, 0.0),
    ));
}
```

## Asset URLs

Roblox assets use `rbxassetid://12345` URLs resolved through Roblox's CDN. **Outside Roblox these URLs are useless** — you must re-source every mesh, texture, and audio asset.

Use `scripts/roblox/rbxlx_inventory.py --asset-urls-only` to get a complete list of asset IDs that need replacing:

```
python3 rbxlx_inventory.py place.rbxlx --asset-urls-only
# Output: ["rbxassetid://12345", "rbxassetid://67890", ...]
```

## Lua → Rust

| Roblox Lua/Luau | Bevy 0.18 |
|---|---|
| `Instance.new("Part")` | `commands.spawn(...)` |
| `:GetService("Workspace")` | `World` / `Query` system parameter |
| `task.wait(0.5)` | `Timer` component or a system that checks `Time::elapsed` |
| `script.Parent.Touched:Connect(fn)` | `On<E>` observer or `EventReader<CollisionEvent>` |
| `game.Players.LocalPlayer` | `Query<Entity, With<LocalPlayer>>` |
| `RunService.Heartbeat:Connect(fn)` | `Update` system |
| `RunService.RenderStepped:Connect(fn)` | `Update` system (render-side) |

```rust
// Roblox: part.Touched:Connect(function(other) takeDamage(other) end)
// Bevy (with bevy_rapier3d):
fn handle_collision(
    mut collision_events: EventReader<CollisionEvent>,
    mut health_query: Query<&mut Health>,
) {
    for event in collision_events.read() {
        if let CollisionEvent::Started(a, b, _) = event {
            if let Ok(mut hp) = health_query.get_mut(*a) { hp.0 -= 10.0; }
        }
    }
}
```

## Physics

Roblox has a built-in physics engine (Nexus/LuaU physics). Bevy has none in core. Options:

- **`bevy_rapier3d`** — wraps Rapier; feature-rich, active community.
- **`avian3d`** — Bevy-native ECS-first design.

Both provide velocity, collision events, and constraints comparable to Roblox Constraints.

## DataStore / persistence

Roblox DataStore is a server-side cloud key-value store. The Bevy equivalent is entirely up to your hosting: write to a file, a SQLite database, or a cloud API. There is no drop-in replacement.

## UI

Roblox `ScreenGui` → `Frame` → `TextLabel`/`ImageLabel`/`TextButton` hierarchy maps to a Bevy `Node` tree. Cross-link: **`bevy-ui`**.

```rust
// Roblox TextLabel → Bevy Text node
commands.spawn((
    Node { width: Val::Px(200.0), height: Val::Px(40.0), ..default() },
    Text::new("Score: 0"),
    TextFont { font_size: 24.0, ..default() },
));
```

## Using `rbxlx_inventory.py`

Full CLI:

```
python3 rbxlx_inventory.py place.rbxlx
python3 rbxlx_inventory.py place.rbxlx --out place.json
python3 rbxlx_inventory.py place.rbxlx --include-properties
python3 rbxlx_inventory.py place.rbxlx --asset-urls-only
```

Output includes an `instances` list (class, name, parent, optional properties) and an `asset_urls` list of every `rbxassetid://` URL found anywhere in the file. Use `--asset-urls-only` to scope work for the asset re-sourcing phase.

## Build / publish

Roblox publishes exclusively through the Roblox platform — it is a **one-way port**. You cannot republish a Bevy game on Roblox. For Bevy's build targets see `bevy-cargo-features`.

## Gotchas

- `Humanoid` is a complex procedural state machine for biped locomotion. There is no Bevy equivalent; plan a full custom character controller rewrite (e.g. using `bevy_rapier3d` + a custom kinematic move system).
- Roblox's `LocalScript` runs client-side; `Script` runs server-side. In a standalone Bevy game this split disappears — design your authority model from scratch.
- `rbxassetid://` URLs expire or require authentication outside Roblox. Always download assets during the extraction phase before Roblox access is lost.
- Binary `.rbxl` files cannot be inspected with stdlib tools — convert to `.rbxlx` in Studio first.
- Roblox's `Decal`, `Texture`, and `SpecialMesh` are editor-only conveniences; port each to a concrete `StandardMaterial` or custom `Mesh`.

## See also

- [`../SKILL.md`](../SKILL.md) — bevy-porting dispatcher
- [`unity-architecture.md`](unity-architecture.md) — similar OO-engine mental shift (Instance hierarchy → ECS)
- `bevy-ui` — `Node` + Taffy/flex, replacing `ScreenGui` hierarchies
- `bevy-pbr-materials` — `StandardMaterial`, `Mesh3d`, replacing `Part` + `SpecialMesh`
