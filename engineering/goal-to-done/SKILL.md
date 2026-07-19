---
name: goal-to-done
description: Steward one substantial goal from a rough request to verified completion - clarify consequential decisions, compile a verifiable goal brief, walk the closed seven-route cascade to the smallest fit (four outcome routes total-tdd, wayfinder, direct, to-tickets; three interstitial outcomes grilling pass, human pause, no-work receipt), drive the dependency-ready ticket frontier through existing harness and tracker mechanisms, re-plan when evidence invalidates the graph, and finish with integration-level verification against the original rubric. Use when the user says "take this goal to done", "turn this into tickets and drive it through", "steward this project to completion", or asks to run a substantial goal, feature, plan, or goal brief through decomposition and execution. Not for one quick fix (just do it) and not a replacement for any composed mechanism.
---

# goal-to-done

Steward one goal from rough request to verified DONE. `SPEC.md` in this
directory is the normative contract; when in doubt, it wins. You compose
existing mechanisms — tracker skill, harness gate/build/verify/judge, TDD,
review council, delegation — and never build a controller, scheduler, daemon,
state store, tracker adapter, or second ticket runner. The `tests/` and
`evals/` here validate this skill's delivery; never run them to drive real
work.

## 0. Verify the composed mechanisms exist

Before stewarding, confirm the tools this skill composes are actually
available — a missing mechanism is a stop, not something to reimplement:

```bash
linear auth whoami >/dev/null || echo "tracker CLI unavailable - authenticate or stop"
harness --help >/dev/null     || echo "harness unavailable - per-unit gating impossible"
council --preflight-only --workspace .   # reviewer seats ready? fail-closed
```

## 1. Admit exactly one steward

Check the parent tracker issue for a current non-stale steward claim. If one
exists, stop — you are not the steward. Otherwise claim the parent through the
host's task controls and the tracker comment:

```bash
linear issue view GOAL-123            # look for a current [claim] comment
linear issue comment add GOAL-123 --body "[claim] steward=<agent> session=<id> started=<iso8601>"
```

Only the steward mutates the graph or claims child tickets; workers execute
steward-issued units and never self-claim.

## 2. Anchor the goal brief

Compile the overall goal with `goal-spec` into one binary destination. On the
parent issue record: goal-brief version 1, the SHA-256 of the exact UTF-8
goal-brief block, and graph revision 1 (`[graph-revision] 1` +
`[graph-reconciled] 1`). The parent issue is the sole lifecycle authority;
local files are evidence snapshots, never state.

A goal-brief version changes only after an authorized material scope change.
Each new version records its digest, predecessor digest, authorization
reference, effective graph revision, and the verbatim block. An authorized
version bump advances the graph revision and runs the section 6 reconciliation;
claims resume only after the new `[graph-reconciled]` marker — recording the
same revision and resuming is not enough.

```bash
# hash the exact UTF-8 goal-brief block, then record it on the parent issue
shasum -a 256 goal-brief-v1.txt
linear issue comment add GOAL-123 --body-file brief-v1-record.md   # version, sha, [graph-revision] 1, [graph-reconciled] 1
```

## 3. Route once, in order

Walk this cascade top-down; first match wins. The route vocabulary is closed.

1. Whole-application inventory/test/fix/retest objective → `total-tdd`.
2. Classify: consequential decisions; unit cardinality; and, if positive,
   boundedness and route certainty. A value unknown because a *decision* is
   unsettled → at most one bounded `grilling` pass per goal-brief version, then
   reclassify once. Grilling settles decisions, not facts: an unknown that only
   an investigation can resolve (a dependency's real behavior, a spike outcome)
   stays unknown here and is handled by `wayfinder` at rule 5. A decision that
   *cannot be made until such a fact is known* is contingent — do not force it
   closed in the grilling pass; leave it pending and let the goal route to
   `wayfinder` with the fact, where it is decided on the re-route.
3. An unresolved decision meets a human stop condition → pause for the human.
4. Cardinality zero → post a no-work receipt proving the rubric already passes
   at the current graph revision, and terminate.
5. Cardinality unknown, or boundedness/route certainty not clearly true →
   `wayfinder`. Never re-grill the same goal-brief version.
6. Cardinality one → execute the bounded unit directly.
7. Cardinality two or more → `to-tickets`.

Consequences: whole-app ownership beats fogginess; one bounded unit beats
decomposition; if any unit of a multi-unit set is uncertain the whole set goes
to `wayfinder`; only an entirely bounded, route-certain multi-unit set reaches
`to-tickets`.

`wayfinder` is not a dead end. It owns route discovery — resolving investigation
tickets (whose shape wayfinder owns; goal-to-done only records their evidence,
which is not an implementation receipt) until the units are bounded and
route-certain. When the fog clears, re-run this cascade over the *same*
goal-brief version on the now-known facts, with the grilling predicate closed
for the version (rule 2's grilling sub-step does not fire again) — which lands
on `direct` (one unit) or `to-tickets` (two or more) for actual execution. This
first exit decomposes under the current, already-reconciled graph revision:
there is no prior implementation plan to invalidate, so no `[graph-revision]`
bump and no section 6 reconciliation are due here. Reconciliation (section 6)
fires only later, when evidence invalidates an implementation plan that already
exists.

A decision that wayfinder's facts settle — one grilling already chose and
discovery reopened, or one left pending as contingent at rule 2 — is decided on
this re-route, never by re-grilling: if the discovered fact now determines it,
record it and continue; if it still needs human judgment, it meets a human stop
condition and you pause (rule 3). Investigation tickets live under the current
graph revision and do not advance it — they yield evidence, not a change to the
implementation-plan shape.

## 4. Give every ticket a full contract

Every implementation ticket and claim carries: a mini goal brief, explicit
dependency edges, a structured verification receipt contract, a stop
condition, the goal-brief version, and the graph revision. Tickets are
vertical, independently verifiable slices.

## 5. Execute only the ready frontier

Claim and dispatch only dependency-ready tickets, serialized after the
matching `[graph-reconciled]` marker. Run each unit through the existing
mechanisms — harness gate/build/verify/judge, TDD, council review, delegation
— never through anything this skill invents:

```bash
harness --gate-only PLAN.md          # gate the unit's plan; nonzero = not clean, fix or stop
harness run --repo . PLAN.md         # build/verify/judge the bounded unit
council --gates . ARTIFACT.md        # judge a diff/spec; trust only its COUNCIL RESULT line
```

Treat the composed CLIs' exit codes as the verdict: a nonzero exit or a
missing/duplicated result line is a failed gate, never noise to route around. A ticket completes only when its
receipt validates against its mini-goal rubric and stop condition at the
current goal-brief version and graph revision. Failed, missing, or stale proof
means rework; only a validated current-revision pass unlocks dependents.

## 6. Re-plan by reconciliation, not patchwork

When evidence invalidates the plan: append a new `[graph-revision]` marker
first (in-flight receipts go stale), block new claims, impact-analyze
completed/queued/in-flight work, invalidate stale receipts and downstream
unlocks, move affected work to rework or obsolete, rewrite tracker relations,
record carry-forward validation for unaffected completed work, revalidate the
new frontier, then append `[graph-reconciled]` before claims resume. A claim
or receipt is valid only if its revision's reconciled marker predates it and
no newer revision marker exists — unless a recorded current-revision
carry-forward validation preserves it across the revision change (SPEC
section 8), which is how unaffected completed work stays valid after a re-plan
instead of deadlocking the frontier. Never preserve a stale backlog through
shims or special cases.

## 7. Pause only for material change

Pause for the human when a discovered requirement materially changes scope,
authority, architecture, or irreversible behavior — or when work would
publish, merge, release, deploy, or broaden authority. Stop and re-design if
you ever need a second runtime state store or ticket runner. Record routine
decisions and continue.

When you pause, hand the human a decision, not a status dump: what changed
and the evidence, which tickets/receipts are affected (the impact analysis),
the options with one recommendation, and exactly what authorization you are
requesting.

## 8. Finish with integration proof

Completed tickets alone are not DONE. After the subject is committed: re-read
the authoritative tracker graph, verify every contributing ticket at the
current graph revision, recompute and verify the goal-brief digest chain, open
the draft PR, then post the final receipt to the parent issue naming the
goal-brief version, digest chain, graph revision, complete ticket closure, the
exact subject commit or artifact digest, and the PR. The receipt lives outside
the subject it certifies.

## Neighbors — what this skill does not own

- `grilling` owns decision resolution; you get at most one pass per goal-brief
  version.
- `goal-spec` owns brief compilation (overall and per-ticket mini briefs).
- `wayfinder` owns route discovery through fog.
- `to-tickets` owns decomposition of clear multi-unit plans.
- `total-tdd` owns whole-app audit/test/fix loops.
- The tracker skill owns issue reads/writes; the harness owns per-unit
  gate/build/verify/judge; host task controls own admission; delegation skills
  own heavy lifting.

This skill never creates a daemon, scheduler, tracker API, harness, TDD
method, or review council.

## Errors

| Issue | Fix |
|---|---|
| Tracker CLI missing or unauthenticated (`linear` not found, auth errors) | Install/authenticate the tracker CLI first; without the tracker there is no lifecycle authority — stop, do not track state in local files instead. |
| `harness` or `council` not on PATH | Install the harness checkout and its shims. Do not hand-roll a substitute gate; a unit that cannot be gated stays unclaimed. |
| Council preflight below quorum (fail-closed `status=unavailable`) | Read each `COUNCIL SEAT:` line's `failure_class` and decoded `recovery` (for example `claude auth login`, restore provider credits). Fix seats or explicitly configure a smaller honest panel; never present a degraded panel as clean. |
| A current steward claim already exists on the parent issue | You are not the steward. Stop; report to the human instead of double-claiming. |
| Goal-brief digest mismatch on rehash | The brief block was edited outside an authorized version change. Halt claims, find the unauthorized edit, restore the verbatim block or record an authorized new version before continuing. |
| `[graph-revision]` marker with no matching `[graph-reconciled]` | Reconciliation is incomplete: claims are blocked. Finish impact analysis and post the reconciled marker before any claim. |
| A worker's receipt fails, is missing, or is stamped with a stale revision | Send the ticket to rework at the current revision; never unlock dependents from stale or missing proof. |
