# jasonv-skills

Curated, self-contained skills for AI coding agents (Claude Code, Cursor, and any agent that reads a `SKILL.md`). Install: `./install.sh` (symlinks each skill into `~/.claude/skills`).

## Skills

- **[total-tdd](total-tdd/)** — Systematic whole-app feature audit → test → fix loop, backed by tracker.py + render.py over one canonical CSV state machine. Inventory every feature into user stories with code-derived expected behavior, then loop: test every story, document errors, fix logic/UX bugs, re-test. Use for "/total-tdd", "auditing an entire app", "building a feature/user-story spec from the code", or a full test-and-fix sweep across all features. Not for a single feature or bug — use `tdd` (red-green-refactor); not for verifying one claim — use `verify-this`; not for reviewing a diff — use `review`.

MIT © 2026 Jason Varbedian
