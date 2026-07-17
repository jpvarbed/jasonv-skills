---
name: adversarial-review
description: Run a fast two-persona or deep four-persona adversarial council across live-verified configured seats. Use when asked to “review this plan,” “red-team this spec,” “challenge this decision,” or independently review an ADR, PRD, or diff. Uses ignored per-device profiles and prohibits Gemini and unplanned runtime substitution. NOT for visual UI critique (use visual-critique) or deterministic claim checking (use verify-this).
---

# Adversarial Review

Run the selected profile’s independent reviewer personas against the same
bounded evidence, then verify and synthesize their findings. Seat allocation is
declared in device config before the run and frozen before any model call.

Gemini is prohibited as an engine, provider, gateway model, alias, or fallback.

Announce at start: “Using adversarial-review `<fast|deep>` on <artifact>.”

## Step 1 — Load the device contract

The device source of truth is the ignored `council-config.json` beside this
file. `council-config.example.json` is the only canonical config shape.
`scripts/council.py` is the thin validation and execution entrypoint; its
bundled adapter registry is the command, receipt, and derived-family authority.
Do not recreate either contract in prose, a shell wrapper, or another launcher.

The config records only device facts: seat ID, adapter, non-secret auth/setup,
absolute direct executable, model, profile bindings, and separate last-observed
`smoke` and `review` status.
It never contains command arguments, receipt selectors, adapter policy, or
credential values. Recovery text is derived at read time from the current
failure, operation, and seat setup; it is never persisted where it can drift.
The registry constructs adapter behavior centrally. Live smoke records
the installed CLI version when its benign metadata probe succeeds; version
discovery never gates readiness and auto-updates do not require editing config.

Keep the working directory at the repository being reviewed. Resolve this
skill's installed directory and invoke the runner there by absolute path; the
default config remains beside the skill while artifact paths remain relative to
the target repository.

Validate the schema:

```bash
python3 /absolute/path/to/adversarial-review/scripts/council.py validate
```

If its `setup_available` array is non-empty, report `SETUP AVAILABLE` and offer
one-time configuration before continuing. The runner checks known executable
aliases in priority order and reports an installed adapter only when no seat for
that adapter is configured. This is advisory; it never auto-adds a seat or
changes the review outcome.
Also report any configured seat whose last-observed smoke or representative
review is not ready, even when the selected profile does not bind it. A passing
smoke proves only the benign identity/auth path; it never overwrites a failed
representative review. `smoke --all` refreshes only smoke observations during
explicit maintenance. Routine reviews update only review observations.
`review_qualified` means the last representative review succeeded and no newer
smoke failure has since disproved basic CLI/auth/model readiness. A later smoke
success never turns a failed review into qualified.

## Step 2 — Configure missing seats

When `council-config.json` is missing:

1. Check only `codex`, Cursor's official `agent`/`cursor-agent` aliases,
   `cline`, and `claude` on `PATH`.
2. Tell the user which known seats are detected and ask which to set up.
3. Copy `council-config.example.json` to the ignored device config and replace
   the four built-in templates with the selected seats. Inspect the installed
   CLI’s own help, auth status, model catalog, and structured output. Do not
   infer a model or auth route from memory.
4. Record the exact non-secret setup and recovery actions. Prepare required
   environment variables in the invoking process without writing or printing
   their values.
5. Record the resolved absolute direct executable. Run `validate` followed by
   `smoke --all`. Repair and re-smoke one seat at a time until every configured
   seat's live structured identity receipt passes.
6. Deliberately bind a new seat into both profiles and run a representative
   review before treating it as review-qualified. Keep it bound only if that
   bounded review succeeds; otherwise leave it configured and visibly unbound
   with its review failure recorded.
7. Keep `fast` and `deep` bound to at least two model families whenever the
   device has two review-qualified families. Keep failed/unqualified seats in
   inventory but do not let them make valid profiles impossible. If only one
   family is qualified, report that limitation instead of inventing diversity.

Record these one-time device steps in the seat itself:

- Codex — install `codex`, complete first-party login, select the exact GPT
  model, then smoke and run a representative review.
- Cursor — install the official `agent`/`cursor-agent`, provision
  `CURSOR_API_KEY` through the device's secret manager, and require the init
  receipt's auth source to be `env`. On the tested build, browser login was
  consumed after one headless call and caused repeated browser prompts, so do
  not use `agent login` for council automation.
- Cline — `npm install -g cline`, approve ClinePass OAuth, select an exact GLM
  model, and run identity smoke. Leave it unbound when a representative review
  exceeds the profile bound even though smoke passes.
- Claude Code — install `claude`, complete first-party browser login, select the
  exact Claude model, then smoke and run a representative review.

The registry owns each adapter's exact read-only command and structured receipt
parser; `scripts/council_adapters.py` is normative. The parent never retries,
resumes, or reassigns an invocation.

Any fallback-named argument, Gemini lineage, shell/interpreter launcher,
embedded credential, malformed receipt, model mismatch, or unsafe built-in
posture is `SETUP REQUIRED`. `validate` also rejects a profile bound to one
family when the device has two or more review-qualified families.

Do not configure a custom executable. An opaque binary cannot prove provider
lineage strongly enough to enforce the no-Gemini rule.

If a known built-in later appears on `PATH` but is absent from the config,
report `SETUP AVAILABLE` and offer its one-time setup. Do not silently add it.
Do not remove a temporarily failed seat to make a review pass. When a seat is
permanently added, revoked, or retired, deliberately update the device config
and profile bindings before the next run, then validate and smoke the new frozen
allocation. That planned maintenance is not runtime substitution.

## Step 3 — Diagnose or maintain seats

`review` validates the whole config, including family diversity, freezes the
selected profile, and launches those persona calls directly. Do not run smoke
on the normal review path: its latency is real, and a benign identity prompt is
not evidence that a representative review will complete.

When diagnosing setup without starting a review, keep the target repository as
the working directory:

```bash
python3 /absolute/path/to/adversarial-review/scripts/council.py smoke --profile fast
```

Use the same absolute runner path with `smoke --all` only for full device
maintenance. Diagnostic smoke probes selected seats concurrently, including
failed ones, and updates only `observed.smoke`. Persona calls update only
`observed.review`. State writes hold a per-config lock and retain the newest
observation for each operation, so later smoke success cannot erase a review
timeout and overlapping processes cannot erase newer state.

Structured stdout is authoritative. Stderr noise is recorded but does not fail
a seat when the process exits zero and every configured result and identity
assertion passes.

| Issue/Error | Fix |
|---|---|
| `unconfigured` | Replace the canonical template with exact device facts, then validate. |
| `not_run` | Deliberately bind the seat into both profiles, run one bounded representative review, and retain the bindings only on success. |
| `cli_missing` | Install the exact recorded direct CLI, then rerun the failed operation. |
| `auth` | Perform the recorded OAuth/environment setup without storing credentials, then rerun the failed operation. |
| `model` | Select an exact supported model on that auth route, update config, then rerun identity smoke and a representative review. |
| `invalid_output` | Repair the built-in structured receipt contract or CLI, then rerun the failed operation; never weaken the expected result. |
| `adapter_error` | Inspect the direct CLI, auth route, model, and structured receipt, then rerun the failed operation. |
| `capacity` or `timeout` | Leave that operation visibly unavailable and rerun it later; never substitute another model or seat within the review. |

## Step 4 — Run the council

Choose:

- profile — `fast` by default for iterative/routine reviews; `deep` for final,
  high-risk, security-sensitive, or architectural decisions. On adapters with
  an effort control, `fast` review calls request low and `deep` review calls
  request medium;
- objective — one sentence describing the intended outcome;
- artifact — the smallest readable file set containing the decision and
  rationale; repeat the flag for multiple files;
- focus — the specific bet to attack, or omit;
- resolved — closed decisions not to re-litigate, or omit;
- evidence — output from a deterministic test, lint, build, typecheck, or
  factual gate actually run in this task (or an attached command receipt),
  treated as ground truth; otherwise omit.

Run:

```bash
python3 /absolute/path/to/adversarial-review/scripts/council.py review \
  --profile fast \
  --objective "Verify that the proposed design satisfies its stated invariants." \
  --artifact SPEC.md \
  --focus "Failure visibility and model identity" \
  --resolved "Gemini and runtime fallback are prohibited" \
  --evidence "python3 -m unittest discover -s tests -v passed"
```

`fast` binds Architect and Adversary to two configured fresh calls and is the
default because it makes the speed/reasoning tradeoff explicit. `deep`
binds Architect, Pragmatist, Verifier, and Adversary to four configured fresh
calls. When the device
has two or more review-qualified model families, both profiles must bind at
least two families; unqualified inventory seats do not force impossible
bindings. A profile
may still reuse a seat for multiple fresh processes. That is planned allocation,
not fallback. Report actual engine/model allocation only from the frozen run
receipt, never from device-specific prose.

The runner accepts only relative artifacts inside the target repository's
working directory. `fast` requests low effort, caps each fully assembled
per-persona prompt at 16 KiB, allows one finding, and caps review calls at 60
seconds. `deep` requests medium effort, caps each prompt at 24 KiB, allows three
findings, and caps review calls at 90 seconds. Explicit diagnostic smoke uses
low effort with a 20-second (`fast`) or 30-second (`deep`) cap. Prompt
limits are measured as UTF-8 bytes after assembly. Version probes are capped at
10 seconds. Both freeze configured bindings and launch distinct seats concurrently
in fresh empty temporary working directories; repeated bindings to the same seat
serialize to avoid self-inflicted capacity failures.
Smoke calls always use low effort regardless of profile. Review calls use the
profile setting when the adapter exposes an effort control; otherwise effective
effort is carried by the configured model variant. The receipt makes that
difference explicit for every call, plus the call-timeout ceiling implied by
any serialized bindings.
Workers never share outputs or write the receipt; the parent serializes results
in profile order and atomically records the same typed seat state after review
failures. A failed or invalid persona is never reassigned, retried
through another model, or repaired.
Every adapter process starts in its own process group. An outer timeout
terminates and then kills that whole group. Cline's internal deadline is five
seconds shorter than the outer bound, and Cline receives a new empty hooks
directory so device-global hooks cannot inject context.

Every adapter returns the same typed JSON persona object. Claude enforces it
with native JSON Schema; the runner validates exact keys, identity,
verdict/severity consistency, and numbered non-blank, non-whitespace artifact
citations for every seat. The runner resolves the exact cited line itself. Missing, invented,
or inconsistent fields remain invalid.

## Step 5 — Verify and synthesize

When personas ran, use the receipt’s `post_run_seats.review` for final review
status and show smoke status separately when it matters. For `SETUP REQUIRED`,
use the validated config/setup error; `INVALID REQUEST` has no seat mutation.
Do not treat model verdicts as council authority.
Against the supplied artifacts, classify every structurally valid finding as:

- accepted;
- already covered;
- closed-decision re-litigation;
- unsupported or invented.

Drop everything except accepted findings. Deduplicate the same defect, re-rank
severity from demonstrated consequence, and recompute each effective persona
verdict: High → `FAIL`, else Medium → `CONCERNS`, else `PASS`.

Return:

```text
COUNCIL VERDICT: PASS | CONCERNS | FAIL | INCOMPLETE | SETUP REQUIRED | INVALID REQUEST
COVERAGE: profile=<fast|deep> personas=<valid>/<required> families=<used> engines=<used> review_ready=<ready seats> timeout_ceiling=<seconds>
RECEIPT: <path; none only when no persona launched>
SEAT STATUS:
- <seat> (<engine>/<model>): smoke=<status> review=<status> — <review recovery if any>
MUST-FIX:
- [H|M|L] <deduped accepted finding> (raised by: <personas>)
DROPPED:
- <finding> — <already covered|re-litigation|unsupported>
PER-PERSONA:
- <persona> via <engine>/<model> effort=<effective>: <raw verdict> -> <effective verdict|invalid|failed> (<failure class if invalid/failed>)
BIGGEST RISK: <one line>
```

Outcome order:

1. `INVALID REQUEST` — the assembled prompt exceeds the profile bound or an
   artifact/request is invalid; no persona ran.
2. `SETUP REQUIRED` — device config/setup is invalid before allocation; no
   persona ran.
3. `INCOMPLETE` — any frozen profile call failed or was invalid, including
   auth, model, capacity, or timeout failures discovered by the real call.
4. `FAIL` — every selected output is valid and an accepted High remains.
5. `CONCERNS` — every selected output is valid, no accepted High remains, and
   an accepted Medium remains.
6. `PASS` — every selected output is valid and no accepted High or Medium
   remains.

There is no degraded pass and no runtime substitution.
