# jasonv-skills — for agents

If you are an AI coding agent, this file is for you. This repo is a set of **skills**:
each is a folder with a `SKILL.md` describing one repeatable method. When a task matches a
skill's stated purpose, open that `SKILL.md` and follow it.

## Installing (per agent)

Each agent reads its own skills directory. `./install.sh <agent>` symlinks every skill
into it; the agent then discovers each `SKILL.md` natively.

- **Claude Code** — `~/.claude/skills`
- **Codex** — `~/.codex/skills`
- **Cursor** — `~/.cursor/skills`

`./install.sh all` does all three. Override any target with `CLAUDE_SKILLS_DIR`/`CODEX_SKILLS_DIR`/`CURSOR_SKILLS_DIR`. Safe and
idempotent: it only creates, refreshes, or prunes symlinks that point back into this repo —
a skill name you already own (a real dir, or a link elsewhere) is left untouched.

## Honest compatibility

These skills were authored and used in **Claude Code**. They're written to be
agent-agnostic — they assume no specific model, only the external *tools* each needs (the
`needs` column). **None have been formally evaluated on other agents yet**; the table is by
dependency, not by proof. Each skill's `SPEC.md` (when present) records what it was actually
tested on. Specs exist for 2/11 skills so far.

| skill | category | needs | spec? |
| --- | --- | --- | --- |
| [goal-to-done](engineering/goal-to-done/) | engineering | a tracker CLI, a review CLI, bundled python | ✓ |
| [total-tdd](engineering/total-tdd/) | engineering | a browser-automation tool, bundled python | ✓ |
| [apply-paper](meta/apply-paper/) | meta | nothing (pure method) | — |
| [determinize-refactor](meta/determinize-refactor/) | meta | nothing (pure method) | — |
| [goal-spec](meta/goal-spec/) | meta | nothing (pure method) | — |
| [instruction-conflicts](meta/instruction-conflicts/) | meta | nothing (pure method) | — |
| [caveman](productivity/caveman/) | productivity | nothing (pure method) | — |
| [adversarial-review](review/adversarial-review/) | review | configured `fast`/`deep` profiles using Codex, Cursor, Cline, and/or Claude | ✓ |
| [gtm-diligence](review/gtm-diligence/) | review | a browser-automation tool | — |
| [visual-critique](review/visual-critique/) | review | `codex` CLI, a browser-automation tool | — |
| [writing-hooks](writing/writing-hooks/) | writing | nothing (pure method) | — |

## The SPEC.md convention

Each skill should be built from a `SPEC.md`: the source-of-truth statement of what it must
do and the record of which agents it has been evaluated on. Change the spec first, then the
`SKILL.md`. Skills without a spec yet are marked `—` above.

## Install

```
./install.sh [claude|codex|cursor|all]
```

MIT © 2026 Jason Varbedian
