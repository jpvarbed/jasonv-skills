# instruction-conflicts

Audit the layered instruction stack (in-conversation user → soul.md/global → project guide → skill → tool/system) for conflicting or ambiguous directives, and surface which layer should win. Use when the user says "check for instruction conflicts", "do my layers contradict", "audit soul.md vs project/skill", "why is the agent ignoring X", or before relying on a deep skill stack. NOT for scoring one skill's quality (use linting-and-scoring) or auditing whether a skill obeys itself (use the adherence audit). Built from ManyIH (arXiv:2604.09443) via apply-paper.

Part of [jasonv-skills](../../AGENTS.md) — skills for AI coding agents. Install with the repo-root `install.sh`; when a task matches, read this `SKILL.md` and follow it.

MIT © 2026 Jason Varbedian
