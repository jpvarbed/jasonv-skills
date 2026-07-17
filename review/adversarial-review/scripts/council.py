#!/usr/bin/env python3
"""Validate, smoke, and run the adversarial-review council."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from council_runtime import review, smoke_all
from council_state import (
    ConfigError,
    RequestError,
    load_config,
    observation_output,
    review_qualified,
    setup_available,
)


def parser() -> argparse.ArgumentParser:
    default_config = Path(__file__).resolve().parents[1] / "council-config.json"
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--config", type=Path, default=default_config)
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("validate")

    smoke = commands.add_parser("smoke")
    smoke.add_argument("--profile", choices=("fast", "deep"), default="fast")
    smoke.add_argument("--all", action="store_true")

    council = commands.add_parser("review")
    council.add_argument("--profile", choices=("fast", "deep"), default="fast")
    council.add_argument("--objective", required=True)
    council.add_argument("--focus", default="")
    council.add_argument("--resolved", default="")
    council.add_argument("--evidence", default="")
    council.add_argument("--artifact", action="append", required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        config = load_config(arguments.config)
        if arguments.command == "validate":
            result = {
                "status": "valid",
                "config": str(arguments.config),
                "seats": [seat["id"] for seat in config["seats"]],
                "seat_status": [
                    {
                        "seat": seat["id"],
                        "adapter": seat["adapter"],
                        "model": seat["model"],
                        "review_qualified": review_qualified(seat),
                        "smoke": observation_output(
                            seat, "smoke", seat["observed"]["smoke"]
                        ),
                        "review": observation_output(
                            seat, "review", seat["observed"]["review"]
                        ),
                    }
                    for seat in config["seats"]
                ],
                "profiles": config["profiles"],
                "setup_available": setup_available(config),
            }
            code = 0
        elif arguments.command == "smoke":
            result = smoke_all(
                config,
                arguments.config,
                profile=arguments.profile,
                all_seats=arguments.all,
            )
            code = 0 if result["status"] == "ready" else 2
        else:
            result, code = review(
                config,
                arguments.config,
                arguments.profile,
                arguments.objective,
                arguments.focus,
                arguments.resolved,
                arguments.evidence,
                arguments.artifact,
            )
    except ConfigError as exc:
        result = {"council_status": "SETUP REQUIRED", "error": str(exc)}
        code = 2
    except RequestError as exc:
        result = {"council_status": "INVALID REQUEST", "error": str(exc)}
        code = 4
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
