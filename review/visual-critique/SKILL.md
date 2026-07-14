---
name: visual-critique
description: Run three independent Codex vision inspections of a render, pose, screenshot, or UI, then synthesize a consensus report. Use to verify visible anatomy, geometry, alignment, or polish before proceeding; use design-critique for structured UX feedback and adversarial-review for text artifacts.
---

# Visual Critique

Run three read-only vision inspections against the same image, then use a fourth Codex pass to
keep findings supported by at least two inspections. Gemini is prohibited from this workflow.

## Process

1. Save the render or screenshot as a readable PNG, JPEG, or other Codex-supported image.
2. Run:

```bash
skills/review/visual-critique/visual-critique.sh \
  --focus "check pelvis tilt, knee flex, and spine continuity" \
  path/to/render.png
```

3. Verify consensus findings against the image and implementation before changing code. A model
critique is evidence to inspect, not proof.

The script attaches the image to three parallel `codex exec` calls in a read-only sandbox. If any
inspection fails or returns empty output, the review fails instead of synthesizing incomplete
evidence. The final pass receives only the three textual inspections and returns the consensus.

## Errors

| Issue | Fix |
| --- | --- |
| `codex CLI not found on PATH` | Install/authenticate Codex and confirm `codex --version`. |
| `cannot read image path` | Pass one readable image path after `--focus`. |
| An inspection returns nonzero or empty | Read the emitted engine error, fix Codex/auth/capacity, and rerun all three inspections. |
| The model cannot decode the image | Convert it to PNG first, e.g. `sips -s format png in.heic --out in.png`. |
