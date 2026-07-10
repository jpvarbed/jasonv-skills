#!/usr/bin/env python3
"""Tests for render.py — CSV → HTML report."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import render # noqa: E402

HERE = os.path.dirname(__file__)
SAMPLE = os.path.join(HERE, "sample-feature-audit.csv")


class TestRender(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
 cls.rows = render.rows_from(SAMPLE)
 cls.html = render.render(cls.rows, app="Demo")

 def test_tally_counts(self):
 self.assertEqual(render.tally_line(self.rows),
 "3 total · 0 spec · 0 pass · 1 fail · 1 fixed · 1 verified")

 def test_one_row_per_feature(self):
 self.assertEqual(self.html.count("<tr>"), len(self.rows) + 1) # +1 header row

 def test_status_classes_present(self):
 for cls in ("fail", "fixed", "verified"):
 self.assertIn(f'class="{cls}"', self.html)

 def test_source_folded_into_expected(self):
 self.assertIn("<code>(auth.ts:42)</code>", self.html)

 def test_app_name_rendered(self):
 self.assertIn(">Demo</span>", self.html)

 def test_self_contained(self):
 self.assertIn("<style>", self.html)
 self.assertNotIn("<link", self.html)

 def test_escaping(self):
 rows = [{"id": "X1", "area": "A", "user_story": "a & b <x>",
 "expected_behavior": "", "source": "", "status": "spec",
 "issues": "", "fix": "", "verified": ""}]
 h = render.render(rows)
 self.assertIn("a &amp; b &lt;x&gt;", h)


if __name__ == "__main__":
 unittest.main()
