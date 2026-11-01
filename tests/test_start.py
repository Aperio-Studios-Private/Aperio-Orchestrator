"""Tests for the start command (apero start — one-command project setup)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from aperio.start import start_project
from aperio.store import Project

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


class StartTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "my-project"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_creates_project_with_all_gates_satisfied(self) -> None:
        start_project(self.root, name="My Project", ask="Build me a landing page")
        self.assertTrue((self.root / ".aperio" / "project.json").is_file())
        project = Project.open(self.root)
        self.assertEqual(len(project.asks()), 1)
        self.assertEqual(project.asks()[0].source, "owner")
        self.assertTrue((self.root / ".aperio" / "learning.json").is_file())
        self.assertTrue((self.root / ".aperio" / "readiness.json").is_file())
        self.assertTrue((self.root / ".aperio" / "discovery.json").is_file())
        # Todo started
        from aperio.todo import status as todo_status

        todo = todo_status(project)
        self.assertEqual(todo["in_progress"], 1)

    def test_gates_pass_after_start(self) -> None:
        """The strongest check: after start, the plan gate should not refuse
        on any of the pre-plan conditions (learning, todo, readiness, discovery)."""
        start_project(self.root, name="Test", ask="Build something")
        self.project = Project.open(self.root)
        from aperio.cli import cmd_next, cmd_plan  # noqa: F401 — verify imports work
        from aperio.discovery import status as discovery_status
        from aperio.learning import status as learning_status
        from aperio.readiness import validate_preflight
        from aperio.todo import status as todo_status

        self.assertTrue(learning_status(self.project)["ready"])
        self.assertTrue(discovery_status(self.project)["ready"])
        self.assertEqual(todo_status(self.project)["in_progress"], 1)
        issues = validate_preflight(self.project)
        self.assertEqual(issues, [])

    def test_ask_is_recorded_with_owner_source(self) -> None:
        start_project(self.root, name="Test", ask="Build me a REST API")
        self.project = Project.open(self.root)
        asks = self.project.asks()
        self.assertEqual(len(asks), 1)
        self.assertEqual(asks[0].text, "Build me a REST API")
        self.assertEqual(asks[0].source, "owner")

    def test_cli_start(self) -> None:
        target = self.root.parent / "cli-project"
        result = subprocess.run(
            [sys.executable, "-m", "aperio", "start", str(target),
             "--name", "CLI Test", "--ask", "Build a tool"],
            capture_output=True, text=True, check=False,
            cwd=str(ROOT),
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(SRC)),
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Aperio ready", result.stdout)
        self.assertTrue((target / ".aperio" / "project.json").is_file())

    def test_start_on_existing_fixture_does_not_clobber(self) -> None:
        start_project(self.root, name="First")
        before = (self.root / ".aperio" / "project.json").read_text(encoding="utf-8")
        # Calling start again on the same directory is safe (idempotent gates).
        start_project(self.root, name="First", ask="Updated ask")
        after = (self.root / ".aperio" / "project.json").read_text(encoding="utf-8")
        # project.json should be unchanged (same project id)
        self.assertEqual(json.loads(before)["id"], json.loads(after)["id"])


if __name__ == "__main__":
    unittest.main()
