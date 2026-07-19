# Deviations

- The first Plannotator approval process expired before recording its decision.
  The exact current file was reopened and returned `{"decision":"approved"}`.
- The first spec exceeded the fast council's fixed prompt ceiling. Repeated
  prose was compressed in the source spec; the profile was not enlarged or
  bypassed.
- Council proposals for local hashes, timestamps, fingerprints, duplicated
  arena results, and self-attested blind-context manifests were rejected. They
  move trust into author-issued metadata instead of establishing authenticity.
- The legacy harness council still binds obsolete Cline Kimi configuration and
  omitted Cursor's required trust flag. Those seats were excluded visibly. The
  current adapters were qualified directly: Cline used explicit
  `cline-pass/glm-5.2`; Cursor used `agent --trust` after native re-login.
- Arena suite v1 mislabeled a hybrid integration that omitted requested and
  effective effort as clean. Suite v2 retains that behavior as a dirty case and
  adds an actually clean counterpart; all final baseline and with-skill evidence
  is from the versioned suite, never the obsolete score.
- `uv run pytest -q` in skill-arena cannot import its committed top-level
  `majority` and `apps` modules. `PYTHONPATH=. uv run pytest -q` is the verified
  repository command; no packaging shim was added to this change.

## Gate run 2026-07-17

- The behavioral eval was saturated: `gpt-5.6-sol` scored 100% at baseline, so the
  suite showed no lift on the strong model. A local discrimination column
  (`qwen-coder-32b-fc` via the LiteLLM proxy) was added; it has headroom and shows
  the skill's effect directly — baseline 8/18 (44%) → with-skill 11/18 (61%),
  +17pp. The strong-model 100%/100% remains a regression guard, not evidence of lift.
- `codex`/`gpt-5.6-sol` hit its subscription usage limit mid-gate (resets 2026-07-23).
  This is a `capacity` failure, kept visible per the no-hidden-integration rule. The
  seat was not substituted: the discriminating eval evidence comes from the local
  qwen seat, and the final council runs the remaining Claude/Cline/Cursor families.
  The codex column in the combined matrix therefore shows honest ERROR cells, never
  fake passes; the canonical eval receipt is the clean local-only run.
- Live integration qualification uses the local model seat (provider `local`, model
  `qwen-coder-32b-fc`, auth none/localhost), the one seat fully qualifiable without a
  secret. Smoke (identity/`/v1/models`) and the representative arena operation are
  separate receipts; observed provider/model match the declaration, no substitution.

## Council findings (final/deep, 2 families: claude + cursor) — verdict FAIL, actionable items fixed

- The checker guarded smoke/representative distinctness but not baseline-vs-behavioral or the
  two forward-test receipts, and accepted zero-byte receipts. All three holes are now closed
  (distinctness guards + non-empty-file rejection in workshop.py, each with a test).
- SKILL.md now states a `complete` checker exit is necessary-not-sufficient; only semantic
  receipt review + independent council make completion real.
- Rejected finding (cursor, factually wrong): `isinstance(0, bool)` is False in Python; the
  code already excludes booleans and complete-receipt tests confirm `exit_code: 0` is accepted.
- Open design decision left to the maintainer: the harness flags the SPEC's prose completion
  criteria as not machine-checkable; either bind each workflow row to a binary receipt key or
  demote the prose rows to guidance and name the checker gates as the acceptance contract.
- Completion remains blocked: the spec/fast review reached only one family (codex capacity /
  cline adapter / cursor auth all down at that moment), and the 2-family final review's verdict
  was FAIL on the pre-fix checker. A clean re-review of the hardened revision is the remaining
  step; it needs a second live review family (claude + cursor are currently reachable; codex
  resets 2026-07-23).

## Council re-review on hardened revision (2026-07-17, second pass)

- All actionable findings from the first pass are addressed: zero-byte receipts rejected,
  baseline!=behavioral and distinct forward-test receipts required, guarded ignore read,
  SKILL.md necessary-not-sufficient, and a binary Acceptance contract added to SPEC.md.
- Result: the council HARNESS (deterministic) gate now PASSES (previously FAIL on prose
  acceptance criteria).
- The council PANEL still cannot run: its preflight policy requires 3 valid seats; only
  claude:opus and cursor:composer-2.5 are ready. codex is capacity-blocked (resets
  2026-07-23) and cline is at $-0.00 credits (the invalid-model-format error was a stale
  `kimi-k2-thinking`; the working format is `z-ai/glm-5.2`, but the account balance is empty).
- No seat was substituted. Completion stays blocked on seat availability, now confirmed by
  the council tool's own min-3-seat preflight, not author judgment. Recovery: restore codex
  quota (Jul 23) or top up Cline credits, then re-run both councils.

## Full 4-seat council round (2026-07-18) — verdict fail, findings fixed

The Cline Pass fix (harness PR #23) restored the cline seat, so both councils finally
convened the full panel: codex/gpt-5.6-sol, cline/glm-5.2, claude/opus, cursor/composer-2.5.
HARNESS PASS, 4/4 personas produced valid verdicts, `status=fail` on both.

Findings accepted and fixed in this revision:

- The content layer exempted the highest-trust evidence: `content_errors` scanned only
  command records and forward tests, so `councils[].status` and `thermos.security|quality`
  were hand-typed enums whose receipt text was never read. `check` could have exited 0 with
  a linked council receipt that said `status=fail`. Councils and Thermos are now checked
  with precise result-line signatures (they quote failures legitimately, so the generic
  traceback/exit signatures would false-positive).
- Family identity was the one identity never grounded, which made cross-family
  independence — the design's core claim — satisfiable by typing a second family name.
  Every declared council family and forward-test family must now appear in its own receipt,
  and the two forward-test receipts must not be identical content.
- Consequently this work unit's own council families were re-recorded from
  `anthropic/cursor/zhipu` (which appear nowhere in the receipts) to the four seats the
  receipts actually evidence: `codex, cline, claude, cursor`.

Finding rejected as factually wrong: "structural check can mark integration complete while
`live` is ready with a non-`none` failure class." It cannot — `completeness_errors` already
rejects that combination, verified by crafting exactly that manifest and observing
`incomplete: ready live state requires none failure and null recovery`.

Finding recorded, not actioned: the Pragmatist's YAGNI critique that the contract accretes
typed fields faster than consumers read them. A real design question for the maintainer, not
a defect in this revision.

Council status is recorded `fail` for this round — it is the honest verdict, and the
completion gate stays closed until a panel clears the fixed revision.

## Final review round (2026-07-19) — bounded by agreement to one pass

Both councils ran on the full 4-seat panel (codex, cline, claude, cursor), HARNESS PASS,
4/4 valid verdicts each, run sequentially (concurrent runs contend on cline's hub and
cursor's credential lookup).

- `spec/fast`: **concerns** — all four personas CONCERNS, zero FAIL. Accepted under the
  no-blocking-defect gate.
- `final/deep`: **fail** — the Architect (codex) returned FAIL. Not accepted. Recorded as
  returned; it is deliberately NOT re-graded on the strength of the fixes below.

Two findings were real defects in this round's own code and were fixed:

- `report_command` computed its verdict from structure + completeness only and never called
  `content_errors`, so a manifest failing the new content layer still rendered
  `Checker verdict: complete` under a banner calling that authoritative — inverting the very
  confusion the round set out to fix. It now mirrors `check_command`'s ordered pipeline.
- Thermos was exempt from the positive `GRADE` cross-check although SPEC required it of every
  non-`.json` receipt, so a hand-typed `{"security":"pass","quality":"pass"}` could pass on
  absence-of-failure alone. `_grade_agreement_error` is now applied to it.

Standing objections — recorded, not actioned (the fix-and-review loop was bounded to one
pass by explicit decision):

- `.json` receipts are exempt from the positive `GRADE` check, so an unrelated or stale JSON
  file can satisfy a command gate when no failure signature matches. Closing this needs a
  recognized result field per JSON receipt kind.
- `failure_class` (`none|auth|model|capacity|timeout|adapter`) is validated for membership but
  the checker never branches on the distinct values — all six collapse to `none`→ready,
  anything else→blocked. It is a vocabulary with no distinct gate logic; `status` + free-text
  `recovery` would carry the same weight. A real YAGNI critique of the contract's size.
- The `GRADE:` vocabulary and casing are enforced in code (`PASS|FAIL|CONCERNS|BLOCKED`,
  uppercased on parse) but not stated normatively in SPEC, and council receipts carry a second
  dialect (`COUNCIL RESULT: status=…`). A documentation gap, not a behavioural one.

The completion gate therefore remains open on `councils[1]`. It is honestly open: closing it
requires a fresh panel on the fixed revision, not a re-grade of the verdict already returned.

## Ship decision (2026-07-19) — maintainer override of the completion gate

`SKILL.md` says to ship only when `workshop.py check` reports `complete`. It reports
`incomplete` on exactly one item: `evidence.councils[1] is fail`. The maintainer
(Jason) reviewed the state and elected to ship anyway rather than run a fourth
fix-and-review round. This is an explicit, recorded override, not an oversight:

- Every other gate passes, including all four content-lint layers.
- The `spec/fast` council is accepted (`concerns`, 4/4 seats, zero FAIL).
- The `final/deep` FAIL was driven by two defects in that round's own code, both since
  fixed with tests; the verdict is kept as returned rather than re-graded.
- The remaining objections are recorded above and none is a live defect.

The receipt is therefore shipped `incomplete` and truthful. Closing the gate later
requires a fresh panel on this revision — the honest path stays open, and nothing in
the manifest was edited to manufacture a green result.
