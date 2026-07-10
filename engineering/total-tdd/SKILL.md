---
name: total-tdd
description: 'Systematic whole-app feature audit → test → fix loop, backed by tracker.py + render.py over one canonical CSV state machine. Inventory every feature into user stories with code-derived expected behavior, then loop: test every story, document errors, fix logic/UX bugs, re-test. Use for "/total-tdd", "auditing an entire app", "building a feature/user-story spec from the code", or a full test-and-fix sweep across all features. Not for a single feature or bug — use `tdd` (red-green-refactor); not for verifying one claim — use `verify-this`; not for reviewing a diff — use `review`.'
---

# total-tdd — whole-app feature audit → test → fix loop

A resumable, four-phase loop over an entire app. The **canonical CSV is the single source
of truth and the state machine**. The deterministic mechanics — schema, phase inference,
done-gates, tally, HTML render — live in two scripts so they never drift across resumes;
your job is the judgment (what a feature is, what the code should do, whether observed
behavior earns a status).

## Scripts (the deterministic core — call these, don't re-derive them)

```bash
S=~/.claude/skills/total-tdd/scripts          # this skill's scripts dir
python3 $S/tracker.py init                     # create docs/feature-audit.csv with the canonical header
python3 $S/tracker.py validate [--repair]      # assert/repair the 9-col schema + status enum
python3 $S/tracker.py phase                    # which phase am I in + why (the resume command)
python3 $S/tracker.py gate --phase N           # exit 0 iff phase N is complete, else lists blockers
python3 $S/tracker.py tally                    # "N total · spec/pass/fail/fixed/verified"
python3 $S/render.py docs/feature-audit.csv --app "<name>"   # write docs/feature-audit.html
```

All read `docs/feature-audit.csv` (override with a path arg). Run `tracker.py phase` to
resume; run `gate --phase N` before advancing; run `render.py` after each phase. Tests:
`python3 -m unittest discover $S`.

## Prerequisites (Phase 2)

Phase 2 drives the *running app* through three roles. Confirm one tool per role first — if
any is missing, name it and stop, rather than downgrading to reading code (that defeats the skill):

- **Browser driver** — `agent-browser` preferred, or any tool/MCP that can navigate, fill,
  click, screenshot, and read console + network.
- **Stable local URL** — `portless` preferred, or any fixed host:port / tunnel.
- **API stub** — `emulate` preferred, or any local mock for Stripe/GitHub/AWS and similar.

## The canonical CSV

`docs/feature-audit.csv`, one row per feature, columns
`id,area,user_story,expected_behavior,source,status,issues,fix,verified`. `tracker.py`
owns the schema; you fill the judgment:

- `user_story`: "As a <role>, I want <action>, so that <outcome>."
- `expected_behavior`: what the code actually does — cite `source` as `file:line`.
- `status` enum: `spec` → `pass`/`fail` → `fixed` → `verified`. `verified` (9th col) holds the
  observed evidence.

The report is the forcing function: an empty cell is a visible gap, so every story gets exercised.

## Phases (advance only when `tracker.py gate --phase N` passes)

1. **Inventory + spec.** Walk the whole app (routes, components, commands, APIs, jobs,
   settings). Add a row per feature with a user story + code-derived expected behavior and a
   `source` ref; status `spec`. *Judgment: feature granularity, reading intent from code.*
2. **Test.** Exercise each story in the **real running app** (not by reading code): serve it at
   a stable URL, drive the UI with the browser driver, stub external APIs with emulate. Set
   `pass`/`fail`; put concrete repro/error in `issues`. *Judgment: what to click, what's broken.*
3. **Fix.** Fix every `fail` (logic + UX). Record the change in `fix`, set `fixed`. Keep each
   fix diff tight. *Judgment: whether a fix is in-scope.*
4. **Re-test.** Re-run every story in the real app; set status `verified` with evidence in the
   `verified` column. Any new break goes back to `fail` → loop to phase 3.

## Rules

- **Evidence before status.** A row is `pass`/`verified` only after the behavior was observed
  running — never from reading code (see `verify-this`, `verification-before-completion`).
  **Enforced:** `tracker.py gate` blocks a `pass`/`verified` row with an empty Evidence cell
  (and a `fail` with no repro in `issues`) — a status without evidence is a blocker, not done.
- The CSV is canonical and updated in place — never fork copies. It survives sessions; that's
  how the loop resumes.
- After each phase: `render.py` to refresh `docs/feature-audit.html`; never let it drift.
- Scope creep is fine for *finding* issues across features; keep each *fix* diff tight.

## Errors

| Issue | Fix |
| --- | --- |
| Browser driver (`agent-browser` / substitute) not installed or its MCP/daemon isn't running, so Phase 2 can't navigate/click/screenshot | Don't downgrade to reading code — that voids the skill. Start the driver (or an equivalent that can navigate, fill, click, screenshot, read console+network); if none exists, name the missing role and stop, leaving rows at `spec`. |
| App won't start, or `portless` can't bind because the dev port is taken | Find the real start/serve command (package scripts, README, or ask) and run it; map it through `portless` to a fixed `.localhost` URL so the driver hits a stable address — fix the port conflict (kill the stale server or change the port), don't test a moving `localhost:PORT`. |
| `emulate` not installed, so external integrations (Stripe/GitHub/AWS) can't be stubbed | Install/run `emulate` (or another local mock) and point the app's API base/keys at it so integration paths run offline; if it can't stand up, mark only the affected rows `fail` with the missing-stub reason in `issues` — never silently skip them. |
| Missing API key/credential the emulator can't fake, blocking a real path | Fetch the key from Bitwarden (`bws`) at run time and inject via env — never hardcode it; if unavailable, record the blocked story as `fail` with the missing-credential note so it's a visible gap, not a fake `pass`. |
| `docs/feature-audit.csv` missing, corrupt, or columns drifted | `tracker.py init` (if absent) or `tracker.py validate --repair` (rewrites to the canonical 9 columns); then `tracker.py phase` to re-derive where you are and `render.py` to re-sync the HTML. Never fork a second copy. |
