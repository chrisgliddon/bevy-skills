# Preserved Bevy 0.19 / Rapier 0.36 path

Use this path when the application is staying on **Bevy 0.19**. The current
`bevy-physics` skill now targets Bevy 0.20 / `bevy_rapier` 0.37; do not copy its
dependency pair into a 0.19 application.

```toml
[dependencies]
bevy = "0.19"
bevy_rapier3d = "0.36"
```

The preserved guidance is pinned to repository commit
`b1b4da5744ebbd5c526342b2351967411cd5ca61` so later edits cannot silently retarget it:

- [Canonical 0.19 physics skill](https://github.com/chrisgliddon/bevy-skills/blob/b1b4da5744ebbd5c526342b2351967411cd5ca61/skills/bevy-physics/SKILL.md)
- [0.19 physics reference directory](https://github.com/chrisgliddon/bevy-skills/tree/b1b4da5744ebbd5c526342b2351967411cd5ca61/skills/bevy-physics/references)
- [Published 0.36.0 manifest](https://docs.rs/crate/bevy_rapier3d/0.36.0/source/Cargo.toml)

Preservation is not a new compile-validation claim. The current rendering, porting,
and camera/orbit skills still use their explicitly pinned 0.19 / Rapier 0.36 examples.
The old unused `headless` feature may occur there; 0.37 removes it. Avian 0.7 is
likewise an older Bevy 0.19 recommendation, not established 0.20 compatibility.

When upgrading, follow the [Bevy 0.19→0.20 skill](../../bevy-migration-0-19-to-0-20/SKILL.md)
and [Rapier 0.36→0.37 checklist](rapier-036-to-037.md) together, then validate the
application's actual features, targets, and behavior.
