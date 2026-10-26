# Bevy 0.20 readiness — staged update

The maintained [coverage, source evidence, verification inventory, and remaining gates](../skills/bevy/references/bevy-020-readiness.md)
live inside the distributed skills tree so installations that copy only `skills/`
retain the same record.

As of 26 October 2026, published Rapier 0.37.0 resolves the Bevy 0.20 physics
release-availability gate. The migration guide and physics guidance are source-reviewed;
Rust compile/runtime verification is still **pending**. General implementation skills
and plugin release metadata remain on the explicit Bevy 0.19 baseline.

This supersedes the dependency-blocker status in [draft plan PR #24](https://github.com/chrisgliddon/bevy-skills/pull/24),
not its historical project assessment. No game projects or companion repository were
changed, and no GitHub Actions workflow was added or enabled.
