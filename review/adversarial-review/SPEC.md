---
ROLE: steward
DELEGATION_DEPTH: 0
WORK_UNIT: 311b4713-ad19-4254-8754-bfd8f389ff21
---

# adversarial-review specification

## Purpose

Run a configured adversarial-review profile across agent seats that are
actually usable on the current device. Seat setup, profile allocation, and
availability must be durable, live-verified, and detectable. A broken selected
seat is exposed; it is never hidden by an unplanned model substitution or
mid-review reassignment.

The skill is the user-facing workflow. A bundled deterministic Python runner
owns config validation, direct process invocation, smoke validation, frozen
allocation, persona-output validation, verified source-line citations, and
ignored run receipts. Its closed adapter registry is the sole authority for
command construction and receipt parsing. This is not the deleted shell
fallback chain.

Gemini is prohibited as an engine, provider, gateway model, alias, or fallback.

## Files and authority

The skill directory contains:

```text
SKILL.md                         user-facing setup and synthesis workflow
council-config.example.json     one canonical config shape
council-config.json             ignored device-local config
scripts/council.py              thin deterministic CLI entrypoint
scripts/council_adapters.py     closed argv, lineage, and receipt registry
scripts/council_state.py        device schema, setup discovery, durable state
scripts/council_runtime.py      bounded invocation and council orchestration
.council-runs/                  ignored per-run receipts
tests/test_council.py           deterministic behavior tests
```

There is no second config schema in `SKILL.md` or this spec. Both reference
`council-config.example.json`. The runner is the executable authority for
validation semantics, and the example must pass it in tests.

The local config contains no credential values or adapter implementation. It
records exact non-secret auth routes, the absolute direct executable, model,
setup actions, profile bindings, and the last observed state for every
configured seat, split into independent `smoke` and `review` observations. Live
smoke records the installed CLI version when a
best-effort metadata probe succeeds rather than pinning an auto-updating binary
in config.

## First-use setup

When `council-config.json` is absent, `SKILL.md` tells the invoking agent to:

1. check only the built-in executable names `codex`, Cursor's official
   `agent`/`cursor-agent` aliases, `cline`, and `claude`;
2. ask which detected seats to configure;
3. ask for each seat's exact auth route and model, then inspect the installed
   CLI's own help, auth status, and model catalog;
4. copy the canonical example shape into the ignored config without credential
   values;
5. prepare required auth in the current process environment;
6. run `scripts/council.py smoke --all`;
7. inspect the registry's live structured identity receipt and repair one
   failed seat at a time until it passes;
8. deliberately bind each new seat into both profiles for a representative
   review and retain those bindings only after that bounded review succeeds;
9. bind `fast` and `deep` to at least two model families whenever the device
   has two review-qualified families; unqualified seats remain visible in
   inventory without forcing an impossible binding.

No Bitwarden installation, environment variable, account type, or default
model is assumed.

If a known built-in later appears on `PATH` but is not configured, the skill
reports `SETUP AVAILABLE` and offers to configure it. Custom executables are not
supported because their provider lineage cannot be independently verified
against the no-Gemini rule.

Seat additions, revocations, and retirements are deliberate config-maintenance
events before a run. The operator updates seats and profile bindings, then
validates and smokes the resulting allocation. Runtime failures never mutate
profile bindings or retire a seat automatically.

`validate` probes the known executable aliases in priority order and emits
`setup_available` for an installed adapter that has no configured seat. This is
advisory discovery only: it never mutates config, auto-adds a seat, or changes
the review outcome.

## Config contract

`council-config.example.json` is the only normative JSON shape. It has
`schema_version: 1`, an ordered `seats` array, and named review `profiles`.

Each seat records only:

- unique seat ID, adapter type, absolute direct executable path, and exact model
  ID;
- auth method, non-secret route label, required and explicitly unset
  environment variable names, and setup actions;
- separate smoke and representative-review observations, each with status,
  typed failure, sanitized error, and fixed-width UTC timestamp.

Recovery text is derived when emitted from the current failure class,
operation, and seat setup steps. It is not persisted, so a changed auth/setup
contract cannot leave stale recovery instructions in device state.

`review_qualified` is derived: the last representative review succeeded and no
newer smoke failure has since disproved basic readiness. Smoke success alone
never qualifies a failed review.

Engine, provider, model family, command arguments, timeout policy, and receipt
parsers are derived from the closed built-in adapter registry. Device config
cannot add flags, receipt selectors, or alternate launchers.

Each profile freezes persona-to-seat bindings before runtime:

- `fast` binds Architect and Adversary to two independent calls;
- `deep` binds Architect, Pragmatist, Verifier, and Adversary to four
  independent calls.

Bindings refer to configured seat IDs. Different model families are a strong
quality requirement whenever the device has a qualified choice: if two or more
derived model families have `review_qualified: true`, both profiles must
bind at least two. Unqualified seats stay in inventory without forcing a failed
seat back into a profile. A profile may
still bind the same seat more than once; that is planned allocation, not
fallback. Every binding gets a fresh direct process/context with no persona
output passed to another. Actual engine/model allocation is reported only from
the frozen run receipt. `family` is derived from the adapter and exact model:
Codex/OpenAI GPT, Cursor/Composer, supported ClinePass model lineages, or
first-party Claude. Two ClinePass seats using DeepSeek and GLM therefore count
as two model families even though they share an adapter. Receipts report model
family and engine separately.

The registry constructs direct argv arrays in code and never invokes a shell.
No config value is interpreted as an argument. Prompt and runner-owned schema
values are passed as opaque single arguments. Claude Code enforces the typed
persona contract natively.

## Static safety validation

Before running any child process, the runner rejects:

- malformed or unknown config keys/types/schema versions;
- credential-looking fields or values;
- Gemini anywhere in engine/provider/model/auth/receipt lineage;
- a built-in adapter whose executable basename is not its known direct CLI;
- missing executable, model, auth, setup, or observed-state facts;
- any adapter or executable outside the four built-in direct CLIs;
- a relative executable path;
- a profile binding fewer than two model families when the device has two or
  more review-qualified families;
- a provider or model outside the adapter's hardcoded non-Gemini family:
  OpenAI GPT for Codex, Cursor Composer, ClinePass for Cline, and
  first-party Claude for Claude Code;

There is no argv denylist. The registry generates the entire accepted command:
Codex is read-only/ephemeral with approvals disabled; Cursor is Ask mode with
sandboxing; Cline is plan mode with tools unapproved, a stateless system prompt,
compaction off, an empty per-invocation hooks directory, an internal deadline
five seconds shorter than the parent hard stop, and the CLI's lowest accepted
internal mistake budget (`--retries 1`); Claude is plan/manual with tools
disabled, safe mode, and no session persistence. The parent never retries a
Cline invocation. Every adapter starts in a new process group; timeout first
terminates and then kills that entire group. Device config
cannot append extension, mutation, persistence, or background flags.

Built-in engine and provider identity are canonical for the adapter. Model
identity is proved by a structured receipt where exposed, otherwise by the
registry-owned exact argv pin. The registry contracts and sanitized receipt
fixtures have tests for all four adapters.

Claude review and smoke calls use Claude Code's native JSON-schema control. The
CLI receipt extracts the schema's single `output` string, then the runner applies
the same persona grammar and citation checks as every other adapter. This keeps
reasoning prose outside the declared result from masquerading as a persona
response.

## Live smoke

`scripts/council.py smoke --profile <fast|deep>`:

1. validates the whole config;
2. probes every seat selected by the profile, including previously failed
   seats; `smoke --all` is the explicit maintenance check for every configured
   seat;
3. resolves the exact absolute executable and attempts a best-effort current
   version observation with a fixed `--version` probe in an empty temporary
   working directory; failure of this diagnostic probe does not affect seat
   readiness;
4. builds an isolated child-environment copy per seat, applies that seat's
   `unset_environment`, then requires every configured environment variable
   without printing it or mutating the parent environment;
5. runs the exact configured executable with the registry-generated smoke argv
   directly;
6. always supplies this canonical challenge:

   ```text
   Return exactly this single line and do not use tools: VERDICT: PASS
   ```

7. parses the declared output format and receipt;
8. requires exactly one extracted result equal to `VERDICT: PASS`;
9. enforces every structured identity assertion and rejects observable
   executable, provider, or model mismatch;
10. runs selected seat smokes concurrently, then updates only each seat's
   smoke observation atomically with typed failures and recovery;

An unexpected exception in one smoke worker becomes that seat's typed
`adapter_error`; other completed seat results are retained and the config is
still atomically updated.
11. emits a machine-readable smoke receipt.

The config cannot replace the canonical challenge or define an always-true
success expression.

For a built-in CLI that exposes no authoritative model field, readiness uses
the registry-owned exact model command. The
receipt labels this as command evidence rather than provider-returned identity.

A passing smoke qualifies only the benign auth/model/receipt path. It neither
qualifies representative-review latency nor overwrites `observed.review`.
Routine review does not run smoke, so unselected seats and setup diagnostics add
no latency to the run.

## Review request

Every review has:

- profile: `fast` by default or explicit `deep`;
- effort: low for `fast`, medium for `deep`, and low for every smoke;
- objective: one sentence;
- one or more readable artifact paths containing the decision and rationale;
- optional focus;
- optional resolved decisions that are closed to re-litigation;
- optional deterministic evidence copied from a gate actually run in the
  current task or an attached command receipt and treated as ground truth;
- artifacts resolve only within the runner's current directory.

The runner reads artifact contents once and uses the same evidence bundle for
every selected persona. `fast` requests low effort, rejects a fully assembled
per-persona prompt over 16 KiB, permits one finding, and caps review calls at 60
seconds. `deep` requests medium effort, rejects a fully assembled per-persona
prompt over 24 KiB, permits three findings, and caps review calls at 90 seconds.
Explicit diagnostic smoke always uses low effort and caps calls at 20 seconds
for `fast` or 30 seconds for `deep`. Bounds are UTF-8 bytes after assembly;
version probes
remain capped at 10 seconds. These measured limits keep the latency/coverage
choice explicit and reject evidence bundles beyond the proven operating range.
Codex and Claude receive an explicit profile effort flag. Cursor's catalog
encodes effort/speed in its model ID, so a device may configure separate fast
and deep Cursor seats. The current Cline CLI contract exposes no independent
reasoning-effort control, so its effective effort is recorded as `none`. Every
call receipt records requested and effective effort. Coverage also reports the
serialized batch count and review call-timeout ceiling, including bounded
version probes but no diagnostic smoke.

## Persona roster and allocation

The roster is fixed:

1. **Architect** — soundness, correctness, hidden assumptions, integration, and
   failure modes.
2. **Pragmatist** — simplicity, YAGNI, cost, sequencing, and scope discipline.
3. **Verifier** — testability, acceptance criteria, blast radius, and
   reward-hacking risk.
4. **Adversary** — concrete defects, edge cases, unsafe assumptions, and
   implementability.

After static validation, the runner copies the selected profile bindings into
the run receipt before the first model call. Each binding launches a fresh direct child
process in a new empty temporary working directory. Distinct seats run
concurrently because they share evidence but never context or output. Repeated
bindings to one seat serialize, preventing the scheduler from creating its own
capacity failure. The prompt prohibition on repository exploration remains a
reviewer instruction, not an unprovable claim of complete filesystem
confinement.

Each worker resolves the configured direct executable immediately before its
fresh invocation. The representative call itself proves current auth, provider,
model, safety posture, latency bound, and structured receipt. Smoke remains an
explicit maintenance diagnostic because its trivial prompt is not predictive
of representative-review completion.

A runtime failure or invalid output is never retried on another seat. Other
already-launched persona calls still complete independently for audit. Any
failed or invalid selected persona makes the run `INCOMPLETE`.

## Persona input

Each persona receives only:

```text
ROLE: independent adversarial reviewer
PERSONA: <Architect|Pragmatist|Verifier|Adversary>
LENS: <persona lens>
ENGINE: <configured engine identity>
MODEL: <configured exact model ID>

OBJECTIVE:
<one sentence>

FOCUS:
<specific focus or "none">

RESOLVED DECISIONS — CLOSED; do not re-litigate:
<decisions or "none">

DETERMINISTIC EVIDENCE — ground truth:
<gate output or "none supplied">

ARTIFACTS:
===== FILE: <path> =====
<000001|source line, preserving original 1-based line numbers including blanks>
===== END FILE =====

RULES:
- Review only the supplied evidence. Do not inspect files, run commands, call
  tools, or modify anything.
- Work independently. You do not see other persona outputs.
- Find concrete defects, not summaries or generic best practices.
- A resolved decision is out of scope unless the artifact contradicts it.
- Return only one JSON object matching the required output contract: zero to one
  finding in `fast`, zero to three in `deep`.
- Copy the exact artifact path from its `FILE` header.
- Set each finding's `evidence.artifact` to that path and `evidence.line` to the
  numbered non-blank, non-whitespace source line shown before `|`.
```

No persona receives another persona's output.

Artifact lines are rendered as six-digit, zero-padded, 1-based original line
numbers followed immediately by `|` and the source line. Blank lines retain
their original numbers but are invalid citation targets. The runner resolves a
citation against the unmodified source, not the rendered prefix.

## Persona output

Zero findings:

```json
{
  "persona": "<name>",
  "engine": "<engine>",
  "model": "<exact model>",
  "verdict": "PASS",
  "findings": [],
  "biggest_risk": "<one line>"
}
```

One finding in `fast`; one to three in `deep`:

```json
{
  "persona": "<name>",
  "engine": "<engine>",
  "model": "<exact model>",
  "verdict": "PASS | CONCERNS | FAIL",
  "findings": [
    {
      "severity": "H | M | L",
      "claim": "<specific defect>",
      "evidence": {
        "artifact": "<exact artifact path>",
        "line": 1
      },
      "why": "<concrete consequence>",
      "fix": "<cheapest sufficient correction>"
    }
  ],
  "biggest_risk": "<one line>"
}
```

The runner validates exact object keys, assignment identity, finding count,
verdict/severity consistency, and that every citation names a real non-blank,
non-whitespace
line in the supplied artifact. It resolves and records the exact original line
itself. Claude enforces the same schema at generation time; the runner validates
it again. It does not infer, normalize, or repair fields.

Before semantic triage, raw output consistency is:

- any High requires `FAIL`;
- otherwise any Medium requires `CONCERNS`;
- only Low findings or no findings permit `PASS`.

## Durable run receipt

Before invoking personas, the runner creates an ignored JSON receipt under
`.council-runs/` containing:

- run ID and timestamps;
- artifact paths and byte counts;
- frozen persona-to-seat allocation.

As workers complete, the parent process serializes results in profile order and
atomically replaces the receipt. Workers never write the receipt. Each result
contains:

- exact executable and executed command with prompt/schema bodies omitted;
- exit/timeout status, never raw process streams;
- provider proof tied to the configured direct executable path, plus model
  proof tied to the executed command or structured CLI receipt;
- structurally extracted persona output;
- structural and citation-validation result;
- any per-invocation observed failure state;
- top-level `post_run_seats` containing separate final smoke and review state
  for every selected seat after all attempts.

The runner never persists raw child stdout/stderr or configured environment
credential values. The extracted persona output is persisted, so the invoking
agent must keep secrets out of review artifacts. A final synthesis without a
receipt showing every profile binding was independently attempted is invalid.

When one configured seat has several profile bindings, the receipt retains each
invocation state and the config receives a deterministic aggregate. Any failure
outweighs success, so the seat becomes ready only when every binding in that run
succeeds. Among failures, executable, CLI, auth, and model failures outrank
generic adapter/output/capacity/timeout failures so recovery cannot depend on
thread completion order.
Observed-state persistence takes an advisory per-config lock, reloads the
current device record, merges smoke and review independently by timestamp, then
atomically replaces it. A later smoke therefore cannot erase a review timeout,
and concurrent processes cannot overwrite a newer operation-specific state.

## Semantic triage and council verdict

The runner returns structurally valid persona outputs and receipt evidence to
the invoking agent. The invoking agent verifies meaning and classifies every
finding:

- accepted;
- already covered;
- closed-decision re-litigation;
- unsupported or invented.

A citation proves only that the line exists. If the resolved line does not
support the claim, classify the finding as unsupported or invented.

Only accepted findings remain. The invoking agent re-ranks severity from the
demonstrated consequence, deduplicates the same underlying defect, and
recomputes effective persona verdicts. Raw persona verdicts are evidence, not
council authority.

Outcome order:

1. `INVALID REQUEST` — the assembled prompt exceeds the profile bound or an
   artifact/request is invalid; no persona ran.
2. `SETUP REQUIRED` — config/setup is invalid before allocation; no persona
   ran.
3. `INCOMPLETE` — any selected persona call failed or returned invalid output,
   including auth, model, capacity, and timeout failures found by real calls.
4. `FAIL` — every selected output is valid and an accepted High remains.
5. `CONCERNS` — every selected output is valid, no accepted High, and an
   accepted Medium remains.
6. `PASS` — every selected output is valid and no accepted High or Medium
   remains.

There is no degraded pass. Family composition is statically enforced in the
selected profile and reported from the frozen allocation.

## Verification

1. Skill validator passes.
2. Canonical example validates; malformed, unsafe, Gemini, unknown-adapter,
   weak-smoke, and fallback configs fail deterministically.
3. Actual `council-config.json` is ignored and contains no credential values.
4. `smoke --all` checks the full device roster without changing representative
   review qualification; only bounded real reviews qualify profile bindings.
5. Tests prove profile/family validation, distinct smoke/review state,
   process-group timeout cleanup, concurrent fresh calls, no reassignment,
   profile completeness, exact output validation, and verified citations.
6. Real `fast` and `deep` reviews produce valid independent persona outputs and
   durable receipts with every frozen binding attempted.
7. A deliberately failed seat makes a review `INCOMPLETE` without reassignment.

## Skill-arena

`~/dev/skill-arena/skills/adversarial-review/` contains `config.json`,
`cases.jsonl`, and `DESIGN.md` with baseline and with-skill variants.

Required cases cover missing config setup, known seats, Gemini rejection,
fast/deep effort selection, isolation, output validation, configured
single-family profiles, runtime failure, profile completeness, operation-specific
recovery visibility, smoke/review separation, direct argv, secret hygiene, and
post-triage verdict computation.

Required commands:

```bash
cd ~/dev/skill-arena
uv run arena run --skill adversarial-review --dry-run
uv run arena run --skill adversarial-review --backends local,codex
uv run arena forge --skill adversarial-review --backends local --target local --generator codex
```

Any reproducible skill-arena paper cut is searched across all `SKILLS` Linear
states and then filed or appended with exact output and a binary verification
condition. No local workaround is added to adversarial-review.

## Evaluation record

- Codex live smoke passed with `gpt-5.6-sol`; its JSONL does not expose provider
  model metadata, so the receipt labels the registry-owned model command as the
  evidence.
- Cursor live stream-JSON smoke and review passed through the official `agent`
  executable with authoritative init model `Composer 2.5 Fast` when
  `CURSOR_API_KEY` was available. On build `2026.07.16-899851b`, a fresh browser
  login survived one headless call and then returned `Not logged in`; OAuth is
  therefore not a durable council route and routine reviews never invoke login.
- ClinePass identity smoke passed with both DeepSeek V4 Flash and GLM 5.2.
  DeepSeek and GLM each failed the real 14.9 KiB review contract at the 90-second
  bound; GLM also timed out with thinking disabled. Kimi 3 is not in ClinePass.
  The GLM seat remains configured with its last review timeout visible, but it
  is deliberately not profile-bound.
- Claude Code live first-party OAuth smoke and review passed with
  `claude-opus-4-8` in model usage.
- Cursor remains configured but unbound on this device until its secret-manager
  API-key route is available again. Its latest smoke auth failure makes the
  older successful review observation visibly unqualified.
- This device binds `fast` to Codex/OpenAI plus Claude/Anthropic at low requested
  effort. `deep` binds each seat twice in fresh serialized contexts at medium
  requested effort. No runtime reassignment is permitted.
- Skill-arena real run: Codex 19/19 baseline and 19/19 with skill; local 11/19
  baseline and 17/19 with skill; zero errors.
- Forge: invalid comparison because original and other cells had backend
  timeouts but the tool declared a hero; tracked as SKILLS-27. No candidate was
  adopted from that receipt.
- First four-persona council: completed but failed the prose-only architecture;
  findings drove this deterministic-runner revision.
- Deterministic runner behavior is covered by 50 unit tests plus canonical and
  device config validation. Skill-arena dry-run generation passes 22/22 cases.
- Final current-runtime deep proof: 4/4 independent medium-effort personas
  across OpenAI and Anthropic completed in 81.140 seconds with no automatic
  smoke phase; receipt
  `.council-runs/b71650ba-018f-4698-b771-462b5b98cb99.json`.
- Final current-runtime default-fast proof: Codex/OpenAI plus Claude/Anthropic
  completed 2/2 independent low-effort personas in 13.218 seconds with no
  automatic smoke phase; receipt
  `.council-runs/539cdea9-2473-4ef4-8583-d05d18f4b7b4.json`.
