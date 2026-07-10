#!/usr/bin/env bash
# Majority-vote visual critique of 3D poses/renders/UI via the Gemini CLI.
# Runs 3 parallel visual analysis queries using gemini-2.5-pro, then uses
# gemini-2.5-flash to synthesize a reliable, hallucination-free consensus.
#
# Usage:
#   gemini-visual-critique.sh [--focus "specific instructions"] IMAGE_PATH
#
# Examples:
#   gemini-visual-critique.sh --focus "Check pelvis and spine tilt" public/hackmotion/clubface-proof/exact-35-85.png
#
# Auth: needs `gemini` configured.
set -euo pipefail

PRO_MODEL="gemini-2.5-pro"
FLASH_MODEL="gemini-2.5-flash"
FOCUS=""
IMAGE_PATH=""

while [ $# -gt 0 ]; do
  case "$1" in
    --focus) FOCUS="$2"; shift 2;;
    -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    -*) echo "unknown flag: $1" >&2; exit 2;;
    *) IMAGE_PATH="$1"; shift;;
  esac
done

[ -n "$IMAGE_PATH" ] || { echo "error: specify an image path to critique" >&2; exit 1; }
[ -r "$IMAGE_PATH" ] || { echo "error: cannot read image path $IMAGE_PATH" >&2; exit 1; }
command -v gemini >/dev/null 2>&1 || { echo "error: gemini CLI not found on PATH" >&2; exit 1; }

# Get absolute path for the image
ABS_IMAGE_PATH="$(cd "$(dirname "$IMAGE_PATH")" && pwd)/$(basename "$IMAGE_PATH")"

# Load the API key from local env if present
[ -z "${GEMINI_API_KEY:-}" ] && [ -f "$HOME/.gemini/.env" ] && \
  export GEMINI_API_KEY="$(sed -nE 's/^GEMINI_API_KEY=//p' "$HOME/.gemini/.env" | head -1)"
export GEMINI_CLI_TRUST_WORKSPACE=true

echo "🎨 Starting visual critique of $(basename "$IMAGE_PATH")..."
echo "⚡ Launching 3 independent runs in parallel to eliminate single-run noise..."

PROMPT="You are a peer-reviewing staff engineer specializing in 3D computer graphics, biomechanics, and human skeletal animation.
Analyze the attached 3D rendering of a rigged human figure (golfer) from 'face-on' and 'down-the-line' views, checking for anatomical correctness, posture athletic quality, and common rotation/projection bugs.

Review specifically:
- Posture/Athleticism: Does the figure look natural, athletic, and balanced, or are there rigid, awkward, or bent-backward parts (scoliosis-like leans, vulture-neck, broken joints)?
- Joint Alignment: Are joints like knees, hips, and shoulders aligned naturally, or do they look inverted, squatted, or physically impossible?
- Rotation/Euler Clues: Look for hints of rotation coupling, local axis leakage, or gimbal lock (e.g., hips or chest twisted/skewed sideways when they should be straight/square, joints rotating around the wrong local axis)."

if [ -n "$FOCUS" ]; then
  PROMPT="$PROMPT

Focus Area: $FOCUS"
fi

PROMPT="$PROMPT

Be ruthless, precise, and concrete. Do NOT say 'it looks great' or be agreeable. For each issue found, describe:
1. The Symptom: What is visually wrong in which view.
2. The Probable Cause: Is it an axis/coordinate-space inversion, a parent-child rotation leak, or a projection issue?
3. Recommended Fix: What mathematical or rigging correction should be applied.

Keep your response structured, concise, and professional."

# Setup temp files for outputs
TMP1="$(mktemp)"
TMP2="$(mktemp)"
TMP3="$(mktemp)"
trap 'rm -f "$TMP1" "$TMP2" "$TMP3"' EXIT

# Append the image path with @ to the prompt string for the vision model
PROMPT_WITH_IMAGE="$PROMPT

@$ABS_IMAGE_PATH"

# Run 3 pro queries in parallel
gemini --skip-trust -m "$PRO_MODEL" -p "$PROMPT_WITH_IMAGE" > "$TMP1" 2>&1 & PID1=$!
gemini --skip-trust -m "$PRO_MODEL" -p "$PROMPT_WITH_IMAGE" > "$TMP2" 2>&1 & PID2=$!
gemini --skip-trust -m "$PRO_MODEL" -p "$PROMPT_WITH_IMAGE" > "$TMP3" 2>&1 & PID3=$!

# Wait for all runs to finish
wait "$PID1" "$PID2" "$PID3"

echo "🧠 Runs complete. Composing consensus report..."

# Read output files
OUT1="$(cat "$TMP1")"
OUT2="$(cat "$TMP2")"
OUT3="$(cat "$TMP3")"

# Use flash to synthesize the consensus
SYNTH_PROMPT="You are a high-signal consensus synthesis engine.
We executed a visual inspection of a 3D model using 3 independent runs of a high-fidelity vision-language model to eliminate single-run hallucinations and noise.

Here are the 3 independent raw reports:
--- REPORT 1 ---
$OUT1
--- REPORT 2 ---
$OUT2
--- REPORT 3 ---
$OUT3

Your task is to:
1. Extract and reconcile all findings.
2. Identify consensus findings (issues mentioned in at least 2 of the 3 runs).
3. Discard outlier findings (issues only mentioned in 1 run, which are likely noise/hallucinations).
4. Present a single, authoritative, high-signal report containing only the verified consensus findings, ranked by severity (Critical / High / Medium).
5. Add a 'Consensus Summary' at the top explaining the state of the render (e.g., '3/3 runs agree that X is broken, while 2/3 agree Y needs adjustment')."

gemini --skip-trust -m "$FLASH_MODEL" -p "$SYNTH_PROMPT" 2>&1 \
  | grep -viE 'token file corrupted|Loaded cached credentials|Failed to load API key|Both GOOGLE_API_KEY|not running in a trusted|256-color|Ripgrep is not available|^[[:space:]]+at (async|File)'
