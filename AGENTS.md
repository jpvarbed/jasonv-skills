# jasonv-skills — for agents

If you are an AI coding agent, this file is for you. This repo is a set of **skills**:
each is a folder with a `SKILL.md` describing one repeatable method. When a task matches a
skill's stated purpose, open that `SKILL.md` and follow it.

## Using a skill, per agent

- **Claude Code** — `./install.sh claude` symlinks skills into `~/.claude/skills`; they
  load automatically and you invoke them by name.
- **Codex / Cursor / Gemini CLI** — `./install.sh <agent>` prints a pointer block; paste it
  into that agent's instructions file (`AGENTS.md` / `.cursor/rules` / `GEMINI.md`). Then,
  when a task matches, read that skill's `SKILL.md` and follow it. These agents don't
  auto-run skills — discovery plus a manual read is the model.

## Honest compatibility

These skills were authored and used in **Claude Code**. They're written to be
agent-agnostic — they assume no specific model, only the external *tools* each needs (the
`needs` column). **None have been formally evaluated on other agents yet**; the table is by
dependency, not by proof. Each skill's `SPEC.md` (when present) records what it was actually
tested on. Specs exist for 1/12 skills so far.

| skill | category | needs | spec? |
| --- | --- | --- | --- |
| [total-tdd](engineering/total-tdd/) | engineering | a browser-automation tool, bundled python | ✓ |
| [agentic-engineering](knowledge/agentic-engineering/) | knowledge | nothing (pure method) | — |
| [gap-briefing](knowledge/gap-briefing/) | knowledge | web search/fetch | — |
| [apply-paper](meta/apply-paper/) | meta | nothing (pure method) | — |
| [determinize-refactor](meta/determinize-refactor/) | meta | nothing (pure method) | — |
| [goal-spec](meta/goal-spec/) | meta | nothing (pure method) | — |
| [instruction-conflicts](meta/instruction-conflicts/) | meta | nothing (pure method) | — |
| [caveman](productivity/caveman/) | productivity | nothing (pure method) | — |
| [adversarial-review](review/adversarial-review/) | review | `gemini` CLI | — |
| [gtm-diligence](review/gtm-diligence/) | review | a browser-automation tool | — |
| [visual-critique](review/visual-critique/) | review | `gemini` CLI, a browser-automation tool | — |
| [writing-hooks](writing/writing-hooks/) | writing | nothing (pure method) | — |

## The SPEC.md convention

Each skill should be built from a `SPEC.md`: the source-of-truth statement of what it must
do and the record of which agents it has been evaluated on. Change the spec first, then the
`SKILL.md`. Skills without a spec yet are marked `—` above.

## Install

```
./install.sh [claude|codex|cursor|gemini|all]
```

MIT © 2026 Jason Varbedian
