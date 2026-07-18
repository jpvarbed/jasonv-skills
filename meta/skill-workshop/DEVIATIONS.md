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
