#!/usr/bin/env bash
# Provider-neutral adversarial review — same contract as gemini-review.sh
# (--model/--focus/FILES) but with a fallback chain so the red-team step never
# hard-fails on one provider: gemini → codex → cursor (all read-only).
#
# Capacity-aware when HARNESS_DIR points at a checkout providing capacity.py:
# a seat marked exhausted in capacity.json is skipped without burning a timeout, and a
# runtime capacity error (429 / spend cap / no credits) is reported back so the state
# self-updates. Without the harness, the chain still works — it just learns by failing.
#
# Usage:
#   adversarial-review.sh [--model M] [--focus "extra attack instructions"] FILE [FILE...]
# Prints "ENGINE: <name>" as the first line so callers know which model reviewed.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
# opt-in: export HARNESS_DIR to enable capacity-aware seat ordering
HARNESS_DIR="${HARNESS_DIR:-}"
CAP_PY="$HARNESS_DIR/capacity.py"
CAP_FILE="${CAPACITY_FILE:-$HARNESS_DIR/capacity.json}"

MODEL=""
FOCUS=""
FILES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --model) MODEL="$2"; shift 2;;
    --focus) FOCUS="$2"; shift 2;;
    -h|--help) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    -*) echo "unknown flag: $1" >&2; exit 2;;
    *) FILES+=("$1"); shift;;
  esac
done
[ "${#FILES[@]}" -gt 0 ] || { echo "error: pass at least one file to review" >&2; exit 1; }
for f in "${FILES[@]}"; do [ -r "$f" ] || { echo "error: cannot read $f" >&2; exit 1; }; done

# Capacity helpers — ADVISORY: any failure to read state means "usable".
usable() { # engine
  [ -f "$CAP_PY" ] || return 0
  python3 "$CAP_PY" check --engine "$1" --file "$CAP_FILE" >/dev/null 2>&1
  [ "$?" -ne 3 ]
}
report() { # engine, output
  [ -f "$CAP_PY" ] || return 0
  local ef; ef="$(mktemp)" || return 0
  printf '%s\n' "$2" > "$ef"
  python3 "$CAP_PY" report --engine "$1" --file "$CAP_FILE" --stderr-file "$ef" >/dev/null 2>&1
  rm -f "$ef"
  return 0
}

# Same skeptic prompt as gemini-review.sh (kept in sync — the wording is the skill).
PROMPT='You are a ruthless, skeptical staff engineer doing an ADVERSARIAL review. Do NOT be agreeable and do NOT summarize the material back. Your only job is to find where this is WRONG, fragile, self-deceiving, or incomplete. Be concrete and specific to THIS material — no generic best-practice advice. For each finding: state the problem, why it actually bites, and the cheapest fix. Rank EVERY finding Critical / High / Medium. Explicitly call out: hidden assumptions, missing work that no part of the plan covers, wrong sequencing/dependencies, and anything deferred that is actually load-bearing now. End with the single biggest risk you would escalate.'
[ -n "$FOCUS" ] && PROMPT="$PROMPT

Pay special attention to: $FOCUS"

bundle() {
  for f in "${FILES[@]}"; do
    printf '===== FILE: %s =====\n' "$f"
    cat "$f"
    printf '\n'
  done
}

try_gemini() {
  command -v gemini >/dev/null 2>&1 || return 3
  usable gemini || { echo "(capacity: gemini exhausted — skipping to fallback)" >&2; return 3; }
  local out rc
  out="$(bash "$HERE/gemini-review.sh" ${MODEL:+--model "$MODEL"} ${FOCUS:+--focus "$FOCUS"} "${FILES[@]}" 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ]; then report gemini "$out"; return 3; fi
  echo "ENGINE: gemini"
  printf '%s\n' "$out"
}

try_codex() {
  command -v codex >/dev/null 2>&1 || return 3
  usable codex || { echo "(capacity: codex exhausted — skipping to fallback)" >&2; return 3; }
  local out rc
  # Read-only + no approvals; artifact is untrusted text, same posture as council.sh.
  # --model is gemini-namespaced; fallback engines use their account defaults.
  out="$(codex exec --sandbox read-only -c approval_policy="never" --skip-git-repo-check "$PROMPT

--- MATERIAL (review ONLY this text; do NOT run commands or modify files) ---
$(bundle)" </dev/null 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ]; then report codex "$out"; return 3; fi
  echo "ENGINE: codex"
  printf '%s\n' "$out"
}

try_cursor() {
  command -v cursor-agent >/dev/null 2>&1 || return 3
  [ -n "${CURSOR_API_KEY:-}" ] || return 3
  usable cursor || { echo "(capacity: cursor exhausted — no seats left)" >&2; return 3; }
  local out rc
  # SECURITY: --mode ask = enforced read-only sandbox; never --force/--yolo (see council.sh).
  out="$(cursor-agent -p --output-format text --mode ask --sandbox enabled "$PROMPT

--- MATERIAL (review ONLY this text; do NOT run commands or modify files) ---
$(bundle)" </dev/null 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ]; then report cursor "$out"; return 3; fi
  echo "ENGINE: cursor"
  printf '%s\n' "$out"
}

try_gemini && exit 0
try_codex && exit 0
try_cursor && exit 0
echo "error: every review engine failed or was unavailable (gemini, codex, cursor)" >&2
exit 1
