---
name: apply-paper
description: Turn a research paper's finding into a concrete change to our skills/agents — distill the claim, map it to where it applies, design the change, and prove it helps. Use when the user says "apply this paper", "what would <paper> change for us", "turn this finding into a skill change", or when triaging a paper in docs/papers.md from "interesting" to "shipped". NOT for summarizing a paper (just read it) or general literature review. Pairs with linting-and-scoring (score the result), adversarial-review (red-team the change plan), and goal-spec (if the change is big enough to dispatch).
---

# apply-paper — research finding → shipped change

Closes the loop on `docs/papers.md`: that file *captures* papers; this skill *applies* them.
A paper only earns its keep when its mechanism changes how a skill or agent behaves. The output
is a change (or a tight change plan), not a summary.

## Step 1 — Distill the claim (no hype)
In 3-4 sentences: what does the paper actually *show*, and by what **mechanism**? Separate the
finding (often robust) from the framing (often oversold). If you can't name a mechanism, you can't
apply it — stop and say so.

## Step 2 — Map it to us
Name the concrete target: which **skill / agent / instruction-layer / flow** does the mechanism
touch? Cite the file. If nothing in our setup is affected, say "no application" and log that in
`docs/papers.md` — that's a valid, honest outcome.

## Step 3 — Design the change
The smallest edit that captures the mechanism: a new check, a new mode/step, a tightened
contract, a deleted footgun. Prefer **scoped edits over broad rewrites** (HarnessFix's own
lesson). Write it as a diff plan: file → what changes → why it captures the mechanism.

## Step 4 — Prove it (the part that makes it real)
State the change's done-condition as a check, then show before/after:
- Behavioral change → a test query / scenario that fails before and passes after.
- New rubric/check → run it on a skill that should fail it and one that should pass.
- "Reliability" claim → measure across runs, not once (per *Beyond pass@1*).
If you can't show a before/after, you've written a summary, not an application.

## Step 5 — Adversarial pass
Red-team with `adversarial-review`: does the change actually capture the paper's mechanism, or
just cite it? Could it be satisfied without the intended effect (cargo-culting the paper)?

## Step 6 — Record it
Update the paper's entry in `docs/papers.md` with `→ applied: <what changed> (<file>)`, so the
list shows captured-vs-shipped at a glance. File/refresh a Linear JAS issue if it's multi-step.

## Output
```
PAPER: <title + url>
CLAIM: <mechanism in one sentence>
TARGET: <skill/agent/layer + file>
CHANGE: <the diff plan or the landed edit>
PROOF: <before/after evidence, or the check that now passes>
```

## Worked example (shipped)
**Offscript** (auto-auditing instruction adherence) → added the **Adherence audit** to
`meta/linting-and-scoring` (behavioral pass: generate adversarial test queries per stated
instruction, flag the ones an agent could violate). See that skill's "Adherence audit" section.

## Errors

| Issue | Fix |
|---|---|
| Can't name a mechanism, only a vibe | The paper isn't applicable yet — record "no application" in papers.md; don't force a change. |
| Change just cites the paper without its effect | Cargo-culting. Redo Step 4 — if there's no before/after, it didn't apply the mechanism. |
| Paper conflicts with an existing skill's approach | Surface both; use `adversarial-review` to decide, and record the decision (don't silently overwrite). |
| Mechanism needs a real model call to test (e.g. behavioral) and no key/tool | Use `openrouter` for a cheap model, or mark the proof step blocked and don't claim it works. |
