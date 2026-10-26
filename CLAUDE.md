# CLAUDE.md — Guidance for agents editing this repo

## What this repo is

A collection of Agent Skills with a **Bevy 0.19 general baseline** and staged
**Bevy 0.20 migration / Rapier 0.37 physics guidance**. Each skill is a folder under `skills/<skill-name>/` containing `SKILL.md` (YAML frontmatter + markdown body) and optional `references/` for long-form deep dives.

The skills target multiple consumers (Claude Code, OpenCode, Cursor, Codex). Conformance to **both** the [Anthropic Agent Skills spec](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/skills) and the [OpenCode Agent Skills spec](https://opencode.ai/docs/skills/) is mandatory.

## Hard rules for every SKILL.md

1. **Frontmatter shape** — only these keys, in any order:
   ```yaml
   ---
   name: bevy-<area>           # ^[a-z0-9]+(-[a-z0-9]+)*$, 1–64 chars, equals directory name
   description: <triggers>     # 1–1024 chars, must include the target version
   license: MIT
   compatibility: opencode,claude-code,cursor
   metadata:
     tier: "1"                 # 1 (router/foundational), 2 (hot path), 3 (MMO), 4 (depth)
     area: <ecs|render|asset|net|...>
     bevy_version: "0.19"        # actual implementation target
     # target_version: "Bevy 0.20" # required override for staged 0.20 skills
   ---
   ```

2. **Description writes triggers, not workflow.** Name ≥3 concrete API symbols or error symptoms. Agents trigger on this field — vague descriptions cause silent non-loading. Bad: "Helps with ECS components." Good: "Use when defining `#[derive(Component)]`, declaring required components with `#[require(...)]`, or hitting `ComponentHooks::on_add` in Bevy 0.19."

3. **Version-pinned, always.** Every implementation skill body opens with its
   actual Bevy target in the heading. The general baseline remains "Bevy 0.19";
   `bevy-physics` targets "Bevy 0.20" and sets `metadata.target_version` for the
   linter. Migration skills name both source and target and set that override too.
   Keep description, metadata, heading, dependencies, and references consistent.
   Historical migration guides retain their original target pins. Document changed
   APIs in Gotchas; cross-links to 0.19 skills are not 0.20 compatibility evidence.

4. **Code first, prose last.** Open the body with a working, copy-pasteable snippet. Prose explains the snippet, not the other way around.

5. **One concept per skill.** Resist splitting "components" into 6 sub-skills. Resist bundling "ECS" into one mega-skill. If you can't write the description in one sentence with ≥3 concrete triggers, the skill scope is wrong.

6. **Under 200 lines per `SKILL.md`.** Move deep reference to `references/<deep-dive>.md` and link from the body.

7. **Cross-link.** "See also" must list ≥2 sibling skills. If you can't, the skill is probably not atomic.

## Workflow for adding or editing a skill

1. **Verify APIs.** Use the skill’s declared Bevy/plugin versions in `bevy-skills-tester` (a separate sibling repo, see below), or consult version-pinned official docs and released source. The general baseline uses <https://docs.rs/bevy/0.19.1>; the staged physics slice uses Bevy 0.20 and `bevy_rapier3d 0.37.0`. Read [0.20 readiness](docs/bevy-020-readiness.md). Do not trust training data or a moving `latest` page as a permanent pin.

2. **Write the snippet first.** Mirror it to `bevy-skills-tester/examples/<skill_name>.rs` (hyphens → underscores). Compile against the declared engine/plugin versions with `cargo check --example <skill_name>`. Record the fixture revision, toolchain, target, features, lockfile, and result. If tooling/access is unavailable, record the gap and keep the PR draft rather than claiming a pass.

3. **Write the `SKILL.md` body around the snippet.** Sections in this order:
   - `## When to use this skill` — bullet list of triggering situations and symptoms.
   - `## Canonical pattern` — the code block.
   - `## Gotchas` — version-specific traps, migration changes, common LLM mistakes from stale training data.
   - `## See also` — sibling skills and `references/` entries.

4. **Lint the frontmatter.** Run `python3 scripts/lint-skills.py --strict` (or pass `skills/<skill>/SKILL.md` for a focused check). Run affected Python tests. This repository currently has no committed GitHub Actions workflow; do not claim PR CI ran or add/enable automation without authorization.

5. **Cross-check the router.** If the new skill belongs in a Tier the `bevy` router lists, add it to that index.

## The companion tester crate

The documented compile-verification workflow uses a sibling repo: `bevy-skills-tester` at `../bevy-skills-tester` (relative to a typical checkout). It is **intentionally not vendored** into this repo — pulling Bevy + its dependency graph would force every docs contributor to compile hundreds of crates to validate a one-line description fix. The lint script checks frontmatter only; an actual tester run is needed to establish snippet compilation.

The documented location is <https://github.com/chrisgliddon/bevy-skills-tester>.
Confirm access and the fixture revision before relying on it. If unavailable, report
that exact limitation; do not infer that every snippet has already been compiled.
Use `examples/<skill_name>.rs` as the intended fixture layout, and inventory linked
reference snippets separately. A replacement harness needs explicit dependency,
feature, and toolchain pins; merely creating a manifest is not compile coverage.

## What `description` should look like

A good description names APIs Claude would search for and symptoms Claude would encounter. Examples from this collection:

> "Use when defining `Component`s, using `#[require(...)]` for required components, registering `on_add`/`on_remove` hooks, or choosing between `#[component(storage = \"Table\")]` and `\"SparseSet\"` in Bevy 0.19."

> "Use when writing a custom `AssetLoader`, depending on other assets via `LoadContext::load`, or handling async asset loading for `.gltf`, `.ron`, or custom binary formats in Bevy 0.19."

The description is the product. The body is a fallback for when the description matched.

## Quality gate — every PR must pass

1. `python3 scripts/lint-skills.py` clean (frontmatter valid).
2. For any new or changed Rust code block: a matching `bevy-skills-tester/examples/<skill_name>.rs` fixture compiles under its declared Bevy/plugin versions. Unavailable compilation remains an open gate, not a successful check.
3. Skill body ≤200 lines; longer content moved to `references/`.
4. Description contains its actual target version verbatim (`Bevy 0.19` by default;
   `metadata.target_version` overrides staged/historical targets) and names ≥3 triggers.
5. `## See also` lists ≥2 sibling skills.

## Persistent task tracking

- Use `dex` for multi-step work: `dex list --ready`, `dex show <id> --full`, then `dex start <id>`.
- Write ticket-quality descriptions with context, approach, and explicit done criteria. Never put ephemeral Dex task IDs in commits, docs, or PR text.
- `.dex/config.toml` stores tasks in the repository and enables GitHub sync on every mutation. Dex uses `GITHUB_TOKEN` when set and otherwise the authenticated `gh` CLI.
- Complete a task only after verification, recording concrete evidence with `dex complete <id> --result "..." --commit <sha>` (or `--no-commit` only for genuinely non-code work).

## Maintenance cadence

- **Bevy release (~quarterly):** Add the next `bevy-migration-*` hop, verify plugin compatibility, and migrate implementation skills in tested slices. Preserve historical guides. Re-run the intended compile/runtime matrix before advancing the general baseline or plugin release metadata; never bulk-relabel unverified examples.
- **Continuous:** When a real-world Bevy gotcha hits, add it to the most relevant skill's Gotchas. The collection grows from friction, not speculation.
