---
name: visual-critique
description: Get a robust, noise-free 3-run majority-vote visual critique of 3D renders, joint positions, skeletal anatomy, or UI look-and-feel via the Gemini CLI, synthesizing a consensus report that eliminates LLM hallucinations. Use when you need to "verify a 3D pose", "spot broken anatomy/rotation bugs", or "review design details before proceeding". Not for structured UX/usability design feedback on a mockup — use design-critique instead; and not for red-teaming a plan, spec, or diff — use adversarial-review instead.
---

# Visual Critique

Get an independent, high-signal visual review of a 3D render, skeletal pose, or UI look-and-feel. 
To defeat single-run visual hallucinations and "noisy" LLM visual reasoning, this skill automates **majority-vote visual critique**: it runs the visual inspection **3 times in parallel** using a high-fidelity pro model (`gemini-2.5-pro`), then pipes the three raw outputs into a fast consensus engine (`gemini-2.5-flash`) to synthesize a single, noise-free, authoritative report containing only verified consensus findings.

## When to use

- After posing a joint or body part to verify its anatomical correctness, athletic quality, and balance.
- To detect subtle rotation coupling, local axis leakage, or coordinate space inversions in a 3D mesh.
- To review UI polish, alignment, margins, font weights, or design details.
- Whenever a single visual inspection feels "unstable" or flips back and forth.

## Process

### 1. Generate the render / screenshot
Save or copy the target render/image into the workspace (e.g., inside `public/` or `tmp/` so it is accessible to local tools and the `gemini` CLI).

### 2. Run the visual critique
Call the visual critique script, passing the image path and a specific focus or expectation:

```bash
skills/review/visual-critique/gemini-visual-critique.sh \
  --focus "Verify the knee flex (address knee line) and check if the pelvis looks squatted" \
  public/hackmotion/clubface-proof/fwd-check.png
```

- `--focus` instructs the model on what specific mechanics, joints, or design details to stress-test.
- The script will launch 3 parallel `gemini-2.5-pro` vision queries, collect their reviews, and pass them to `gemini-2.5-flash` to synthesize a consensus.

### 3. Act on the consensus
The final report only includes findings verified by at least 2 of the 3 runs. Use these to debug your math:
* **Check the Coordinate Order:** If the model reports a "broken/twisted spine" under turn, check if your rotation order is rotating the tilt axis.
* **Check Bone vs. Proxy Measurement:** If the model reports a visual posture match but the measured metric is off, calibrate the measurement engine using the actual 3D bone orientation rather than 2D/projected proxies.

## Errors

| Issue | Fix |
| --- | --- |
| Script exits with `error: gemini CLI not found on PATH` | Install the Gemini CLI and ensure `gemini` is on `PATH` (`command -v gemini`); the script hard-fails at the `command -v gemini` check before any run. |
| Reports come back empty or say "Failed to load API key" / "Both GOOGLE_API_KEY" | `GEMINI_API_KEY` is unset. Add `GEMINI_API_KEY=<key>` to `~/.gemini/.env` (the script auto-loads it via `sed`) or `export GEMINI_API_KEY` before calling; don't hardcode it in the SKILL. |
| `error: cannot read image path <path>` or `error: specify an image path` | Pass the IMAGE_PATH as the final positional arg (after `--focus`), and use a path readable from cwd — the script `cd`s into the image's dirname to build the absolute `@`-attached path, so relative paths must resolve from where you invoke it. |
| Gemini ignores the image or critiques nothing (HEIC/unsupported format) | Convert to PNG first: `sips -s format png in.heic --out tmp/in.png`, then point `--focus` + IMAGE_PATH at the PNG. The model only ingests the `@$ABS_IMAGE_PATH` it can decode. |
| One run's critique contradicts the others / a finding looks hallucinated | This is the expected single-run noise — trust the flash consensus report (only findings in ≥2 of 3 runs survive), and eyeball the named view/joint yourself before acting; never act on a 1/3 outlier. |
| Synthesis report is truncated or garbled (image too large for the API) | Downscale before sending: `sips -Z 1600 tmp/in.png` (or re-render at a smaller resolution) so the encoded image fits the vision model's request limit, then re-run. |
