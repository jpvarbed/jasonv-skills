#!/usr/bin/env python3
"""Generate and validate skill-workshop completion manifests."""

import argparse
import json
import re
import sys
import uuid
from pathlib import Path


TOP_KEYS = {
    "schema_version",
    "work_unit",
    "tier",
    "bundles_code",
    "effort",
    "author_family",
    "artifacts",
    "evidence",
}
COMMON_ARTIFACTS = {
    "spec": "SPEC.md",
    "skill": "SKILL.md",
    "deviations": "DEVIATIONS.md",
}
COMMON_EVIDENCE = {
    "baseline": None,
    "behavioral": None,
    "forward_tests": [],
    "lint": None,
    "install": None,
    "councils": [],
}
COMMAND_KEYS = {"command", "exit_code", "receipt", "dry_run"}
FORWARD_KEYS = COMMAND_KEYS | {"family"}
INSTALL_KEYS = COMMAND_KEYS | {"targets"}
REPRESENTATIVE_KEYS = COMMAND_KEYS | {
    "observed_provider",
    "observed_model",
    "substituted",
}
COUNCIL_KEYS = {"phase", "profile", "families", "status", "receipt"}
LIVE_KEYS = {
    "provider",
    "model",
    "auth_kind",
    "device_config",
    "status",
    "failure_class",
    "recovery",
}
THERMOS_KEYS = {"security", "quality", "receipt"}
IDENTIFIER = re.compile(r"[a-z][a-z0-9-]*\Z")
PLACEHOLDER = re.compile(r"\$\{[A-Z][A-Z0-9_]*\}\Z")
TARGETS = ["claude", "codex", "cursor", "cline"]
FAILURE_CLASSES = {"none", "auth", "model", "capacity", "timeout", "adapter"}


def _write_json(value):
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def _exact_keys(value, expected, path, errors):
    if not isinstance(value, dict):
        errors.append(f"invalid: {path} must be an object")
        return False
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            errors.append(f"invalid: {path} missing keys: {', '.join(missing)}")
        if extra:
            errors.append(f"invalid: {path} extra keys: {', '.join(extra)}")
        return False
    return True


def _identifier(value):
    return isinstance(value, str) and IDENTIFIER.fullmatch(value) is not None


def _relative(value):
    if not isinstance(value, str) or not value:
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def _valid_command(value, keys, path, errors):
    if value is None:
        return
    if not _exact_keys(value, keys, path, errors):
        return
    if not isinstance(value["command"], str):
        errors.append(f"invalid: {path}.command must be a string")
    if not isinstance(value["exit_code"], int) or isinstance(value["exit_code"], bool):
        errors.append(f"invalid: {path}.exit_code must be an integer")
    if not _relative(value["receipt"]):
        errors.append(f"invalid: {path}.receipt must be a safe relative path")
    if not isinstance(value["dry_run"], bool):
        errors.append(f"invalid: {path}.dry_run must be boolean")


def _artifact_keys(tier, bundles_code):
    keys = set(COMMON_ARTIFACTS)
    if tier == "scripted" or (tier == "integration" and bundles_code):
        keys |= {"scripts", "tests"}
    if tier == "integration":
        keys |= {"config_example", "ignore_file"}
    return keys


def _evidence_keys(tier, bundles_code):
    keys = set(COMMON_EVIDENCE)
    if tier == "scripted" or (tier == "integration" and bundles_code):
        keys.add("repo_tests")
    if tier in {"scripted", "integration"}:
        keys.add("thermos")
    if tier == "integration":
        keys |= {"live", "smoke", "representative"}
    return keys


def structural_errors(value):
    errors = []
    if not _exact_keys(value, TOP_KEYS, "$", errors):
        return sorted(errors)
    if value["schema_version"] != 1:
        errors.append("invalid: schema_version must be 1")
    try:
        parsed = uuid.UUID(value["work_unit"])
        if parsed.version != 4 or str(parsed) != value["work_unit"]:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        errors.append("invalid: work_unit must be a lowercase UUIDv4")
    tier = value["tier"]
    if tier not in {"method", "scripted", "integration"}:
        errors.append("invalid: tier must be method, scripted, or integration")
        return sorted(errors)
    bundles = value["bundles_code"]
    if not isinstance(bundles, bool):
        errors.append("invalid: bundles_code must be boolean")
        return sorted(errors)
    if tier == "method" and bundles:
        errors.append("invalid: method requires bundles_code false")
    if tier == "scripted" and not bundles:
        errors.append("invalid: scripted requires bundles_code true")
    effort = value["effort"]
    if effort not in {"standard", "deep"}:
        errors.append("invalid: effort must be standard or deep")
    if tier in {"scripted", "integration"} and effort != "deep":
        errors.append(f"invalid: {tier} requires deep effort")
    if not _identifier(value["author_family"]):
        errors.append("invalid: author_family must match [a-z][a-z0-9-]*")

    artifact_keys = _artifact_keys(tier, bundles)
    if _exact_keys(value["artifacts"], artifact_keys, "artifacts", errors):
        for key, artifact in value["artifacts"].items():
            if key in {"scripts", "tests"}:
                if not isinstance(artifact, list) or any(not _relative(item) for item in artifact):
                    errors.append(f"invalid: artifacts.{key} must be safe relative paths")
            elif not _relative(artifact):
                errors.append(f"invalid: artifacts.{key} must be a safe relative path")

    evidence_keys = _evidence_keys(tier, bundles)
    evidence = value["evidence"]
    if not _exact_keys(evidence, evidence_keys, "evidence", errors):
        return sorted(errors)
    for key in ("baseline", "behavioral", "lint"):
        _valid_command(evidence[key], COMMAND_KEYS, f"evidence.{key}", errors)
    if not isinstance(evidence["forward_tests"], list):
        errors.append("invalid: evidence.forward_tests must be an array")
    else:
        for index, item in enumerate(evidence["forward_tests"]):
            path = f"evidence.forward_tests[{index}]"
            if item is None:
                errors.append(f"invalid: {path} must be an object")
                continue
            _valid_command(item, FORWARD_KEYS, path, errors)
            if isinstance(item, dict) and set(item) == FORWARD_KEYS and not _identifier(item["family"]):
                errors.append(f"invalid: {path}.family must match [a-z][a-z0-9-]*")
    _valid_command(evidence["install"], INSTALL_KEYS, "evidence.install", errors)
    if isinstance(evidence["install"], dict) and set(evidence["install"]) == INSTALL_KEYS:
        if evidence["install"]["targets"] != TARGETS:
            errors.append("invalid: evidence.install.targets must be claude,codex,cursor,cline")
    if not isinstance(evidence["councils"], list):
        errors.append("invalid: evidence.councils must be an array")
    else:
        for index, council in enumerate(evidence["councils"]):
            path = f"evidence.councils[{index}]"
            if not _exact_keys(council, COUNCIL_KEYS, path, errors):
                continue
            if council["phase"] not in {"spec", "final"}:
                errors.append(f"invalid: {path}.phase must be spec or final")
            if council["profile"] not in {"fast", "deep"}:
                errors.append(f"invalid: {path}.profile must be fast or deep")
            if council["status"] not in {"pass", "fail", "blocked"}:
                errors.append(f"invalid: {path}.status must be pass, fail, or blocked")
            if not isinstance(council["families"], list) or any(
                not _identifier(family) for family in council["families"]
            ):
                errors.append(f"invalid: {path}.families must be lowercase identifiers")
            if not _relative(council["receipt"]):
                errors.append(f"invalid: {path}.receipt must be a safe relative path")
    if "repo_tests" in evidence:
        _valid_command(evidence["repo_tests"], COMMAND_KEYS, "evidence.repo_tests", errors)
    if "thermos" in evidence and evidence["thermos"] is not None:
        thermos = evidence["thermos"]
        if _exact_keys(thermos, THERMOS_KEYS, "evidence.thermos", errors):
            if thermos["security"] not in {"pass", "fail"}:
                errors.append("invalid: evidence.thermos.security must be pass or fail")
            if thermos["quality"] not in {"pass", "fail"}:
                errors.append("invalid: evidence.thermos.quality must be pass or fail")
            if not _relative(thermos["receipt"]):
                errors.append("invalid: evidence.thermos.receipt must be a safe relative path")
    if tier == "integration":
        live = evidence["live"]
        if live is not None and _exact_keys(live, LIVE_KEYS, "evidence.live", errors):
            for key in ("provider", "model", "auth_kind"):
                if not isinstance(live[key], str) or not live[key]:
                    errors.append(f"invalid: evidence.live.{key} must be a non-empty string")
            if not _relative(live["device_config"]):
                errors.append("invalid: evidence.live.device_config must be a safe relative path")
            if live["status"] not in {"ready", "blocked"}:
                errors.append("invalid: evidence.live.status must be ready or blocked")
            if live["failure_class"] not in FAILURE_CLASSES:
                errors.append("invalid: evidence.live.failure_class is unknown")
            if live["recovery"] is not None and not isinstance(live["recovery"], str):
                errors.append("invalid: evidence.live.recovery must be string or null")
        _valid_command(evidence["smoke"], COMMAND_KEYS, "evidence.smoke", errors)
        _valid_command(
            evidence["representative"],
            REPRESENTATIVE_KEYS,
            "evidence.representative",
            errors,
        )
        representative = evidence["representative"]
        if isinstance(representative, dict) and set(representative) == REPRESENTATIVE_KEYS:
            if not isinstance(representative["observed_provider"], str):
                errors.append("invalid: evidence.representative.observed_provider must be a string")
            if not isinstance(representative["observed_model"], str):
                errors.append("invalid: evidence.representative.observed_model must be a string")
            if not isinstance(representative["substituted"], bool):
                errors.append("invalid: evidence.representative.substituted must be boolean")
    return sorted(errors)


def _safe_file(root, relative, label, errors):
    path = root / relative
    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            errors.append(f"incomplete: {label} must be a regular non-symlink file")
            return None
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root.resolve())
    except (FileNotFoundError, RuntimeError, ValueError):
        errors.append(f"incomplete: {label} must reference a file inside the receipt root")
        return None
    if path.is_symlink() or not resolved.is_file():
        errors.append(f"incomplete: {label} must be a regular non-symlink file")
        return None
    if resolved.stat().st_size == 0:
        errors.append(f"incomplete: {label} must not be an empty file")
        return None
    return resolved


def _check_command(root, value, label, errors):
    if value is None:
        errors.append(f"incomplete: {label} is missing")
        return
    if not value["command"].strip():
        errors.append(f"incomplete: {label}.command is empty")
    if value["exit_code"] != 0:
        errors.append(f"incomplete: {label}.exit_code is not zero")
    if value["dry_run"]:
        errors.append(f"incomplete: {label} is a dry run")
    _safe_file(root, value["receipt"], f"{label}.receipt", errors)


def _strings_are_placeholders(value):
    if isinstance(value, str):
        return value == "" or PLACEHOLDER.fullmatch(value) is not None
    if isinstance(value, list):
        return all(_strings_are_placeholders(item) for item in value)
    if isinstance(value, dict):
        return all(_strings_are_placeholders(item) for item in value.values())
    return value is None or isinstance(value, (bool, int, float))


def completeness_errors(value, receipt_path):
    errors = []
    root = receipt_path.parent.resolve()
    artifacts = value["artifacts"]
    for key, artifact in artifacts.items():
        paths = artifact if isinstance(artifact, list) else [artifact]
        if key in {"scripts", "tests"} and not paths:
            errors.append(f"incomplete: artifacts.{key} must not be empty")
        for index, relative in enumerate(paths):
            label = f"artifacts.{key}" if len(paths) == 1 else f"artifacts.{key}[{index}]"
            _safe_file(root, relative, label, errors)

    evidence = value["evidence"]
    for key in ("baseline", "behavioral", "lint"):
        _check_command(root, evidence[key], f"evidence.{key}", errors)
    base, behavioral = evidence["baseline"], evidence["behavioral"]
    if isinstance(base, dict) and isinstance(behavioral, dict):
        if base.get("receipt") == behavioral.get("receipt"):
            errors.append("incomplete: baseline and behavioral receipts must differ")
    forwards = evidence["forward_tests"]
    if len(forwards) != 2:
        errors.append("incomplete: forward_tests must contain exactly two records")
    else:
        for index, forward in enumerate(forwards):
            _check_command(root, forward, f"evidence.forward_tests[{index}]", errors)
        if len({forward["family"] for forward in forwards}) != 2:
            errors.append("incomplete: forward_tests must use distinct families")
        if len({forward["receipt"] for forward in forwards}) != 2:
            errors.append("incomplete: forward_tests must use distinct receipts")
    _check_command(root, evidence["install"], "evidence.install", errors)
    if "repo_tests" in evidence:
        _check_command(root, evidence["repo_tests"], "evidence.repo_tests", errors)

    expected_profile = "deep" if value["effort"] == "deep" else "fast"
    expected_councils = {("spec", "fast"), ("final", expected_profile)}
    if len(evidence["councils"]) != 2:
        errors.append("incomplete: councils must contain exactly two records")
    actual_councils = {(item["phase"], item["profile"]) for item in evidence["councils"]}
    for phase, profile in sorted(expected_councils - actual_councils):
        errors.append(f"incomplete: council {phase}/{profile} is missing")
    for index, council in enumerate(evidence["councils"]):
        label = f"evidence.councils[{index}]"
        _safe_file(root, council["receipt"], f"{label}.receipt", errors)
        if council["status"] != "pass":
            errors.append(f"incomplete: {label} is {council['status']}")
        if len(set(council["families"])) < 2:
            errors.append(f"incomplete: {label} requires two distinct families")

    if "thermos" in evidence:
        thermos = evidence["thermos"]
        if thermos is None:
            errors.append("incomplete: evidence.thermos is missing")
        else:
            if thermos["security"] != "pass" or thermos["quality"] != "pass":
                errors.append("incomplete: Thermos security and quality must pass")
            _safe_file(root, thermos["receipt"], "evidence.thermos.receipt", errors)

    if value["tier"] == "integration":
        live = evidence["live"]
        smoke = evidence["smoke"]
        representative = evidence["representative"]
        if live is None:
            errors.append("incomplete: evidence.live is missing")
        else:
            if live["status"] == "ready":
                if live["failure_class"] != "none" or live["recovery"] is not None:
                    errors.append("incomplete: ready live state requires none failure and null recovery")
            elif live["failure_class"] == "none" or not live["recovery"]:
                errors.append("incomplete: blocked live state requires failure class and recovery")
            if live["status"] != "ready":
                errors.append("incomplete: live integration is blocked")
            ignore_path = _safe_file(root, artifacts["ignore_file"], "artifacts.ignore_file", errors)
            if ignore_path is not None:
                device_config = Path(live["device_config"]).as_posix()
                try:
                    ignore_text = ignore_path.read_text()
                except OSError:
                    errors.append("incomplete: ignore file could not be read")
                    ignore_text = ""
                rules = [line.strip() for line in ignore_text.splitlines()]
                if device_config not in rules:
                    errors.append("incomplete: ignore file needs exact positive device-config rule")
                if f"!{device_config}" in rules:
                    errors.append("incomplete: exact device-config rule must not be negated")
        _check_command(root, smoke, "evidence.smoke", errors)
        _check_command(root, representative, "evidence.representative", errors)
        if smoke is not None and representative is not None:
            if smoke["command"] == representative["command"]:
                errors.append("incomplete: smoke and representative commands must differ")
            if smoke["receipt"] == representative["receipt"]:
                errors.append("incomplete: smoke and representative receipts must differ")
        if live is not None and representative is not None:
            if representative["substituted"]:
                errors.append("incomplete: representative operation was substituted")
            if representative["observed_provider"] != live["provider"]:
                errors.append("incomplete: observed provider does not match declared provider")
            if representative["observed_model"] != live["model"]:
                errors.append("incomplete: observed model does not match declared model")
        config_path = _safe_file(root, artifacts["config_example"], "artifacts.config_example", errors)
        if config_path is not None:
            try:
                config = json.loads(config_path.read_text())
            except (json.JSONDecodeError, OSError):
                errors.append("incomplete: config example must be valid JSON")
            else:
                if not _strings_are_placeholders(config):
                    errors.append("incomplete: config strings must be empty or ${PLACEHOLDER}")

    seen = set()
    for record, label in _receipt_bearing_records(evidence):
        if not isinstance(record, dict):
            continue
        receipt = record.get("receipt")
        if not isinstance(receipt, str):
            continue
        if receipt in seen:
            errors.append(f"incomplete: {label} reuses a receipt already used by another gate")
        seen.add(receipt)
    return sorted(set(errors))


def _receipt_bearing_records(evidence):
    for key in ("baseline", "behavioral", "lint", "install", "repo_tests", "smoke", "representative"):
        if key in evidence and evidence[key] is not None:
            yield evidence[key], f"evidence.{key}"
    for index, item in enumerate(evidence.get("forward_tests") or []):
        yield item, f"evidence.forward_tests[{index}]"
    for index, item in enumerate(evidence.get("councils") or []):
        yield item, f"evidence.councils[{index}]"
    if evidence.get("thermos") is not None:
        yield evidence["thermos"], "evidence.thermos"


def make_manifest(arguments):
    tier = arguments.tier
    if tier == "method":
        if arguments.bundles_code not in (None, False):
            raise ValueError("method requires --bundles-code false")
        bundles = False
        effort = arguments.effort or "standard"
    elif tier == "scripted":
        if arguments.bundles_code not in (None, True):
            raise ValueError("scripted requires --bundles-code true")
        bundles = True
        effort = arguments.effort or "deep"
    else:
        if arguments.bundles_code is None:
            raise ValueError("integration requires --bundles-code true or false")
        bundles = arguments.bundles_code
        effort = arguments.effort or "deep"
    artifacts = dict(COMMON_ARTIFACTS)
    if tier == "scripted" or (tier == "integration" and bundles):
        artifacts.update({"scripts": [], "tests": []})
    if tier == "integration":
        artifacts.update(
            {"config_example": "config.example.json", "ignore_file": ".gitignore"}
        )
    evidence = {key: ([] if isinstance(value, list) else value) for key, value in COMMON_EVIDENCE.items()}
    if tier == "scripted" or (tier == "integration" and bundles):
        evidence["repo_tests"] = None
    if tier in {"scripted", "integration"}:
        evidence["thermos"] = None
    if tier == "integration":
        evidence.update({"live": None, "smoke": None, "representative": None})
    return {
        "schema_version": 1,
        "work_unit": arguments.work_unit,
        "tier": tier,
        "bundles_code": bundles,
        "effort": effort,
        "author_family": arguments.author_family,
        "artifacts": artifacts,
        "evidence": evidence,
    }


def parse_bool(value):
    if value == "true":
        return True
    if value == "false":
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def init_command(arguments):
    output = Path(arguments.output)
    if output.exists() or output.is_symlink():
        print(f"refusing to overwrite {output}", file=sys.stderr)
        return 2
    try:
        manifest = make_manifest(arguments)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    errors = structural_errors(manifest)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return 0


def check_command(arguments):
    receipt = Path(arguments.receipt)
    try:
        value = json.loads(receipt.read_text())
    except (OSError, json.JSONDecodeError) as error:
        _write_json({"errors": [f"invalid: {error}"], "status": "invalid"})
        return 2
    errors = structural_errors(value)
    if errors:
        _write_json({"errors": errors, "status": "invalid"})
        return 2
    errors = completeness_errors(value, receipt)
    if errors:
        _write_json({"errors": errors, "status": "incomplete"})
        return 1
    _write_json(
        {"status": "complete", "tier": value["tier"], "work_unit": value["work_unit"]}
    )
    return 0


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--tier", choices=("method", "scripted", "integration"), required=True)
    init.add_argument("--bundles-code", type=parse_bool)
    init.add_argument("--work-unit", required=True)
    init.add_argument("--author-family", required=True)
    init.add_argument("--effort", choices=("standard", "deep"))
    init.add_argument("--output", required=True)
    init.set_defaults(handler=init_command)
    check = commands.add_parser("check")
    check.add_argument("receipt")
    check.set_defaults(handler=check_command)
    return root


def main():
    arguments = parser().parse_args()
    return arguments.handler(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
