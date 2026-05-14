# similarity-rs 0.5 — LLM Duplication Antipatterns

These are the patterns `similarity-rs --cross-file` catches most often in
LLM-generated Rust code.

---

## 1. One-off utility that already exists in `std` or a dep

**Why it happens:** The model generates from training-data patterns instead of
checking what the project already imports.

```rust
// BEFORE — agent wrote a custom clamp helper
fn clamp_f32(val: f32, lo: f32, hi: f32) -> f32 {
    if val < lo { lo } else if val > hi { hi } else { val }
}

// AFTER — std already provides this
let v = val.clamp(lo, hi);  // f32::clamp, stable since 1.50
```

**Check first:** `rg "fn clamp"` and `cargo doc --open --package <dep>` before writing anything.

---

## 2. Copy-paste-modify (90 % similar, different cosmetic detail)

A function is duplicated with a variable rename or a single constant changed.
The duplication is invisible until you diff the two.

```rust
// BEFORE — two functions, both do the same thing with different magic numbers
fn lerp_color_a(a: Vec3, b: Vec3, t: f32) -> Vec3 {
    a + (b - a) * t.clamp(0.0, 1.0)
}

fn lerp_color_b(a: Vec3, b: Vec3, t: f32) -> Vec3 {
    a + (b - a) * t.clamp(0.0, 1.0)  // identical body — different name only
}

// AFTER — one function
fn lerp(a: Vec3, b: Vec3, t: f32) -> Vec3 {
    a + (b - a) * t.clamp(0.0, 1.0)
}
```

`similarity-rs --cross-file` flags these with a score near 1.0.

---

## 3. Near-duplicate enums from uncoordinated feature additions

Two features are added at different points; each agent session creates a new
enum without noticing the existing one.

```rust
// BEFORE — two enums, written months apart, covering the same domain
enum GamePhase { Setup, Running, Paused, GameOver }
enum AppState  { Init, Playing, Paused, Done }       // overlapping intent

// AFTER — one enum, variants merged thoughtfully
enum AppState { Setup, Playing, Paused, GameOver }
```

`similarity-rs` will flag the structural similarity; the merge decision still
requires human judgment.

---

## 4. Multiple "init" functions that share scaffolding

Each system `setup_X` spawns a camera, adds lighting, and then does something
specific. The first 10 lines are copy-paste across three files.

```rust
// BEFORE — three setup functions, all start identically
fn setup_main_menu(mut commands: Commands) {
    commands.spawn(Camera3d::default());
    commands.spawn(DirectionalLight::default());
    // ... menu-specific spawning
}

fn setup_gameplay(mut commands: Commands) {
    commands.spawn(Camera3d::default());
    commands.spawn(DirectionalLight::default());
    // ... gameplay-specific spawning
}

// AFTER — extract the shared scaffolding
fn spawn_scene_defaults(commands: &mut Commands) {
    commands.spawn(Camera3d::default());
    commands.spawn(DirectionalLight::default());
}

fn setup_main_menu(mut commands: Commands) {
    spawn_scene_defaults(&mut commands);
    // ... menu-specific spawning
}

fn setup_gameplay(mut commands: Commands) {
    spawn_scene_defaults(&mut commands);
    // ... gameplay-specific spawning
}
```

---

## 5. "I'll just inline this here" when the helper exists three modules over

The agent writes a new private helper in `rendering.rs` without checking
`utils.rs`, where the same logic lives.

**Workflow to prevent this:**

```bash
rg "fn <verb>" src/          # broad first pass
rg "fn <verb>" src/utils.rs  # check the most likely home
```

If found: import and reuse. If not: write it in `utils.rs`, not inline.

---

## 6. Bevy-specific: duplicate `Plugin` setup

Two plugins both register `Update` systems and insert the same `Resource`
without knowing about each other.

```rust
// BEFORE — both plugins insert a Transform resource and register a camera system
impl Plugin for MenuPlugin {
    fn build(&self, app: &mut App) {
        app.insert_resource(CameraConfig::default())
           .add_systems(Update, update_menu_camera);
    }
}

impl Plugin for HudPlugin {
    fn build(&self, app: &mut App) {
        app.insert_resource(CameraConfig::default())  // duplicated
           .add_systems(Update, update_hud_camera);
    }
}

// AFTER — move shared resource to a shared plugin (e.g., CorePlugin)
```

---

## 7. Bevy-specific: similar systems with different `Query` filters

Two systems share identical body logic and differ only in which component they
query. Consider a generic system or a shared helper.

```rust
// BEFORE
fn move_enemies(mut q: Query<&mut Transform, With<Enemy>>) { /* body */ }
fn move_allies (mut q: Query<&mut Transform, With<Ally>>)  { /* body */ }

// AFTER — if the body is truly identical, unify with a marker trait or
// pass through a shared helper function that takes &mut Transform
```

---

## 8. Bevy-specific: repeated `commands.spawn(...)` bundles

Spawning the same multi-component tuple in three places instead of defining a
`Bundle`.

```rust
// BEFORE — repeated in setup_level, spawn_pickup, and tests
commands.spawn((
    Mesh3d(meshes.add(Sphere::new(0.3).mesh())),
    MeshMaterial3d(materials.add(StandardMaterial {
        base_color: Color::srgb(0.8, 0.2, 0.2),
        ..default()
    })),
    PickupMarker,
));

// AFTER — define a bundle
#[derive(Bundle)]
struct PickupBundle {
    mesh: Mesh3d,
    material: MeshMaterial3d<StandardMaterial>,
    marker: PickupMarker,
}
```
