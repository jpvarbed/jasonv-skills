# Receipt rubric — one per gate

Every receipt is the same three parts. Never put a summary where OUTPUT goes —
OUTPUT is the raw, unedited result. Author notes (if any) go under NOTES only.

    INPUT:  <exactly what was run / fed in: the command, the task, the diff, the cases>
    OUTPUT: <the raw, verbatim result — tool stdout, the agent's own returned text/JSON,
             the results file. NOT a paraphrase.>
    GRADE:  <PASS | FAIL | CONCERNS | BLOCKED> by rule: <the stated pass rule and the
             number that decides it, e.g. "with-skill > baseline", "verdict == PASS",
             ">= 2 model families", "all tests green">
    NOTES:  <optional: deviations, excluded seats, known limits. Never replaces OUTPUT.>

`workshop.py report` renders INPUT -> OUTPUT -> GRADE for every gate on one page, so
reading a receipt is one question: did the OUTPUT actually earn the GRADE?
