# templates/

- `receipt.md` — skeleton for each step's receipt. Readable by design: real command +
  verbatim output + a one-line verdict. Every gate leaves one under `receipts/`.

The reviewer-facing artifact is generated, not hand-written:

    python3 scripts/workshop.py report WORKSHOP.json --format md   -o REPORT.md
    python3 scripts/workshop.py report WORKSHOP.json --format html -o REPORT.html

`report` inlines every receipt's contents into one page next to the checker verdict,
so semantic review (confirming the receipts are *true*, not merely present) is one read.
