# SPEC — total-tdd

Source-of-truth for the total-tdd skill. Change this first, then the SKILL.md. The SKILL.md is
the agent-facing procedure; this is what it must achieve and how we know it works.

## Purpose

Given a whole app, produce a complete feature inventory and drive every feature to a verified
pass/fail state through a repeatable test → document → fix → re-test loop, backed by one
canonical CSV state machine (`tracker.py`) rendered to HTML (`render.py`). Nothing is marked
`pass`/`verified` without observed evidence from a running app.

## Must do

1. Inventory every feature into user stories with code-derived expected behavior + a `source` ref;
   start each at status `spec`.
2. Exercise each story against a *running* app (not by reading code), recording concrete
   repro/error in `issues`; set `pass`/`fail`.
3. Gate: `tracker.py gate` blocks a `pass`/`verified` row with an empty Evidence cell, and a
   `fail` with no repro — a status without evidence is a blocker, not done.
4. Fix logic/UX bugs, keep the diff tight, re-test; new breaks return to `fail` and loop.
5. Maintain a single canonical `docs/feature-audit.csv` (9-column schema) + its rendered HTML;
   never fork a second copy.

## External tools it needs (deps)

- **browser** — a browser-automation tool the agent can drive (navigate/click/screenshot/read
  console+network). The skill names `agent-browser` / `portless` / `emulate` as the reference
  set, but any equivalent that can supply those capabilities works.
- **python** — runs the bundled `tracker.py` / `render.py` (stdlib only).

## Done = verifiable

- `tracker.py validate` passes on the canonical CSV (9 columns, valid status enum).
- `tracker.py gate --phase N` exits 0 only when phase N is genuinely complete.
- Every `pass`/`verified` row carries evidence; every `fail` carries a repro.

## Evaluated on

Honest status: **authored and used in Claude Code; not yet formally evaluated on Codex, Cursor,
or Cline.** The method is agent-agnostic (it only needs the deps above), but cross-agent
eval via skill-arena is a TODO. Update this section with concrete results when run.

| agent | evaluated | notes |
| --- | --- | --- |
| Claude Code | used in practice | primary authoring environment |
| Codex | no | untested |
| Cursor | no | untested |
