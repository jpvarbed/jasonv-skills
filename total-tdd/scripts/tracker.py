#!/usr/bin/env python3
"""total-tdd state machine over the canonical feature-audit CSV.

The CSV is the single source of truth. This script owns the *deterministic* parts the
model used to re-derive every resume (and drift on): the schema, the phase inference,
the per-phase done-gates, and the tally. Judgment (what a feature is, expected behavior,
whether observed behavior justifies a status) stays in SKILL.md.

Usage:
 tracker.py init [csv] # write the canonical header if absent
 tracker.py validate [csv] [--repair] # assert header+status enum; --repair rewrites header
 tracker.py phase [csv] # print current phase (1-4) or "done" + reason
 tracker.py gate [csv] --phase N # exit 0 if phase N is complete, else list blockers
 tracker.py tally [csv] # one-line status tally

csv defaults to docs/feature-audit.csv. Only init and --repair mutate the file.
"""
import argparse
import csv
import sys

HEADER = ["id", "area", "user_story", "expected_behavior", "source",
 "status", "issues", "fix", "verified"]
STATUSES = ["spec", "pass", "fail", "fixed", "verified"]
DEFAULT_CSV = "docs/feature-audit.csv"


def read(path):
 """Return (header, rows) or raise FileNotFoundError."""
 with open(path, newline="") as f:
 r = csv.reader(f)
 rows = list(r)
 if not rows:
 return [], []
 return rows[0], rows[1:]


def as_dicts(path):
 header, rows = read(path)
 return [dict(zip(header, r + [""] * (len(header) - len(r)))) for r in rows]


def statuses(path):
 return [(d.get("id") or f"row{i+1}", (d.get("status") or "").strip())
 for i, d in enumerate(as_dicts(path))]


def infer_phase(sts):
 """sts: list of (id, status). Returns (phase:int|None, reason). None == done."""
 if not sts:
 return 1, "no rows yet — inventory not started"
 vals = [s for _, s in sts]
 bad = [i for i, s in sts if s not in STATUSES]
 if bad:
 return 1, f"{len(bad)} row(s) without a valid status (e.g. {bad[0]}) — still speccing"
 if "spec" in vals:
 return 2, f"{vals.count('spec')} row(s) still 'spec' — test them"
 if "fail" in vals:
 return 3, f"{vals.count('fail')} row(s) 'fail' — fix them"
 if any(v != "verified" for v in vals):
 n = sum(1 for v in vals if v != "verified")
 return 4, f"{n} row(s) not yet 'verified' — re-test"
 return None, "all rows verified"


def _f(d, col):
 return (d.get(col) or "").strip()


def gate_blockers(rows, phase):
 """Rows blocking completion of `phase`, as (id, reason). Empty == phase complete.

 Enforces evidence-before-status (the Offscript adherence-audit finding): a terminal
 status with no recorded evidence is a blocker, not a pass — `pass`/`verified` need the
 Evidence (`verified`) cell, `fail` needs a repro in `issues`, `fixed` needs a `fix` note.
 """
 if phase not in (1, 2, 3, 4):
 raise SystemExit(f"bad phase {phase} (1-4)")

 def rid(d, i):
 return d.get("id") or f"row{i + 1}"

 if phase == 1:
 b = [(rid(d, i), "no valid status") for i, d in enumerate(rows) if _f(d, "status") not in STATUSES]
 return b or ([("(none)", "no rows")] if not rows else [])

 b = []
 for i, d in enumerate(rows):
 s = _f(d, "status")
 if phase == 2:
 if s in ("", "spec") or s not in STATUSES:
 b.append((rid(d, i), "untested"))
 elif s == "pass" and not _f(d, "verified"):
 b.append((rid(d, i), "pass without evidence"))
 elif s == "fail" and not _f(d, "issues"):
 b.append((rid(d, i), "fail without repro"))
 elif phase == 3:
 if s == "fail":
 b.append((rid(d, i), "fail not fixed"))
 elif s == "fixed" and not _f(d, "fix"):
 b.append((rid(d, i), "fixed without a fix note"))
 elif phase == 4:
 if s != "verified":
 b.append((rid(d, i), "not verified"))
 elif not _f(d, "verified"):
 b.append((rid(d, i), "verified without evidence"))
 return b


def cmd_init(a):
 try:
 read(a.csv)
 print(f"exists: {a.csv}")
 return 0
 except FileNotFoundError:
 pass
 import os
 os.makedirs(os.path.dirname(a.csv) or ".", exist_ok=True)
 with open(a.csv, "w", newline="") as f:
 csv.writer(f).writerow(HEADER)
 print(f"created: {a.csv}")
 return 0


def cmd_validate(a):
 header, rows = read(a.csv)
 problems = []
 if header != HEADER:
 problems.append(f"header drift: {header} != {HEADER}")
 for i, r in enumerate(rows):
 d = dict(zip(header, r + [""] * (len(header) - len(r))))
 st = (d.get("status") or "").strip()
 if st and st not in STATUSES:
 problems.append(f"row {d.get('id') or i+1}: bad status {st!r}")
 if not problems:
 print(f"ok: {len(rows)} rows, schema valid")
 return 0
 if a.repair:
 fixed = [dict(zip(header, r + [""] * (len(header) - len(r)))) for r in rows]
 with open(a.csv, "w", newline="") as f:
 w = csv.writer(f)
 w.writerow(HEADER)
 for d in fixed:
 w.writerow([d.get(c, "") for c in HEADER])
 print(f"repaired header → {a.csv} ({len(rows)} rows). Re-check status values:")
 for p in problems:
 print(f" - {p}")
 return 0
 print("INVALID:")
 for p in problems:
 print(f" - {p}")
 print("run with --repair to rewrite the header to the canonical 9 columns")
 return 1


def cmd_phase(a):
 phase, reason = infer_phase(statuses(a.csv))
 print(f"done — {reason}" if phase is None else f"phase {phase} — {reason}")
 return 0


def cmd_gate(a):
 blockers = gate_blockers(as_dicts(a.csv), a.phase)
 if not blockers:
 print(f"phase {a.phase}: COMPLETE")
 return 0
 print(f"phase {a.phase}: BLOCKED by {len(blockers)} row(s):")
 for i, s in blockers[:50]:
 print(f" - {i}: {s}")
 return 1


def cmd_tally(a):
 sts = [s for _, s in statuses(a.csv)]
 parts = " · ".join(f"{sts.count(s)} {s}" for s in STATUSES)
 print(f"{len(sts)} total · {parts}")
 return 0


def main(argv=None):
 p = argparse.ArgumentParser(description=__doc__)
 sub = p.add_subparsers(dest="cmd", required=True)
 for name in ("init", "validate", "phase", "gate", "tally"):
 sp = sub.add_parser(name)
 sp.add_argument("csv", nargs="?", default=DEFAULT_CSV)
 if name == "validate":
 sp.add_argument("--repair", action="store_true")
 if name == "gate":
 sp.add_argument("--phase", type=int, required=True, choices=[1, 2, 3, 4])
 a = p.parse_args(argv)
 return {"init": cmd_init, "validate": cmd_validate, "phase": cmd_phase,
 "gate": cmd_gate, "tally": cmd_tally}[a.cmd](a)


if __name__ == "__main__":
 sys.exit(main())
