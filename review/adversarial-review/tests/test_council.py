import copy
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import council_adapters as adapters
import council_runtime as runtime
import council_state as state


FIXTURES = Path(__file__).parent / "fixtures"


class CouncilContractTests(unittest.TestCase):
    def example(self):
        return json.loads((ROOT / "council-config.example.json").read_text())

    def seat(self, adapter):
        return next(seat for seat in self.example()["seats"] if seat["adapter"] == adapter)

    def test_canonical_example_contains_and_validates_all_four_adapters(self):
        config = state.validate_config(self.example())
        self.assertEqual(
            [seat["adapter"] for seat in config["seats"]],
            ["codex", "cursor", "cline", "claude"],
        )

    def test_device_config_cannot_override_adapter_implementation(self):
        config = self.example()
        config["seats"][0]["review"] = {"argv": ["--worktree"]}
        with self.assertRaisesRegex(state.ConfigError, "expected keys"):
            state.validate_config(config)

    def test_adapter_registry_constructs_a_closed_command_grammar(self):
        forbidden = {
            "--worktree",
            "--background",
            "--output-last-message",
            "--force",
            "--yolo",
            "--resume",
            "--continue",
        }
        for seat in self.example()["seats"]:
            with self.subTest(adapter=seat["adapter"]):
                argv = adapters.adapter_for(seat).build_argv(
                    "review",
                    seat["model"],
                    Path("/tmp/isolated"),
                    "PROMPT",
                    "SCHEMA",
                    "high",
                    90,
                )
                self.assertFalse(forbidden & set(argv))

    def test_cline_contract_is_stateless_and_uses_lowest_legal_retry_budget(self):
        seat = self.seat("cline")
        argv = adapters.adapter_for(seat).build_argv(
            "review", seat["model"], Path("/tmp/isolated"), "PROMPT", "SCHEMA", "high", 90
        )
        self.assertIn(adapters.CLINE_SYSTEM_PROMPT, argv)
        self.assertEqual(argv[argv.index("--retries") + 1], "1")
        self.assertEqual(argv[argv.index("--thinking") + 1], "none")
        self.assertEqual(argv[argv.index("--compaction") + 1], "off")
        self.assertEqual(argv[argv.index("--auto-approve") + 1], "false")
        self.assertEqual(
            argv[argv.index("--hooks-dir") + 1], "/tmp/isolated/.cline-hooks"
        )
        self.assertEqual(argv[argv.index("--timeout") + 1], "85")

    def test_effort_is_explicit_or_carried_by_the_cursor_model(self):
        for adapter in ("codex", "claude"):
            seat = self.seat(adapter)
            argv = adapters.adapter_for(seat).build_argv(
                "review",
                seat["model"],
                Path("/tmp/isolated"),
                "PROMPT",
                "SCHEMA",
                "high",
                90,
            )
            self.assertIn("high", " ".join(argv))
            self.assertEqual(
                adapters.adapter_for(seat).effective_effort(seat["model"], "high"),
                "high",
            )
        cursor = self.seat("cursor")
        self.assertEqual(
            adapters.adapter_for(cursor).effective_effort(cursor["model"], "high"),
            f"model:{cursor['model']}",
        )
        cline = self.seat("cline")
        self.assertEqual(
            adapters.adapter_for(cline).effective_effort(cline["model"], "high"),
            "none",
        )
        self.assertEqual(runtime.PROFILE_EFFORT, {"fast": "low", "deep": "medium"})

    def test_cursor_prefers_official_agent_alias(self):
        self.assertEqual(adapters.ADAPTERS["cursor"].executable_names, ("agent", "cursor-agent"))

    def test_wrong_executable_basename_is_rejected(self):
        config = self.example()
        config["seats"][1]["executable"] = "/absolute/path/to/not-agent"
        with self.assertRaisesRegex(state.ConfigError, "requires basename"):
            state.validate_config(config)

    def test_relative_executable_is_rejected(self):
        config = self.example()
        config["seats"][0]["executable"] = "codex"
        with self.assertRaisesRegex(state.ConfigError, "absolute"):
            state.validate_config(config)

    def test_gemini_is_rejected_anywhere(self):
        config = self.example()
        config["seats"][0]["auth"]["label"] = "gateway Gemini seat"
        with self.assertRaisesRegex(state.ConfigError, "Gemini"):
            state.validate_config(config)

    def test_credential_values_and_fields_are_rejected(self):
        config = self.example()
        config["seats"][0]["auth"]["label"] = "token sk-example12345678901234567890"
        with self.assertRaisesRegex(state.ConfigError, "credential-looking"):
            state.validate_config(config)
        config = self.example()
        config["seats"][0]["auth"]["api_key"] = "anything"
        with self.assertRaisesRegex(state.ConfigError, "credential fields|expected keys"):
            state.validate_config(config)

    def test_cursor_environment_auth_requires_cursor_api_key(self):
        config = self.example()
        config["seats"][1]["auth"]["method"] = "secret_manager"
        config["seats"][1]["auth"]["required_environment"] = []
        with self.assertRaisesRegex(state.ConfigError, "requires CURSOR_API_KEY"):
            state.validate_config(config)

    def test_cursor_browser_oauth_is_rejected_after_repeated_headless_failure(self):
        config = self.example()
        config["seats"][1]["auth"]["method"] = "oauth"
        config["seats"][1]["auth"]["required_environment"] = []
        with self.assertRaisesRegex(state.ConfigError, "not durable"):
            state.validate_config(config)

    def test_model_family_is_derived_from_adapter_and_model(self):
        expected = {
            "codex": "openai",
            "cursor": "cursor",
            "cline": "zhipu",
            "claude": "anthropic",
        }
        for seat in self.example()["seats"]:
            contract = adapters.adapter_for(seat)
            self.assertEqual(contract.model_family(seat["model"]), expected[seat["adapter"]])

    def test_unsupported_model_lineage_is_rejected(self):
        config = self.example()
        config["seats"][2]["model"] = "cline-pass/unknown-family"
        with self.assertRaisesRegex(state.ConfigError, "closed non-Gemini"):
            state.validate_config(config)

    def test_diversity_uses_model_family_not_adapter(self):
        first = self.seat("cline")
        second = copy.deepcopy(first)
        first["id"] = "deepseek"
        second["id"] = "moonshot"
        second["model"] = "cline-pass/kimi-k2.7-code"
        config = {
            "schema_version": 1,
            "profiles": {
                "fast": [
                    {"persona": "Architect", "seat": "deepseek"},
                    {"persona": "Adversary", "seat": "moonshot"},
                ],
                "deep": [
                    {"persona": "Architect", "seat": "deepseek"},
                    {"persona": "Pragmatist", "seat": "moonshot"},
                    {"persona": "Verifier", "seat": "deepseek"},
                    {"persona": "Adversary", "seat": "moonshot"},
                ],
            },
            "seats": [first, second],
        }
        state.validate_config(config)

    def test_single_family_profile_is_rejected_when_device_has_two(self):
        config = self.example()
        for seat in config["seats"]:
            seat["observed"]["review"] = state.observed(
                "ready", "none", seat=seat, error=None, operation="review"
            )
        for profile in config["profiles"].values():
            for binding in profile:
                binding["seat"] = "example-codex"
        with self.assertRaisesRegex(state.ConfigError, "model families"):
            state.validate_config(config)

    def test_unqualified_inventory_seat_does_not_force_an_impossible_binding(self):
        config = self.example()
        codex = config["seats"][0]
        cline = config["seats"][2]
        codex["observed"]["review"] = state.observed(
            "ready", "none", seat=codex, error=None, operation="review"
        )
        cline["observed"]["review"] = state.observed(
            "temporarily_unavailable",
            "timeout",
            seat=cline,
            error="representative review timed out",
            operation="review",
        )
        config["seats"] = [codex, cline]
        for profile in config["profiles"].values():
            for binding in profile:
                binding["seat"] = codex["id"]
        state.validate_config(config)

    def test_newer_smoke_failure_revokes_stale_review_qualification(self):
        seat = self.seat("cursor")
        seat["observed"]["review"] = state.observed(
            "ready", "none", seat=seat, error=None, operation="review"
        )
        seat["observed"]["review"]["verified_at"] = "2026-07-16T01:00:00.000000Z"
        seat["observed"]["smoke"] = state.observed(
            "setup_required",
            "auth",
            seat=seat,
            error="auth failed",
            operation="smoke",
        )
        seat["observed"]["smoke"]["verified_at"] = "2026-07-16T02:00:00.000000Z"
        self.assertFalse(state.review_qualified(seat))
        seat["observed"]["review"] = state.observed(
            "ready", "none", seat=seat, error=None, operation="review"
        )
        seat["observed"]["review"]["verified_at"] = "2026-07-16T03:00:00.000000Z"
        self.assertTrue(state.review_qualified(seat))

    def test_qualification_uses_real_timestamp_order_within_one_second(self):
        seat = self.seat("cursor")
        seat["observed"]["review"] = state.observed(
            "ready", "none", seat=seat, error=None, operation="review"
        )
        seat["observed"]["review"]["verified_at"] = "2026-07-16T12:00:00.000000Z"
        seat["observed"]["smoke"] = state.observed(
            "setup_required",
            "auth",
            seat=seat,
            error="auth failed",
            operation="smoke",
        )
        seat["observed"]["smoke"]["verified_at"] = "2026-07-16T12:00:00.100000Z"
        self.assertFalse(state.review_qualified(seat))

    def test_single_family_profile_is_valid_on_one_family_device(self):
        config = self.example()
        config["seats"] = [config["seats"][0]]
        for profile in config["profiles"].values():
            for binding in profile:
                binding["seat"] = "example-codex"
        state.validate_config(config)

    def test_profile_persona_order_and_seats_are_closed(self):
        config = self.example()
        config["profiles"]["deep"][1]["persona"] = "Adversary"
        with self.assertRaisesRegex(state.ConfigError, "expected 'Pragmatist'"):
            state.validate_config(config)

    def test_unqualified_cline_seat_is_configured_but_not_profile_bound(self):
        config = state.validate_config(self.example())
        bound = {
            binding["seat"]
            for bindings in config["profiles"].values()
            for binding in bindings
        }
        self.assertIn("example-cline", {seat["id"] for seat in config["seats"]})
        self.assertNotIn("example-cline", bound)

    def test_observed_status_and_failure_class_must_be_coherent(self):
        config = self.example()
        config["seats"][0]["observed"]["review"]["status"] = "ready"
        with self.assertRaisesRegex(state.ConfigError, "ready requires"):
            state.validate_config(config)
        config = self.example()
        config["seats"][0]["observed"]["review"]["failure_class"] = "timeout"
        with self.assertRaisesRegex(state.ConfigError, "temporary failures"):
            state.validate_config(config)
        config = self.example()
        config["profiles"]["fast"][0]["seat"] = "missing"
        with self.assertRaisesRegex(state.ConfigError, "unknown configured seat"):
            state.validate_config(config)

    def test_setup_discovery_prefers_agent_and_skips_configured_adapters(self):
        config = self.example()
        config["seats"] = [config["seats"][0]]

        def which(name):
            return {
                "agent": "/opt/bin/agent",
                "cursor-agent": "/opt/bin/cursor-agent",
                "cline": "/opt/bin/cline",
            }.get(name)

        with mock.patch.object(state.shutil, "which", side_effect=which):
            self.assertEqual(
                state.setup_available(config),
                [
                    {"adapter": "cursor", "executable": "/opt/bin/agent"},
                    {"adapter": "cline", "executable": "/opt/bin/cline"},
                ],
            )

    def test_failure_recovery_depends_on_failure_class(self):
        seat = self.seat("cline")
        timeout = state.recovery_for(seat, "timeout", operation="review")
        invalid = state.recovery_for(seat, "invalid_output", operation="smoke")
        auth = state.recovery_for(seat, "auth")
        not_run = state.recovery_for(seat, "not_run")
        self.assertIn("Wait", timeout)
        self.assertIn("representative review", timeout)
        self.assertIn("structured output", invalid)
        self.assertIn("live smoke", invalid)
        self.assertIn("Authenticate the ClinePass provider", auth)
        self.assertIn("Deliberately bind", not_run)
        self.assertNotEqual(timeout, auth)

    def test_persist_observed_does_not_overwrite_newer_disk_state(self):
        config = self.example()
        stale = config["seats"][0]
        stale["observed"]["review"] = state.observed(
            "setup_required", "adapter_error", seat=stale, error="stale"
        )
        stale["observed"]["review"]["verified_at"] = "2026-07-16T01:00:00.000000Z"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "council-config.json"
            disk = copy.deepcopy(config)
            disk["seats"][0]["observed"]["review"] = state.observed(
                "ready", "none", seat=disk["seats"][0], error=None
            )
            disk["seats"][0]["observed"]["review"]["verified_at"] = (
                "2026-07-16T02:00:00.000000Z"
            )
            path.write_text(json.dumps(disk))
            state.persist_observed(path, config)
            persisted = json.loads(path.read_text())

        self.assertEqual(
            persisted["seats"][0]["observed"]["review"]["status"], "ready"
        )

    def test_persist_rejects_qualification_that_invalidates_profile_diversity(self):
        config = self.example()
        codex = config["seats"][0]
        cline = config["seats"][2]
        for seat in (codex, cline):
            seat["observed"]["smoke"] = state.observed(
                "ready", "none", seat=seat, error=None, operation="smoke"
            )
        codex["observed"]["review"] = state.observed(
            "ready", "none", seat=codex, error=None, operation="review"
        )
        cline["observed"]["review"] = state.observed(
            "temporarily_unavailable",
            "timeout",
            seat=cline,
            error="review timed out",
            operation="review",
        )
        config["seats"] = [codex, cline]
        for profile in config["profiles"].values():
            for binding in profile:
                binding["seat"] = codex["id"]
        state.validate_config(config)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "council-config.json"
            state.atomic_write_json(path, config)
            cline["observed"]["review"] = state.observed(
                "ready", "none", seat=cline, error=None, operation="review"
            )
            with self.assertRaisesRegex(state.ConfigError, "model families"):
                state.persist_observed(path, config)
            persisted = state.load_config(path)

        self.assertEqual(
            persisted["seats"][1]["observed"]["review"]["failure_class"],
            "timeout",
        )


class AdapterReceiptTests(unittest.TestCase):
    def example(self):
        return json.loads((ROOT / "council-config.example.json").read_text())

    def seat(self, adapter):
        return next(seat for seat in self.example()["seats"] if seat["adapter"] == adapter)

    def parse_fixture(self, adapter, filename):
        seat = self.seat(adapter)
        fixture_models = {
            "cursor": "composer-2.5-fast",
            "cline": "cline-pass/deepseek-v4-flash",
            "claude": "claude-opus-4-8",
        }
        seat["model"] = fixture_models.get(adapter, seat["model"])
        return adapters.adapter_for(seat).parse_receipt(
            (FIXTURES / filename).read_text(), seat, seat["executable"]
        )

    def test_codex_fixture(self):
        parsed = self.parse_fixture("codex", "codex.jsonl")
        self.assertEqual(parsed.output, runtime.SMOKE_EXPECTED)
        self.assertEqual(parsed.identity["model"]["assurance"], "command")

    def test_cursor_fixture(self):
        parsed = self.parse_fixture("cursor", "cursor.jsonl")
        self.assertEqual(parsed.output, runtime.SMOKE_EXPECTED)
        self.assertEqual(parsed.identity["model"]["evidence"], "Composer 2.5 Fast")

    def test_cline_fixture(self):
        parsed = self.parse_fixture("cline", "cline.jsonl")
        self.assertEqual(parsed.output, runtime.SMOKE_EXPECTED)
        self.assertEqual(parsed.identity["provider"]["assurance"], "receipt")

    def test_claude_fixture(self):
        parsed = self.parse_fixture("claude", "claude.json")
        self.assertEqual(parsed.output, runtime.SMOKE_EXPECTED)
        self.assertEqual(parsed.identity["model"]["configured"], "claude-opus-4-8")

    def test_receipts_reject_model_or_auth_mismatch(self):
        seat = self.seat("cursor")
        bad = (FIXTURES / "cursor.jsonl").read_text().replace('"env"', '"login"')
        with self.assertRaisesRegex(adapters.ReceiptError, "auth source mismatch"):
            adapters.adapter_for(seat).parse_receipt(bad, seat, seat["executable"])
        seat = self.seat("cline")
        bad = (FIXTURES / "cline.jsonl").read_text().replace("deepseek-v4-flash", "kimi-k2.7-code")
        with self.assertRaisesRegex(adapters.ReceiptError, "identity mismatch"):
            adapters.adapter_for(seat).parse_receipt(bad, seat, seat["executable"])

    def test_receipts_reject_extra_or_missing_terminal_records(self):
        seat = self.seat("codex")
        duplicate = (FIXTURES / "codex.jsonl").read_text() * 2
        with self.assertRaisesRegex(adapters.ReceiptError, "exactly one"):
            adapters.adapter_for(seat).parse_receipt(duplicate, seat, seat["executable"])

    def test_jsonl_receipts_reject_contradictory_terminal_records(self):
        cases = {
            "codex": ("codex.jsonl", '{"type":"turn.failed"}\n'),
            "cursor": (
                "cursor.jsonl",
                '{"type":"result","subtype":"error","is_error":true}\n',
            ),
            "cline": (
                "cline.jsonl",
                '{"type":"run_result","finishReason":"timeout"}\n',
            ),
        }
        fixture_models = {
            "cursor": "composer-2.5-fast",
            "cline": "cline-pass/deepseek-v4-flash",
        }
        for adapter, (filename, terminal) in cases.items():
            with self.subTest(adapter=adapter):
                seat = self.seat(adapter)
                seat["model"] = fixture_models.get(adapter, seat["model"])
                payload = (FIXTURES / filename).read_text() + terminal
                with self.assertRaisesRegex(adapters.ReceiptError, "exactly one"):
                    adapters.adapter_for(seat).parse_receipt(
                        payload, seat, seat["executable"]
                    )

    def test_adapter_failure_contracts_normalize_capacity_and_auth(self):
        capacity = (
            "Usage limit reached",
            "insufficient credits",
            "quota exceeded",
            "HTTP 429",
        )
        auth = ("HTTP 401", "not logged in", "please sign in")
        for contract in adapters.ADAPTERS.values():
            for message in capacity:
                self.assertEqual(contract.classify_failure("", message), "capacity")
            for message in auth:
                self.assertEqual(contract.classify_failure("", message), "auth")
            self.assertEqual(
                contract.classify_failure(
                    '{"type":"error","message":"quota exceeded"}', ""
                ),
                "capacity",
            )
            self.assertEqual(
                contract.classify_failure(
                    '{"type":"agent_message","text":"please sign in"}', ""
                ),
                "adapter_error",
            )


class RuntimeTests(unittest.TestCase):
    def example(self):
        return json.loads((ROOT / "council-config.example.json").read_text())

    def seat(self, adapter):
        return next(seat for seat in self.example()["seats"] if seat["adapter"] == adapter)

    def persona_output(self, seat, persona, **overrides):
        value = {
            "persona": persona,
            "engine": adapters.adapter_for(seat).engine,
            "model": seat["model"],
            "verdict": "PASS",
            "findings": [],
            "biggest_risk": "No material defect found.",
        }
        value.update(overrides)
        return value

    def test_environment_scopes_cursor_key_to_cursor_child(self):
        cursor = self.seat("cursor")
        codex = self.seat("codex")
        with mock.patch.dict(
            os.environ,
            {"CURSOR_API_KEY": "secret-cursor-value", "BWS_ACCESS_TOKEN": "secret-bws-value"},
            clear=False,
        ):
            cursor_env = runtime._environment(cursor)
            codex_env = runtime._environment(codex)
        self.assertEqual(cursor_env["CURSOR_API_KEY"], "secret-cursor-value")
        self.assertNotIn("BWS_ACCESS_TOKEN", cursor_env)
        self.assertNotIn("CURSOR_API_KEY", codex_env)
        self.assertNotIn("BWS_ACCESS_TOKEN", codex_env)

    def test_invoke_executes_exactly_one_model_process(self):
        seat = self.seat("codex")
        seat["executable"] = "/bin/echo"
        process = mock.Mock(returncode=0, stdout=(FIXTURES / "codex.jsonl").read_text(), stderr="")
        with (
            mock.patch.object(runtime, "_probe_version", return_value="test-version"),
            mock.patch.object(runtime, "_run_bounded", return_value=process) as run,
        ):
            result = runtime._invoke(
                seat,
                kind="smoke",
                profile="fast",
                prompt=runtime.SMOKE_PROMPT,
                output_schema=runtime.smoke_output_schema(),
            )
        self.assertEqual(run.call_count, 1)
        self.assertEqual(result["status"], "valid")

    def test_version_probe_uses_the_isolated_workspace(self):
        process = mock.Mock(returncode=0, stdout="1.2.3\n", stderr="")
        workspace = Path("/tmp/isolated")
        with mock.patch.object(
            runtime, "_run_bounded", return_value=process
        ) as run:
            version = runtime._probe_version("/bin/tool", {"PWD": str(workspace)}, workspace)
        self.assertEqual(version, "1.2.3")
        self.assertEqual(run.call_args.kwargs["cwd"], workspace)
        self.assertEqual(run.call_args.kwargs["environment"]["PWD"], str(workspace))

    def test_timeout_is_not_retried_and_has_typed_recovery(self):
        seat = self.seat("codex")
        seat["executable"] = "/bin/echo"
        with (
            mock.patch.object(runtime, "_probe_version", return_value="test-version"),
            mock.patch.object(
                runtime,
                "_run_bounded",
                side_effect=runtime.subprocess.TimeoutExpired(["codex"], 20),
            ) as run,
        ):
            result = runtime._invoke(
                seat,
                kind="smoke",
                profile="fast",
                prompt=runtime.SMOKE_PROMPT,
                output_schema=runtime.smoke_output_schema(),
            )
        self.assertEqual(run.call_count, 1)
        self.assertEqual(result["seat_observed"]["failure_class"], "timeout")
        self.assertIn(
            "Wait",
            state.observation_output(seat, "smoke", result["seat_observed"])[
                "recovery"
            ],
        )

    def test_bounded_process_terminates_and_kills_the_process_group(self):
        process = mock.Mock(pid=1234)
        process.communicate.side_effect = [
            runtime.subprocess.TimeoutExpired(["adapter"], 1),
            runtime.subprocess.TimeoutExpired(["adapter"], 2),
            ("partial", "timed out"),
        ]
        with (
            mock.patch.object(runtime.subprocess, "Popen", return_value=process),
            mock.patch.object(runtime.os, "killpg") as killpg,
            self.assertRaises(runtime.subprocess.TimeoutExpired),
        ):
            runtime._run_bounded(
                ["adapter"], timeout=1, environment={}, cwd=Path("/tmp")
            )
        self.assertEqual(
            killpg.call_args_list,
            [mock.call(1234, runtime.signal.SIGTERM), mock.call(1234, runtime.signal.SIGKILL)],
        )

    def test_missing_required_environment_is_auth_failure(self):
        seat = self.seat("cursor")
        seat["executable"] = "/bin/echo"
        seat["auth"]["method"] = "secret_manager"
        seat["auth"]["required_environment"] = ["CURSOR_API_KEY"]
        with mock.patch.dict(os.environ, {}, clear=True):
            result = runtime._invoke(
                seat,
                kind="smoke",
                profile="fast",
                prompt=runtime.SMOKE_PROMPT,
                output_schema=runtime.smoke_output_schema(),
            )
        self.assertEqual(result["seat_observed"]["failure_class"], "auth")

    def test_unexpected_smoke_worker_error_is_typed_and_other_seats_are_retained(self):
        config = self.example()
        config["seats"] = config["seats"][:2]
        config["profiles"]["fast"] = [
            {"persona": "Architect", "seat": config["seats"][0]["id"]},
            {"persona": "Adversary", "seat": config["seats"][1]["id"]},
        ]
        config["profiles"]["deep"] = [
            {"persona": "Architect", "seat": config["seats"][0]["id"]},
            {"persona": "Pragmatist", "seat": config["seats"][1]["id"]},
            {"persona": "Verifier", "seat": config["seats"][0]["id"]},
            {"persona": "Adversary", "seat": config["seats"][1]["id"]},
        ]
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "council-config.json"
            config_path.write_text(json.dumps(config))

            def smoke(seat, profile):
                del profile
                if seat["adapter"] == "cursor":
                    raise TypeError("unexpected")
                seat["observed"]["smoke"] = state.observed(
                    "ready", "none", seat=seat, error=None, operation="smoke"
                )
                return {
                    "seat": seat["id"],
                    "status": "valid",
                    **seat["observed"]["smoke"],
                }

            with mock.patch.object(runtime, "smoke_seat", side_effect=smoke):
                result = runtime.smoke_all(config, config_path)

        self.assertEqual(len(result["seats"]), 2)
        self.assertEqual(result["status"], "SETUP REQUIRED")
        failed = next(
            item for item in result["seats"] if item["failure_class"] == "adapter_error"
        )
        self.assertEqual(failed["failure_class"], "adapter_error")

    def test_prompt_has_raw_json_instruction_and_no_markdown_example(self):
        seat = self.seat("codex")
        prompt = runtime.build_prompt(
            "Architect", seat, "Review it.", "", "", "", [("artifact.md", "line")], 1
        )
        self.assertIn("The first character is { and the last character is }", prompt)
        self.assertNotIn("```", prompt)

    def test_persona_output_requires_exact_identity_and_citation(self):
        seat = self.seat("codex")
        output = self.persona_output(
            seat,
            "Architect",
            verdict="CONCERNS",
            findings=[
                {
                    "severity": "M",
                    "claim": "A concrete problem",
                    "evidence": {"artifact": "artifact.md", "line": 1},
                    "why": "It breaks the contract.",
                    "fix": "Repair the contract.",
                }
            ],
        )
        parsed = runtime.parse_persona_output(
            json.dumps(output),
            persona="Architect",
            seat=seat,
            artifacts={"artifact.md": "exact cited line"},
            max_findings=1,
        )
        self.assertEqual(parsed["findings"][0]["excerpt"], "exact cited line")
        output["model"] = "wrong"
        with self.assertRaisesRegex(state.PersonaError, "identity mismatch"):
            runtime.parse_persona_output(
                json.dumps(output),
                persona="Architect",
                seat=seat,
                artifacts={"artifact.md": "exact cited line"},
                max_findings=1,
            )

    def test_persona_output_rejects_fences_blank_citations_and_bad_verdicts(self):
        seat = self.seat("codex")
        valid = self.persona_output(seat, "Architect")
        with self.assertRaisesRegex(state.PersonaError, "raw JSON"):
            runtime.parse_persona_output(
                f"```json\n{json.dumps(valid)}\n```",
                persona="Architect",
                seat=seat,
                artifacts={"artifact.md": "line"},
                max_findings=1,
            )
        bad = self.persona_output(
            seat,
            "Architect",
            verdict="CONCERNS",
            findings=[
                {
                    "severity": "M",
                    "claim": "problem",
                    "evidence": {"artifact": "artifact.md", "line": 2},
                    "why": "why",
                    "fix": "fix",
                }
            ],
        )
        with self.assertRaisesRegex(state.PersonaError, "blank line"):
            runtime.parse_persona_output(
                bad,
                persona="Architect",
                seat=seat,
                artifacts={"artifact.md": "line\n\nline"},
                max_findings=1,
            )
        bad = self.persona_output(seat, "Architect", verdict="FAIL")
        with self.assertRaisesRegex(state.PersonaError, "High"):
            runtime.parse_persona_output(
                bad,
                persona="Architect",
                seat=seat,
                artifacts={"artifact.md": "line"},
                max_findings=1,
            )

    def test_oversized_prompt_fails_before_any_persona(self):
        config = self.example()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "council-config.json"
            state.atomic_write_json(config_path, config)
            (root / "artifact.md").write_text("x" * runtime.PROFILE_MAX_PROMPT_BYTES["fast"])
            with mock.patch.object(runtime.Path, "cwd", return_value=root):
                with self.assertRaisesRegex(state.RequestError, "maximum"):
                    runtime.review(
                        config,
                        config_path,
                        "fast",
                        "Review it.",
                        "",
                        "",
                        "",
                        ["artifact.md"],
                    )

    def test_review_freezes_all_bindings_and_never_reassigns(self):
        config = self.example()
        calls = []

        def invoke(seat, *, kind, profile, prompt, output_schema):
            self.assertEqual(kind, "review")
            persona = next(line.removeprefix("PERSONA: ") for line in prompt.splitlines() if line.startswith("PERSONA: "))
            calls.append((persona, seat["id"]))
            return {
                "status": "valid",
                "output": self.persona_output(seat, persona),
                "identity": {},
                "seat_observed": state.observed("ready", "none", seat=seat, error=None),
            }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "council-config.json"
            state.atomic_write_json(config_path, config)
            (root / "artifact.md").write_text("evidence line")
            with (
                mock.patch.object(runtime.Path, "cwd", return_value=root),
                mock.patch.object(runtime, "_invoke", side_effect=invoke),
            ):
                result, code = runtime.review(
                    config,
                    config_path,
                    "deep",
                    "Review it.",
                    "",
                    "",
                    "",
                    ["artifact.md"],
                )
        self.assertEqual(code, 0)
        self.assertEqual(result["council_status"], "complete")
        self.assertEqual(len(calls), 4)
        self.assertEqual({seat for _persona, seat in calls}, {
            "example-codex",
            "example-cursor",
            "example-claude",
        })
        self.assertEqual(result["coverage"]["distinct_families"], [
            "openai",
            "cursor",
            "anthropic",
        ])
        self.assertEqual(result["coverage"]["independent_invocations"], 4)
        self.assertEqual(result["coverage"]["serialized_batches"], 2)

    def test_failed_persona_makes_review_incomplete_without_second_call(self):
        config = self.example()
        counts = {}

        def invoke(seat, *, kind, profile, prompt, output_schema):
            counts[seat["id"]] = counts.get(seat["id"], 0) + 1
            persona = next(line.removeprefix("PERSONA: ") for line in prompt.splitlines() if line.startswith("PERSONA: "))
            if seat["adapter"] == "claude":
                return {
                    "status": "failed",
                    "error": "timeout",
                    "seat_observed": state.observed(
                        "temporarily_unavailable",
                        "timeout",
                        seat=seat,
                        error="review timed out",
                        operation="review",
                    ),
                }
            return {
                "status": "valid",
                "output": self.persona_output(seat, persona),
                "identity": {},
                "seat_observed": state.observed("ready", "none", seat=seat, error=None),
            }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "council-config.json"
            state.atomic_write_json(config_path, config)
            (root / "artifact.md").write_text("evidence line")
            with (
                mock.patch.object(runtime.Path, "cwd", return_value=root),
                mock.patch.object(runtime, "_invoke", side_effect=invoke),
            ):
                result, code = runtime.review(
                    config,
                    config_path,
                    "deep",
                    "Review it.",
                    "",
                    "",
                    "",
                    ["artifact.md"],
                )
        self.assertEqual(code, 3)
        self.assertEqual(result["council_status"], "INCOMPLETE")
        self.assertEqual(counts["example-claude"], 1)
        self.assertEqual(sum(counts.values()), 4)

    def test_smoke_success_does_not_overwrite_review_timeout(self):
        config = self.example()
        seat = next(seat for seat in config["seats"] if seat["adapter"] == "cline")
        config["seats"] = [seat]
        config["profiles"] = {
            profile: [
                {"persona": persona, "seat": seat["id"]}
                for persona in state.PROFILE_PERSONAS[profile]
            ]
            for profile in state.PROFILE_PERSONAS
        }

        def review_timeout(seat, *, kind, profile, prompt, output_schema):
            del profile, prompt, output_schema
            self.assertEqual(kind, "review")
            observation = state.observed(
                "temporarily_unavailable",
                "timeout",
                seat=seat,
                error="representative review timed out",
                operation="review",
            )
            return {
                "status": "failed",
                "error": "timeout",
                "seat_observed": observation,
            }

        def smoke_ready(seat, *, kind, profile, prompt, output_schema):
            del profile, prompt, output_schema
            self.assertEqual(kind, "smoke")
            return {
                "status": "valid",
                "output": runtime.SMOKE_EXPECTED,
                "identity": {},
                "seat_observed": state.observed(
                    "ready", "none", seat=seat, error=None, operation="smoke"
                ),
            }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "council-config.json"
            state.atomic_write_json(config_path, config)
            (root / "artifact.md").write_text("evidence line")
            with (
                mock.patch.object(runtime.Path, "cwd", return_value=root),
                mock.patch.object(runtime, "_invoke", side_effect=review_timeout),
            ):
                result, code = runtime.review(
                    config,
                    config_path,
                    "fast",
                    "Review it.",
                    "",
                    "",
                    "",
                    ["artifact.md"],
                )
            self.assertEqual(code, 3)
            self.assertEqual(result["council_status"], "INCOMPLETE")
            refreshed = state.load_config(config_path)
            with mock.patch.object(runtime, "_invoke", side_effect=smoke_ready):
                smoke = runtime.smoke_all(refreshed, config_path, all_seats=True)
            persisted = state.load_config(config_path)

        self.assertEqual(smoke["status"], "ready")
        self.assertEqual(persisted["seats"][0]["observed"]["smoke"]["status"], "ready")
        self.assertEqual(
            persisted["seats"][0]["observed"]["review"]["failure_class"],
            "timeout",
        )
        self.assertIn(
            "representative review",
            state.observation_output(
                persisted["seats"][0],
                "review",
                persisted["seats"][0]["observed"]["review"],
            )["recovery"],
        )

    def test_duplicate_seat_bindings_are_serialized(self):
        config = self.example()
        seat = config["seats"][0]
        config["seats"] = [seat]
        config["profiles"] = {
            profile: [
                {"persona": persona, "seat": seat["id"]}
                for persona in state.PROFILE_PERSONAS[profile]
            ]
            for profile in state.PROFILE_PERSONAS
        }
        active = 0
        peak = 0
        guard = threading.Lock()

        def invoke(seat, *, kind, profile, prompt, output_schema):
            nonlocal active, peak
            del kind, profile, output_schema
            persona = next(
                line.removeprefix("PERSONA: ")
                for line in prompt.splitlines()
                if line.startswith("PERSONA: ")
            )
            with guard:
                active += 1
                peak = max(peak, active)
            runtime.time.sleep(0.01)
            with guard:
                active -= 1
            return {
                "status": "valid",
                "output": self.persona_output(seat, persona),
                "identity": {},
                "seat_observed": state.observed("ready", "none", seat=seat, error=None),
            }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "council-config.json"
            state.atomic_write_json(config_path, config)
            (root / "artifact.md").write_text("evidence line")
            with (
                mock.patch.object(runtime.Path, "cwd", return_value=root),
                mock.patch.object(runtime, "_invoke", side_effect=invoke),
            ):
                result, code = runtime.review(
                    config,
                    config_path,
                    "deep",
                    "Review it.",
                    "",
                    "",
                    "",
                    ["artifact.md"],
                )

        self.assertEqual(code, 0)
        self.assertEqual(result["coverage"]["independent_invocations"], 4)
        self.assertEqual(result["coverage"]["serialized_batches"], 4)
        self.assertEqual(peak, 1)


if __name__ == "__main__":
    unittest.main()
