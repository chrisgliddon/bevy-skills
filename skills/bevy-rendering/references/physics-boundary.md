# Physics is not rendering

`bevy_rapier3d` owns collision detection, rigid-body integration, joints, queries, and
optional debug visualization. It does not shade meshes or replace Bevy's renderer.

## Bevy 0.20 pairing

`bevy_rapier3d 0.37` declares `bevy 0.20` (`0.36` is the Bevy 0.19 line). Its default features include async
colliders, Bevy debug rendering, picking integration, and mesh conversion. Those are
convenient in a built-in-renderer game but can pull render crates into a server or
external-renderer build.

```toml
# Ordinary Bevy-rendered game.
bevy_rapier3d = "0.37"

# No Bevy renderer/debug drawing. (The 0.36 `headless` feature was removed in 0.37.)
bevy_rapier3d = { version = "0.37", default-features = false, features = [
  "dim3"
] }
```

Inspect `cargo tree -e features` after choosing features. Cargo unifies features, so
another dependency may still enable Rapier's render-related defaults.

For rigid bodies, colliders, collision groups/messages, scene queries, character
controllers, joints, timestep configuration, and tests, load
[`bevy-physics`](../../bevy-physics/SKILL.md). This reference only defines the
renderer boundary.

## Transform authority

Choose one policy per entity class:

- dynamic rigid body: physics writes authoritative simulation pose;
- kinematic controller: gameplay supplies the next kinematic pose;
- static collider: authored transform changes rarely and is synchronized explicitly;
- visual child: render-only interpolation/offset follows the physics parent.

Do not let a render interpolation system write the same authoritative transform as the
physics step. A common layout is a physics root with collider/body components and a
visual child whose local transform handles smoothing or model offsets.

## Scheduling

Rapier defaults to `PostUpdate` with a variable timestep. If the game needs a
tick-coupled simulation, explicitly place Rapier in `FixedUpdate`, match its `dt` to
Bevy's fixed clock, consume actions before the physics sets, and react after writeback.
Rendering may run at another cadence and must not change collision results.

## Debug drawing

Rapier's debug renderer is diagnostic only. Keep it behind a project development
feature and remove it from shipping/headless artifacts. An external renderer can draw
collider shapes from its own bridge without enabling Bevy PBR/gizmos.

## Sources

- [`bevy_rapier3d` crate](https://crates.io/crates/bevy_rapier3d/0.37.0)
- [Rapier user guide](https://rapier.rs/docs/user_guides/bevy_plugin/getting_started_bevy/)
- [`bevy-core-concepts`](../../bevy-core-concepts/SKILL.md)
