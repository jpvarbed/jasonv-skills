#!/usr/bin/env python3
"""Deterministic delivery tests for the goal-to-done skill.

These validate the shipped contract artifacts (SPEC/SKILL, arena fixture,
adapter). They are never an operational ticket runner. Run directly:

    python3 skills/engineering/goal-to-done/tests/test_goal_to_done.py
"""

import importlib.util
import json
import re
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
FIXTURE = SKILL_DIR / "evals" / "arena" / "goal-to-done"

ROUTES = {"total-tdd", "grilling-pass", "pause-human", "no-work-receipt",
          "wayfinder", "direct", "to-tickets"}
VIOLATIONS = {"stale-receipt", "self-claim", "second-steward", "skip-frontier",
              "premature-done", "missing-ticket-contract",
              "pre-reconciliation-claim", "invented-runtime", "regrill",
              "brief-tamper"}
VOCABULARY = ROUTES | VIOLATIONS

OVERLAP_CASE_IDS = {"rt-whole-app-foggy-overlap", "rt-bounded-vs-decompose-overlap",
                    "rt-mixed-multi-overlap"}

TICKET_CONTRACT_FIELDS = ("mini_goal_brief", "dependency_edges", "receipt_contract",
                          "stop_condition", "goal_brief_version", "graph_revision")


def load_run_arena():
    spec = importlib.util.spec_from_file_location(
        "run_arena", SKILL_DIR / "evals" / "run_arena.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_cases():
    cases = []
    for line in (FIXTURE / "cases.jsonl").read_text().splitlines():
        if line.strip():
            cases.append(json.loads(line))
    return cases


def expect_ids(case):
    expect = case["expect"]
    if isinstance(expect, str):
        return [expect]
    return list(expect)


# --- Reference model of the SPEC's claim/receipt validity rules -------------
# This transcribes SPEC.md sections 5-8 for deterministic checking only; it is
# not runtime machinery.

def claim_valid(markers, claim, current_brief_version=1):
    """markers: ordered list of ("revision", n) / ("reconciled", n).
    claim: dict with revision (int), brief_version (int), at (index into the
    marker stream after which the claim was written), by ("steward"|"worker"),
    steward_active (a current non-stale steward claim by someone else exists).
    Valid only if the claim carries the current goal-brief version, the
    matching reconciled marker predates it, no newer revision marker exists
    anywhere, the writer is the steward, and no second steward is acting. An
    authorized brief-version bump advances the graph revision (SPEC section
    3), so a post-bump claim under the old marker fails both checks."""
    if claim.get("by") != "steward":
        return False
    if claim.get("steward_active"):
        return False
    if claim.get("brief_version", 1) != current_brief_version:
        return False
    preceding = markers[:claim["at"]]
    if ("reconciled", claim["revision"]) not in preceding:
        return False
    newest = max((n for kind, n in markers if kind == "revision"), default=0)
    return newest <= claim["revision"]


def receipt_valid(markers, receipt, current_brief_version):
    """receipt: dict with revision, at (index into the marker stream after
    which the receipt was written), brief_version, fields (tuple), passed
    (bool), affected_by_replan (bool). Like claims, a receipt is valid only if
    its revision's [graph-reconciled] marker predates it and no newer
    [graph-revision] marker exists (SPEC section 8)."""
    if not receipt.get("passed"):
        return False
    if sorted(receipt.get("fields", ())) != sorted(TICKET_CONTRACT_FIELDS):
        return False
    if receipt["brief_version"] != current_brief_version:
        return False
    preceding = markers[:receipt.get("at", len(markers))]
    if ("reconciled", receipt["revision"]) not in preceding:
        return False
    newest = max((n for kind, n in markers if kind == "revision"), default=0)
    if receipt["revision"] != newest:
        # SPEC section 8 step 5: an unaffected completed contributor stays
        # valid only through explicit current-revision carry-forward
        # validation recorded after the newest revision's reconciliation.
        if receipt.get("carried_forward_to") != newest:
            return False
        if ("reconciled", newest) not in markers:
            return False
    return not receipt.get("affected_by_replan", False)


class RouteVocabularyTests(unittest.TestCase):
    def test_spec_route_vocabulary_is_closed_and_exact(self):
        spec = (SKILL_DIR / "SPEC.md").read_text()
        match = re.search(r"route vocabulary is closed: (.+?)\. No other route exists\.",
                          spec, re.S)
        self.assertIsNotNone(match, "SPEC.md must declare the closed route vocabulary")
        declared = set(re.findall(r"`([a-z-]+)`", match.group(1)))
        self.assertEqual(declared, ROUTES)

    def test_design_vocabulary_matches(self):
        design = (FIXTURE / "DESIGN.md").read_text()
        declared = set(re.findall(r"^- `([a-z-]+)` —", design, re.M))
        self.assertEqual(declared, VOCABULARY)

    def test_case_expectations_stay_inside_vocabulary(self):
        for case in load_cases():
            for rule_id in expect_ids(case):
                self.assertIn(rule_id, VOCABULARY, f"case {case['id']}")

    def test_every_route_is_covered(self):
        covered = set()
        for case in load_cases():
            covered.update(expect_ids(case))
        for route in ROUTES:
            self.assertIn(route, covered, f"route {route} has no case")

    def test_overlap_cases_present_and_prove_precedence(self):
        cases = {c["id"]: c for c in load_cases()}
        for case_id in OVERLAP_CASE_IDS:
            self.assertIn(case_id, cases)
        self.assertEqual(expect_ids(cases["rt-whole-app-foggy-overlap"]), ["total-tdd"])
        self.assertEqual(expect_ids(cases["rt-bounded-vs-decompose-overlap"]), ["direct"])
        self.assertEqual(expect_ids(cases["rt-mixed-multi-overlap"]), ["wayfinder"])


class FixtureIntegrityTests(unittest.TestCase):
    def test_config_shape(self):
        config = json.loads((FIXTURE / "config.json").read_text())
        self.assertEqual(config["name"], "goal-to-done")
        self.assertEqual(config["scorer"], {"type": "expect_set"})
        skill_path = (FIXTURE / config["skill_path"]).resolve()
        self.assertEqual(skill_path, (SKILL_DIR / "SKILL.md").resolve())
        self.assertTrue(skill_path.is_file())
        variants = {v["name"]: v for v in config["prompt_variants"]}
        self.assertEqual(set(variants), {"baseline", "with-skill"})
        self.assertNotIn("inject_skill", variants["baseline"])
        self.assertIs(variants["with-skill"]["inject_skill"], True)
        for variant in variants.values():
            self.assertIn("{draft}", variant["template"])

    def test_cases_are_well_formed(self):
        cases = load_cases()
        self.assertGreaterEqual(len(cases), 20)
        ids = [c["id"] for c in cases]
        self.assertEqual(len(ids), len(set(ids)), "case ids must be unique")
        for case in cases:
            self.assertIn(case["kind"], {"dirty", "clean"}, case["id"])
            self.assertTrue(case["draft"].strip(), case["id"])
            self.assertIsInstance(case["expect"], list, case["id"])
            if case["kind"] == "clean":
                self.assertEqual(case["expect"], [], case["id"])
            else:
                self.assertTrue(expect_ids(case), case["id"])


class ClaimAndReceiptRuleTests(unittest.TestCase):
    def setUp(self):
        self.reconciled_r1 = [("revision", 1), ("reconciled", 1)]

    def steward_claim(self, revision, at, **kwargs):
        claim = {"revision": revision, "at": at, "by": "steward",
                 "steward_active": False, "brief_version": 1}
        claim.update(kwargs)
        return claim

    def test_claim_at_stale_brief_version_is_invalid(self):
        claim = self.steward_claim(1, at=2, brief_version=1)
        self.assertFalse(claim_valid(self.reconciled_r1, claim,
                                     current_brief_version=2))

    def test_authorized_brief_bump_requires_new_reconciliation(self):
        # brief v2 advances the graph to revision 2 (SPEC section 3); a claim
        # made under revision 1's marker is invalid until reconciled 2 posts.
        markers = self.reconciled_r1 + [("revision", 2)]
        stale = self.steward_claim(1, at=3, brief_version=2)
        self.assertFalse(claim_valid(markers, stale, current_brief_version=2))
        markers.append(("reconciled", 2))
        fresh = self.steward_claim(2, at=4, brief_version=2)
        self.assertTrue(claim_valid(markers, fresh, current_brief_version=2))

    def test_claim_after_reconciliation_is_valid(self):
        self.assertTrue(claim_valid(self.reconciled_r1, self.steward_claim(1, at=2)))

    def test_same_revision_claim_before_reconciliation_is_invalid(self):
        markers = [("revision", 1)]
        self.assertFalse(claim_valid(markers, self.steward_claim(1, at=1)))

    def test_claim_goes_stale_when_newer_revision_exists(self):
        markers = self.reconciled_r1 + [("revision", 2)]
        self.assertFalse(claim_valid(markers, self.steward_claim(1, at=2)))

    def test_pre_reconciliation_claim_at_new_revision_is_invalid(self):
        markers = self.reconciled_r1 + [("revision", 2)]
        self.assertFalse(claim_valid(markers, self.steward_claim(2, at=3)))
        markers.append(("reconciled", 2))
        self.assertTrue(claim_valid(markers, self.steward_claim(2, at=4)))

    def test_worker_self_claim_is_invalid(self):
        claim = self.steward_claim(1, at=2, by="worker")
        self.assertFalse(claim_valid(self.reconciled_r1, claim))

    def test_second_steward_must_stop(self):
        claim = self.steward_claim(1, at=2, steward_active=True)
        self.assertFalse(claim_valid(self.reconciled_r1, claim))

    def receipt(self, **kwargs):
        base = {"revision": 1, "brief_version": 1,
                "fields": TICKET_CONTRACT_FIELDS, "passed": True,
                "affected_by_replan": False}
        base.update(kwargs)
        return base

    def test_valid_receipt_unlocks(self):
        self.assertTrue(receipt_valid(self.reconciled_r1, self.receipt(), 1))

    def test_in_flight_receipt_goes_stale_on_replan(self):
        markers = self.reconciled_r1 + [("revision", 2), ("reconciled", 2)]
        self.assertFalse(receipt_valid(markers, self.receipt(revision=1), 1))

    def test_carried_forward_receipt_stays_valid_after_replan(self):
        markers = self.reconciled_r1 + [("revision", 2), ("reconciled", 2)]
        retained = self.receipt(revision=1, carried_forward_to=2)
        self.assertTrue(receipt_valid(markers, retained, 1))

    def test_affected_receipt_without_carry_forward_is_invalid(self):
        markers = self.reconciled_r1 + [("revision", 2), ("reconciled", 2)]
        self.assertFalse(receipt_valid(markers, self.receipt(revision=1), 1))
        unreconciled = self.reconciled_r1 + [("revision", 2)]
        premature = self.receipt(revision=1, carried_forward_to=2)
        self.assertFalse(receipt_valid(unreconciled, premature, 1))

    def test_receipt_in_pre_reconciliation_window_is_invalid(self):
        markers = self.reconciled_r1 + [("revision", 2)]
        receipt = self.receipt(revision=2, at=3)
        self.assertFalse(receipt_valid(markers, receipt, 1))
        markers.append(("reconciled", 2))
        self.assertTrue(receipt_valid(markers, self.receipt(revision=2, at=4), 1))

    def test_receipt_at_stale_brief_version_is_invalid(self):
        self.assertFalse(receipt_valid(self.reconciled_r1,
                                       self.receipt(brief_version=1), 2))

    def test_receipt_missing_contract_field_is_invalid(self):
        fields = tuple(f for f in TICKET_CONTRACT_FIELDS if f != "stop_condition")
        self.assertFalse(receipt_valid(self.reconciled_r1,
                                       self.receipt(fields=fields), 1))

    def test_failed_or_unaffirmed_receipt_never_unlocks(self):
        self.assertFalse(receipt_valid(self.reconciled_r1,
                                       self.receipt(passed=False), 1))
        self.assertFalse(receipt_valid(self.reconciled_r1,
                                       self.receipt(affected_by_replan=True), 1))


class ArenaAdapterTests(unittest.TestCase):
    def setUp(self):
        self.run_arena = load_run_arena()

    def test_backend_allowlist_is_codex_openai_claude_anthropic_only(self):
        self.assertEqual(self.run_arena.ALLOWED_BACKENDS,
                         {"codex", "openai", "claude-cli", "anthropic",
                          "opus", "sonnet", "haiku"})
        config = json.loads((FIXTURE / "config.json").read_text())
        self.assertTrue(set(config["models"]) <= self.run_arena.ALLOWED_BACKENDS)

    def test_disallowed_backend_is_rejected(self):
        with self.assertRaises(SystemExit) as ctx:
            self.run_arena.main(["--backends", "google", "--out-dir", "/tmp/unused"])
        self.assertNotEqual(ctx.exception.code, 0)

    def test_registered_live_gate_matches_design(self):
        design = (FIXTURE / "DESIGN.md").read_text()
        self.assertIn("pass rate >= 0.80", design)
        self.assertEqual(self.run_arena.LIVE_PASS_RATE, 0.80)
        self.assertEqual(self.run_arena.LIVE_VARIANT, "with-skill")

    def test_frozen_input_digest_matches_recorded(self):
        digest_file = FIXTURE / "input.sha256"
        self.assertTrue(digest_file.is_file(),
                        "freeze the arena input digest in input.sha256")
        self.assertEqual(self.run_arena.input_digest(),
                         digest_file.read_text().strip())

    def _results(self, cells):
        return {"skills": {"goal-to-done": {"cells": cells}}}

    def _cell(self, variant="with-skill", backend="openai", passes=28, n=28, errors=0):
        return {"backend": backend, "prompt_variant": variant, "passes": passes,
                "n": n, "errors": errors, "pass_rate": (passes / n if n else 0.0)}

    def test_gate_passes_on_clean_live_cells(self):
        results = self._results([self._cell(backend="openai"),
                                 self._cell(backend="anthropic")])
        self.assertEqual(self.run_arena.check_thresholds(results, False, 28), [])

    def test_gate_fails_on_backend_error(self):
        results = self._results([self._cell(errors=1)])
        self.assertTrue(self.run_arena.check_thresholds(results, False, 28))

    def test_gate_fails_below_pass_rate(self):
        results = self._results([self._cell(passes=20)])  # 0.71 < 0.80
        self.assertTrue(self.run_arena.check_thresholds(results, False, 28))

    def test_gate_fails_when_not_every_case_ran(self):
        results = self._results([self._cell(passes=27, n=27)])
        self.assertTrue(self.run_arena.check_thresholds(results, False, 28))

    def test_gate_only_scores_the_with_skill_variant(self):
        # a weak baseline cell must not fail the live gate
        results = self._results([self._cell(variant="baseline", passes=1),
                                 self._cell(variant="with-skill")])
        self.assertEqual(self.run_arena.check_thresholds(results, False, 28), [])

    def test_gate_fails_on_empty_cells(self):
        self.assertTrue(self.run_arena.check_thresholds(self._results([]), False, 28))

    def test_dry_run_gate_requires_every_case_to_pass(self):
        ok = self._results([self._cell(variant="baseline"), self._cell()])
        self.assertEqual(self.run_arena.check_thresholds(ok, True, 28), [])
        bad = self._results([self._cell(passes=27)])
        self.assertTrue(self.run_arena.check_thresholds(bad, True, 28))

    def test_dry_run_end_to_end(self):
        import tempfile
        arena_root = Path(self.run_arena.default_arena_root())
        if not (arena_root / "arena.py").is_file():
            self.skipTest("skill-arena checkout not available")
        with tempfile.TemporaryDirectory() as tmp:
            rc = self.run_arena.main(["--dry-run", "--out-dir", tmp])
            self.assertEqual(rc, 0)
            results = json.loads((Path(tmp) / "results.json").read_text())
            cells = results["skills"]["goal-to-done"]["cells"]
            self.assertTrue(cells)
            for cell in cells:
                self.assertEqual(cell["passes"], cell["n"], cell["prompt_variant"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
