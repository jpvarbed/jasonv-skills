#!/usr/bin/env python3
"""Eval-only adapter: run the goal-to-done arena fixture through the existing
skill-arena library without modifying its source tree.

This script validates the skill's delivery. It is never part of the
operational goal-to-done workflow and must not be wired into it.
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "arena" / "goal-to-done"
SKILL_DIR = HERE.parent
DIGEST_FILE = FIXTURE / "input.sha256"

# Codex/OpenAI and Claude/Anthropic only — registered in DESIGN.md.
ALLOWED_BACKENDS = {"codex", "openai", "claude-cli", "anthropic", "opus", "sonnet", "haiku"}

# Live gate registered in DESIGN.md: per configured cell on the with-skill
# variant — zero backend errors, every case executed, pass rate >= 0.80.
LIVE_VARIANT = "with-skill"
LIVE_PASS_RATE = 0.80

# The freeze covers the tested behavior (SKILL/SPEC), the fixture, AND the gate
# logic + contract tests, so adapter or threshold drift also forces a re-freeze
# and a live re-run — the recorded receipt otherwise stops proving the delivery.
SKILL_DIR_FILES = {"SKILL.md", "SPEC.md"}
EVAL_FILES = {"run_arena.py": SKILL_DIR / "evals" / "run_arena.py",
              "test_goal_to_done.py": SKILL_DIR / "tests" / "test_goal_to_done.py"}
INPUT_FILES = ("SKILL.md", "SPEC.md", "DESIGN.md", "config.json", "cases.jsonl",
               "run_arena.py", "test_goal_to_done.py")


def input_digest() -> str:
    """Deterministic SHA-256 over the tested SKILL.md/SPEC.md, the fixture, and
    the eval adapter + contract tests — any of them changing forces a re-freeze."""
    h = hashlib.sha256()
    for name in INPUT_FILES:
        if name in SKILL_DIR_FILES:
            path = SKILL_DIR / name
        elif name in EVAL_FILES:
            path = EVAL_FILES[name]
        else:
            path = FIXTURE / name
        h.update(name.encode("utf-8"))
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def default_arena_root() -> str:
    return os.environ.get("SKILL_ARENA_ROOT", str(Path.home() / "dev" / "skill-arena"))


def check_thresholds(results: dict, dry_run: bool, case_count: int) -> list:
    failures = []
    skill_result = results.get("skills", {}).get("goal-to-done", {})
    cells = skill_result.get("cells", [])
    if not cells:
        return ["no cells were produced"]
    for cell in cells:
        label = f"{cell.get('backend')}/{cell.get('prompt_variant')}"
        if dry_run:
            if cell.get("passes") != cell.get("n") or cell.get("n") != case_count:
                failures.append(f"dry-run cell {label}: {cell.get('passes')}/{cell.get('n')} of {case_count}")
            continue
        if cell.get("prompt_variant") != LIVE_VARIANT:
            continue
        if cell.get("errors", 0) != 0:
            failures.append(f"live cell {label}: {cell.get('errors')} backend error(s)")
        if cell.get("n") != case_count:
            failures.append(f"live cell {label}: executed {cell.get('n')} of {case_count} cases")
        if cell.get("pass_rate", 0.0) < LIVE_PASS_RATE:
            failures.append(f"live cell {label}: pass rate {cell.get('pass_rate')} < {LIVE_PASS_RATE}")
    return failures


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backends", default="openai,anthropic",
                        help="comma-separated backend names (Codex/OpenAI and Claude/Anthropic only); "
                             "default matches the models registered in config.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate scorer wiring offline; no backend is called")
    parser.add_argument("--out-dir", required=True,
                        help="directory for results.json, leaderboard.html, and the run receipt")
    parser.add_argument("--arena-root", default=default_arena_root(),
                        help="skill-arena checkout (or set SKILL_ARENA_ROOT)")
    args = parser.parse_args(argv)

    backends = [b.strip() for b in args.backends.split(",") if b.strip()]
    disallowed = sorted(set(backends) - ALLOWED_BACKENDS)
    if not backends or disallowed:
        parser.error(f"backends must be a non-empty subset of {sorted(ALLOWED_BACKENDS)}; got {backends}")

    arena_root = Path(args.arena_root).expanduser()
    if not (arena_root / "arena.py").is_file():
        parser.error(f"skill-arena not found at {arena_root}")
    sys.path.insert(0, str(arena_root))
    import arena  # noqa: E402  (library import, source tree untouched)

    digest = input_digest()
    recorded = DIGEST_FILE.read_text().strip() if DIGEST_FILE.is_file() else None
    if not args.dry_run and digest != recorded:
        print(f"error: input digest {digest} does not match frozen {DIGEST_FILE.name} "
              f"({recorded}); freeze the skill and fixture bytes before a live run", file=sys.stderr)
        return 2

    config = json.loads((FIXTURE / "config.json").read_text())
    skill = arena.Skill(name=config["name"], directory=FIXTURE, config=config)
    cases = arena.load_cases(skill)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # arena.run() resolves skills by name inside its own skills/ tree, so this
    # external fixture drives run_cell() and the reporters directly instead.
    from datetime import datetime, timezone
    from report import print_comparison, write_leaderboard  # noqa: E402
    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "skills": {},
    }
    cells = []
    for variant in config.get("prompt_variants", []):
        for backend in backends:
            cells.append(arena.run_cell(skill, cases, variant, backend, dry_run=args.dry_run))
    results["skills"][skill.name] = {
        "cases_path": config.get("cases_path", "cases.jsonl"),
        "scorer": config.get("scorer", {}),
        "case_count": len(cases),
        "cells": cells,
    }
    (out_dir / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print_comparison(results)
    write_leaderboard(results, out_dir / "leaderboard.html")

    failures = check_thresholds(results, args.dry_run, len(cases))
    receipt = {
        "input_sha256": digest,
        "frozen_digest_matched": digest == recorded,
        "dry_run": args.dry_run,
        "backends": backends,
        "case_count": len(cases),
        "registered_gate": {"variant": LIVE_VARIANT, "min_pass_rate": LIVE_PASS_RATE, "max_errors": 0},
        "gate_failures": failures,
    }
    (out_dir / "run-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    if failures:
        for failure in failures:
            print(f"GATE FAIL: {failure}", file=sys.stderr)
        return 1
    print(f"arena gate PASS ({'dry-run' if args.dry_run else 'live'}); input sha256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
