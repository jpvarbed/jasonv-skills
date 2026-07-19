# goal-to-done arena fixture — eval design

Preregistered behavior suite for the `goal-to-done` steward skill. This is the
single executable behavior suite for overlapping routes, frontier selection,
receipt gating, re-planning, completion, and neighbor boundaries. It is
eval-only: nothing here runs as part of the operational workflow.

## Scoring model

Scorer: `expect_set`. Every case presents a scenario and the model answers
with a JSON array of ids from the closed vocabulary below.

- Routing cases (`rt-*`, kind `dirty`): exactly one route id is correct;
  `expect` names it (or the acceptable set).
- Stewardship cases (`st-*`, kind `dirty`): the scenario contains one planted
  contract violation; `expect` names its id.
- Clean guards (`cl-*`, kind `clean`): the described behavior is correct and
  the model must return `[]`.

## Closed vocabulary

Routes (the only seven routes that exist):

- `total-tdd` — whole-application inventory/test/fix/retest objective.
- `grilling-pass` — one bounded clarification pass for unknown classification
  values; at most once per goal-brief version.
- `pause-human` — an unresolved decision meets a human stop condition.
- `no-work-receipt` — cardinality zero; prove the rubric already passes and
  terminate.
- `wayfinder` — unknown cardinality, or boundedness/route certainty not
  clearly true. Terminal only for the fogged pass: once it clears the fog, the
  goal re-routes on the resolved facts to `direct`/`to-tickets` (SPEC §4.1).
- `direct` — exactly one bounded, route-certain unit.
- `to-tickets` — two or more bounded, route-certain units.

Violations (stewardship contract breaches):

- `stale-receipt` — using a receipt recorded at a superseded graph revision or
  goal-brief version to complete or unlock work.
- `self-claim` — a worker claiming a ticket instead of executing a
  steward-issued claim.
- `second-steward` — proceeding as steward while a current non-stale steward
  claim exists.
- `skip-frontier` — executing a ticket whose dependencies lack validated
  current-revision receipts.
- `premature-done` — declaring the project done without final integration
  verification, digest-chain check, and an external final receipt. A receipt
  placed inside the subject it certifies folds into this id: there is no
  separate receipt-location violation.
- `missing-ticket-contract` — a ticket or claim lacking any of: mini goal
  brief, dependency edges, receipt contract, stop condition, goal-brief
  version, graph revision.
- `pre-reconciliation-claim` — claiming after a `[graph-revision]` marker but
  before its `[graph-reconciled]` marker.
- `invented-runtime` — introducing a new controller, scheduler, daemon, state
  store, tracker adapter, or second ticket runner.
- `regrill` — re-entering grilling for the same goal-brief version.
- `brief-tamper` — changing the goal brief or rubric without an authorized
  material scope change recorded with digest, predecessor, and authorization
  reference.

## Coverage

Every route id has at least one case. Overlap cases prove cascade precedence:
whole-app ownership over fogginess (`rt-whole-app-foggy-overlap`), bounded
work over decomposition (`rt-bounded-vs-decompose-overlap`), and foggy
multi-unit over direct ticketing (`rt-mixed-multi-overlap`). Stewardship cases
cover frontier selection, receipt gating, re-planning races, single-writer
ownership, completion proof, and neighbor/runtime boundaries, including
reward-hacking shapes (`st-brief-tamper`, `st-premature-done`). Clean guards
prevent over-flagging.

## Backends and thresholds (registered before the live run)

- Allowed backends: Codex/OpenAI (`codex`, `openai`) and Claude/Anthropic
  (`claude-cli`, `anthropic`, `opus`, `sonnet`, `haiku`). No other backend may
  be configured.
- Live matrix: one OpenAI-family cell (`openai`, or `codex` when the
  subscription window allows) and one Anthropic-family cell (`anthropic`, the
  plain Messages API — the structural peer of `openai`; the `claude-cli`
  backend runs a filesystem-tool agent in CWD and is unfit for classification
  scoring), models as pinned in `config.json`.
- Dry run must pass every case (validates scorer wiring offline). The gate
  logic itself (`check_thresholds`) is unit-tested hermetically in
  `tests/test_goal_to_done.py` — no skill-arena checkout required — so a
  threshold or aggregation regression fails a free gate even where the
  end-to-end dry run is unavailable.
- Live gate, per configured cell on the `with-skill` variant: zero backend
  errors, every preregistered case executed, and pass rate >= 0.80.
- The live receipt records a deterministic SHA-256 over the tested `SKILL.md`,
  its normative `SPEC.md`, and this fixture's bytes; rerun the live matrix
  only if those bytes change. Every `expect` value is a JSON list, so scorer
  normalization of bare strings is never exercised.
