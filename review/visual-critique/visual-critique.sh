#!/usr/bin/env bash
# Three independent Codex vision inspections followed by a fourth consensus pass.
set -uo pipefail

FOCUS=""
IMAGE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --focus) [ $# -ge 2 ] || { echo 'error: --focus needs a value' >&2; exit 2; }; FOCUS="$2"; shift 2;;
    -h|--help) sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    -*) echo "error: unknown flag: $1" >&2; exit 2;;
    *) [ -z "$IMAGE" ] || { echo "error: one image only (extra: $1)" >&2; exit 2; }; IMAGE="$1"; shift;;
  esac
done

[ -n "$IMAGE" ] || { echo 'error: specify an image path' >&2; exit 2; }
[ -r "$IMAGE" ] || { echo "error: cannot read image path $IMAGE" >&2; exit 2; }
command -v codex >/dev/null 2>&1 || { echo 'error: codex CLI not found on PATH' >&2; exit 1; }

ABS_IMAGE="$(cd "$(dirname "$IMAGE")" && pwd)/$(basename "$IMAGE")"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PROMPT='Inspect the attached image as a skeptical visual reviewer. Report only concrete visible defects or mismatches. For every finding, name the exact region, what is visibly wrong, and the smallest correction. Separate direct observations from uncertain inferences. Do not run commands or modify files.'
[ -n "$FOCUS" ] && PROMPT="$PROMPT

Focus: $FOCUS"

pids=""
for i in 1 2 3; do
  codex exec --sandbox read-only -c approval_policy="never" --skip-git-repo-check \
    --image "$ABS_IMAGE" "$PROMPT" > "$TMP/review.$i" 2>&1 &
  pids="$pids $!"
done

failed=0
i=0
for pid in $pids; do
  i=$((i+1))
  wait "$pid" || failed=1
  [ -s "$TMP/review.$i" ] || { echo "error: visual inspection $i returned empty output" >&2; failed=1; }
done
if [ "$failed" -ne 0 ]; then
  for i in 1 2 3; do [ -s "$TMP/review.$i" ] && cat "$TMP/review.$i" >&2; done
  exit 1
fi

SYNTH='Synthesize the three visual inspections below. Keep only findings independently supported by at least two inspections. Discard every one-review outlier regardless of severity. Return a concise ranked report with evidence and the smallest correction. Do not run commands or modify files.'
for i in 1 2 3; do
  SYNTH="$SYNTH

===== INSPECTION $i =====
$(cat "$TMP/review.$i")"
done

out="$(codex exec --sandbox read-only -c approval_policy="never" --skip-git-repo-check "$SYNTH" </dev/null 2>&1)"
rc=$?
[ "$rc" -eq 0 ] || { printf '%s\n' "$out" >&2; exit "$rc"; }
[ -n "$(printf '%s' "$out" | tr -d '[:space:]')" ] || { echo 'error: consensus returned empty output' >&2; exit 1; }
printf '%s\n' "$out"
