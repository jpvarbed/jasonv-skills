# jasonv-skills

Skills for AI coding agents. **This repo is written for agents — start with [AGENTS.md](AGENTS.md).**

Humans: each skill lives under `<category>/<skill>/` with a `SKILL.md` (the method) and, increasingly, a `SPEC.md` (what it must do + eval record). Install: `./install.sh`.

<!-- arena-publish:begin -->
| Skill | Category | Status | Headline | Evidence |
|---|---|---|---|---|
| total-tdd | engineering | measured | detection codex / with-skill 8/8 | [PERF.md](engineering/total-tdd/PERF.md) |
| apply-paper | meta | no eval yet | evidence unavailable; see PERF.md | [PERF.md](meta/apply-paper/PERF.md) |
| determinize-refactor | meta | no eval yet | evidence unavailable; see PERF.md | [PERF.md](meta/determinize-refactor/PERF.md) |
| goal-spec | meta | measured | detection codex / with-skill 7/8 | [PERF.md](meta/goal-spec/PERF.md) |
| instruction-conflicts | meta | measured | detection codex-56luna / with-skill 15/18; codex-56sol +27.8pp pre->post | [PERF.md](meta/instruction-conflicts/PERF.md) |
| caveman | productivity | measured | detection codex / with-skill 6/12 | [PERF.md](productivity/caveman/PERF.md) |
| adversarial-review | review | no eval yet | evidence unavailable; see PERF.md | [PERF.md](review/adversarial-review/PERF.md) |
| gtm-diligence | review | no eval yet | evidence unavailable; see PERF.md | [PERF.md](review/gtm-diligence/PERF.md) |
| visual-critique | review | no eval yet | evidence unavailable; see PERF.md | [PERF.md](review/visual-critique/PERF.md) |
| highsignal | writing | measured | detection `codex exec` (codex-cli 0.142.4, default model) 13/14; openai +10.5pp / haiku -10.5pp pre->post | [PERF.md](writing/highsignal/PERF.md) |
| writing-hooks | writing | measured | detection codex / with-skill 17/18 | [PERF.md](writing/writing-hooks/PERF.md) |
<!-- arena-publish:end -->

## Skills

### engineering

- **[total-tdd](engineering/total-tdd/)** — Systematic whole-app feature audit → test → fix loop, backed by tracker.py + render.py over one canonical CSV state machine. _(needs: a browser-automation tool, bundled python)_

### meta

- **[apply-paper](meta/apply-paper/)** — Turn a research paper's finding into a concrete change to our skills/agents — distill the claim, map it to where it applies, design the change, and prove it helps. _(needs: nothing (pure method))_
- **[determinize-refactor](meta/determinize-refactor/)** — Analyze a prompt-heavy skill/plugin and produce a prioritized migration plan that moves deterministic instructions out of prose into scripts or structured contracts — improving…. _(needs: nothing (pure method))_
- **[goal-spec](meta/goal-spec/)** — Turn a rough task into a launch-ready /goal brief — a verifiable spec with context-access, a verification plan, and a binary rubric — so a dispatched agent runs to completion un…. _(needs: nothing (pure method))_
- **[instruction-conflicts](meta/instruction-conflicts/)** — Audit the layered instruction stack (in-conversation user → soul.md/global → project guide → skill → tool/system) for conflicting or ambiguous directives, and surface which laye…. _(needs: nothing (pure method))_
- **[skill-workshop](meta/skill-workshop/)** — Build or materially redesign an agent skill from a rough idea or solved workflow, then prove it with tiered tests, evaluation, blind cross-family forward tests, and a typed completion receipt. _(needs: bundled python, skill-arena, configured review seats)_

### productivity

- **[caveman](productivity/caveman/)** — Ultra-compressed communication mode. _(needs: nothing (pure method))_

### review

- **[adversarial-review](review/adversarial-review/)** — Run a fast two-persona or deep four-persona council across live-verified device seats, with exact setup/auth/model receipts and no runtime fallback. _(needs: 1+ configured agent seat)_
- **[gtm-diligence](review/gtm-diligence/)** — Run a comprehensive pre-ship / go-to-market readiness audit of an application across security, reliability, concurrency/race conditions, accessibility (WCAG 2.2 AA), performance…. _(needs: a browser-automation tool)_
- **[visual-critique](review/visual-critique/)** — Run three independent Codex vision inspections of a render, pose, screenshot, or UI, then synthesize a consensus report. _(needs: `codex` CLI, a browser-automation tool)_

### writing

- **[writing-hooks](writing/writing-hooks/)** — Personal compilation of hook and social-post writing gotchas (X/LinkedIn) in Jason''s voice. _(needs: nothing (pure method))_

MIT © 2026 Jason Varbedian
