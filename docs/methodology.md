# Skill Performance Methodology

`arena publish` renders public skill-performance surfaces from evidence artifacts produced by
[skill-arena](https://github.com/jpvarbed/skill-arena).

Numbers come from objective evidence files, not hand-entered claims. Deterministic scorers check
gold cases directly when an output can be judged without another model. LLM judges are used only
when the task genuinely needs judgment, and benchmark cases should keep expected outcomes explicit.

Gold cases live with the benchmark. For nondeterministic model behavior, k-trial majority voting is
the preferred shape: run each case multiple times and count the majority verdict, so one flaky call
does not dominate the score.

Forge pre/post results compare the original skill with generated variants on the same cases and
models. Lift is strict: a tie is not an improvement, and negative lift is published as a regression.
The published data keeps the original score, best-variant score, and per-model lift so readers can
see where a variant helped and where it hurt.

Trajectory benchmarks use real issues or realistic task traces when a skill is supposed to improve
multi-step agent work. Those results should link back to the exact evidence snapshot used to render
the public page.
