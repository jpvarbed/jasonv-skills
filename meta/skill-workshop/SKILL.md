---
name: skill-workshop
description: Build or materially redesign an agent skill from a rough idea or a workflow that just succeeded, with a spec-first design, risk-based evidence, real baseline and with-skill evaluation, blind cross-family forward tests, and a typed completion receipt. Use for “create/add a skill,” “turn what we just did into a skill,” or “redesign a skill's behavior, setup, scripts, or eval.” NOT for prose-only edits (use writing-great-skills), static scoring (use linting-and-scoring), prompt-to-script audits (use determinize-refactor), or installing an existing skill (use skill-installer).
---

# Skill Workshop

Build the smallest skill that owns the behavior, then prove its declared claims.
Compose the repo's existing authoring, arena, review, and install tools; do not
create another controller around them.

## Non-negotiable design rules

- Write or update `SPEC.md` before `SKILL.md` or executable behavior.
- Treat a wall as evidence that the design is wrong. Re-derive the design; do
  not hide it behind a flag, shim, special case, fallback, or parallel path.
- Keep dry-run, static, smoke, behavioral, and representative-live evidence
  separate. One never stands in for another.
- Keep every attempted adapter call, failure class, and recovery action visible;
  omitting a failed integration attempt is itself a failed gate.
- A final review needs at least one model family other than the author. Missing
  capacity blocks completion; it does not authorize substitution.
- Record requested/effective effort because latency and reasoning depth trade
  directly against each other.
- Never persist credentials. Device config is ignored and non-secret.
- Do not add hashes, fingerprints, or timestamps as self-attestation. Actual
  command output and independent review own authenticity.

## 1. Discover the behavior

Capture the real trigger, non-trigger, user, repository, authority, and the
failure or successful workflow being generalized. Describe the desired
behavior without preserving accidental details of the first solution.

Redirect a narrow request to the skill named in the description instead of
running the full workshop.

## 2. Select the fixed risk tier

Choose the highest matching tier before build. Tiers are cumulative.

| Tier | Select when | Required evidence |
|---|---|---|
| `method` | Instructions/reference only; no executable or live dependency. | Spec, real eval, two-family blind test, lint, four-agent install, fast councils. |
| `scripted` | Bundled code, validator, schema, or generated artifact. | Method plus public-seam TDD, repo tests, deep final council, Thermos. |
| `integration` | Auth, third-party CLI/API, provider/model identity, capacity, or device setup. | Method plus deep final council, Thermos, device config contract, smoke and representative qualification; add TDD/tests when code is bundled. |

For integration work, read
[`references/integration-tier.md`](references/integration-tier.md) before
specifying the contract.

Effort defaults to `standard` for method and `deep` for scripted/integration.
Use deep for a security-sensitive or architectural method skill.

## 3. Specify and gate

Before promising evidence, exercise each required external CLI end to end: run
its help/version command and its smallest non-mutating validate, identity, or
smoke operation. A name on `PATH` is not readiness.

Create one source `SPEC.md` containing:

- outcome, triggers, non-triggers, fixed tier, and effort;
- public seams and exact observable behavior;
- required artifacts and receipts;
- behavioral cases, blind forward-test fixtures, and binary completion rubric;
- resolved decisions and deviations.

Gate that exact file with the repository's plan-review provider and a fast
cross-family adversarial review. Apply valid findings to the source spec.
Record rejected findings with the design boundary they would violate; do not
add machinery just to satisfy a reviewer.

## 4. Establish the baseline

Before implementing the skill:

1. Create dirty cases for every invariant and clean guards for valid boundary
   combinations.
2. Run the arena's dry mode only to prove wiring.
3. Run at least one real model as the no-skill baseline and retain its receipt.

Do not tune cases after seeing baseline answers. If semantic review finds a
mislabeled case, version the suite, record the defect, and establish a new real
baseline before comparison; never reuse the old score. If the baseline is
perfect, report no measured lift; the suite remains a regression guard.

## 5. Build the smallest artifact

Use `skill-creator` for the canonical scaffold and `writing-great-skills` for
the instruction surface. Keep `SKILL.md` lean and move only integration-specific
detail into the reference.

When code is bundled, use TDD at the public seam:

1. Write one failing subprocess or external-interface test.
2. Run it and retain the red result.
3. Implement only enough behavior to pass.
4. Add boundary cases, then run the full relevant suite.

Do not manufacture scripts or tests for a code-free method/integration skill.

## 6. Evaluate the same cases

Add a with-skill arena variant and rerun the same cases and model used for the
baseline. Preserve errors, regressions, and missing cells. A dry run is never
behavioral evidence.

## 7. Forward-test blindly

Run two fresh isolated agents from distinct model families. Give each only:

- the skill path;
- one raw realistic task.

Do not provide expected answers, arena cases, another agent's output, or the
workshop's implementation discussion. Capture commands and receipts, then
remove temporary fixtures. One family may equal the author family; the two
forward-test families must differ.

Install and qualify the skill through each repository target: Claude Code,
Codex, Cursor, and Cline. A target that cannot discover or execute the skill is
visible incomplete evidence, not permission to relabel another process.

## 8. Review and receipt

Run tier-required tests, static lint, install checks, final council, and
Thermos. Review the semantic contents of external receipts; the helper checks
their structure and existence but is not a second evaluator.

Initialize the receipt from the skill directory:

```bash
python3 scripts/workshop.py init \
  --tier integration \
  --bundles-code true \
  --work-unit f84bad5c-2488-41f4-ae0b-75003a5f0b5b \
  --author-family openai \
  --output WORKSHOP.json
```

Each step leaves a readable receipt, not an opaque blob: copy
[`templates/receipt.md`](templates/receipt.md) — the real command, its verbatim
output, and a one-line verdict. Fill `WORKSHOP.json` only from those retained
receipts, then check it:

```bash
python3 scripts/workshop.py check WORKSHOP.json
```

Render the reviewer-facing report so semantic review is one read instead of
fifteen file-opens:

```bash
python3 scripts/workshop.py report WORKSHOP.json --format md   -o REPORT.md
python3 scripts/workshop.py report WORKSHOP.json --format html -o REPORT.html
```

`report` inlines every receipt's contents next to the checker verdict. The
checker proves the receipts exist, are non-empty, and are distinct; reading the
report is what confirms they are *true*. A green checker never ships alone.

Exit 0 means the declared structural gates are complete. Exit 1 means valid but
incomplete evidence. Exit 2 means the receipt violates the contract. Never edit
an exit code, family, model identity, status, or `substituted` field to make the
checker pass.

A `complete` exit is necessary but not sufficient: the checker validates receipt
structure, distinctness, and existence, not the truth of what a receipt records.
Only semantic review of the receipt contents plus the independent council make
the completion claim real. Never treat a green checker as a standalone ship signal.

Ship only when the checker reports `complete`, semantic receipt review is
clean, deviations are explicit, and the requested commit/PR authority exists.
Ask before merge, publication, or release unless higher-level instructions
already grant that exact action.

## Failure handling

| Issue/Error | Fix |
|---|---|
| Required CLI is absent or its identity check fails | Record the gate incomplete and provide the exact install/setup action; do not replace the tool. |
| Auth, model, capacity, timeout, or adapter qualification fails | Preserve the typed failure and recovery from the integration reference; retry the same declared seat only after recovery. |
| Plan review times out or is dismissed | Reopen the exact unchanged artifact and obtain a recorded decision; timeout is not approval. |
| Arena dry-run passes but a live cell errors or regresses | Keep the error visible, inspect the raw receipt, and fix the skill or version a mislabeled suite before establishing a new baseline. |
| `workshop.py check` exits 1 or 2 | Read the sorted diagnostics, repair the missing evidence or invalid contract at its source, and rerun the producing command. |
| Independent model family is unavailable | Leave final review blocked and report recovery; never substitute another process from the author family. |
