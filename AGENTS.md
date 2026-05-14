# AGENTS.md

You are an AI coding agent that has landed in the `bevy-skills` repository.

## What this repo is

A collection of Agent Skills (`SKILL.md` files) that teach AI agents how to write correct **Bevy 0.18** code. Targets Claude Code, OpenCode, Cursor, Codex, Pi, and any other Agent Skills consumer.

## If you are HERE TO USE the skills

You are in the wrong place. Skills load automatically from your agent's skill directory (e.g. `~/.claude/skills/`). See [`README.md`](./README.md) for install instructions, then close this checkout and let the skills load via your normal workflow.

## If you are HERE TO EDIT the skills

Read [`CLAUDE.md`](./CLAUDE.md). It is the authoritative editor guide. Highlights:

- Every skill is a folder under `skills/` with a `SKILL.md` (YAML frontmatter + body) and optional `references/`.
- Frontmatter must pass `scripts/lint-skills.py` — name regex `^[a-z0-9]+(-[a-z0-9]+)*$` matching the directory, description 1–1024 chars, keys limited to `name`/`description`/`license`/`compatibility`/`metadata`.
- Every code snippet must `cargo check` against `bevy = "0.18"` in the companion `bevy-skills-tester` crate (not in this repo — see `CLAUDE.md`).
- Pin Bevy 0.18 explicitly in every skill's description. No unversioned guidance.

## License

MIT. See [`LICENSE`](./LICENSE).
