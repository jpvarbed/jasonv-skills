#!/usr/bin/env bash
# Install jasonv-skills for one or more agents:  ./install.sh [claude|codex|cursor|gemini|all]
#   claude  -> symlink each skill into ~/.claude/skills (auto-discovered by Claude Code).
#   codex/cursor/gemini -> print a pointer block to paste into that agent's instructions file
#     (AGENTS.md / .cursor/rules / GEMINI.md). We do NOT edit those files for you — they usually
#     hold your own config. Most agents can't auto-run a skill; the pointer makes them discover it.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
skills=(); for d in "$here"/*/*/; do [ -f "$d/SKILL.md" ] && skills+=("$d"); done
agents=("$@"); [ ${#agents[@]} -eq 0 ] && agents=(all)
[ "${agents[*]}" = "all" ] && agents=(claude codex cursor gemini)

pointer() {
  echo "<!-- jasonv-skills -->"
  echo "## Skills (jasonv-skills)"
  echo "Skills live under \`$here/<category>/<skill>/\`. When a task matches a skill's purpose,"
  echo "READ that skill's SKILL.md and follow it. See $here/AGENTS.md for the full guide. Available:"
  for d in "${skills[@]}"; do
    echo "- $(basename "$d") — ${d#$here/}SKILL.md"
  done
}

for a in "${agents[@]}"; do case "$a" in
  claude)
    dest="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"; mkdir -p "$dest"
    for d in "${skills[@]}"; do ln -sfn "$d" "$dest/$(basename "$d")"; done
    echo "claude: linked ${#skills[@]} skills into $dest (auto-discovered)."
    ;;
  codex)  echo; echo "# codex — paste into ~/.codex/AGENTS.md (or your project AGENTS.md):"; echo; pointer;;
  cursor) echo; echo "# cursor — paste into your project .cursor/rules (or Settings > Rules):"; echo; pointer;;
  gemini) echo; echo "# gemini — paste into ~/.gemini/GEMINI.md:"; echo; pointer;;
  *) echo "unknown agent: $a (use claude|codex|cursor|gemini|all)" >&2;;
esac; done
