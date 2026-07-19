import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InstallTest(unittest.TestCase):
    def run_install(self, *agents):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        env = os.environ.copy()
        for agent in ("claude", "codex", "cursor", "cline"):
            env[f"{agent.upper()}_SKILLS_DIR"] = str(root / agent)
        result = subprocess.run(
            [str(ROOT / "install.sh"), *agents],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        return root, result

    def tearDown(self):
        if hasattr(self, "temp"):
            self.temp.cleanup()

    def test_all_installs_each_skill_for_four_agents(self):
        root, result = self.run_install("all")
        self.assertEqual(result.returncode, 0, result.stderr)
        for agent in ("claude", "codex", "cursor", "cline"):
            self.assertTrue((root / agent / "apply-paper").is_symlink(), agent)
            self.assertIn(f"{agent}:", result.stdout)

    def test_cline_target_uses_cline_override(self):
        root, result = self.run_install("cline")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((root / "cline" / "apply-paper").is_symlink())
        self.assertFalse((root / "codex").exists())

    def test_unknown_agent_lists_cline(self):
        _, result = self.run_install("other")
        self.assertEqual(result.returncode, 2)
        self.assertIn("claude|codex|cursor|cline|all", result.stderr)


if __name__ == "__main__":
    unittest.main()
