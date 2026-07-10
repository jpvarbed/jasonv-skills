# instruction-conflicts

Audit the layered instruction stack (in-conversation user → soul.md/global → project guide → skill → tool/system) for conflicting or ambiguous directives, and surface which layer should win. Use when the user says "check for instruction conflicts", "do my layers contradict", "audit soul.md vs project/skill", "why is the agent ignoring X", or before relying on a deep skill stack. NOT for scoring one skill's quality (use linting-and-scoring) or auditing whether a skill obeys itself (use the adherence audit). Built from ManyIH (arXiv:2604.09443) via apply-paper.

A skill for AI coding agents (Claude Code, Cursor, etc.). Drop it in your agent's skills directory — see the repo root `install.sh`.

MIT © 2026 Jason Varbedian
