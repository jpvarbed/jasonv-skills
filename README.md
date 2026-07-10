# jasonv-skills

Curated, self-contained skills for AI coding agents (Claude Code, Cursor, and any agent that reads a `SKILL.md`). Install: `./install.sh` (symlinks each skill into `~/.claude/skills`).

## Skills

### engineering

- **[total-tdd](engineering/total-tdd/)** — Systematic whole-app feature audit → test → fix loop, backed by tracker.py + render.py over one canonical CSV state machine.

### knowledge

- **[agentic-engineering](knowledge/agentic-engineering/)** — Read-only reference KB (not a procedure) on building agentic systems — loop engineering, harness design, agent reliability, context/token engineering, the agentic web (MCP/disco….
- **[gap-briefing](knowledge/gap-briefing/)** — Use when the user wants to catch up on what changed in the world since the model's knowledge cutoff and have it filtered through their own projects — "what did I miss", "anythin….

### meta

- **[apply-paper](meta/apply-paper/)** — Turn a research paper's finding into a concrete change to our skills/agents — distill the claim, map it to where it applies, design the change, and prove it helps.
- **[determinize-refactor](meta/determinize-refactor/)** — Analyze a prompt-heavy skill/plugin and produce a prioritized migration plan that moves deterministic instructions out of prose into scripts or structured contracts — improving….
- **[goal-spec](meta/goal-spec/)** — Turn a rough task into a launch-ready /goal brief — a verifiable spec with context-access, a verification plan, and a binary rubric — so a dispatched agent runs to completion un….
- **[instruction-conflicts](meta/instruction-conflicts/)** — Audit the layered instruction stack (in-conversation user → soul.md/global → project guide → skill → tool/system) for conflicting or ambiguous directives, and surface which laye….

### productivity

- **[caveman](productivity/caveman/)** — Ultra-compressed communication mode.

### review

- **[adversarial-review](review/adversarial-review/)** — Get a ruthless, INDEPENDENT second-model critique of a plan, spec, ADR, PRD, or diff via the Gemini CLI, then triage the findings (valid vs.
- **[gtm-diligence](review/gtm-diligence/)** — Run a comprehensive pre-ship / go-to-market readiness audit of an application across security, reliability, concurrency/race conditions, accessibility (WCAG 2.2 AA), performance….
- **[visual-critique](review/visual-critique/)** — Get a robust, noise-free 3-run majority-vote visual critique of 3D renders, joint positions, skeletal anatomy, or UI look-and-feel via the Gemini CLI, synthesizing a consensus r….

### writing

- **[writing-hooks](writing/writing-hooks/)** — Personal compilation of hook and social-post writing gotchas (X/LinkedIn) in Jason''s voice.

MIT © 2026 Jason Varbedian
