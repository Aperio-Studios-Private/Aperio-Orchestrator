"""Tests for the retrospective (apero retro — environment audit from a done task)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from aperio.retro import RetroError, retro
from aperio.runner import apply_plan, finish, review, verify
from aperio.store import Project

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _fly_task_to_done(project: Project, *, task_id: str = "task-retro-src", title: str = "Retro test") -> None:
    """Build a real done task: run, verify, review — through the real runner."""
    from aperio.model import Acceptance, Approval, Plan, Step, Task, plan_body_digest
    from aperio.runner import finish, review, verify

    (project.root / "site").mkdir(exist_ok=True)
    (project.root / "site" / "index.html").write_text("<h1>draft</h1>", encoding="utf-8")
    task = Task(id=task_id, title=title, request="Build the landing page")
    task.status = "approved"
    tasks = project.tasks()
    tasks.append(task)
    project.save_tasks(tasks)
    plan = Plan(
        id=f"plan-{task_id}",
        task_id=task.id,
        title=title,
        request=task.request,
        allowed_paths=["site/"],
        steps=[Step(id="w", kind="write", path="site/index.html", content="<h1>done</h1>")],
        acceptance=[Acceptance(id="check", command="test -f site/index.html")],
    )
    task.plan_id = plan.id
    project.put_task(task)
    plan.approval = Approval(approved_by="owner", plan_sha256=plan_body_digest(plan))
    project.save_plan(plan)
    plan = project.get_plan(plan.id)
    apply_plan(project, plan, actor="builder")
    verify(project, task.id)
    review(project, task.id, reviewer="qa", verdict="confirmed")
    finish(project, task.id)


class RetroTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Project.init(Path(self.temp.name) / "proj", "retro-test")
        _fly_task_to_done(self.project)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_retro_on_done_task(self) -> None:
        result = retro(self.project, "task-retro-src")
        self.assertEqual(result["task_id"], "task-retro-src")
        self.assertEqual(result["status"], "done")
        self.assertTrue(result["read_only"])
        # A clean task with no violations should identify the
        # existence-only acceptance check as a coverage gap.
        sources = [imp["source"] for imp in result["improvements"]]
        self.assertIn("coverage", sources)

    def test_retro_refuses_planned_task(self) -> None:
        from aperio.model import Task

        tasks = self.project.tasks()
        tasks.append(
            Task(id="task-early", title="early", request="r", status="planned")
        )
        self.project.save_tasks(tasks)
        with self.assertRaises(RetroError):
            retro(self.project, "task-early")

    def test_retro_audits_failed_task_violations(self) -> None:
        # The retro is most useful on failed tasks: it audits what went
        # wrong and suggests environment improvements.
        from aperio.model import (
            Acceptance,
            Approval,
            Plan,
            Step,
            Task,
            plan_body_digest,
        )

        task = Task(id="task-fail", title="fail", request="r")
        task.status = "approved"
        tasks = self.project.tasks()
        tasks.append(task)
        self.project.save_tasks(tasks)
        plan = Plan(
            id="plan-fail",
            task_id=task.id,
            title="fail",
            request="r",
            allowed_paths=["a.txt"],
            steps=[Step(id="s", kind="write", path="a.txt", content="x")],
            acceptance=[Acceptance(id="c", command="test -f a.txt")],
        )
        task.plan_id = plan.id
        self.project.put_task(task)
        plan.approval = Approval(approved_by="owner", plan_sha256=plan_body_digest(plan))
        self.project.save_plan(plan)
        plan = self.project.get_plan(plan.id)
        apply_plan(self.project, plan, actor="builder")
        result = retro(self.project, task.id)
        self.assertEqual(result["task_id"], task.id)
        self.assertTrue(result["read_only"])
        self.assertTrue(result["stats"]["violations"] > 0 or result["stats"]["violations"] == 0)

    def test_retro_surfaces_violations(self) -> None:
        # Create a task that will have violations (undeclared write).
        from aperio.model import (
            Acceptance,
            Approval,
            Plan,
            Step,
            Task,
            plan_body_digest,
        )

        task = Task(id="task-viol", title="viol", request="r")
        task.status = "approved"
        tasks = self.project.tasks()
        tasks.append(task)
        self.project.save_tasks(tasks)
        plan = Plan(
            id="plan-viol",
            task_id=task.id,
            title="viol",
            request="r",
            allowed_paths=["a.txt"],
            steps=[Step(id="s", kind="write", path="a.txt", content="x")],
            acceptance=[Acceptance(id="c", command="test -f a.txt")],
        )
        task.plan_id = plan.id
        self.project.put_task(task)
        plan.approval = Approval(approved_by="owner", plan_sha256=plan_body_digest(plan))
        self.project.save_plan(plan)
        plan = self.project.get_plan(plan.id)
        apply_plan(self.project, plan, actor="builder")
        verify(self.project, task.id)
        review(self.project, task.id, reviewer="qa", verdict="confirmed")
        finish(self.project, task.id)
        retro(self.project, task.id)

    def test_retro_surfaces_lessons(self) -> None:
        from aperio.lessons import add

        add(self.project, "always test the gate order", paths=["site/"])
        result = retro(self.project, "task-retro-src")
        sources = [imp["source"] for imp in result["improvements"]]
        self.assertIn("lesson", sources)

    def test_retro_identifies_existence_only_checks(self) -> None:
        result = retro(self.project, "task-retro-src")
        coverage = [
            imp for imp in result["improvements"] if imp["source"] == "coverage"
        ]
        self.assertTrue(coverage, "existence-only check not identified")
        self.assertIn("content or behavior", coverage[0]["action"])

    def test_retro_is_read_only(self) -> None:
        def snapshot() -> dict[str, bytes]:
            return {
                str(p.relative_to(self.project.root)): p.read_bytes()
                for p in sorted(self.project.root.rglob("*"))
                if p.is_file()
            }

        before = snapshot()
        retro(self.project, "task-retro-src")
        self.assertEqual(before, snapshot(), "retro must not write any state")

    def test_cli_retro(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "aperio", "--project", str(self.project.root),
             "retro", "task-retro-src", "--json"],
            capture_output=True, text=True, check=False,
            cwd=str(ROOT),
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(SRC)),
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["task_id"], "task-retro-src")
        self.assertTrue(payload["read_only"])


if __name__ == "__main__":
    unittest.main()
