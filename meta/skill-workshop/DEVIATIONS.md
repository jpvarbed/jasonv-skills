# Deviations

- The first Plannotator approval process expired before recording its decision.
  The exact current file was reopened and returned `{"decision":"approved"}`.
- The first spec exceeded the fast council's fixed prompt ceiling. Repeated
  prose was compressed in the source spec; the profile was not enlarged or
  bypassed.
- Council proposals for local hashes, timestamps, fingerprints, duplicated
  arena results, and self-attested blind-context manifests were rejected. They
  move trust into author-issued metadata instead of establishing authenticity.
- The legacy harness council still binds obsolete Cline Kimi configuration and
  omitted Cursor's required trust flag. Those seats were excluded visibly. The
  current adapters were qualified directly: Cline used explicit
  `cline-pass/glm-5.2`; Cursor used `agent --trust` after native re-login.
- Arena suite v1 mislabeled a hybrid integration that omitted requested and
  effective effort as clean. Suite v2 retains that behavior as a dirty case and
  adds an actually clean counterpart; all final baseline and with-skill evidence
  is from the versioned suite, never the obsolete score.
- `uv run pytest -q` in skill-arena cannot import its committed top-level
  `majority` and `apps` modules. `PYTHONPATH=. uv run pytest -q` is the verified
  repository command; no packaging shim was added to this change.
