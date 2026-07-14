---
name: adversarial-review
description: Get a ruthless independent critique of a plan, spec, ADR, PRD, or diff through a read-only Codex, Cline, Claude, then Cursor fallback chain; triage the findings before applying them. Use to red-team an expensive decision or sanity-check a diff before shipping.
---

# Adversarial Review

Use a different reviewer with no stake in the artifact, then treat every finding as a
hypothesis to verify. Gemini is prohibited from this workflow: it is not a primary engine,
gateway-hosted model, or fallback.

**Announce at start:** "Using adversarial-review to get an independent critique of <X>."

## Process

### 1. Pick the artifact

Choose the smallest set of files that captures the decisions and their rationale. Do not send
the whole repository when a plan, ADR, or focused diff is enough. Keep secrets out of the input.

### 2. Run the review

```bash
skills/review/adversarial-review/adversarial-review.sh \
  --focus "the specific bet to attack" \
  path/to/plan.md path/to/decision.md
```

The script tries Codex → Cline → Claude → Cursor. Every adapter is read-only, capacity-aware
when `~/dev/harness/capacity.py` is present, and prints `ENGINE: <name>` before the critique.
It fails plainly only after every allowed reviewer is unavailable.

If the first engine also authored the artifact, use `council` for a genuinely multi-engine panel.
For a noisy decision, run the critique two or three times and keep findings that recur.

### 3. Triage

For every finding:

- Verify it against the actual artifact and surrounding code.
- Classify it as `VALID + actionable`, `valid but already covered`,
  `re-litigates a settled decision`, or `wrong (reviewer lacked context)`.
- Re-rank severity when the reviewer over- or under-sold it.

Present `finding → verdict → action`. Apply only valid actionable findings; explicitly reject
re-litigation and invented gaps.

## Errors

| Issue | Fix |
| --- | --- |
| `error: pass at least one file to review` / `cannot read` | Pass at least one readable artifact path. |
| One engine is unavailable or capacity-capped | The script records/skips it and tries the next allowed engine. |
| `every review engine failed or was unavailable` | Restore at least one of Codex, Cline, Claude, or Cursor; do not add a forbidden fallback. |
| A review attempts tools or edits | Stop: the adapters must remain read-only (`codex` sandbox, Cline auto-approve off, Claude no-tools safe mode, Cursor ask+sandbox). |
