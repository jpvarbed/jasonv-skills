# Receipt template — one per step, kept human-readable

Copy this per gate so every step leaves an artifact a reviewer can actually read.
The command block must be the real command; paste the real output verbatim below it.
End with a one-line verdict. `workshop.py report` inlines these into REPORT.md/REPORT.html.

---

STEP: <gate name, e.g. Behavioral eval / Council final/deep / Thermos>
FAMILY / SEAT: <model family or reviewer seat, if applicable>

$ <exact command that produced this evidence>
<paste the real, verbatim output — not a summary>

VERDICT: <PASS | FAIL | CONCERNS | BLOCKED> — <one sentence, with the number that proves it>
NOTES: <deviations, excluded seats, known limitations — keep failures visible>
