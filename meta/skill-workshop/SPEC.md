# skill-workshop specification

WORK_UNIT: `f84bad5c-2488-41f4-ae0b-75003a5f0b5b`

## Outcome

`skill-workshop` turns a rough idea, solved workflow, or material redesign into
the smallest correct skill and evidence its declared behavior works. The repo's
normal install path shares it with Codex, Claude Code, Cursor, and Cline.

It composes existing authoring, test, evaluation, and review tools; it is not a
new harness, controller, evaluator, daemon, or state store.

## Trigger boundary

Trigger to create and prove a skill, capture solved work, or materially redesign
behavior, setup, scripts, or evaluation.

Redirect narrow requests:

- prose/invocation editing only → `writing-great-skills`;
- static score only → `linting-and-scoring`;
- prompt-to-script audit only → `determinize-refactor`;
- install an existing skill → `skill-installer`.

## Risk tiers

Classify before build at the highest tier.

| Tier | Select when | Inherited obligations |
|---|---|---|
| `method` | The skill is instructions/reference only and uses no bundled executable or live service. | Common specification, behavioral eval, blind forward-test, static lint, cross-family review. |
| `scripted` | The skill bundles executable code, validators, schemas, generated artifacts, or other fixed behavior. | All `method` obligations plus public-seam TDD, script tests, deep final council, and Thermos. |
| `integration` | The skill depends on authentication, a third-party CLI/API, model/provider identity, capacity, or device-specific setup. | All `method` obligations plus deep final council and Thermos; TDD/script tests only when code is bundled; plus ignored non-secret device config, canonical example, separate smoke/representative state, live qualification, typed recovery, and explicit no-substitution behavior. |

A hybrid scripted integration is `integration`; it still fails when bundled
script tests are absent. The tier is recorded in the receipt and remains fixed
for the work unit.

## Effort and review depth

- `method` defaults to `standard` effort and a fast cross-family council.
- `scripted` and `integration` require `deep` effort, a fast spec council, deep
  final council, and Thermos.
- Security-sensitive or architectural method skills may deliberately select
  `deep`.
- Final completion requires an independent reviewer family beyond the author.
  Work may continue without that seat, but the review gate is `blocked`; there
  is no same-family or single-family completion.

## Durable artifacts

Every workshop creates `SPEC.md` before `SKILL.md`, only necessary resources,
skill-arena design/config/cases, real baseline/with-skill and two-family blind
receipts, review/install receipts, `WORKSHOP.json`, and `DEVIATIONS.md` (`none`
is explicit). Scripted adds tests and Thermos. Integration adds Thermos, config
example, ignore rule, smoke, representative-operation evidence, and tests only
when it bundles code.

Each step's receipt is human-readable (`templates/receipt.md`: real command,
verbatim output, one-line verdict). `workshop.py report` renders a single
`REPORT.md`/`REPORT.html` that inlines every receipt beside the checker verdict,
so semantic review — confirming the receipts are true, not merely present — is
one read. The report is a generated view, not a gate artifact.

## Receipt tool

The workshop bundles `scripts/workshop.py`. It generates and checks
receipts; it never invokes models, runs arbitrary receipt commands, installs
tools, edits skills, stores credentials, or controls the workflow.

Public seams, agreed for TDD:

```bash
python3 scripts/workshop.py init \
  --tier integration \
  --bundles-code true \
  --work-unit f84bad5c-2488-41f4-ae0b-75003a5f0b5b \
  --author-family openai \
  --output WORKSHOP.json

python3 scripts/workshop.py check WORKSHOP.json
```

`init` creates a deterministic skeleton with exact keys and tier-appropriate
empty evidence slots. `--bundles-code` is required for integration, fixed false
for method, and fixed true for scripted. It refuses to overwrite a file.

`check` resolves artifact and evidence-receipt paths relative to the receipt
file, validates exact keys and typed values, verifies each is a regular file
inside the receipt root, and returns:

- exit `0` plus JSON `{status: "complete", ...}` only when every gate required
  by the fixed tier passes;
- exit `1` plus JSON `{status: "incomplete", errors: [...]}` when evidence or
  artifacts are absent, contradictory, unsafe, or failed;
- exit `2` plus JSON `{status: "invalid", errors: [...]}` when the receipt is
  malformed or outside the contract.

Validation runs in three ordered layers; each runs only after the prior passes.
Structural/type validation first (exit 2 alone). Then evidence completeness
(artifacts and receipts present, non-empty, distinct). Then a content layer that
checks the OUTPUT actually backs the recorded GRADE, catching honest drift with
exact-string, format-tolerant checks:

- grounding — the identities a record claims must literally appear in its own
  receipt: the representative operation's `observed_provider`/`observed_model`,
  every `install` target, every declared council `family`, and each forward
  test's `family`. Cross-family independence is the design's core claim, so it
  is grounded rather than trusted;
- no contradiction — a receipt graded pass must not contain a failure signature.
  Command records use generic signatures (a Python traceback, `exit=1`); review
  receipts, which quote failures legitimately, use precise result lines instead
  (`COUNCIL RESULT: status=fail`, `status=preflight_failed`, a Thermos
  `"security_verdict": "fail"`). Review evidence is the highest-trust evidence,
  so it is checked, not exempt;
- no duplication — the two blind forward-test receipts must not be identical
  content, so one run cannot stand in for both families.

The content layer catches mistakes (a stale receipt, a substituted model, a
missing target), not a determined forger who rewrites the receipt text — the
independent council reading the receipt owns that.

Diagnostics are stable, sorted, and safe to print. The checker rejects escaping
paths and symlinks for evidence/artifact files.
`live.device_config` is a device-local declaration, not a receipt artifact: the
checker requires a non-escaping relative path and an exact normalized positive
ignore rule with no exact negation, but not the ignored file itself.
It detects missing or contradictory evidence, not malicious forgery. Terminal,
CI, and review output establish authenticity; self-issued local attestation is
outside this contract.

## WORKSHOP.json contract

Top-level exact keys:

- `schema_version`: `1`;
- `work_unit`: lowercase UUIDv4;
- `tier`: `method | scripted | integration`;
- `bundles_code`: boolean; method requires false, scripted requires true, and
  integration records the selected capability explicitly;
- `effort`: `standard | deep`; scripted/integration require `deep`;
- `author_family`: lowercase identifier;
- `artifacts`: path map;
- `evidence`: evidence object.

Common artifacts are target-local `spec`, `skill`, and `deviations`. Cross-repo
arena files stay in behavioral receipts; never copy or escape to them. Scripted
requires non-empty `scripts` and `tests` arrays.
Integration requires `config_example` and `ignore_file`; it may add
`scripts` and `tests` as a non-empty pair exactly when `bundles_code` is true.
Extra keys fail. Review, not the structural checker, catches a false capability
declaration.

Command evidence uses exact keys:

```json
{
  "command": "python3 -m unittest ...",
  "exit_code": 0,
  "receipt": "receipts/tests.txt",
  "dry_run": false
}
```

The checker validates that the recorded command is non-empty, exit code is
zero, `dry_run` is false, and receipt exists. It does not execute the command.

Common evidence is real `baseline` and `behavioral` commands, two passing
`forward_tests`, Ship Ready `lint`, `install`, and required `council` records.
Forward-test records add one exact key, `family`, to command evidence; it is a
lowercase identifier. Exactly two must pass with distinct families; either may
equal `author_family`. Install adds exact key `targets`, whose value is exactly
`claude`, `codex`, `cursor`, and `cline`. Other commands use the shape above
except the representative record below. Dry runs remain outside `WORKSHOP.json`.

`scripted` requires passing `repo_tests` command evidence. Integration requires
it when `bundles_code` is true. Both tiers require Thermos
`{security: "pass", quality: "pass", receipt: <path>}`.

`integration` additionally requires:

- exact `live` keys `provider`, `model`, `auth_kind`, `device_config`, `status`,
  `failure_class`, `recovery`; identity/auth values are non-empty and config is
  relative;
- passing smoke command evidence;
- representative command evidence extended by exact keys `observed_provider`,
  `observed_model`, and `substituted`;
- config example and ignore-file artifacts;
- representative command and receipt path both differ from smoke.

`status` is `ready | blocked`; `failure_class` is
`none | auth | model | capacity | timeout | adapter`. Ready requires
`recovery` is `string | null`; ready requires exactly null, while blocked
requires another class and a non-empty string.
Completion requires ready, observed identity equal to declared identity, and
`substituted: false`.

Config examples are recursively fail-closed: string values are empty or
`${UPPER_SNAKE_CASE}` placeholders, never literals. The ignore file contains
the exact normalized device-config path without an exact negation.

Council rules:

- every council record has `phase`, `profile`, `families`, `status`, `receipt`;
- `status` is `pass | fail | blocked`; only pass completes, while fail and
  blocked return exit 1 with distinct diagnostics;
- `families` contains at least two distinct values and excludes
  `author_family` only as a sole family, not as a participant;
- `standard` requires passing `spec/fast` and `final/fast` records;
- `deep` requires passing `spec/fast` and `final/deep` records.

## Acceptance contract

The binary, machine-checkable acceptance criterion is exactly one thing:
`python3 scripts/workshop.py check WORKSHOP.json` exits `0` (`status: complete`)
over the tier's enumerated gates — artifacts present and non-empty, every
required command receipt real (non-empty, exit `0`, `dry_run: false`), receipts
distinct where the contract requires it, and councils/Thermos at the required
status and family count. That checker result plus clean semantic review of the
receipt contents is the acceptance contract; it is necessary but not sufficient
on its own (see `SKILL.md`). The workflow rows below are guidance toward that
contract, not additional independent pass/fail gates.

## Skill workflow (guidance)

| Step | Guidance |
|---|---|
| Discover | Triggers, failures, users, repo, and authority define behavior. |
| Specify | `SPEC.md` fixes tier, effort, seams, claims, rubric, and decisions. |
| Baseline | Dirty and clean cases plus a real baseline; dry-run stays separate. |
| Build | Method stays lean; code uses red→green; integrations qualify adapters visibly. |
| Evaluate | Same cases/models run with-skill; errors and missing cells stay explicit. |
| Forward-test | Fresh isolated agents get only skill path and task; two families pass. |
| Review | Lint, install, councils, tests, Thermos by tier, and checker pass. |
| Handoff/ship | Commands, identities, effort, receipts, deviations, commits, and PRs are recorded. |

## Behavioral evaluation

The companion skill-arena suite uses a closed violation vocabulary and
`expect_set` scoring. Every invariant has at least one dirty case and clean
guards cover valid combinations. Required violations cover spec-after-build,
patchwork, tier downgrade or hybrid misclassification, missing inherited tests,
dry-run/static/smoke relabeling, answer leakage, persisted secrets,
smoke-as-representative, hidden integration failure or substitution,
single-family completion, implicit effort, and premature ship.

Dry-run proves only wiring. At least one live model run provides behavioral
evidence. Clean guards include a code-free integration without invented script
tests and a hybrid integration with inherited script evidence. Blind
forward-tests are separate from classifier-style arena cases.

## Forward-test fixtures

- Method: turn a judgment-heavy recurring editorial decision into a skill;
  output stays lean without scripts/config/Thermos.
- Integration: drive an authenticated CLI with a bundled validator; output
  inherits script tests, separates smoke/representative readiness, uses ignored
  non-secret config, and blocks without cross-family review.

Codex and Claude run one each and swap only if a result exposes ambiguity.

## Verification matrix

| Claim | Evidence |
|---|---|
| CLI contract | Python unit tests through subprocess CLI only |
| Tier inheritance | method/scripted/integration receipts plus hybrid dirty cases |
| Evidence separation | malformed and shortcut receipt fixtures rejected |
| Skill behavior | real skill-arena baseline and with-skill results |
| Cross-agent portability | isolated Codex and Claude forward-test receipts; install targets for Codex/Claude/Cursor/Cline; bounded Cline discovery/execution qualification |
| Review quality | fast spec council; deep final council; Thermos security and quality |
| Reproducibility | full commands and receipts; clean checkout reruns deterministic gates; refreshing live readiness requires device setup |

## Resolved decisions

- “Workshop” is the leading word and `meta/skill-workshop` is the home.
- Existing tools are composed, not wrapped in a new orchestrator.
- `WORKSHOP.json` is a typed completion receipt, not mutable workflow state.
- The helper generates/checks receipts but never executes recorded commands.
- Tiers are cumulative and fixed before build.
- Behavioral/live claims require real runs; dry-run/static/smoke stay distinct.
- Cross-family review is a hard final gate.
- Method skills stay lean; deep machinery is risk-triggered.
- Cline's native global skill directory is `~/.cline/skills/`; the installer
  exposes it as `CLINE_SKILLS_DIR` and `all` includes Cline.
- The receipt is a manifest, not a second evaluator. Skill-arena owns semantic
  result validation; the checker validates its command and receipt reference.
- Target-local artifacts; cross-repo eval files stay in semantic receipts.
- Blindness/isolation is established by independent forward-test receipts and
  review, not unverifiable self-attestation fields in the manifest.

## Implementation plan

1. Gate this SPEC with Plannotator and fast council.
2. Red→green CLI and four-target installer seam tests.
3. Author lean skill/reference, indexes/install, and arena suite.
4. Run real baseline/with-skill eval and isolated Codex/Claude forward-tests.
5. Build `WORKSHOP.json`; run lint, tests, deep council, Thermos, and checker.
6. Commit both repos, push draft PRs, and receipt Linear.

## Deviations

- Missing worktree council config: reused the device contract via `--config`.
- Fast prompt overflow: compressed this source rather than changing profiles.
- Rejected self-issued hashes/timestamps; terminal, CI, and review are trust.
- Rejected duplicating arena results; the manifest references arena receipts.
- Official Cline docs select `~/.cline/skills/`; its experimental qualification
  stays separate from the two-family forward-test gate.
