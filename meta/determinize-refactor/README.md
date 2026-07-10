# determinize-refactor

Analyze a prompt-heavy skill/plugin and produce a prioritized migration plan that moves deterministic instructions out of prose into scripts or structured contracts — improving reliability and cutting token cost. Use when the user says "reduce prompt tokens", "make this skill deterministic", "script-mode this skill", or "audit a skill for token bloat". Outputs a Markdown audit report with a token summary and per-file conversion plan, NOT code. NOT for authoring a skill from scratch (use writing-great-skills) or scoring quality (use linting-and-scoring).

Part of [jasonv-skills](../../AGENTS.md) — skills for AI coding agents. Install with the repo-root `install.sh`; when a task matches, read this `SKILL.md` and follow it.

MIT © 2026 Jason Varbedian
