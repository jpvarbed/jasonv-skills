#!/usr/bin/env bash
# Install these skills into ~/.claude/skills (symlinks). Set CLAUDE_SKILLS_DIR to override.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dest="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$dest"
for d in "$here"/*/; do
  name="$(basename "$d")"
  [ -f "$d/SKILL.md" ] || continue
  ln -sfn "$d" "$dest/$name"
  echo "linked $name"
done
