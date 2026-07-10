#!/usr/bin/env python3
"""Render the canonical feature-audit CSV to a self-contained HTML report.

Pure function of the CSV — no judgment. Owns the HTML/CSS template that used to live in
reference-report.html (kept now only as a visual fixture). Reproduces its shape: a tally
line + one <tr> per feature, status as a CSS class, source folded into Expected behavior.

Usage:
 render.py [csv] [-o out.html] [--app NAME]

csv defaults to docs/feature-audit.csv; out defaults to docs/feature-audit.html.
Also prints the one-line tally to stdout.
"""
import argparse
import csv
import html
import sys

HEADER = ["id", "area", "user_story", "expected_behavior", "source",
 "status", "issues", "fix", "verified"]
STATUSES = ["spec", "pass", "fail", "fixed", "verified"]

STYLE = """\
 body { font: 14px/1.5 system-ui, sans-serif; margin: 2rem; color: #1a1a1a; }
 h1 { font-size: 20px; margin: 0 0 .25rem; }
 .tally { margin: 0 0 1rem; font-weight: 600; color: #444; }
 table { border-collapse: collapse; width: 100%; }
 th, td { border: 1px solid #e0e0e0; padding: 6px 9px; text-align: left; vertical-align: top; }
 th { background: #f6f7f9; }
 .spec { color: #8a6d00; }
 .pass { color: #137333; }
 .fail { color: #c5221f; font-weight: 600; }
 .fixed { color: #1a56c4; }
 .verified { color: #137333; font-weight: 600; }
 code { font: 12px ui-monospace, monospace; color: #555; }"""


def rows_from(path):
 with open(path, newline="") as f:
 return list(csv.DictReader(f))


def tally_line(rows):
 sts = [(r.get("status") or "").strip() for r in rows]
 parts = " · ".join(f"{sts.count(s)} {s}" for s in STATUSES)
 return f"{len(rows)} total · {parts}"


def render(rows, app="App"):
 e = lambda s: html.escape(s or "")
 trs = []
 for r in rows:
 st = (r.get("status") or "").strip()
 cls = st if st in STATUSES else ""
 expected = e(r.get("expected_behavior"))
 src = e(r.get("source"))
 if src:
 expected += f' <code>({src})</code>'
 trs.append(
 " <tr>\n"
 f" <td>{e(r.get('id'))}</td>\n"
 f" <td>{e(r.get('area'))}</td>\n"
 f" <td>{e(r.get('user_story'))}</td>\n"
 f" <td>{expected}</td>\n"
 f' <td class="{cls}">{e(st)}</td>\n'
 f" <td>{e(r.get('issues'))}</td>\n"
 f" <td>{e(r.get('fix'))}</td>\n"
 f" <td>{e(r.get('verified'))}</td>\n"
 " </tr>"
 )
 return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Feature Audit</title>
<style>
{STYLE}
</style>
</head>
<body>
 <h1>Feature Audit — <span id="app">{e(app)}</span></h1>
 <p class="tally">{e(tally_line(rows))}</p>
 <table>
 <thead>
 <tr>
 <th>ID</th><th>Area</th><th>User story</th><th>Expected behavior</th>
 <th>Status</th><th>Issues</th><th>Fix</th><th>Evidence</th>
 </tr>
 </thead>
 <tbody>
{chr(10).join(trs)}
 </tbody>
 </table>
</body>
</html>
"""


def main(argv=None):
 p = argparse.ArgumentParser(description=__doc__)
 p.add_argument("csv", nargs="?", default="docs/feature-audit.csv")
 p.add_argument("-o", "--out", default="docs/feature-audit.html")
 p.add_argument("--app", default="App")
 a = p.parse_args(argv)
 rows = rows_from(a.csv)
 with open(a.out, "w") as f:
 f.write(render(rows, a.app))
 print(tally_line(rows))
 print(f"wrote {a.out} ({len(rows)} rows)")
 return 0


if __name__ == "__main__":
 sys.exit(main())
