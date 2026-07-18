import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "workshop.py"
WORK_UNIT = "f84bad5c-2488-41f4-ae0b-75003a5f0b5b"


class WorkshopCliTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.receipt = self.root / "WORKSHOP.json"

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, arguments)],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )

    def init(self, tier="method", bundles_code=None, effort=None):
        arguments = [
            "init",
            "--tier",
            tier,
            "--work-unit",
            WORK_UNIT,
            "--author-family",
            "openai",
            "--output",
            self.receipt,
        ]
        if bundles_code is not None:
            arguments += ["--bundles-code", str(bundles_code).lower()]
        if effort is not None:
            arguments += ["--effort", effort]
        result = self.run_cli(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(self.receipt.read_text())

    def write_json(self, value):
        self.receipt.write_text(json.dumps(value, indent=2) + "\n")

    def touch(self, relative, content="ok\n"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def command(self, name, command=None):
        receipt = f"receipts/{name}.txt"
        self.touch(receipt)
        return {
            "command": command or f"run-{name}",
            "exit_code": 0,
            "receipt": receipt,
            "dry_run": False,
        }

    def complete_method(self):
        value = self.init()
        for path in value["artifacts"].values():
            self.touch(path)
        value["evidence"]["baseline"] = self.command("baseline")
        value["evidence"]["behavioral"] = self.command("behavioral")
        value["evidence"]["forward_tests"] = [
            {**self.command("forward-openai"), "family": "openai"},
            {**self.command("forward-anthropic"), "family": "anthropic"},
        ]
        value["evidence"]["lint"] = self.command("lint")
        value["evidence"]["install"] = {
            **self.command("install"),
            "targets": ["claude", "codex", "cursor", "cline"],
        }
        value["evidence"]["councils"] = []
        for phase in ("spec", "final"):
            evidence = self.command(f"council-{phase}")
            value["evidence"]["councils"].append(
                {
                    "phase": phase,
                    "profile": "fast",
                    "families": ["openai", "anthropic"],
                    "status": "pass",
                    "receipt": evidence["receipt"],
                }
            )
        self.write_json(value)
        return value

    def check(self):
        return self.run_cli("check", self.receipt)

    def test_init_method_is_deterministic_and_incomplete(self):
        first = self.init()
        self.assertEqual(
            set(first),
            {
                "schema_version",
                "work_unit",
                "tier",
                "bundles_code",
                "effort",
                "author_family",
                "artifacts",
                "evidence",
            },
        )
        self.assertEqual(first["tier"], "method")
        self.assertFalse(first["bundles_code"])
        self.assertEqual(first["effort"], "standard")
        self.assertEqual(set(first["artifacts"]), {"spec", "skill", "deviations"})
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "incomplete")

    def test_init_refuses_to_overwrite(self):
        self.init()
        result = self.run_cli(
            "init",
            "--tier",
            "method",
            "--work-unit",
            WORK_UNIT,
            "--author-family",
            "openai",
            "--output",
            self.receipt,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing to overwrite", result.stderr)

    def test_complete_method_passes(self):
        self.complete_method()
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "complete")

    def test_structural_errors_take_precedence(self):
        value = self.init()
        value["tier"] = "scripted"
        self.write_json(value)
        result = self.check()
        body = json.loads(result.stdout)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(body["status"], "invalid")
        self.assertTrue(all(error.startswith("invalid:") for error in body["errors"]))

    def test_duplicate_forward_test_families_are_incomplete(self):
        value = self.complete_method()
        value["evidence"]["forward_tests"][1]["family"] = "openai"
        self.write_json(value)
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("distinct families", result.stdout)

    def test_shared_baseline_behavioral_receipt_is_incomplete(self):
        value = self.complete_method()
        value["evidence"]["behavioral"]["receipt"] = value["evidence"]["baseline"]["receipt"]
        self.write_json(value)
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("baseline and behavioral receipts must differ", result.stdout)

    def test_shared_forward_test_receipt_is_incomplete(self):
        value = self.complete_method()
        shared = value["evidence"]["forward_tests"][0]["receipt"]
        value["evidence"]["forward_tests"][1]["receipt"] = shared
        self.write_json(value)
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("distinct receipts", result.stdout)

    def test_cross_gate_receipt_reuse_is_incomplete(self):
        value = self.complete_method()
        value["evidence"]["lint"]["receipt"] = value["evidence"]["install"]["receipt"]
        self.write_json(value)
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("reuses a receipt already used by another gate", result.stdout)

    def test_empty_receipt_is_incomplete(self):
        value = self.complete_method()
        self.touch(value["evidence"]["baseline"]["receipt"], content="")
        self.write_json(value)
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("must not be an empty file", result.stdout)

    def test_report_renders_readable_artifact(self):
        self.complete_method()
        out = self.root / "REPORT.md"
        result = self.run_cli("report", self.receipt, "--output", str(out))
        self.assertEqual(result.returncode, 0, result.stderr)
        text = out.read_text()
        self.assertIn("completion report", text)
        self.assertIn("Baseline eval", text)
        self.assertIn("Council: spec/fast", text)
        # every gate renders the rubric: INPUT -> OUTPUT -> GRADE
        self.assertIn("**INPUT:**", text)
        self.assertIn("**OUTPUT:**", text)
        self.assertIn("**GRADE:**", text)
        # receipt contents are inlined for semantic review, not just referenced
        self.assertIn("run-baseline", text)

    def test_report_html_is_self_contained(self):
        self.complete_method()
        out = self.root / "REPORT.html"
        result = self.run_cli("report", self.receipt, "--format", "html", "--output", str(out))
        self.assertEqual(result.returncode, 0, result.stderr)
        text = out.read_text()
        self.assertIn("<!doctype html>", text)
        self.assertNotIn("http://", text.split("<title>")[0])  # no external asset before title

    def test_null_forward_records_are_invalid_not_a_crash(self):
        value = self.init()
        value["evidence"]["forward_tests"] = [None, None]
        self.write_json(value)
        result = self.check()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "invalid")

    def test_duplicate_council_records_are_incomplete(self):
        value = self.complete_method()
        value["evidence"]["councils"].append(value["evidence"]["councils"][1])
        self.write_json(value)
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("exactly two", result.stdout)

    def test_escaping_artifact_is_invalid(self):
        value = self.complete_method()
        value["artifacts"]["spec"] = "../SPEC.md"
        self.write_json(value)
        self.assertEqual(self.check().returncode, 2)

    def test_symlink_artifact_is_incomplete(self):
        value = self.complete_method()
        target = self.root / "real-spec.md"
        target.write_text("spec\n")
        link = self.root / value["artifacts"]["spec"]
        link.unlink()
        link.symlink_to(target)
        self.write_json(value)
        self.assertEqual(self.check().returncode, 1)

    def test_artifact_beneath_symlinked_directory_is_incomplete(self):
        value = self.complete_method()
        real = self.root / "real"
        real.mkdir()
        (real / "SPEC.md").write_text("spec\n")
        linked = self.root / "linked"
        linked.symlink_to(real, target_is_directory=True)
        value["artifacts"]["spec"] = "linked/SPEC.md"
        self.write_json(value)
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("non-symlink", result.stdout)

    def test_integration_requires_identity_and_no_substitution(self):
        value = self.init(tier="integration", bundles_code=False, effort="deep")
        self.assertIn("live", value["evidence"])
        value["evidence"]["live"] = {
            "provider": "cline",
            "model": "glm-4.5-air",
            "auth_kind": "oauth",
            "device_config": "council-config.json",
            "status": "ready",
            "failure_class": "none",
            "recovery": None,
        }
        value["evidence"]["representative"] = {
            **self.command("representative"),
            "observed_provider": "cline",
            "observed_model": "glm-4.5-air",
            "substituted": True,
        }
        self.write_json(value)
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("substituted", result.stdout)

    def test_config_example_is_fail_closed(self):
        value = self.init(tier="integration", bundles_code=False, effort="deep")
        self.touch(value["artifacts"]["config_example"], '{"credential":"live-value"}\n')
        self.touch(value["artifacts"]["ignore_file"], "council-config.json\n")
        value["evidence"]["live"] = {
            "provider": "cline",
            "model": "glm-4.5-air",
            "auth_kind": "oauth",
            "device_config": "council-config.json",
            "status": "ready",
            "failure_class": "none",
            "recovery": None,
        }
        self.write_json(value)
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("PLACEHOLDER", result.stdout)

    def test_device_config_may_be_absent_when_exactly_ignored(self):
        value = self.init(tier="integration", bundles_code=False, effort="deep")
        self.assertFalse((self.root / "council-config.json").exists())
        self.touch(value["artifacts"]["ignore_file"], "council-config.json\n")
        self.touch(value["artifacts"]["config_example"], '{"model":"${MODEL}"}\n')
        value["evidence"]["live"] = {
            "provider": "cline",
            "model": "glm-4.5-air",
            "auth_kind": "oauth",
            "device_config": "council-config.json",
            "status": "ready",
            "failure_class": "none",
            "recovery": None,
        }
        self.write_json(value)
        result = self.check()
        self.assertNotIn("device config file", result.stdout)

    def test_nested_device_config_requires_exact_non_negated_rule(self):
        value = self.init(tier="integration", bundles_code=False, effort="deep")
        self.touch(value["artifacts"]["ignore_file"], "other/council-config.json\n")
        self.touch(value["artifacts"]["config_example"], '{"model":"${MODEL}"}\n')
        value["evidence"]["live"] = {
            "provider": "cline",
            "model": "glm-4.5-air",
            "auth_kind": "oauth",
            "device_config": "config/council-config.json",
            "status": "ready",
            "failure_class": "none",
            "recovery": None,
        }
        self.write_json(value)
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("exact positive device-config rule", result.stdout)

        self.touch(
            value["artifacts"]["ignore_file"],
            "config/council-config.json\n!config/council-config.json\n",
        )
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("negated", result.stdout)

    def test_smoke_and_representative_must_differ(self):
        value = self.init(tier="integration", bundles_code=False, effort="deep")
        evidence = self.command("same", command="cline smoke")
        value["evidence"]["smoke"] = evidence
        value["evidence"]["representative"] = {
            **evidence,
            "observed_provider": "cline",
            "observed_model": "glm-4.5-air",
            "substituted": False,
        }
        self.write_json(value)
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("must differ", result.stdout)


if __name__ == "__main__":
    unittest.main()
