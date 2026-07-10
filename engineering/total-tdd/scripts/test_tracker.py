#!/usr/bin/env python3
"""Tests for tracker.py — the total-tdd state machine."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import tracker  # noqa: E402

HERE = os.path.dirname(__file__)
SAMPLE = os.path.join(HERE, "sample-feature-audit.csv")


def write_csv(text):
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    with open(path, "w") as f:
        f.write(text)
    return path


class TestPhaseInference(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(tracker.infer_phase([])[0], 1)

    def test_missing_status_is_phase1(self):
        self.assertEqual(tracker.infer_phase([("F1", "")])[0], 1)

    def test_any_spec_is_phase2(self):
        self.assertEqual(tracker.infer_phase([("F1", "verified"), ("F2", "spec")])[0], 2)

    def test_any_fail_is_phase3(self):
        self.assertEqual(tracker.infer_phase([("F1", "pass"), ("F2", "fail")])[0], 3)

    def test_pass_fixed_remaining_is_phase4(self):
        self.assertEqual(tracker.infer_phase([("F1", "verified"), ("F2", "fixed")])[0], 4)

    def test_all_verified_is_done(self):
        self.assertIsNone(tracker.infer_phase([("F1", "verified"), ("F2", "verified")])[0])

    def test_phase3_precedes_phase4(self):
        # a fail outranks a non-verified pass
        self.assertEqual(tracker.infer_phase([("F1", "fail"), ("F2", "pass")])[0], 3)


def _row(status="", verified="", issues="", fix="", id="F1"):
    return {"id": id, "status": status, "verified": verified, "issues": issues, "fix": fix}


class TestGate(unittest.TestCase):
    def test_phase3_blocked_by_fail(self):
        self.assertTrue(tracker.gate_blockers([_row(status="fail", issues="x"), _row(status="fixed", fix="y", id="F2")], 3))

    def test_phase3_complete(self):
        self.assertEqual(tracker.gate_blockers([_row(status="fixed", fix="y"), _row(status="verified", verified="ok", id="F2")], 3), [])

    def test_phase4_blocked_until_all_verified(self):
        self.assertTrue(tracker.gate_blockers([_row(status="verified", verified="ok"), _row(status="fixed", fix="y", id="F2")], 4))

    def test_phase2_blocked_by_spec(self):
        self.assertTrue(tracker.gate_blockers([_row(status="spec")], 2))

    # evidence-before-status enforcement (Offscript adherence-audit finding)
    def test_pass_without_evidence_blocks_phase2(self):
        b = tracker.gate_blockers([_row(status="pass", verified="")], 2)
        self.assertTrue(any("evidence" in r for _, r in b))

    def test_pass_with_evidence_clears_phase2(self):
        self.assertEqual(tracker.gate_blockers([_row(status="pass", verified="logged in; dashboard ok")], 2), [])

    def test_verified_without_evidence_blocks_phase4(self):
        b = tracker.gate_blockers([_row(status="verified", verified="")], 4)
        self.assertTrue(any("evidence" in r for _, r in b))

    def test_fail_without_repro_blocks_phase2(self):
        b = tracker.gate_blockers([_row(status="fail", issues="")], 2)
        self.assertTrue(any("repro" in r for _, r in b))


class TestFileOps(unittest.TestCase):
    def test_init_creates_header(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "sub", "feature-audit.csv")
        rc = tracker.main(["init", path])
        self.assertEqual(rc, 0)
        header, rows = tracker.read(path)
        self.assertEqual(header, tracker.HEADER)
        self.assertEqual(rows, [])

    def test_validate_ok_on_sample(self):
        self.assertEqual(tracker.main(["validate", SAMPLE]), 0)

    def test_validate_detects_bad_status(self):
        path = write_csv(",".join(tracker.HEADER) + "\nF1,A,s,e,src,bogus,,,\n")
        self.assertEqual(tracker.main(["validate", path]), 1)

    def test_repair_fixes_header(self):
        # extra trailing column / wrong header → repair rewrites canonical header
        path = write_csv("id,area,user_story,expected_behavior,source,status,issues,fix,verified,extra\n"
                         "F1,A,s,e,src,spec,,,,junk\n")
        self.assertEqual(tracker.main(["validate", path, "--repair"]), 0)
        header, _ = tracker.read(path)
        self.assertEqual(header, tracker.HEADER)

    def test_phase_on_sample_is_3(self):
        # sample has a fail row → phase 3
        self.assertEqual(tracker.infer_phase(tracker.statuses(SAMPLE))[0], 3)


if __name__ == "__main__":
    unittest.main()
