"""Bounded process orchestration for the adversarial-review council."""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import signal
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from council_adapters import ReceiptError, adapter_for
from council_state import (
    ConfigError,
    PersonaError,
    PROFILE_PERSONAS,
    RequestError,
    atomic_write_json,
    now_utc,
    observed,
    observation_output,
    persist_observed,
    review_qualified,
)


PROFILE_MAX_PROMPT_BYTES = {"fast": 16 * 1024, "deep": 24 * 1024}
PROFILE_MAX_FINDINGS = {"fast": 1, "deep": 3}
PROFILE_EFFORT = {"fast": "low", "deep": "medium"}
PROFILE_REVIEW_TIMEOUT_SECONDS = {"fast": 60, "deep": 90}
PROFILE_SMOKE_TIMEOUT_SECONDS = {"fast": 20, "deep": 30}
SMOKE_EXPECTED = "VERDICT: PASS"
SMOKE_PROMPT = f"Return exactly this single line and do not use tools: {SMOKE_EXPECTED}"
PERSONA_LENSES = {
    "Architect": "soundness, hidden assumptions, integration, and failure modes",
    "Pragmatist": "simplicity, YAGNI, cost, sequencing, and scope discipline",
    "Verifier": "testability, acceptance criteria, blast radius, and reward hacking",
    "Adversary": "concrete defects, edge cases, unsafe assumptions, and implementability",
}
FAILURE_PRIORITY = {
    "none": 0,
    "timeout": 10,
    "capacity": 20,
    "invalid_output": 30,
    "trust": 40,
    "model": 50,
    "auth": 60,
    "cli_missing": 70,
    "adapter_error": 80,
}
SECRET_RES = (
    re.compile(r"\b(?:sk|key|token|secret)[-_][A-Za-z0-9_-]{16,}\b", re.I),
    re.compile(r"\b[A-Za-z0-9+/]{32,}={0,2}\b"),
)


PERSONA_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "persona": {"type": "string"},
        "engine": {"type": "string"},
        "model": {"type": "string"},
        "verdict": {"type": "string", "enum": ["PASS", "CONCERNS", "FAIL"]},
        "findings": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "severity": {"type": "string", "enum": ["H", "M", "L"]},
                    "claim": {"type": "string"},
                    "evidence": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "artifact": {"type": "string"},
                            "line": {"type": "integer", "minimum": 1},
                        },
                        "required": ["artifact", "line"],
                    },
                    "why": {"type": "string"},
                    "fix": {"type": "string"},
                },
                "required": ["severity", "claim", "evidence", "why", "fix"],
            },
        },
        "biggest_risk": {"type": "string"},
    },
    "required": [
        "persona",
        "engine",
        "model",
        "verdict",
        "findings",
        "biggest_risk",
    ],
}


def persona_output_schema(max_findings: int) -> str:
    value = json.loads(json.dumps(PERSONA_SCHEMA))
    value["properties"]["findings"]["maxItems"] = max_findings
    return json.dumps(
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {"output": value},
            "required": ["output"],
        },
        separators=(",", ":"),
    )


def smoke_output_schema() -> str:
    return json.dumps(
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "output": {"type": "string", "const": SMOKE_EXPECTED}
            },
            "required": ["output"],
        },
        separators=(",", ":"),
    )


def _scrub(
    text: str,
    seat: dict[str, Any],
    environment: dict[str, str] | None = None,
) -> str:
    cleaned = str(text)
    environment = environment or {}
    for name in seat["auth"]["required_environment"]:
        value = environment.get(name) or os.environ.get(name)
        if value:
            cleaned = cleaned.replace(value, "[REDACTED]")
    for pattern in SECRET_RES:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    return cleaned[:4000]


def _environment(seat: dict[str, Any]) -> dict[str, str]:
    environment = dict(os.environ)
    contract = adapter_for(seat)
    for name in contract.unset_environment | set(seat["auth"]["unset_environment"]):
        environment.pop(name, None)
    missing = [
        name
        for name in seat["auth"]["required_environment"]
        if not environment.get(name)
    ]
    if missing:
        raise RuntimeError(f"missing required environment: {', '.join(missing)}")
    return environment


def _failure_status(failure: str) -> str:
    return "temporarily_unavailable" if failure in {"capacity", "timeout"} else "setup_required"


def _safe_command(argv: list[str], prompt: str, output_schema: str) -> list[str]:
    return [
        "<schema>" if argument == output_schema else "<prompt>" if argument == prompt else argument
        for argument in argv
    ]


def _run_bounded(
    argv: list[str],
    *,
    timeout: int,
    environment: dict[str, str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
        cwd=cwd,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
        raise subprocess.TimeoutExpired(
            argv, timeout, output=stdout or exc.output, stderr=stderr or exc.stderr
        ) from exc
    return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)


def _probe_version(
    executable: str, environment: dict[str, str], workspace: Path
) -> str:
    try:
        process = _run_bounded(
            [executable, "--version"],
            timeout=10,
            environment=environment,
            cwd=workspace,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    output = (process.stdout or process.stderr).strip().splitlines()
    return output[0][:200] if process.returncode == 0 and output else "unavailable"


def _invoke(
    seat: dict[str, Any],
    *,
    kind: str,
    profile: str,
    prompt: str,
    output_schema: str,
) -> dict[str, Any]:
    contract = adapter_for(seat)
    configured = Path(seat["executable"])
    executable = str(configured) if configured.is_file() and os.access(configured, os.X_OK) else None
    if executable is None:
        state = observed(
            "setup_required",
            "cli_missing",
            seat=seat,
            error="configured executable is missing or not executable",
            operation=kind,
        )
        return {"status": "failed", "error": state["last_error"], "seat_observed": state}
    environment: dict[str, str] | None = None
    timeout_seconds = (
        PROFILE_SMOKE_TIMEOUT_SECONDS[profile]
        if kind == "smoke"
        else PROFILE_REVIEW_TIMEOUT_SECONDS[profile]
    )
    requested_effort = "low" if kind == "smoke" else PROFILE_EFFORT[profile]
    effective_effort = contract.effective_effort(seat["model"], requested_effort)
    argv: list[str] = []
    try:
        environment = _environment(seat)
        with tempfile.TemporaryDirectory(prefix=f"adversarial-review-{kind}-") as isolated:
            workspace = Path(isolated)
            (workspace / ".cline-hooks").mkdir(mode=0o700)
            child_environment = dict(environment)
            child_environment["PWD"] = isolated
            child_environment.pop("OLDPWD", None)
            version = _probe_version(executable, child_environment, workspace)
            argv = contract.build_argv(
                kind,
                seat["model"],
                workspace,
                prompt,
                output_schema,
                requested_effort,
                timeout_seconds,
            )
            process = _run_bounded(
                [executable, *argv],
                timeout=timeout_seconds,
                environment=child_environment,
                cwd=workspace,
            )
    except subprocess.TimeoutExpired as exc:
        state = observed(
            "temporarily_unavailable",
            "timeout",
            seat=seat,
            error=f"{kind} timed out after {timeout_seconds} seconds",
            operation=kind,
        )
        return {
            "command": [executable, *_safe_command(argv, prompt, output_schema)],
            "effort": {
                "requested": requested_effort,
                "effective": effective_effort,
            },
            "exit_code": None,
            "status": "failed",
            "error": "timeout",
            "seat_observed": state,
        }
    except RuntimeError as exc:
        message = _scrub(str(exc), seat, environment)
        state = observed(
            "setup_required", "auth", seat=seat, error=message, operation=kind
        )
        return {"status": "failed", "error": message, "seat_observed": state}
    except OSError as exc:
        message = _scrub(str(exc), seat, environment)
        state = observed(
            "setup_required",
            "adapter_error",
            seat=seat,
            error=message,
            operation=kind,
        )
        return {"status": "failed", "error": message, "seat_observed": state}

    record = {
        "version": version,
        "command": [executable, *_safe_command(argv, prompt, output_schema)],
        "effort": {
            "requested": requested_effort,
            "effective": effective_effort,
        },
        "exit_code": process.returncode,
    }
    if process.returncode != 0:
        failure = contract.classify_failure(process.stdout, process.stderr)
        message = f"process exited {process.returncode}"
        state = observed(
            _failure_status(failure),
            failure,
            seat=seat,
            error=message,
            operation=kind,
        )
        return {**record, "status": "failed", "error": message, "seat_observed": state}
    try:
        parsed = contract.parse_receipt(process.stdout, seat, executable)
    except ReceiptError as exc:
        message = _scrub(str(exc), seat, environment)
        failure = "model" if "model" in message.casefold() or "identity" in message.casefold() else "invalid_output"
        state = observed(
            "setup_required", failure, seat=seat, error=message, operation=kind
        )
        return {**record, "status": "invalid", "error": message, "seat_observed": state}
    state = observed("ready", "none", seat=seat, error=None, operation=kind)
    return {
        **record,
        "status": "valid",
        "output": parsed.output,
        "identity": parsed.identity,
        "seat_observed": state,
    }


def _seats_for_profile(
    config: dict[str, Any], profile: str, *, all_seats: bool = False
) -> list[dict[str, Any]]:
    if all_seats:
        return config["seats"]
    by_id = {seat["id"]: seat for seat in config["seats"]}
    seen = set()
    selected = []
    for binding in config["profiles"][profile]:
        if binding["seat"] not in seen:
            selected.append(by_id[binding["seat"]])
            seen.add(binding["seat"])
    return selected


def smoke_seat(seat: dict[str, Any], profile: str) -> dict[str, Any]:
    result = _invoke(
        seat,
        kind="smoke",
        profile=profile,
        prompt=SMOKE_PROMPT,
        output_schema=smoke_output_schema(),
    )
    if result["status"] == "valid" and result["output"] != SMOKE_EXPECTED:
        message = f"smoke output mismatch: expected {SMOKE_EXPECTED!r}"
        state = observed(
            "setup_required",
            "invalid_output",
            seat=seat,
            error=message,
            operation="smoke",
        )
        result = {**result, "status": "invalid", "error": message, "seat_observed": state}
    seat["observed"]["smoke"] = result["seat_observed"]
    contract = adapter_for(seat)
    return {
        "seat": seat["id"],
        "family": contract.model_family(seat["model"]),
        "engine": contract.engine,
        "model": seat["model"],
        **{key: value for key, value in result.items() if key not in {"output", "seat_observed"}},
        **observation_output(seat, "smoke", seat["observed"]["smoke"]),
    }


def smoke_all(
    config: dict[str, Any],
    config_path: Path,
    *,
    profile: str = "fast",
    all_seats: bool = False,
) -> dict[str, Any]:
    started = time.monotonic()
    selected = _seats_for_profile(config, profile, all_seats=all_seats)
    def run(seat: dict[str, Any]) -> dict[str, Any]:
        try:
            return smoke_seat(seat, profile)
        except Exception as exc:
            message = _scrub(f"runner error: {type(exc).__name__}: {exc}", seat)
            seat["observed"]["smoke"] = observed(
                "setup_required",
                "adapter_error",
                seat=seat,
                error=message,
                operation="smoke",
            )
            contract = adapter_for(seat)
            return {
                "seat": seat["id"],
                "family": contract.model_family(seat["model"]),
                "engine": contract.engine,
                "model": seat["model"],
                "status": "failed",
                "error": message,
                **observation_output(seat, "smoke", seat["observed"]["smoke"]),
            }

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(selected)) as executor:
        futures = [executor.submit(run, seat) for seat in selected]
        results = [future.result() for future in futures]
    persist_observed(config_path, config)
    ready = [
        seat for seat in selected if seat["observed"]["smoke"]["status"] == "ready"
    ]
    return {
        "status": "ready" if len(ready) == len(selected) else "SETUP REQUIRED",
        "profile": "all" if all_seats else profile,
        "ready_seats": [seat["id"] for seat in ready],
        "seats": results,
        "verified_at": now_utc(),
        "duration_seconds": round(time.monotonic() - started, 3),
    }


def build_prompt(
    persona: str,
    seat: dict[str, Any],
    objective: str,
    focus: str,
    resolved: str,
    evidence: str,
    artifacts: list[tuple[str, str]],
    max_findings: int,
) -> str:
    contract = adapter_for(seat)
    bundle = []
    for label, contents in artifacts:
        numbered = "\n".join(
            f"{number:06d}|{line}"
            for number, line in enumerate(contents.splitlines(), start=1)
        )
        bundle.extend([f"===== FILE: {label} =====", numbered, "===== END FILE ====="])
    example = {
        "persona": persona,
        "engine": contract.engine,
        "model": seat["model"],
        "verdict": "PASS",
        "findings": [],
        "biggest_risk": "<one line>",
    }
    return "\n".join(
        [
            "ROLE: independent adversarial reviewer",
            f"PERSONA: {persona}",
            f"LENS: {PERSONA_LENSES[persona]}",
            f"ENGINE: {contract.engine}",
            f"MODEL: {seat['model']}",
            "",
            "OBJECTIVE:",
            objective,
            "",
            "FOCUS:",
            focus or "none",
            "",
            "RESOLVED DECISIONS — CLOSED; do not re-litigate:",
            resolved or "none",
            "",
            "DETERMINISTIC EVIDENCE — ground truth:",
            evidence or "none supplied",
            "",
            "ARTIFACTS:",
            *bundle,
            "",
            "RULES:",
            "- Review only supplied evidence. Do not inspect files, run commands, call tools, or modify anything.",
            "- Work independently. You do not see other persona outputs.",
            "- Find concrete defects, not summaries or generic best practices.",
            "- A resolved decision is out of scope unless the artifact contradicts it.",
            f"- Return only one JSON object with zero to {max_findings} findings. No Markdown or outside prose.",
            "- The first character is { and the last character is }.",
            "- Copy the exact artifact path and cite a numbered non-blank line as a plain integer.",
            "- severity is exactly H, M, or L. Never spell out High, Medium, or Low.",
            "- FAIL requires H; CONCERNS requires M and no H; PASS allows no H or M.",
            "",
            "ZERO-FINDING EXAMPLE:",
            json.dumps(example, separators=(",", ":")),
            "",
            "OUTPUT KEYS:",
            "persona, engine, model, verdict, findings, biggest_risk. Each finding has severity, claim, evidence {artifact,line}, why, fix.",
        ]
    )


def parse_persona_output(
    output: Any,
    *,
    persona: str,
    seat: dict[str, Any],
    artifacts: dict[str, str],
    max_findings: int,
) -> dict[str, Any]:
    contract = adapter_for(seat)
    if isinstance(output, str):
        stripped = output.strip()
        if not stripped.startswith("{") or not stripped.endswith("}") or "```" in stripped:
            raise PersonaError("persona output must be one raw JSON object")
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise PersonaError("persona output is invalid JSON") from exc
    else:
        value = output
    expected_keys = {"persona", "engine", "model", "verdict", "findings", "biggest_risk"}
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise PersonaError("persona output has invalid keys")
    expected_identity = (persona, contract.engine, seat["model"])
    actual_identity = (value["persona"], value["engine"], value["model"])
    if actual_identity != expected_identity:
        raise PersonaError(
            f"persona identity mismatch: expected {expected_identity!r}, got {actual_identity!r}"
        )
    verdict = value["verdict"]
    if verdict not in {"PASS", "CONCERNS", "FAIL"}:
        raise PersonaError("persona verdict is invalid")
    raw_findings = value["findings"]
    if not isinstance(raw_findings, list) or len(raw_findings) > max_findings:
        raise PersonaError("persona findings exceed the profile limit")
    findings = []
    for index, finding in enumerate(raw_findings):
        if not isinstance(finding, dict) or set(finding) != {
            "severity",
            "claim",
            "evidence",
            "why",
            "fix",
        }:
            raise PersonaError(f"finding {index} has invalid keys")
        if finding["severity"] not in {"H", "M", "L"}:
            raise PersonaError(f"finding {index} has invalid severity")
        for field in ("claim", "why", "fix"):
            if not isinstance(finding[field], str) or not finding[field].strip():
                raise PersonaError(f"finding {index} has invalid {field}")
        citation = finding["evidence"]
        if not isinstance(citation, dict) or set(citation) != {"artifact", "line"}:
            raise PersonaError(f"finding {index} has invalid evidence")
        artifact = citation["artifact"]
        line = citation["line"]
        if artifact not in artifacts:
            raise PersonaError(f"finding {index} cites unknown artifact {artifact!r}")
        lines = artifacts[artifact].splitlines()
        if isinstance(line, bool) or not isinstance(line, int) or line < 1 or line > len(lines):
            raise PersonaError(f"finding {index} citation is outside {artifact}")
        if not lines[line - 1].strip():
            raise PersonaError(f"finding {index} cites a blank line")
        findings.append(
            {
                **finding,
                "artifact": artifact,
                "line": line,
                "excerpt": lines[line - 1],
            }
        )
    severities = {finding["severity"] for finding in findings}
    if verdict == "FAIL" and "H" not in severities:
        raise PersonaError("FAIL requires a High finding")
    if verdict == "CONCERNS" and ("H" in severities or "M" not in severities):
        raise PersonaError("CONCERNS requires Medium and no High")
    if verdict == "PASS" and severities & {"H", "M"}:
        raise PersonaError("PASS cannot contain High or Medium")
    if not isinstance(value["biggest_risk"], str) or not value["biggest_risk"].strip():
        raise PersonaError("biggest_risk must be non-empty")
    return {**value, "findings": findings}


def _read_artifacts(paths: list[str]) -> tuple[list[tuple[str, str]], dict[str, str]]:
    root = Path.cwd().resolve()
    artifacts = []
    mapping = {}
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_absolute():
            raise RequestError(f"artifact must be relative: {raw_path}")
        resolved = (root / path).resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise RequestError(f"artifact escapes current directory: {raw_path}") from exc
        label = str(path)
        if label in mapping:
            raise RequestError(f"duplicate artifact: {label}")
        try:
            contents = resolved.read_text()
        except (OSError, UnicodeError) as exc:
            raise RequestError(f"cannot read artifact {label}: {exc}") from exc
        artifacts.append((label, contents))
        mapping[label] = contents
    if not artifacts:
        raise RequestError("at least one artifact is required")
    return artifacts, mapping


def _aggregate_state(
    prior: dict[str, Any], states: list[dict[str, Any]]
) -> dict[str, Any]:
    if not states:
        return prior
    return max(states, key=lambda state: FAILURE_PRIORITY[state["failure_class"]])


def review(
    config: dict[str, Any],
    config_path: Path,
    profile: str,
    objective: str,
    focus: str,
    resolved: str,
    evidence: str,
    artifact_paths: list[str],
) -> tuple[dict[str, Any], int]:
    started = time.monotonic()
    artifacts, artifact_map = _read_artifacts(artifact_paths)
    by_id = {seat["id"]: seat for seat in config["seats"]}
    jobs = []
    for index, binding in enumerate(config["profiles"][profile]):
        seat = by_id[binding["seat"]]
        persona = binding["persona"]
        prompt = build_prompt(
            persona,
            seat,
            objective,
            focus,
            resolved,
            evidence,
            artifacts,
            PROFILE_MAX_FINDINGS[profile],
        )
        size = len(prompt.encode())
        if size > PROFILE_MAX_PROMPT_BYTES[profile]:
            raise RequestError(
                f"{persona} prompt is {size} bytes; maximum for {profile} is "
                f"{PROFILE_MAX_PROMPT_BYTES[profile]}"
            )
        jobs.append(
            {
                "index": index,
                "invocation_id": str(uuid.uuid4()),
                "persona": persona,
                "seat": seat,
                "prompt": prompt,
            }
        )

    seat_counts: dict[str, int] = {}
    for job in jobs:
        seat_id = job["seat"]["id"]
        seat_counts[seat_id] = seat_counts.get(seat_id, 0) + 1
    serialized_batches = max(seat_counts.values())
    call_timeout_ceiling_seconds = serialized_batches * (
        10 + PROFILE_REVIEW_TIMEOUT_SECONDS[profile]
    )

    run_id = str(uuid.uuid4())
    run_path = config_path.parent / ".council-runs" / f"{run_id}.json"
    allocation = []
    for job in jobs:
        contract = adapter_for(job["seat"])
        allocation.append(
            {
                "index": job["index"],
                "invocation_id": job["invocation_id"],
                "persona": job["persona"],
                "seat": job["seat"]["id"],
                "family": contract.model_family(job["seat"]["model"]),
                "engine": contract.engine,
                "model": job["seat"]["model"],
                "effort": {
                    "requested": PROFILE_EFFORT[profile],
                    "effective": contract.effective_effort(
                        job["seat"]["model"], PROFILE_EFFORT[profile]
                    ),
                },
            }
        )
    receipt = {
        "schema_version": 1,
        "run_id": run_id,
        "profile": profile,
        "status": "running",
        "started_at": now_utc(),
        "completed_at": None,
        "artifacts": {
            label: {"bytes": len(contents.encode())}
            for label, contents in artifacts
        },
        "allocation": allocation,
        "personas": [],
    }
    atomic_write_json(run_path, receipt)
    results: list[dict[str, Any] | None] = [None] * len(jobs)
    seat_locks = {job["seat"]["id"]: threading.Lock() for job in jobs}

    def run(job: dict[str, Any]) -> dict[str, Any]:
        seat = job["seat"]
        with seat_locks[seat["id"]]:
            result = _invoke(
                seat,
                kind="review",
                profile=profile,
                prompt=job["prompt"],
                output_schema=persona_output_schema(PROFILE_MAX_FINDINGS[profile]),
            )
        if result["status"] == "valid":
            try:
                parsed = parse_persona_output(
                    result["output"],
                    persona=job["persona"],
                    seat=seat,
                    artifacts=artifact_map,
                    max_findings=PROFILE_MAX_FINDINGS[profile],
                )
            except PersonaError as exc:
                message = _scrub(str(exc), seat)
                state = observed(
                    "setup_required",
                    "invalid_output",
                    seat=seat,
                    error=message,
                    operation="review",
                )
                result = {**result, "status": "invalid", "error": message, "seat_observed": state}
            else:
                result = {**result, "output": parsed}
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as executor:
        futures = {executor.submit(run, job): job for job in jobs}
        for future in concurrent.futures.as_completed(futures):
            job = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                message = _scrub(f"runner error: {type(exc).__name__}: {exc}", job["seat"])
                state = observed(
                    "setup_required",
                    "adapter_error",
                    seat=job["seat"],
                    error=message,
                    operation="review",
                )
                result = {"status": "failed", "error": message, "seat_observed": state}
            contract = adapter_for(job["seat"])
            results[job["index"]] = {
                "index": job["index"],
                "invocation_id": job["invocation_id"],
                "persona": job["persona"],
                "seat": job["seat"]["id"],
                "family": contract.model_family(job["seat"]["model"]),
                "engine": contract.engine,
                "model": job["seat"]["model"],
                "effort": {
                    "requested": PROFILE_EFFORT[profile],
                    "effective": contract.effective_effort(
                        job["seat"]["model"], PROFILE_EFFORT[profile]
                    ),
                },
                **result,
            }
            receipt["personas"] = [item for item in results if item is not None]
            atomic_write_json(run_path, receipt)

    completed = [item for item in results if item is not None]
    for seat in config["seats"]:
        states = [
            item["seat_observed"]
            for item in completed
            if item["seat"] == seat["id"]
        ]
        if states:
            seat["observed"]["review"] = _aggregate_state(
                seat["observed"]["review"], states
            )
    persistence_error = None
    try:
        persist_observed(config_path, config)
    except ConfigError as exc:
        persistence_error = str(exc)
    valid = sum(item["status"] == "valid" for item in completed)
    receipt["personas"] = completed
    receipt["status"] = (
        "complete" if valid == len(jobs) and persistence_error is None else "INCOMPLETE"
    )
    receipt["persistence_error"] = persistence_error
    receipt["completed_at"] = now_utc()
    receipt["post_run_seats"] = [
        {
            "seat": seat["id"],
            "family": adapter_for(seat).model_family(seat["model"]),
            "engine": adapter_for(seat).engine,
            "model": seat["model"],
            "review_qualified": review_qualified(seat),
            "smoke": observation_output(seat, "smoke", seat["observed"]["smoke"]),
            "review": observation_output(
                seat, "review", seat["observed"]["review"]
            ),
        }
        for seat in config["seats"]
        if any(item["seat"] == seat["id"] for item in allocation)
    ]
    receipt["coverage"] = {
        "profile": profile,
        "valid_personas": valid,
        "required_personas": len(jobs),
        "attempted_personas": len(completed),
        "distinct_families": list(dict.fromkeys(item["family"] for item in allocation)),
        "distinct_engines": list(dict.fromkeys(item["engine"] for item in allocation)),
        "independent_invocations": len({item["invocation_id"] for item in completed}),
        "serialized_batches": serialized_batches,
        "call_timeout_ceiling_seconds": call_timeout_ceiling_seconds,
    }
    receipt["duration_seconds"] = round(time.monotonic() - started, 3)
    atomic_write_json(run_path, receipt)
    return {
        "council_status": receipt["status"],
        "profile": profile,
        "run_id": run_id,
        "receipt": str(run_path),
        "coverage": receipt["coverage"],
        "personas": [
            {
                "persona": item["persona"],
                "family": item["family"],
                "engine": item["engine"],
                "model": item["model"],
                "effort": item["effort"],
                "status": item["status"],
                "output": item.get("output"),
                "error": item.get("error"),
            }
            for item in completed
        ],
        "post_run_seats": receipt["post_run_seats"],
        "duration_seconds": receipt["duration_seconds"],
    }, 0 if receipt["status"] == "complete" else 3
