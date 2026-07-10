# total-tdd

Systematic whole-app feature audit → test → fix loop, backed by tracker.py + render.py over one canonical CSV state machine. Inventory every feature into user stories with code-derived expected behavior, then loop: test every story, document errors, fix logic/UX bugs, re-test. Use for "/total-tdd", "auditing an entire app", "building a feature/user-story spec from the code", or a full test-and-fix sweep across all features. Not for a single feature or bug — use `tdd` (red-green-refactor); not for verifying one claim — use `verify-this`; not for reviewing a diff — use `review`.

A skill for AI coding agents (Claude Code, Cursor, etc.). Drop it in your agent's skills directory — see the repo root `install.sh`.

MIT © 2026 Jason Varbedian
