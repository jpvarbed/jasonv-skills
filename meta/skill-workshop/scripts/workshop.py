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


FAILURE_SIGNATURES = ("Traceback (most recent call last)", "exit=1", '"exit_code": 1')


def _receipt_text(root, relative):
    if not isinstance(relative, str):
        return ""
    try:
        return (root / relative).read_text()
    except OSError:
        return ""


def content_errors(value, receipt_path):
    """Catch honest drift: does the OUTPUT actually back the GRADE the manifest claims?

    Exact-string, format-tolerant checks only. A determined forger who edits the
    receipt text is caught by the independent council reading it, not here.
    """
    errors = []
    root = receipt_path.parent.resolve()
    ev = value["evidence"]

    # Grounding: the identities the manifest asserts must literally appear in the receipt.
    representative = ev.get("representative")
    if isinstance(representative, dict) and isinstance(representative.get("receipt"), str):
        text = _receipt_text(root, representative["receipt"])
        for key in ("observed_provider", "observed_model"):
            claimed = representative.get(key)
            if isinstance(claimed, str) and claimed and claimed not in text:
                errors.append(f"incomplete: representative receipt never mentions {key} '{claimed}'")
    install = ev.get("install")
    if isinstance(install, dict) and isinstance(install.get("receipt"), str):
        text = _receipt_text(root, install["receipt"])
        for target in install.get("targets") or []:
            if isinstance(target, str) and target not in text:
                errors.append(f"incomplete: install receipt never mentions target '{target}'")

    # No contradiction: a pass-graded command receipt must not contain a failure signature.
    graded_pass = []
    for key in ("baseline", "behavioral", "lint", "install", "repo_tests", "smoke", "representative"):
        record = ev.get(key)
        if isinstance(record, dict) and record.get("exit_code") == 0:
            graded_pass.append((f"evidence.{key}", record.get("receipt")))
    for index, forward in enumerate(ev.get("forward_tests") or []):
        if isinstance(forward, dict) and forward.get("exit_code") == 0:
            graded_pass.append((f"evidence.forward_tests[{index}]", forward.get("receipt")))
    for label, relative in graded_pass:
        text = _receipt_text(root, relative)
        for signature in FAILURE_SIGNATURES:
            if signature in text:
                errors.append(
                    f"incomplete: {label} is graded pass but its receipt contains a failure signature: {signature!r}"
                )
    return sorted(set(errors))


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
    if not errors:
        errors = content_errors(value, receipt)
    if errors:
        _write_json({"errors": errors, "status": "incomplete"})
        return 1
    _write_json(
        {"status": "complete", "tier": value["tier"], "work_unit": value["work_unit"]}
    )
    return 0


def _excerpt(root, receipt, max_lines=40):
    if not isinstance(receipt, str):
        return None, "no receipt path recorded"
    path = root / receipt
    try:
        text = path.read_text()
    except OSError:
        return None, f"receipt not readable: {receipt}"
    lines = text.splitlines()
    body = "\n".join(lines[:max_lines])
    if len(lines) > max_lines:
        body += f"\n… (+{len(lines) - max_lines} more lines in {receipt})"
    return body, None


def report_sections(value):
    """Yield (title, facts, receipt) for every gate, in reading order."""
    ev = value["evidence"]
    labels = {
        "baseline": "Baseline eval (no skill)",
        "behavioral": "Behavioral eval (with skill)",
        "representative": "Representative live operation",
        "smoke": "Smoke / identity",
        "lint": "Static lint",
        "install": "Install across targets",
        "repo_tests": "Repository tests",
    }
    for key, title in labels.items():
        record = ev.get(key)
        if record is None:
            continue
        facts = {k: v for k, v in record.items() if k != "receipt"}
        yield title, facts, record.get("receipt")
    for index, forward in enumerate(ev.get("forward_tests") or []):
        if not isinstance(forward, dict):
            continue
        facts = {k: v for k, v in forward.items() if k != "receipt"}
        yield f"Blind forward-test #{index + 1} ({forward.get('family', '?')})", facts, forward.get("receipt")
    for council in ev.get("councils") or []:
        if not isinstance(council, dict):
            continue
        facts = {k: v for k, v in council.items() if k != "receipt"}
        yield f"Council: {council.get('phase', '?')}/{council.get('profile', '?')}", facts, council.get("receipt")
    if ev.get("thermos") is not None:
        facts = {k: v for k, v in ev["thermos"].items() if k != "receipt"}
        yield "Thermos (security + quality)", facts, ev["thermos"].get("receipt")
    if value["tier"] == "integration" and ev.get("live") is not None:
        yield "Live seat qualification", dict(ev["live"]), None


def _grade_line(facts):
    """Derive the pass GRADE from a record's own fields."""
    if "status" in facts:  # councils, live
        return facts["status"].upper()
    if "security" in facts and "quality" in facts:  # thermos
        return f"security={facts['security']} quality={facts['quality']}"
    if "exit_code" in facts:  # command records
        return "PASS (exit 0)" if facts["exit_code"] == 0 else f"FAIL (exit {facts['exit_code']})"
    return "—"


def _input_line(title, facts):
    if "command" in facts:
        return facts["command"]
    if "families" in facts:
        return f"cross-family review, seats: {', '.join(facts['families'])}"
    if "provider" in facts:
        return f"seat {facts.get('provider')}/{facts.get('model')}"
    return title


def render_report_markdown(value, root, verdict):
    out = [
        f"# skill-workshop completion report — `{value['work_unit']}`",
        "",
        f"**Checker verdict:** `{verdict['status']}`  ·  "
        f"tier `{value['tier']}`  ·  effort `{value['effort']}`  ·  "
        f"author family `{value['author_family']}`",
        "",
    ]
    if verdict.get("errors"):
        out += ["**Open gates:**", ""] + [f"- {e}" for e in verdict["errors"]] + [""]
    out += ["> Read each receipt excerpt below to confirm the claim is real. The checker proves",
            "> the receipts exist, are non-empty, and are distinct; only this read confirms truth.",
            "", "---", ""]
    for title, facts, receipt in report_sections(value):
        out.append(f"## {title}")
        out.append("")
        out.append(f"- **INPUT:** `{_input_line(title, facts)}`")
        if receipt is not None:
            body, err = _excerpt(root, receipt)
            if err:
                out.append(f"- **OUTPUT:** ⚠️ {err}")
            else:
                out.append(f"- **OUTPUT:** <details><summary>receipt: <code>{receipt}</code></summary>")
                out.append("")
                out.append("```")
                out.append(body)
                out.append("```")
                out.append("</details>")
        else:
            out.append("- **OUTPUT:** _(declared fields only — no receipt file)_")
        out.append(f"- **GRADE:** {_grade_line(facts)}")
        out.append("")
    return "\n".join(out) + "\n"


def _html_escape(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def render_report_html(value, root, verdict):
    status = verdict["status"]
    colour = {"complete": "#1a7f37", "incomplete": "#9a6700", "invalid": "#cf222e"}.get(status, "#57606a")
    parts = [
        "<!doctype html><meta charset='utf-8'>",
        "<title>skill-workshop report</title>",
        "<style>body{font:15px/1.5 -apple-system,system-ui,sans-serif;max-width:900px;"
        "margin:2rem auto;padding:0 1rem;color:#1f2328}h1{font-size:1.5rem}"
        "code{background:#f6f8fa;padding:.1em .3em;border-radius:4px}"
        f".verdict{{display:inline-block;background:{colour};color:#fff;padding:.2em .6em;"
        "border-radius:6px;font-weight:600}details{margin:.4rem 0}"
        "pre{background:#f6f8fa;padding:.8rem;border-radius:6px;overflow:auto;font-size:13px}"
        "section{border-top:1px solid #d0d7de;padding:.6rem 0}li{margin:.1rem 0}</style>",
        f"<h1>skill-workshop completion report</h1>",
        f"<p><span class='verdict'>{_html_escape(status)}</span> &nbsp; tier "
        f"<code>{_html_escape(value['tier'])}</code> · effort <code>{_html_escape(value['effort'])}</code> "
        f"· work unit <code>{_html_escape(value['work_unit'])}</code></p>",
    ]
    if verdict.get("errors"):
        parts.append("<p><b>Open gates:</b></p><ul>"
                     + "".join(f"<li>{_html_escape(e)}</li>" for e in verdict["errors"]) + "</ul>")
    parts.append("<p><em>Read each receipt to confirm the claim is real — the checker proves "
                 "receipts exist and are distinct, not that their contents are true.</em></p>")
    for title, facts, receipt in report_sections(value):
        parts.append(f"<section><h2>{_html_escape(title)}</h2>")
        parts.append(f"<p><b>INPUT:</b> <code>{_html_escape(_input_line(title, facts))}</code></p>")
        if receipt is not None:
            body, err = _excerpt(root, receipt, max_lines=200)
            if err:
                parts.append(f"<p><b>OUTPUT:</b> ⚠️ {_html_escape(err)}</p>")
            else:
                parts.append(f"<p><b>OUTPUT:</b></p><details><summary>receipt: "
                             f"<code>{_html_escape(receipt)}</code></summary>"
                             f"<pre>{_html_escape(body)}</pre></details>")
        else:
            parts.append("<p><b>OUTPUT:</b> <em>declared fields only — no receipt file</em></p>")
        parts.append(f"<p><b>GRADE:</b> <code>{_html_escape(_grade_line(facts))}</code></p>")
        parts.append("</section>")
    return "".join(parts) + "\n"


def report_command(arguments):
    receipt = Path(arguments.receipt)
    try:
        value = json.loads(receipt.read_text())
    except (OSError, json.JSONDecodeError) as error:
        print(f"invalid: {error}", file=sys.stderr)
        return 2
    errors = structural_errors(value)
    if errors:
        print("invalid receipt; run check first", file=sys.stderr)
        return 2
    completeness = completeness_errors(value, receipt)
    verdict = {"status": "complete" if not completeness else "incomplete", "errors": completeness}
    root = receipt.parent.resolve()
    if arguments.format == "html":
        text = render_report_html(value, root, verdict)
    else:
        text = render_report_markdown(value, root, verdict)
    Path(arguments.output).write_text(text)
    print(f"wrote {arguments.output} ({verdict['status']})")
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
    report = commands.add_parser("report")
    report.add_argument("receipt")
    report.add_argument("--format", choices=("md", "html"), default="md")
    report.add_argument("--output", "-o", required=True)
    report.set_defaults(handler=report_command)
    return root


def main():
    arguments = parser().parse_args()
    return arguments.handler(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
