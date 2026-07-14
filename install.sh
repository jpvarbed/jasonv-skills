#!/usr/bin/env bash
# Install jasonv-skills for one or more agents:  ./install.sh [claude|codex|cursor|all]
# Each agent reads a native per-skill dir; we symlink each skill into it. Override any dir with
# CLAUDE_SKILLS_DIR / CODEX_SKILLS_DIR / CURSOR_SKILLS_DIR.
# Safe & idempotent: we only ever create, refresh, or prune symlinks that point back into THIS
# repo. A name you already own (a real dir, or a link pointing elsewhere) is left untouched.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
skills=(); for d in "$here"/*/*/; do [ -f "$d/SKILL.md" ] && skills+=("${d%/}"); done
[ ${#skills[@]} -gt 0 ] || { echo "no skills found under $here" >&2; exit 1; }

# refuse to install if two skills share a folder name (they'd collide in a flat dest)
dupes="$(for d in "${skills[@]}"; do basename "$d"; done | sort | uniq -d)"
[ -z "$dupes" ] || { printf 'duplicate skill names, refusing to install:\n%s\n' "$dupes" >&2; exit 1; }
names=" "; for d in "${skills[@]}"; do names+="$(basename "$d") "; done   # space-delimited for the prune membership test

agents=("$@"); [ ${#agents[@]} -eq 0 ] && agents=(all)
case " ${agents[*]} " in *" all "*) agents=(claude codex cursor);; esac

ours() { case "$(readlink "$1" 2>/dev/null)" in "$here"/*) return 0;; *) return 1;; esac; }

link_into() { # dest label
  local dest="$1" label="$2" n=0 skipped=0 pruned=0 name tgt
  mkdir -p "$dest"
  for d in "${skills[@]}"; do
    name="$(basename "$d")"; tgt="$dest/$name"
    if { [ -e "$tgt" ] || [ -L "$tgt" ]; } && ! { [ -L "$tgt" ] && ours "$tgt"; }; then
      echo "  skip $name — you already have $tgt"; skipped=$((skipped + 1)); continue
    fi
    ln -sfn "$d" "$tgt"; n=$((n + 1))
  done
  for l in "$dest"/*; do                      # prune OUR stale links (skill removed from repo)
    [ -L "$l" ] && ours "$l" || continue
    case "$names" in *" $(basename "$l") "*) ;; *) rm -f "$l"; pruned=$((pruned + 1));; esac
  done
  echo "$label: linked/updated $n · skipped $skipped · pruned $pruned → $dest"
}

for a in "${agents[@]}"; do case "$a" in
  claude) link_into "${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}" claude;;
  codex)  link_into "${CODEX_SKILLS_DIR:-$HOME/.codex/skills}"  codex;;
  cursor) link_into "${CURSOR_SKILLS_DIR:-$HOME/.cursor/skills}" cursor;;
  *) echo "unknown agent: $a (use claude|codex|cursor|all)" >&2; exit 2;;
esac; done
