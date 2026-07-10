#!/usr/bin/env bash
# Adversarial review via the Gemini CLI — an independent second model attacks your
# plan/spec/ADR/diff. Pipes the given files to `gemini` framed as a ruthless skeptic.
#
# Usage:
#   gemini-review.sh [--model M] [--focus "extra attack instructions"] FILE [FILE...]
#
# Examples:
#   gemini-review.sh apps/x/specs/ADR-001.md apps/x/specs/tasks.md
#   gemini-review.sh --model gemini-2.5-flash --focus "the auth flow" diff.patch
#
# Auth: needs `gemini` configured. If it 403s with SUBSCRIPTION_REQUIRED, use
# API-key auth (see the skill's Troubleshooting section).
set -euo pipefail

MODEL="gemini-2.5-pro"
FOCUS=""
FILES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --model) MODEL="$2"; shift 2;;
    --focus) FOCUS="$2"; shift 2;;
    -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    -*) echo "unknown flag: $1" >&2; exit 2;;
    *) FILES+=("$1"); shift;;
  esac
done

[ "${#FILES[@]}" -gt 0 ] || { echo "error: pass at least one file to review" >&2; exit 1; }
command -v gemini >/dev/null 2>&1 || { echo "error: gemini CLI not found on PATH" >&2; exit 1; }
for f in "${FILES[@]}"; do [ -r "$f" ] || { echo "error: cannot read $f" >&2; exit 1; }; done

# gemini 0.46+ compat: load the API key if not already in the env (bws-load is
# on-demand), and bypass the new trusted-folder gate for headless use.
[ -z "${GEMINI_API_KEY:-}" ] && [ -f "$HOME/.gemini/.env" ] && \
  export GEMINI_API_KEY="$(sed -nE 's/^GEMINI_API_KEY=//p' "$HOME/.gemini/.env" | head -1)"
export GEMINI_CLI_TRUST_WORKSPACE=true

PROMPT='You are a ruthless, skeptical staff engineer doing an ADVERSARIAL review. Do NOT be agreeable and do NOT summarize the material back. Your only job is to find where this is WRONG, fragile, self-deceiving, or incomplete. Be concrete and specific to THIS material — no generic best-practice advice. For each finding: state the problem, why it actually bites, and the cheapest fix. Rank EVERY finding Critical / High / Medium. Explicitly call out: hidden assumptions, missing work that no part of the plan covers, wrong sequencing/dependencies, and anything deferred that is actually load-bearing now. End with the single biggest risk you would escalate.'
[ -n "$FOCUS" ] && PROMPT="$PROMPT

Pay special attention to: $FOCUS"

{
  for f in "${FILES[@]}"; do
    printf '===== FILE: %s =====\n' "$f"
    cat "$f"
    printf '\n'
  done
# SECURITY: no --yolo. The reviewed files are untrusted text; --yolo auto-approves
# tool calls, so an injected "run this command" in a file could auto-execute. Without
# it, a pure-text review still works and an injected tool call can't run unattended.
} | gemini --skip-trust -m "$MODEL" -p "$PROMPT" 2>&1 \
  | grep -viE 'token file corrupted|Loaded cached credentials|Failed to load API key|Both GOOGLE_API_KEY|not running in a trusted|256-color|Ripgrep is not available|^[[:space:]]+at (async|File)'
