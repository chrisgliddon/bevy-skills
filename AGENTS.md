# AGENTS.md

You are an AI coding agent that has landed in the `bevy-skills` repository.

## What this repo is

A collection of Agent Skills (`SKILL.md` files) that teach AI agents how to write version-pinned Bevy code: a **Bevy 0.19 general baseline**, plus staged **Bevy 0.20 migration and Rapier 0.37 physics guidance**. Targets Claude Code, OpenCode, Cursor, Codex, Pi, and any other Agent Skills consumer.

## If you are HERE TO USE the skills

You are in the wrong place. Skills load automatically from your agent's skill directory (e.g. `~/.claude/skills/`). See [`README.md`](./README.md) for install instructions, then close this checkout and let the skills load via your normal workflow.

## If you are HERE TO EDIT the skills

Read [`CLAUDE.md`](./CLAUDE.md). It is the authoritative editor guide. Highlights:

- Every skill is a folder under `skills/` with a `SKILL.md` (YAML frontmatter + body) and optional `references/`.
- Frontmatter must pass `scripts/lint-skills.py` — name regex `^[a-z0-9]+(-[a-z0-9]+)*$` matching the directory, description 1–1024 chars, keys limited to `name`/`description`/`license`/`compatibility`/`metadata`.
- New or changed Rust snippets require `cargo check` against their declared Bevy and plugin versions in the companion `bevy-skills-tester` crate (not vendored here — see `CLAUDE.md`). Record unavailable checks; do not equate lint with compilation.
- Pin the actual target explicitly in each description and heading. The general
  baseline remains Bevy 0.19; the 0.20 physics/migration slice and historical skills
  set `metadata.target_version`. Do not bulk-rewrite historical version pins.
- Read `docs/bevy-020-readiness.md` before expanding 0.20 coverage. Cross-links to
  0.19 skills do not certify their APIs for 0.20; plugin metadata remains on 0.19
  pending broader validation.
- Use `dex` for persistent project work. Repository-local tasks live in `.dex/tasks.jsonl` and automatically sync root tasks to GitHub Issues.

## License

MIT. See [`LICENSE`](./LICENSE).
