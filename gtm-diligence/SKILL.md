---
name: gtm-diligence
description: Run a comprehensive pre-ship / go-to-market readiness audit of an application across security, reliability, concurrency/race conditions, accessibility (WCAG 2.2 AA), performance, and visual/UI consistency — tracing real user flows end-to-end, then returning a severity-grouped findings report, a remediation plan, quick wins, and a Safe-to-ship / Ship-with-risks / Do-not-ship recommendation. Use when the user says "gtm diligence", "ship-readiness audit", "production audit", "is this safe to ship", "full app audit", "security + a11y + reliability review", or before launching / GA'ing a product. Broader than code-review (single diff) or adversarial-review (a plan) — this audits a whole running app.
---

# GTM Diligence — pre-ship application audit

A comprehensive, adversarial audit of a whole application before it goes to market. Unlike a diff
review, this **traces important flows end-to-end** — codebase, architecture, data flows, API
interactions, authN/authZ, state management, async operations, error handling, and user-facing
surfaces — and challenges the assumptions that only hold under ideal content, a single viewport,
and a cooperative user.

The output is a decision: **Safe to ship / Ship with known risks / Do not ship**, backed by
evidence. Be adversarial in security, systematic in accessibility, precise in UI.

Credit: prompt by [@shugarDadddy](https://x.com/shugarDadddy/status/2075148611680149656).

## When to use

- Before a launch, GA, or handing an app to real users
- "Is this safe to ship?", "production audit", "ship-readiness / GTM diligence"
- You want one report that spans security + reliability + a11y + UI, not a single-diff review

**Not for:** reviewing one diff/PR (use `code-review`), red-teaming a plan or spec (use
`adversarial-review` / `review-council`), or pure visual/3D critique (use `visual-critique`).

## Before you start (mandatory scope)

Every GTM audit confirms these first — an end-to-end audit is expensive and easy to mis-target. If
the user doesn't answer, proceed only as an **explicitly capped partial audit** and say so.

1. **Target + environment** — which repo/app + commit/SHA, and can it actually be run (dev server,
   staging, prod-only)?
2. **Priority flows** — the top user-critical flows to trace (auth, checkout, submit…). No
   preference → pick the flows touching money, auth, or data-writes first.
3. **Available test material** — extra role/tenant accounts, seed data, or credentials? Their
   absence caps what authz / cross-tenant / concurrency checks can *confirm* (see coverage rule).

### Declare the audit mode (top of the report)

State one, and cap the verdict accordingly (see release gate):

- **Runtime verified** — priority flows were actually exercised (app run, browser/requests driven).
- **Partial runtime** — some flows exercised, others static-only. List which is which.
- **Static only** — no runtime access. All runtime-dependent findings are **Needs Verification**;
  the audit may **not** call itself complete.

A category that *requires* runtime evidence (a11y contrast/screen-reader, races, CSRF, cross-tenant)
but wasn't exercised is a **coverage gap → Needs Verification**, never a silent "no findings".

## Rules of engagement

1. **Do NOT modify code during the initial audit.** Produce the complete findings report first.
2. **Trace flows, don't skim files.** Follow auth, checkout, submit, etc. end-to-end. For each
   priority flow, produce a one-row trace: `route → client action → server endpoint/action → authz
   check → data stores touched → external services → failure states tested → evidence`. No trace
   row = the flow was not actually traced.
3. **Evidence over speculation — enforced, not goodwill.** Every finding carries an **evidence
   type** (see report format). A finding with no evidence/repro is a **Risk hypothesis**, labelled
   as such, severity capped at **Medium** — it is not a defect.
4. **Missing coverage ≠ no finding.** If you couldn't test something, it's a coverage gap (Needs
   Verification), not a pass. Never let "nothing found" stand in for "tested and clean".
5. **Don't assume client-side validation is sufficient.** Check every trust boundary server-side.
6. **Prioritise by real-world impact and exploitability**, not by how easy the finding was to spot.

## What to investigate

Many of these can only be **confirmed** at runtime. Where you have the app running, exercise it
(drive the browser, fire concurrent/raw requests, run axe/contrast/keyboard checks). Where you
don't, report the item as a **static risk → Needs Verification** and say what tool/access would
confirm it. Do not present a static inference as a confirmed runtime finding.

### Security & data exposure (be adversarial)
- AuthN/authZ flaws: missing **server-side** permission checks, privilege escalation, IDOR,
  cross-tenant data access.
- Sensitive data leaked via client code, env vars, API responses, logs, analytics, URLs,
  local/session storage, cookies, error messages, or source maps.
- Injection: SQL, command, template, **prompt**, HTML, script.
- XSS, CSRF, SSRF, open redirects, unsafe file uploads, path traversal, weak sessions, insecure
  token storage, missing security boundaries.
- Overly permissive DB rules, endpoints, CORS, storage buckets, webhook handlers, 3rd-party
  integrations.
- Secrets, API keys, credentials, internal endpoints, PII, or implementation details exposed.
- Missing validation/sanitisation at trust boundaries.

### Race conditions, concurrency & state integrity
- Duplicate submissions from repeated clicks, retries, refreshes, concurrent requests.
- Non-idempotent operations creating duplicate records, payments, messages, bookings, jobs.
- Stale state, failed optimistic updates, lost updates, conflicting/out-of-order writes.
- Effects, subscriptions, listeners, timers, requests not cleaned up.
- Actions left available while an operation is already in progress.
- Cache invalidation bugs; client vs server vs persisted state inconsistency.
- Multi-tab, multi-device, poor-network scenarios.

### Reliability & failure handling
- Unhandled rejections, swallowed errors, silent failures, infinite loading, broken retries,
  incomplete rollback.
- Missing loading / empty / error / offline / timeout / partial-success states.
- Failure paths that leave data or UI inconsistent.
- Unsafe assumptions about API shape, nullability, ordering, timing, network availability.
- Memory leaks, unnecessary rerenders, expensive ops, obvious perf bottlenecks affecting UX.
  (This is a **static performance-risk** review unless you run Lighthouse / profiles / measure a
  budget — say which. Don't imply measured perf you didn't measure.)

### Accessibility (systematic — WCAG 2.2 AA)
Contrast, focus-trap, live-region, screen-reader, and zoom/reflow checks require **runtime tooling**
(axe, computed-contrast, keyboard traversal, an actual screen reader). Without it, these are static
a11y risks → Needs Verification — don't claim WCAG conformance from reading markup.
- Semantic HTML: landmarks, headings, labels, lists, tables, buttons, links.
- Keyboard nav, logical tab order, focus visibility, focus trapping, focus restoration.
- Accessible names/labels/descriptions and correct ARIA.
- Colour contrast, legibility, touch-target size, zoom, reduced-motion, colour-only meaning.
- Screen-reader behaviour for modals, menus, dropdowns, tabs, toasts, validation errors,
  loading states, and dynamically updated content.
- Forms: instructions, accessible validation, autocomplete attributes, error recovery.

### Visual & interaction consistency (precise)
- Inconsistent spacing, type, colour, radii, shadows, icon sizing, alignment, dimensions,
  responsive behaviour.
- Components that look identical but behave differently (or vice-versa); inconsistent design-token
  and shared-component use.
- Missing/inconsistent hover, focus, active, selected, disabled, loading, success, warning,
  destructive, error states.
- Layout shift, clipping, overflow, truncation, wrapping, breakpoint issues, inconsistent empties.
- Copy: terminology drift, capitalisation, punctuation, date/number formats, action labels.

### Responsive & edge-case behaviour
- Narrow mobile, tablet, desktop, ultra-wide, zoomed, large-text settings.
- Long names/emails, translated/expanded text, empty values, huge datasets, zero-result states,
  malformed/unexpected content.
- Assumptions that only work with ideal content or one viewport.

## Report format

### 1. Coverage matrix (before any findings)

So "nothing found" can never masquerade as "tested and clean". One row per category:

| Category | Flows / endpoints sampled | Method (runtime / static) | Evidence artifact | Status | Verdict impact |
|---|---|---|---|---|---|

Status ∈ `Verified` / `Static reviewed` / `Not tested` / `N/A`. A `Not tested` runtime-critical row
caps the verdict (see release gate).

### 2. Findings

**Ordering & dedup:** one finding per **root cause** (list all affected instances under it, don't
file ten copies). Sort by severity, then exploitability, then affected users/data, then confidence.

**Severity** (impact + exploitability, independent of confidence):
- **Critical** — exploitable now, or data-loss / auth-bypass / payment corruption in a priority flow.
- **High** — serious impact but gated (needs a role, a race window, specific input).
- **Medium** — real but limited blast radius, or a Risk hypothesis with no confirmed exploit.
- **Low / Informational** — hygiene, defence-in-depth, cosmetic.

For every finding report:

- **Severity** and **Category** (Security / Race Condition / Reliability / Accessibility / Performance / Visual Consistency)
- **Location:** exact file:line, component, function, endpoint, or flow
- **Issue / Impact:** what's wrong + what can realistically happen in production
- **Evidence type + evidence:** one of `file:line + source→sink path` / `request/response` / `browser
  or tool output` / `failing command` / `screenshot`. **No evidence → label "Risk hypothesis",
  severity ≤ Medium** — not a defect.
- **Reproduction:** concrete steps (required for Critical/High).
- **Recommended fix:** specific, actionable remediation.
- **Confidence:** Confirmed / High Confidence / Needs Verification (a *separate* axis from severity).

## Deliverables (after the report)

1. **Prioritised remediation plan** — ordered by real-world impact.
2. **Quick wins** — safe to fix with low regression risk.
3. **Deeper work** — issues needing architectural change or further investigation.
4. **Release recommendation** — apply the release gate below (don't freehand it), then justify.

## Release gate (verdict is a function of findings + coverage, not vibes)

Two audits of the same app should reach the same verdict. Take the **first** row that matches:

| Condition | Verdict |
|---|---|
| Any **Critical**, or a Confirmed/High-Confidence **High** in auth / data / payments | **Do not ship** |
| Audit mode is **Static only** or **Partial**, and a launch-critical auth/payment/data-write flow is **not runtime-verified** | **Ship with known risks** (max — cannot be "Safe to ship") |
| Unresolved **High** findings, or **Not tested** rows on runtime-critical categories | **Ship with known risks** |
| Priority flows **runtime-verified**, no Critical/High, only Medium/Low remain | **Safe to ship** |

State the row you matched and why. "Safe to ship" requires runtime verification of the priority
flows — a static-only audit can never award it.

## Edge cases & failure modes

| Situation | What to do |
|---|---|
| App can't be run (prod-only, no dev server, missing creds) | Audit statically; mark every finding that needs runtime as **Needs Verification**, and list the checks you couldn't run (a11y, visual, responsive, races) so the coverage gap is explicit — never imply full coverage. |
| Scope too large to trace end-to-end in one pass | Audit the top user-critical flows first (money / auth / data-writes), and end the report with an explicit **"Not traced"** list. Don't silently skip. |
| A finding has no repro / no supporting code path | Don't report it as a defect. Downgrade to **Informational** with a note, or drop it. Evidence-free findings violate the rules of engagement. |
| Codebase access is partial (some services/repos missing) | State the assumption and which surfaces were out of scope; flag cross-service auth/data-flow as **Needs Verification**. |
| Nothing found in a category | Say so explicitly ("No Critical/High security findings") — an empty section, not a silent omission. |
