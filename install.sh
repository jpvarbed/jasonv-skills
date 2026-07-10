#!/usr/bin/env bash
# Install these skills into ~/.claude/skills (symlinks). Set CLAUDE_SKILLS_DIR to override.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dest="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$dest"
# skills are laid out category/skill (engineering/, meta/, review/, ...); link each
# skill leaf into ~/.claude/skills by its own name (flat, the way agents expect).
for d in "$here"/*/*/; do
  [ -f "$d/SKILL.md" ] || continue
  name="$(basename "$d")"
  ln -sfn "$d" "$dest/$name"
  echo "linked $name"
done
