"""Closed adapter registry for the adversarial-review council."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


CLINE_SYSTEM_PROMPT = (
    "You are a stateless review function. Do not use tools, spawn agents, inspect "
    "files, or modify anything. Evaluate only the user's supplied artifacts. Return "
    "only the exact response format requested by the user."
)


class ReceiptError(ValueError):
    """The CLI returned a receipt that does not prove the configured call."""


@dataclass(frozen=True)
class ParsedOutput:
    output: Any
    identity: dict[str, Any]


ArgvBuilder = Callable[[str, str, Path, str, str, str, int], list[str]]
ReceiptParser = Callable[[str, dict[str, Any], str], ParsedOutput]
FailureClassifier = Callable[[str, str], str]


@dataclass(frozen=True)
class AdapterContract:
    name: str
    engine: str
    provider: str
    executable_names: tuple[str, ...]
    model_families: tuple[tuple[re.Pattern[str], str], ...]
    effort_control: str
    unset_environment: frozenset[str]
    build_argv: ArgvBuilder
    parse_receipt: ReceiptParser
    classify_failure: FailureClassifier

    def model_family(self, model: str) -> str | None:
        for pattern, family in self.model_families:
            if pattern.match(model):
                return family
        return None

    def effective_effort(self, model: str, requested: str) -> str:
        if self.effort_control == "flag":
            return requested
        if self.effort_control == "model":
            return f"model:{model}"
        return "none"


def _jsonl(stdout: str) -> list[dict[str, Any]]:
    records = []
    for line_number, line in enumerate(stdout.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReceiptError(f"invalid JSONL at line {line_number}") from exc
        if not isinstance(value, dict):
            raise ReceiptError(f"JSONL line {line_number} is not an object")
        records.append(value)
    if not records:
        raise ReceiptError("structured stdout is empty")
    return records


def _one(records: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool], label: str) -> dict[str, Any]:
    matches = [record for record in records if predicate(record)]
    if len(matches) != 1:
        raise ReceiptError(f"expected exactly one {label}; found {len(matches)}")
    return matches[0]


def _failure_evidence(stdout: str, stderr: str) -> str:
    evidence = [stderr]

    def collect(value: Any, *, error_context: bool = False) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_context = error_context or str(key).casefold() in {
                    "code",
                    "detail",
                    "error",
                    "errors",
                    "finishreason",
                    "message",
                    "reason",
                    "status",
                    "subtype",
                    "type",
                }
                collect(child, error_context=child_context)
        elif isinstance(value, list):
            for child in value:
                collect(child, error_context=error_context)
        elif error_context and value is not None:
            evidence.append(str(value))

    for line in stdout.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            evidence.append(line)
        else:
            collect(value)
    return "\n".join(evidence).casefold()


def _classify_failure(stdout: str, stderr: str) -> str:
    evidence = _failure_evidence(stdout, stderr)
    if any(
        phrase in evidence
        for phrase in (
            "capacity",
            "rate limit",
            "overloaded",
            "429",
            "usage limit reached",
            "insufficient credits",
            "quota exceeded",
        )
    ):
        return "capacity"
    if any(
        phrase in evidence
        for phrase in (
            "unauthorized",
            "authentication",
            "api key",
            "missing required environment",
            "not logged in",
            "please sign in",
            "login required",
            "401",
        )
    ):
        return "auth"
    if any(
        phrase in evidence
        for phrase in ("model not found", "unknown model", "invalid model")
    ):
        return "model"
    if "trust" in evidence:
        return "trust"
    return "adapter_error"


def _identity(
    provider: str,
    model: str,
    executable: str,
    *,
    provider_assurance: str = "executable",
    model_assurance: str = "receipt",
    provider_evidence: Any | None = None,
    model_evidence: Any | None = None,
) -> dict[str, Any]:
    return {
        "provider": {
            "assurance": provider_assurance,
            "configured": provider,
            "evidence": provider_evidence
            if provider_evidence is not None
            else {"provider": provider, "path": executable},
        },
        "model": {
            "assurance": model_assurance,
            "configured": model,
            "evidence": model_evidence if model_evidence is not None else model,
        },
    }


def _codex_argv(
    kind: str,
    model: str,
    workspace: Path,
    prompt: str,
    output_schema: str,
    effort: str,
    timeout_seconds: int,
) -> list[str]:
    del kind, workspace, output_schema, timeout_seconds
    return [
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "-c",
        'approval_policy="never"',
        "-c",
        f'model_reasoning_effort="{effort}"',
        "--model",
        model,
        "--json",
        prompt,
    ]


def _parse_codex(stdout: str, seat: dict[str, Any], executable: str) -> ParsedOutput:
    records = _jsonl(stdout)
    item = _one(
        records,
        lambda value: value.get("type") == "item.completed"
        and isinstance(value.get("item"), dict)
        and value["item"].get("type") == "agent_message",
        "Codex agent message",
    )
    terminal = _one(
        records,
        lambda value: value.get("type")
        in {"turn.completed", "turn.failed", "turn.cancelled", "turn.interrupted"},
        "Codex terminal turn",
    )
    if terminal.get("type") != "turn.completed":
        raise ReceiptError(f"Codex terminal turn failed: {terminal.get('type')!r}")
    output = item["item"].get("text")
    if not isinstance(output, str):
        raise ReceiptError("Codex agent message text is missing")
    return ParsedOutput(
        output,
        _identity(
            "openai",
            seat["model"],
            executable,
            model_assurance="command",
        ),
    )


def _cursor_argv(
    kind: str,
    model: str,
    workspace: Path,
    prompt: str,
    output_schema: str,
    effort: str,
    timeout_seconds: int,
) -> list[str]:
    del kind, output_schema, effort, timeout_seconds
    return [
        "-p",
        "--output-format",
        "stream-json",
        "--mode",
        "ask",
        "--sandbox",
        "enabled",
        "--workspace",
        str(workspace),
        "--trust",
        "--model",
        model,
        prompt,
    ]


def _parse_cursor(stdout: str, seat: dict[str, Any], executable: str) -> ParsedOutput:
    records = _jsonl(stdout)
    init = _one(
        records,
        lambda value: value.get("type") == "system" and value.get("subtype") == "init",
        "Cursor init receipt",
    )
    result = _one(records, lambda value: value.get("type") == "result", "Cursor terminal result")
    if result.get("subtype") != "success" or result.get("is_error") is not False:
        raise ReceiptError("Cursor terminal result is not successful")
    if init.get("apiKeySource") != "env":
        raise ReceiptError(
            "Cursor auth source mismatch: expected 'env', "
            f"got {init.get('apiKeySource')!r}"
        )
    expected_model = seat["model"].replace("-", " ").casefold()
    actual_model = str(init.get("model", "")).replace("-", " ").casefold()
    if actual_model != expected_model:
        raise ReceiptError(
            f"Cursor model mismatch: expected {seat['model']!r}, got {init.get('model')!r}"
        )
    output = result.get("result")
    if not isinstance(output, str):
        raise ReceiptError("Cursor result text is missing")
    return ParsedOutput(
        output,
        _identity(
            "cursor",
            seat["model"],
            executable,
            model_evidence=init["model"],
        ),
    )


def _cline_argv(
    kind: str,
    model: str,
    workspace: Path,
    prompt: str,
    output_schema: str,
    effort: str,
    timeout_seconds: int,
) -> list[str]:
    del kind, output_schema, effort
    return [
        "--plan",
        "--json",
        "--auto-approve",
        "false",
        "--thinking",
        "none",
        "--compaction",
        "off",
        "--retries",
        "1",
        "--hooks-dir",
        str(workspace / ".cline-hooks"),
        "--system",
        CLINE_SYSTEM_PROMPT,
        "--timeout",
        str(max(1, timeout_seconds - 5)),
        "--cwd",
        str(workspace),
        "--provider",
        "cline",
        "--model",
        model,
        prompt,
    ]


def _parse_cline(stdout: str, seat: dict[str, Any], executable: str) -> ParsedOutput:
    result = _one(
        _jsonl(stdout), lambda value: value.get("type") == "run_result", "Cline terminal result"
    )
    if result.get("finishReason") != "completed":
        raise ReceiptError("Cline terminal result is not successful")
    model = result.get("model")
    if not isinstance(model, dict):
        raise ReceiptError("Cline model receipt is missing")
    if model.get("provider") != "cline" or model.get("id") != seat["model"]:
        raise ReceiptError(
            f"Cline identity mismatch: expected cline/{seat['model']}, got {model!r}"
        )
    output = result.get("text")
    if not isinstance(output, str):
        raise ReceiptError("Cline result text is missing")
    return ParsedOutput(
        output,
        _identity(
            "cline",
            seat["model"],
            executable,
            provider_assurance="receipt",
            provider_evidence="cline",
            model_evidence=model["id"],
        ),
    )


def _claude_argv(
    kind: str,
    model: str,
    workspace: Path,
    prompt: str,
    output_schema: str,
    effort: str,
    timeout_seconds: int,
) -> list[str]:
    del workspace, timeout_seconds
    argv = [
        "-p",
        "--output-format",
        "json",
        "--permission-mode",
        "plan",
        "--tools",
        "",
        "--safe-mode",
        "--no-session-persistence",
        "--json-schema",
        output_schema,
    ]
    argv.extend(["--effort", effort])
    return [*argv, "--model", model, prompt]


def _parse_claude(stdout: str, seat: dict[str, Any], executable: str) -> ParsedOutput:
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ReceiptError("Claude stdout is not one JSON object") from exc
    if not isinstance(result, dict):
        raise ReceiptError("Claude stdout is not one JSON object")
    expected = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "terminal_reason": "completed",
    }
    for key, value in expected.items():
        if result.get(key) != value:
            raise ReceiptError(f"Claude receipt {key} mismatch")
    if result.get("permission_denials") != []:
        raise ReceiptError("Claude reported permission denials")
    model_usage = result.get("modelUsage")
    if not isinstance(model_usage, dict) or seat["model"] not in model_usage:
        raise ReceiptError(f"Claude model usage does not contain {seat['model']!r}")
    structured = result.get("structured_output")
    if not isinstance(structured, dict) or "output" not in structured:
        raise ReceiptError("Claude structured output is missing")
    return ParsedOutput(
        structured["output"],
        _identity(
            "anthropic-first-party",
            seat["model"],
            executable,
            model_evidence=seat["model"],
        ),
    )


COMMON_ROUTING_ENV = frozenset(
    {
        "BWS_ACCESS_TOKEN",
        "CURSOR_API_KEY",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_API_BASE",
        "CODEX_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
        "CLAUDE_CODE_USE_BEDROCK",
        "CLAUDE_CODE_USE_VERTEX",
        "CLAUDE_CODE_USE_FOUNDRY",
    }
)


def _routing_environment(*allowed: str) -> frozenset[str]:
    return COMMON_ROUTING_ENV - set(allowed)


ADAPTERS: dict[str, AdapterContract] = {
    "codex": AdapterContract(
        name="codex",
        engine="codex",
        provider="openai",
        executable_names=("codex",),
        model_families=((re.compile(r"^gpt-", re.I), "openai"),),
        effort_control="flag",
        unset_environment=_routing_environment(),
        build_argv=_codex_argv,
        parse_receipt=_parse_codex,
        classify_failure=_classify_failure,
    ),
    "cursor": AdapterContract(
        name="cursor",
        engine="cursor",
        provider="cursor",
        executable_names=("agent", "cursor-agent"),
        model_families=((re.compile(r"^composer-", re.I), "cursor"),),
        effort_control="model",
        unset_environment=_routing_environment("CURSOR_API_KEY"),
        build_argv=_cursor_argv,
        parse_receipt=_parse_cursor,
        classify_failure=_classify_failure,
    ),
    "cline": AdapterContract(
        name="cline",
        engine="cline",
        provider="cline",
        executable_names=("cline",),
        model_families=(
            (re.compile(r"^cline-pass/deepseek-", re.I), "deepseek"),
            (re.compile(r"^cline-pass/kimi-", re.I), "moonshot"),
            (re.compile(r"^cline-pass/glm-", re.I), "zhipu"),
            (re.compile(r"^cline-pass/qwen", re.I), "alibaba"),
        ),
        effort_control="none",
        unset_environment=_routing_environment(),
        build_argv=_cline_argv,
        parse_receipt=_parse_cline,
        classify_failure=_classify_failure,
    ),
    "claude": AdapterContract(
        name="claude",
        engine="claude-code",
        provider="anthropic-first-party",
        executable_names=("claude",),
        model_families=((re.compile(r"^claude-", re.I), "anthropic"),),
        effort_control="flag",
        unset_environment=_routing_environment(),
        build_argv=_claude_argv,
        parse_receipt=_parse_claude,
        classify_failure=_classify_failure,
    ),
}


def adapter_for(seat: dict[str, Any]) -> AdapterContract:
    try:
        return ADAPTERS[seat["adapter"]]
    except KeyError as exc:
        raise ValueError(f"unknown adapter {seat.get('adapter')!r}") from exc
