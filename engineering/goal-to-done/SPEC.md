# goal-to-done — normative contract

This document is the closed, normative contract for the `goal-to-done` steward
skill. `SKILL.md` is the concise operating procedure derived from it. Where the
two disagree, this contract wins. Requirement keywords (SHALL, SHALL NOT, MAY)
are normative.

## 1. Scope and authority

`goal-to-done` is the steward policy that takes one substantial goal from a
rough request through clarification, a verifiable overall goal brief, route
selection, optional ticket decomposition, dependency-frontier execution,
re-planning, and final integration verification. It is invoked by a human or by
a model when the user asks to turn a substantial goal, project, feature, plan,
or goal brief into tickets and drive it through completion.

The skill SHALL stay active through final verification. It SHALL pause only for
a material change to scope, authority, architecture, or irreversible behavior.

The skill composes existing mechanisms and SHALL NOT implement another
controller, scheduler, daemon, state store, tracker adapter, harness, TDD
method, or review council. Test and eval helpers under this skill validate this
delivery only; they SHALL NOT be invoked as a second operational ticket runner.

## 2. Definitions

- **Goal brief** — the binary, verifiable overall destination compiled with
  `goal-spec` (GOAL/CONTEXT/EFFORT/VERIFY/RESOLVED/RUBRIC/DONE).
- **Goal-brief version** — an integer identifying one authorized verbatim UTF-8
  goal-brief block. Version *n*+1 records its own SHA-256 digest, its
  predecessor's digest, the authorization reference for the change, the
  effective graph revision, and the verbatim block.
- **Graph revision** — an integer identifying one authoritative shape of the
  ticket dependency graph, advanced by an authoritative `[graph-revision]`
  marker on the parent issue.
- **Steward** — the single active agent holding the current parent claim; the
  only writer of graph mutations and child claims.
- **Worker** — an agent executing one steward-issued unit; workers SHALL NOT
  self-claim.
- **Claim** — a steward-serialized comment marking a unit as actively executed,
  stamped with goal-brief version and graph revision.
- **Receipt** — structured completion evidence for one unit, validated against
  that unit's mini-goal rubric and stop condition at the receipt's recorded
  goal-brief version and graph revision.
- **Frontier** — the set of tickets whose dependency edges are all satisfied by
  validated current-revision receipts.
- **Unit** — one vertical, independently verifiable slice of the goal,
  deliverable in one bounded execution with its own binary mini-goal rubric.
- **Bounded** — a unit is bounded when its scope, rubric, and stop condition
  are fully stated and the work fits one execution context with no remaining
  discovery. Whether several units happen to fit one working session never
  changes their cardinality.
- **Route-certain** — the implementation approach for the unit is decided; no
  open investigation determines how it will be built.
- **Carry-forward validation** — a steward-recorded, current-revision
  revalidation of an unaffected completed contributor's receipt after
  reconciliation; it is the one receipt-equivalent object that keeps prior
  proof valid across a graph-revision change.

## 3. Lifecycle authority

The parent Linear goal issue is the sole lifecycle authority.

- Before decomposition, the steward SHALL record on the parent issue: goal-brief
  version 1, the SHA-256 of the exact UTF-8 goal-brief block, and graph
  revision 1 — as both a `[graph-revision] 1` marker and its
  `[graph-reconciled] 1` marker, so first-revision claims satisfy section 8.
- Child issue relations and states are the graph. Comments carry claims,
  graph-revision changes, invalidations, and receipts.
- A goal-brief version SHALL change only after an authorized material scope
  change, and every version SHALL record its digest, predecessor digest,
  authorization reference, effective graph revision, and the verbatim UTF-8
  block before claims resume.
- An authorized goal-brief version change SHALL advance the graph revision and
  run section 8's reconciliation; claims resume only after the new version's
  `[graph-reconciled]` marker. A claim or receipt under a stale marker never
  validates version-changed work.
- Final verification SHALL rehash every retained block and check every
  predecessor link.
- Local exports are evidence snapshots and SHALL NOT act as a competing state
  store.

## 4. Routing

Routing over a goal-brief version SHALL follow this ordered predicate cascade;
the first matching rule wins.

1. A whole-application inventory/test/fix/retest objective routes to
   `total-tdd`, whose first state may clarify scope and inventory.
2. Otherwise classify: consequential decisions, non-negative unit cardinality,
   and — when cardinality is positive — unit boundedness and route certainty.
   If a required value is unknown because a human *decision* is unsettled, run
   at most one bounded grilling pass per goal-brief version, then reclassify
   once. Grilling resolves decisions, not empirical facts: a value that remains
   unknown because it depends on investigation no decision can settle (a
   dependency's real behavior, a spike's outcome) is left unknown here and is
   resolved by the `wayfinder` route at rule 5, not by grilling. A decision that
   *cannot be made until such a fact is known* is contingent, not settleable:
   grilling SHALL NOT force it closed. Leave it pending and let the goal route to
   `wayfinder` with the fact it depends on; it is decided on the re-route
   (section 4.1) once the fact is known.
3. If an unresolved decision now meets a human stop condition, pause for the
   human.
4. If cardinality is zero, terminate with a no-work receipt proving the goal
   already satisfies the current rubric and graph revision.
5. If cardinality is unknown, or boundedness or route certainty is anything
   other than true, route to `wayfinder`. The grilling predicate SHALL NOT be
   re-entered for the same goal-brief version.
6. If cardinality is one, execute the bounded unit directly.
7. If cardinality is two or more, route through `to-tickets`.

The route vocabulary is closed: `total-tdd`, `grilling-pass`, `pause-human`,
`no-work-receipt`, `wayfinder`, `direct`, `to-tickets`. No other route exists.
The seven divide into four **outcome routes** that decide how execution
proceeds — `total-tdd`, `wayfinder`, `direct`, `to-tickets` — and three
**interstitial outcomes** that resolve, defer, or terminate the pass without
executing: `grilling-pass` (resolve decisions, then reclassify), `pause-human`
(defer to the human), and `no-work-receipt` (terminate; the goal is already
satisfied).

### 4.1 Leaving `wayfinder`

`wayfinder` is terminal only for the *current, fogged* routing pass: it owns
route discovery, resolving investigation tickets until the units are bounded
and route-certain (see the neighbor table, section 11). Its discovery output is
recorded as investigation evidence on the tracker, not as an implementation
receipt. When the fog clears, routing re-runs over the **same** goal-brief
version with the now-known classification values and no new grilling pass — the
grilling predicate stays closed for the version, but re-routing on new facts is
required, not forbidden. That re-run lands on `direct` (one bounded unit) or
`to-tickets` (two or more), which then decompose and execute. `wayfinder` never
leaves the goal stranded without an execution route.

This first exit decomposes under the current, already-reconciled graph revision.
There is no prior implementation plan to invalidate, so no `[graph-revision]`
bump and no section 8 reconciliation are due at the wayfinder exit; section 8
fires only when evidence later invalidates an implementation plan that already
exists. Investigation tickets themselves live under the current graph revision
and do not advance it: they produce investigation evidence, not a change to the
implementation-plan shape that a revision numbers.

A decision that discovery reopens — one grilling settled, or one left pending as
contingent (rule 2) — is decided on this re-route, never by re-grilling. If the
discovered fact now determines the decision, the steward records it and
continues. If it still requires human judgment, it is an unresolved consequential
decision meeting a human stop condition and routes to `pause-human` (rule 3).

Consequences of the cascade order:

- Whole-app ownership wins over fogginess.
- One bounded unit wins over unnecessary decomposition.
- A foggy multi-unit set wins over direct `to-tickets` routing: if any unit's
  boundedness or route is uncertain, the whole set routes through `wayfinder`;
  only an entirely bounded, route-certain set of two or more units reaches
  `to-tickets`.
- Unknown cardinality never falls through: after the single grilling pass it
  routes to `wayfinder`, not back into grilling.
- `wayfinder` is not a dead end: once it clears the fog, the goal re-routes on
  the resolved facts to `direct` or `to-tickets` for execution.

## 5. Ticket contract

Every implementation ticket and every claim SHALL carry:

1. a mini goal brief (binary destination for the unit),
2. explicit dependency edges,
3. a structured verification receipt contract,
4. a stop condition,
5. the goal-brief version, and
6. the graph revision.

## 6. Receipt validation and unlocking

- A ticket is complete only after its receipt is validated against that
  ticket's mini-goal rubric and stop condition at the current goal-brief
  version and graph revision.
- Failed, missing, or stale proof sends the ticket to rework.
- Only a validated current-revision pass MAY unlock dependents.

## 7. Frontier execution and claim ownership

- The steward SHALL execute only dependency-ready tickets.
- The existing host task controls and the parent Linear claim admit one active
  steward per goal. If a current non-stale parent claim already exists, a new
  steward SHALL stop.
- Only the steward MAY mutate the graph or claim child tickets. It serializes
  claim writes after the matching `[graph-reconciled]` marker and dispatches
  already-claimed units.
- Workers SHALL NOT self-claim and SHALL return receipts keyed to the
  steward-issued claim.
- This skill does not invent an atomic lease; it relies on the host task
  controls and the parent claim.
- Per-unit execution runs through the existing mechanisms (harness gate/build/
  verify/judge, TDD, council review, `efficient-fable` delegation) — never
  through a mechanism this skill invents.

## 8. Re-planning and reconciliation

A re-plan and a version bump advance the graph revision under different
authority. A goal-brief version change alters the destination and therefore
requires an authorization reference (section 2–3). A re-plan advances the graph
revision without changing the destination; its authority is the invalidating
evidence itself, recorded in the impact analysis of step 3 below — no separate
human authorization is needed unless the re-plan also trips a section 9 pause.
The invalidating evidence includes a `wayfinder` or spike finding, which is
recorded as investigation evidence (section 4.1), not as an implementation
receipt, and so is never subject to the receipt-staleness rule.

When evidence invalidates the plan:

1. First append a new authoritative `[graph-revision]` marker so in-flight
   receipts become stale.
2. Block new claims.
3. Impact-analyze affected completed, queued, and in-flight tickets.
4. Invalidate stale completed receipts and their downstream unlocks; move
   affected work to rework or obsolete; rewrite tracker relations.
5. Record current-revision carry-forward validation for every unaffected
   completed contributor.
6. Recursively revalidate the newly ready frontier.
7. Append `[graph-reconciled]` for that revision before claims resume.

A claim or receipt is valid only if the matching `[graph-reconciled]` marker
predates it and no newer `[graph-revision]` marker exists — unless a recorded
current-revision carry-forward validation for that receipt exists, which
preserves it across the revision change (section 2).

## 9. Stop conditions

- Stop and re-design if the work would need a second runtime state store or
  ticket runner.
- Pause for the human if a discovered requirement materially changes scope,
  authority, architecture, or irreversible behavior, or if the work would
  publish, merge, release, deploy, or broaden agent authority.
- Otherwise record routine decisions and continue.

The threshold between a routine re-plan (reconcile and continue, section 8) and
a human pause is what the evidence changes. If it changes only *how* units are
built within the current brief, authority, and architecture — a different
approach, ordering, or interface at one boundary — it is routine; reconcile and
continue. It becomes a pause only when it changes the goal-level destination,
authority boundary, or a load-bearing architecture decision, or forces an
irreversible behavior. Discovering that a dependency needs a different but
equivalent integration at one seam is routine; discovering that satisfying the
goal now requires another team to change a public contract, or that the chosen
architecture cannot meet the rubric, is a pause.

## 10. Final verification and DONE

Project completion SHALL be verified against the original overall goal-brief
version and its authorized change history. Completed tickets alone are
insufficient. After the subject is committed, the steward SHALL:

1. re-read the authoritative Linear graph,
2. verify every contributing ticket at the current graph revision,
3. recompute and verify the authorized goal-brief digest chain,
4. open the draft PR, and
5. post the final receipt to the parent issue naming the authoritative
   goal-brief version, verified digest chain, current graph revision, complete
   tracker-derived ticket closure, the exact subject commit or artifact digest,
   and the draft PR.

The receipt lives outside the subject it certifies.

## 11. Neighbor boundaries

| Neighbor | It owns | goal-to-done's use of it |
| --- | --- | --- |
| `grilling` | Resolving consequential human decisions one at a time | At most one bounded pass per goal-brief version, only for an unknown *decision* (not an empirical unknown) |
| `goal-spec` | Compiling one binary, verifiable dispatch brief | Producing the overall goal brief and each ticket's mini brief |
| `wayfinder` | Discovering the route through foggy work | Discovery route for unknown cardinality or uncertain boundedness/route; terminal for the fogged pass, then re-routes on the resolved facts to `direct`/`to-tickets` (section 4.1) |
| `to-tickets` | Decomposing a clear plan into vertical slices | Route for two or more bounded, route-certain units |
| `total-tdd` | Whole-application inventory/test/fix/retest | First cascade rule for whole-app objectives |
| `efficient-fable` | Delegating bounded heavy lifting | Per-unit delegation during execution |
| `linear` skill | Tracker operations | All parent/child issue reads and writes |
| harness (`harness run` / `--gate-only`, `council`) | Gating, building, verifying, judging one bounded unit | Per-unit gate/build/verify/judge |
| Host task controls | Task lifecycle, single-steward admission | Claim admission and dispatch |

`goal-to-done` SHALL NOT claim to create a daemon, scheduler, tracker API,
harness, TDD method, or review council.
