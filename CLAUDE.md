# CLAUDE.md — Guidance for agents editing this repo

## What this repo is

A collection of Agent Skills for **Bevy 0.18**. Each skill is a folder under `skills/<skill-name>/` containing `SKILL.md` (YAML frontmatter + markdown body) and optional `references/` for long-form deep dives.

The skills target multiple consumers (Claude Code, OpenCode, Cursor, Codex). Conformance to **both** the [Anthropic Agent Skills spec](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/skills) and the [OpenCode Agent Skills spec](https://opencode.ai/docs/skills/) is mandatory.

## Hard rules for every SKILL.md

1. **Frontmatter shape** — only these keys, in any order:
   ```yaml
   ---
   name: bevy-<area>           # ^[a-z0-9]+(-[a-z0-9]+)*$, 1–64 chars, equals directory name
   description: <triggers>     # 1–1024 chars, must include "Bevy 0.18"
   license: MIT
   compatibility: opencode,claude-code,cursor
   metadata:
     tier: "1"                 # 1 (router/foundational), 2 (hot path), 3 (MMO), 4 (depth)
     area: <ecs|render|asset|net|...>
     bevy_version: "0.18"
   ---
   ```

2. **Description writes triggers, not workflow.** Name ≥3 concrete API symbols or error symptoms. Agents trigger on this field — vague descriptions cause silent non-loading. Bad: "Helps with ECS components." Good: "Use when defining `#[derive(Component)]`, declaring required components with `#[require(...)]`, or hitting `ComponentHooks::on_add` in Bevy 0.18."

3. **Version-pinned, always.** Every skill body opens with a "Bevy 0.18" heading. Every API is version-honest. If an API changed in 0.18, say so in the Gotchas section.

4. **Code first, prose last.** Open the body with a working, copy-pasteable snippet. Prose explains the snippet, not the other way around.

5. **One concept per skill.** Resist splitting "components" into 6 sub-skills. Resist bundling "ECS" into one mega-skill. If you can't write the description in one sentence with ≥3 concrete triggers, the skill scope is wrong.

6. **Under 200 lines per `SKILL.md`.** Move deep reference to `references/<deep-dive>.md` and link from the body.

7. **Cross-link.** "See also" must list ≥2 sibling skills. If you can't, the skill is probably not atomic.

## Workflow for adding or editing a skill

1. **Verify APIs.** Run `cargo doc --open` against `bevy = "0.18"` in the `bevy-skills-tester` crate (a separate sibling repo, see below) or browse https://docs.rs/bevy/0.18 . Do not trust your training data — Bevy moves fast.

2. **Write the snippet first.** Mirror it to `bevy-skills-tester/examples/<skill_name>.rs` (hyphens → underscores). Run `cargo check --example <skill_name>` until clean.

3. **Write the `SKILL.md` body around the snippet.** Sections in this order:
   - `## When to use this skill` — bullet list of triggering situations and symptoms.
   - `## Canonical pattern` — the code block.
   - `## Gotchas` — version-specific traps, 0.17→0.18 changes, common LLM mistakes from stale training data.
   - `## See also` — sibling skills and `references/` entries.

4. **Lint the frontmatter.** Run `scripts/lint-skills.py` (or `python3 scripts/lint-skills.py skills/<skill>/SKILL.md`). CI runs this on every PR.

5. **Cross-check the router.** If the new skill belongs in a Tier the `bevy` router lists, add it to that index.

## The companion tester crate

Compile verification lives in a sibling repo: `bevy-skills-tester` at `../bevy-skills-tester` (relative to a typical checkout). It is **intentionally not vendored** into this repo — pulling Bevy + its dependency graph would force every docs contributor to compile hundreds of crates to validate a one-line description fix. The lint script enforces frontmatter; the tester crate enforces snippets compile.

If you don't have the tester crate locally, clone it from <https://github.com/chrisgliddon/bevy-skills-tester> (or create it from scratch — its `Cargo.toml` is six lines).

## What `description` should look like

A good description names APIs Claude would search for and symptoms Claude would encounter. Examples from this collection:

> "Use when defining `Component`s, using `#[require(...)]` for required components, registering `on_add`/`on_remove` hooks, or choosing between `#[component(storage = \"Table\")]` and `\"SparseSet\"` in Bevy 0.18."

> "Use when writing a custom `AssetLoader`, depending on other assets via `LoadContext::load`, or handling async asset loading for `.gltf`, `.ron`, or custom binary formats in Bevy 0.18."

The description is the product. The body is a fallback for when the description matched.

## Quality gate — every PR must pass

1. `python3 scripts/lint-skills.py` clean (frontmatter valid).
2. For any new or changed code block: matching `bevy-skills-tester/examples/<skill>.rs` compiles under `bevy = "0.18"`.
3. Skill body ≤200 lines; longer content moved to `references/`.
4. Description contains "Bevy 0.18" verbatim and names ≥3 concrete triggers.
5. `## See also` lists ≥2 sibling skills.

## Maintenance cadence

- **Bevy release (~quarterly):** Bump `bevy = "0.x"` in the tester crate, bump version pins in every skill description, update `bevy-migration-*` skill, re-run `cargo check --examples` and fix breakage.
- **Continuous:** When a real-world Bevy gotcha hits, add it to the most relevant skill's Gotchas. The collection grows from friction, not speculation.
