"""Black-box CLI tests, isolated from users' real experiments."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class CLIBase(unittest.TestCase):
    def setUp(self):
        # Keep temporary projects under the known writable checkout. Some managed
        # Windows runtimes redirect system TEMP to an inaccessible sandbox path.
        temp_root = REPO / ".test-tmp"
        temp_root.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="paper-composer-test-", dir=temp_root)
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name) / "project"

    def run_cli(self, *args):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        return subprocess.run(
            [sys.executable, "-m", "paper_composer", *map(str, args)],
            cwd=REPO,
            env=env,
            capture_output=True,
            encoding="utf-8",
            timeout=30,
        )

    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_rejected(self, result):
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertNotIn("Traceback (most recent call last)", result.stderr)


class CommandTests(CLIBase):
    def test_help_is_available_without_network_or_install(self):
        result = self.run_cli("--help")
        self.assert_ok(result)
        for command in ("init", "validate", "freeze", "record", "report", "demo"):
            self.assertIn(command, result.stdout)

    def test_init_does_not_overwrite_existing_project(self):
        self.assert_ok(self.run_cli("init", self.project, "--name", "test fixture"))
        before = {p.relative_to(self.project): p.read_bytes()
                  for p in self.project.rglob("*") if p.is_file()}
        self.assert_rejected(self.run_cli("init", self.project, "--name", "overwrite"))
        after = {p.relative_to(self.project): p.read_bytes()
                 for p in self.project.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_invalid_module_count_rejected(self):
        for count in ("0", "1", "4", "-1", "two"):
            with self.subTest(count=count):
                self.assert_rejected(self.run_cli("init", self.project, "--modules", count))
                self.assertFalse(self.project.exists())

    def test_missing_project_reports_controlled_error(self):
        for command in ("validate", "freeze", "report", "ablations"):
            with self.subTest(command=command):
                self.assert_rejected(self.run_cli(command, self.project))

    def test_demo_does_not_overwrite_existing_directory(self):
        self.project.mkdir()
        marker = self.project / "keep.txt"
        marker.write_text("existing unrelated content", encoding="utf-8")
        self.assert_rejected(self.run_cli("demo", self.project))
        self.assertEqual(marker.read_text(encoding="utf-8"), "existing unrelated content")

    def test_report_output_cannot_overwrite_protocol_input(self):
        self.assert_ok(self.run_cli("init", self.project))
        brief = self.project / "brief.json"
        before = brief.read_bytes()
        self.assert_rejected(self.run_cli("report", self.project, "--output", brief))
        self.assertEqual(brief.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
