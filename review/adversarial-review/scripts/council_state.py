"""Device configuration and durable state for adversarial-review."""

from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from council_adapters import ADAPTERS, adapter_for


SCHEMA_VERSION = 1
PROFILE_PERSONAS = {
    "fast": ("Architect", "Adversary"),
    "deep": ("Architect", "Pragmatist", "Verifier", "Adversary"),
}
TOP_KEYS = {"schema_version", "profiles", "seats"}
SEAT_KEYS = {"id", "adapter", "executable", "auth", "model", "observed"}
AUTH_KEYS = {
    "method",
    "label",
    "required_environment",
    "unset_environment",
    "setup_steps",
}
OBSERVED_KEYS = {"smoke", "review"}
OBSERVATION_KEYS = {
    "status",
    "failure_class",
    "last_error",
    "verified_at",
}
PROFILE_BINDING_KEYS = {"persona", "seat"}
STATUSES = {"ready", "setup_required", "temporarily_unavailable"}
FAILURES = {
    "none",
    "cli_missing",
    "auth",
    "model",
    "trust",
    "capacity",
    "timeout",
    "invalid_output",
    "adapter_error",
    "not_run",
    "unconfigured",
}
SECRET_VALUE_RES = (
    re.compile(r"\b(?:sk|key|token|secret)[-_][A-Za-z0-9_-]{16,}\b", re.I),
    re.compile(r"\b[A-Za-z0-9+/]{32,}={0,2}\b"),
)
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")


class ConfigError(ValueError):
    """The device contract is invalid."""


class RequestError(ValueError):
    """A review request cannot be executed safely."""


class PersonaError(ValueError):
    """A persona response violates the typed output contract."""


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _parse_timestamp(value: Any, path: str) -> datetime:
    timestamp = _string(value, path)
    if not TIMESTAMP_RE.fullmatch(timestamp):
        raise ConfigError(f"{path}: expected fixed-width UTC timestamp")
    return datetime.fromisoformat(timestamp.removesuffix("Z") + "+00:00")


def _exact_keys(value: dict[str, Any], expected: set[str], path: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ConfigError(
            f"{path}: expected keys {sorted(expected)!r}; got {sorted(actual)!r}"
        )


def _string(value: Any, path: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ConfigError(f"{path}: expected non-empty string")
    return value


def _string_list(value: Any, path: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        raise ConfigError(f"{path}: expected string array")
    for index, item in enumerate(value):
        _string(item, f"{path}[{index}]")
    if len(set(value)) != len(value):
        raise ConfigError(f"{path}: duplicate values are forbidden")
    return value


def _reject_secrets(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in {
                "api_key",
                "apikey",
                "access_token",
                "auth_token",
                "password",
                "secret_value",
            }:
                raise ConfigError(f"{path}.{key}: credential fields are forbidden")
            _reject_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secrets(child, f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in SECRET_VALUE_RES:
            if pattern.search(value):
                raise ConfigError(f"{path}: credential-looking value is forbidden")


def _reject_gemini(value: Any, path: str = "$") -> None:
    if isinstance(value, str) and "gemini" in value.casefold():
        raise ConfigError(f"{path}: Gemini is prohibited")
    if isinstance(value, dict):
        for key, child in value.items():
            if "gemini" in str(key).casefold():
                raise ConfigError(f"{path}.{key}: Gemini is prohibited")
            _reject_gemini(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_gemini(child, f"{path}[{index}]")


def _validate_observation(value: Any, path: str) -> None:
    if not isinstance(value, dict):
        raise ConfigError(f"{path}: expected object")
    _exact_keys(value, OBSERVATION_KEYS, path)
    if value["status"] not in STATUSES:
        raise ConfigError(f"{path}.status: unsupported value")
    if value["failure_class"] not in FAILURES:
        raise ConfigError(f"{path}.failure_class: unsupported value")
    if value["last_error"] is not None:
        _string(value["last_error"], f"{path}.last_error")
    _parse_timestamp(value["verified_at"], f"{path}.verified_at")
    if value["status"] == "ready":
        if value["failure_class"] != "none":
            raise ConfigError(f"{path}: ready requires failure_class 'none'")
        if value["last_error"] is not None:
            raise ConfigError(f"{path}: ready cannot retain an error")
    elif value["failure_class"] == "none":
        raise ConfigError(f"{path}: non-ready observation requires a failure class")
    if value["status"] == "temporarily_unavailable" and value["failure_class"] not in {
        "capacity",
        "timeout",
    }:
        raise ConfigError(
            f"{path}: temporarily_unavailable requires capacity or timeout"
        )
    if value["status"] == "setup_required" and value["failure_class"] in {
        "capacity",
        "timeout",
    }:
        raise ConfigError(f"{path}: capacity and timeout are temporary failures")


def _validate_observed(value: Any, path: str) -> None:
    if not isinstance(value, dict):
        raise ConfigError(f"{path}: expected object")
    _exact_keys(value, OBSERVED_KEYS, path)
    for operation in sorted(OBSERVED_KEYS):
        _validate_observation(value[operation], f"{path}.{operation}")


def _validate_seat(value: Any, index: int) -> dict[str, Any]:
    path = f"$.seats[{index}]"
    if not isinstance(value, dict):
        raise ConfigError(f"{path}: expected object")
    _exact_keys(value, SEAT_KEYS, path)
    _string(value["id"], f"{path}.id")
    if value["adapter"] not in ADAPTERS:
        raise ConfigError(f"{path}.adapter: unsupported value {value['adapter']!r}")
    contract = adapter_for(value)
    executable = Path(_string(value["executable"], f"{path}.executable"))
    if not executable.is_absolute():
        raise ConfigError(f"{path}.executable: expected absolute direct CLI path")
    if executable.name.casefold() not in contract.executable_names:
        raise ConfigError(
            f"{path}.executable: adapter {contract.name!r} requires basename in "
            f"{contract.executable_names!r}"
        )
    model = _string(value["model"], f"{path}.model")
    if contract.model_family(model) is None:
        raise ConfigError(
            f"{path}.model: model is outside the adapter's closed non-Gemini families"
        )
    auth = value["auth"]
    if not isinstance(auth, dict):
        raise ConfigError(f"{path}.auth: expected object")
    _exact_keys(auth, AUTH_KEYS, f"{path}.auth")
    if auth["method"] not in {"oauth", "environment", "secret_manager"}:
        raise ConfigError(f"{path}.auth.method: unsupported value")
    _string(auth["label"], f"{path}.auth.label")
    required = _string_list(
        auth["required_environment"], f"{path}.auth.required_environment"
    )
    unset = _string_list(auth["unset_environment"], f"{path}.auth.unset_environment")
    _string_list(auth["setup_steps"], f"{path}.auth.setup_steps", nonempty=True)
    overlap = set(required) & set(unset)
    if overlap:
        raise ConfigError(f"{path}.auth: required and unset overlap {sorted(overlap)!r}")
    if contract.name == "cursor":
        if auth["method"] == "oauth":
            raise ConfigError(
                f"{path}.auth: Cursor browser OAuth is not durable for repeated "
                "headless calls; use environment or secret_manager"
            )
        if "CURSOR_API_KEY" not in required:
            raise ConfigError(
                f"{path}.auth: environment Cursor auth requires CURSOR_API_KEY"
            )
    _validate_observed(value["observed"], f"{path}.observed")
    return value


def review_qualified(seat: dict[str, Any]) -> bool:
    review = seat["observed"]["review"]
    smoke = seat["observed"]["smoke"]
    if review["status"] != "ready":
        return False
    return not (
        smoke["status"] != "ready"
        and _parse_timestamp(smoke["verified_at"], "observed.smoke.verified_at")
        > _parse_timestamp(review["verified_at"], "observed.review.verified_at")
    )


def _validate_profiles(value: Any, seats: list[dict[str, Any]]) -> None:
    if not isinstance(value, dict) or set(value) != set(PROFILE_PERSONAS):
        raise ConfigError("$.profiles: expected exactly fast and deep")
    by_id = {seat["id"]: seat for seat in seats}
    qualified_families = {
        adapter_for(seat).model_family(seat["model"])
        for seat in seats
        if review_qualified(seat)
    }
    for profile, personas in PROFILE_PERSONAS.items():
        bindings = value[profile]
        if not isinstance(bindings, list) or len(bindings) != len(personas):
            raise ConfigError(
                f"$.profiles.{profile}: expected {len(personas)} ordered bindings"
            )
        families = set()
        for index, (binding, persona) in enumerate(zip(bindings, personas)):
            path = f"$.profiles.{profile}[{index}]"
            if not isinstance(binding, dict):
                raise ConfigError(f"{path}: expected object")
            _exact_keys(binding, PROFILE_BINDING_KEYS, path)
            if binding["persona"] != persona:
                raise ConfigError(f"{path}.persona: expected {persona!r}")
            seat_id = _string(binding["seat"], f"{path}.seat")
            if seat_id not in by_id:
                raise ConfigError(f"{path}.seat: unknown configured seat {seat_id!r}")
            seat = by_id[seat_id]
            families.add(adapter_for(seat).model_family(seat["model"]))
        if len(qualified_families) >= 2 and len(families) < 2:
            raise ConfigError(
                f"$.profiles.{profile}: expected at least two model families because "
                "the device has review-qualified families "
                f"{sorted(qualified_families)!r}"
            )


def validate_config(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise ConfigError("$: expected object")
    _exact_keys(config, TOP_KEYS, "$")
    if config["schema_version"] != SCHEMA_VERSION:
        raise ConfigError(f"$.schema_version: expected {SCHEMA_VERSION}")
    _reject_secrets(config)
    _reject_gemini(config)
    if not isinstance(config["seats"], list) or not config["seats"]:
        raise ConfigError("$.seats: expected non-empty array")
    seats = [_validate_seat(seat, index) for index, seat in enumerate(config["seats"])]
    ids = [seat["id"] for seat in seats]
    if len(ids) != len(set(ids)):
        raise ConfigError("$.seats: duplicate seat ids")
    _validate_profiles(config["profiles"], seats)
    return config


def load_config(path: Path) -> dict[str, Any]:
    try:
        return validate_config(json.loads(path.read_text()))
    except FileNotFoundError as exc:
        raise ConfigError(f"config missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path}: invalid JSON: {exc}") from exc


def setup_available(config: dict[str, Any]) -> list[dict[str, str]]:
    configured = {seat["adapter"] for seat in config["seats"]}
    available = []
    for adapter, contract in ADAPTERS.items():
        if adapter in configured:
            continue
        executable = next(
            (path for name in contract.executable_names if (path := shutil.which(name))),
            None,
        )
        if executable:
            available.append({"adapter": adapter, "executable": executable})
    return available


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _definition(config: dict[str, Any]) -> dict[str, Any]:
    return {
        **config,
        "seats": [
            {**seat, "observed": None}
            for seat in config["seats"]
        ],
    }


def persist_observed(config_path: Path, config: dict[str, Any]) -> None:
    lock_path = config_path.with_name(f".{config_path.name}.lock")
    lock_path.touch(exist_ok=True)
    with lock_path.open("r+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        disk = load_config(config_path)
        if _definition(disk) != _definition(config):
            raise ConfigError("config changed during run; observed state was not persisted")
        states = {seat["id"]: seat["observed"] for seat in config["seats"]}
        for seat in disk["seats"]:
            for operation in sorted(OBSERVED_KEYS):
                candidate = states[seat["id"]][operation]
                current = seat["observed"][operation]
                if _parse_timestamp(
                    candidate["verified_at"], f"$.seats.{seat['id']}.{operation}"
                ) >= _parse_timestamp(
                    current["verified_at"], f"$.seats.{seat['id']}.{operation}"
                ):
                    seat["observed"][operation] = candidate
        validate_config(disk)
        atomic_write_json(config_path, disk)
        fcntl.flock(lock, fcntl.LOCK_UN)


def recovery_for(
    seat: dict[str, Any], failure: str, *, operation: str = "review"
) -> str | None:
    setup = " ".join(seat["auth"]["setup_steps"])
    rerun = "live smoke" if operation == "smoke" else "representative review"
    if failure == "none":
        return None
    if failure == "not_run":
        return (
            "Deliberately bind this seat into both profiles, run a bounded "
            "representative review, and keep it bound only if that review succeeds."
        )
    if failure in {"cli_missing", "auth", "model", "unconfigured"}:
        return setup
    if failure in {"timeout", "capacity"}:
        return (
            f"Wait for the configured seat to recover, then rerun its {rerun}. "
            "Do not substitute another seat."
        )
    if failure == "trust":
        return f"Complete the configured CLI trust step, then rerun the isolated {rerun}."
    if failure == "invalid_output":
        return (
            f"Inspect the installed {seat['adapter']} structured output against the "
            f"built-in adapter contract, repair the contract or CLI, then rerun {rerun}."
        )
    return (
        f"Inspect the configured direct {seat['adapter']} CLI, auth route, and model; "
        f"repair that seat and rerun {rerun}."
    )


def observed(
    status: str,
    failure: str,
    *,
    seat: dict[str, Any],
    error: str | None,
    operation: str = "review",
) -> dict[str, Any]:
    return {
        "status": status,
        "failure_class": failure,
        "last_error": error,
        "verified_at": now_utc(),
    }


def observation_output(
    seat: dict[str, Any], operation: str, observation: dict[str, Any]
) -> dict[str, Any]:
    return {
        **observation,
        "recovery": recovery_for(
            seat, observation["failure_class"], operation=operation
        ),
    }
