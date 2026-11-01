"""Tests for the promo generator (apero promo — launch-video plan from a done task)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from aperio.promo import PromoError, build_promo
from aperio.store import Project

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _fly_task_to_done(project: Project, *, task_id: str = "task-promo-src", title: str = "Landing page") -> None:
    """Build a real done task: run, verify, review — through the real runner."""
    from aperio.model import Acceptance, Approval, Plan, Step, Task, plan_body_digest
    from aperio.runner import apply_plan, finish, review, verify

    (project.root / "site").mkdir(exist_ok=True)
    (project.root / "site" / "index.html").write_text("<h1>draft</h1>", encoding="utf-8")
    task = Task(
        id=task_id, title=title, request="Build the landing page"
    )
    task.status = "approved"
    tasks = project.tasks()
    tasks.append(task)
    project.save_tasks(tasks)
    plan = Plan(
        id=f"plan-{task_id}",
        task_id=task.id,
        title="Landing page",
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


class PromoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Project.init(Path(self.temp.name) / "proj", "promo-test")
        _fly_task_to_done(self.project)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_generates_sheet_and_plan_from_done_task(self) -> None:
        result = build_promo(self.project, "task-promo-src")
        sheet = result["sheet"]
        self.assertEqual(sheet["duration_s"], 12)
        self.assertEqual(sheet["width"], 1920)
        self.assertEqual(sheet["height"], 1080)
        total = sum(scene["duration"] for scene in sheet["scenes"])
        self.assertAlmostEqual(total, 12, places=2)
        # Sourced from real evidence: the changed file and the check are cited.
        self.assertIn("site/index.html", sheet["sourced_from"]["changed_files"])
        self.assertTrue(sheet["sourced_from"]["acceptance_checks"])
        # The promo plan is a valid plan-shaped dict with bounded paths.
        promo_plan = result["promo_plan"]
        self.assertEqual(promo_plan["allowed_paths"], ["promo/"])
        writes = [s for s in promo_plan["steps"] if s["kind"] == "write"]
        self.assertEqual(len(writes), 5)
        for step in writes:
            self.assertTrue(step["path"].startswith("promo/"))
        # The render is a declared run step (a host review caught it missing).
        render_steps = [s for s in promo_plan["steps"] if s["kind"] == "run"]
        self.assertEqual(len(render_steps), 1)
        self.assertEqual(render_steps[0]["command"], "sh promo/render.sh")
        self.assertEqual(render_steps[0]["writes"], ["promo/promo.mp4", "promo/.hyperframes/"])
        # The motion contract's gate lives in the script: lint && validate before render.
        render_sh = next(
            s["content"] for s in promo_plan["steps"] if s["path"] == "promo/render.sh"
        )
        self.assertIn("hyperframes check", render_sh)
        self.assertIn("hyperframes render", render_sh)
        # The local-font rule: warn (not block) without fonts/promo.woff2,
        # so the generated plan is runnable out of the box.
        self.assertIn("missing fonts/promo.woff2", render_sh)
        font_readme = next(
            s["content"] for s in promo_plan["steps"] if s["path"] == "promo/fonts/README.md"
        )
        self.assertIn("promo.woff2", font_readme)
        index_html = next(
            s["content"] for s in promo_plan["steps"] if s["path"] == "promo/index.html"
        )
        index_html = next(
            s["content"] for s in promo_plan["steps"] if s["path"] == "promo/index.html"
        )
        self.assertIn("@font-face", index_html)
        self.assertIn("fonts/promo.woff2", index_html)
        self.assertNotIn("'Inter'", index_html)
        self.assertIn('data-composition-id="root"', index_html)
        self.assertIn(f'data-width="{sheet["width"]}"', index_html)
        # And the acceptance carries the video-exists gate.
        acceptance_ids = [a["id"] for a in promo_plan["acceptance"]]
        self.assertIn("video-rendered", acceptance_ids)

    def test_refuses_a_task_that_is_not_done(self) -> None:
        from aperio.model import Task

        tasks = self.project.tasks()
        tasks.append(
            Task(id="task-early", title="early", request="r", status="planned")
        )
        self.project.save_tasks(tasks)
        with self.assertRaises(PromoError):
            build_promo(self.project, "task-early")

    def test_duration_bounds(self) -> None:
        with self.assertRaises(PromoError):
            build_promo(self.project, "task-promo-src", duration=4)
        with self.assertRaises(PromoError):
            build_promo(self.project, "task-promo-src", duration=60)

    def test_vertical_option(self) -> None:
        result = build_promo(self.project, "task-promo-src", vertical=True)
        self.assertEqual(result["sheet"]["width"], 1080)
        self.assertEqual(result["sheet"]["height"], 1920)

    def test_determinism_contract_in_generated_plan(self) -> None:
        # The generated index_html must carry the docs/MOTION.md contract:
        # declared meta, no random/now, paused timeline.
        result = build_promo(self.project, "task-promo-src")
        index_html = next(
            s["content"] for s in result["promo_plan"]["steps"] if s["path"] == "promo/index.html"
        )
        self.assertIn('name="hyperframes"', index_html)
        self.assertNotIn("Math.random", index_html)
        self.assertNotIn("Date.now", index_html)
        self.assertIn("__timelines", index_html)

    def test_generated_plan_passes_aperio_validation(self) -> None:
        # The strongest check: the generated promo plan is a real Aperio plan
        # — it validates through the model and saves into a project.
        result = build_promo(self.project, "task-promo-src")
        from aperio.model import Plan

        data = dict(result["promo_plan"])
        data["id"] = "plan-generated"
        data["task_id"] = "task-generated"
        data["steps"] = [
            {**s, "id": f"{s['id']}-gen"} for s in data["steps"]
        ]
        plan = Plan.from_dict(data)
        self.project.save_plan(plan)
        loaded = self.project.get_plan("plan-generated")
        self.assertEqual(len(loaded.steps), 6)

    def test_evidence_text_is_escaped_in_composition(self) -> None:
        # A host review caught unescaped interpolation: task content could
        # inject markup or scripts into the generated index_html. A title
        # carrying HTML must come out escaped.
        _fly_task_to_done(
            self.project,
            task_id="task-evil",
            title="Evil <script>alert(1)</script> & <b>bold</b>",
        )
        result = build_promo(self.project, "task-evil")
        index_html = next(
            s["content"]
            for s in result["promo_plan"]["steps"]
            if s["path"] == "promo/index.html"
        )
        self.assertNotIn("<script>alert(1)</script>", index_html)
        self.assertIn("&lt;script&gt;", index_html)

    def test_button_lands_in_the_final_two_seconds(self) -> None:
        # The motion contract requires the button shot in the last two
        # seconds for every supported duration (a host review caught the
        # 20s promo starting its button at 17s with a 3s span).
        for duration in (8, 12, 20, 30):
            result = build_promo(self.project, "task-promo-src", duration=duration)
            button = result["sheet"]["scenes"][-1]
            self.assertEqual(button["name"], "button")
            self.assertLessEqual(button["duration"], 2.0)
            self.assertAlmostEqual(
                button["start"] + button["duration"], duration, places=2
            )
            total = sum(s["duration"] for s in result["sheet"]["scenes"])
            self.assertAlmostEqual(total, duration, places=2)

    def test_sheet_cites_only_the_current_run_files(self) -> None:
        # A host review caught _changed_files unioning every record: an
        # earlier run's files leaked into the sheet. Fly a second task that
        # touches a different file; the first task's sheet must not cite it.
        (self.project.root / "other").mkdir(exist_ok=True)
        (self.project.root / "other" / "b.txt").write_text("x", encoding="utf-8")
        from aperio.model import Acceptance, Approval, Plan, Step, plan_body_digest

        task2 = __import__("aperio.model", fromlist=["Task"]).Task(
            id="task-second", title="Second", request="Second slice"
        )
        task2.status = "approved"
        tasks = self.project.tasks()
        tasks.append(task2)
        self.project.save_tasks(tasks)
        plan2 = Plan(
            id="plan-second",
            task_id=task2.id,
            title="Second",
            request=task2.request,
            allowed_paths=["other/"],
            steps=[Step(id="w", kind="write", path="other/b.txt", content="y")],
            acceptance=[Acceptance(id="check", command="test -f other/b.txt")],
        )
        task2.plan_id = plan2.id
        self.project.put_task(task2)
        plan2.approval = Approval(approved_by="owner", plan_sha256=plan_body_digest(plan2))
        self.project.save_plan(plan2)
        plan2 = self.project.get_plan(plan2.id)
        from aperio.runner import apply_plan as apply2
        from aperio.runner import finish as finish2
        from aperio.runner import review as review2
        from aperio.runner import verify as verify2

        apply2(self.project, plan2, actor="builder")
        verify2(self.project, task2.id)
        review2(self.project, task2.id, reviewer="qa", verdict="confirmed")
        finish2(self.project, task2.id)
        result = build_promo(self.project, "task-second")
        cited = result["sheet"]["sourced_from"]["changed_files"]
        self.assertIn("other/b.txt", cited)
        self.assertNotIn("site/index.html", cited, "an earlier task's files leaked")

    def test_promo_refuses_when_review_signature_is_stripped(self) -> None:
        # The cited review must carry a valid signature — the same bar
        # finish() applies (a host review caught generation citing
        # unvalidated review records).
        fresh = self.project.get_task("task-promo-src")
        review_record = next(p for p in fresh.evidence if "review-" in p)
        record_path = Path(review_record)
        data = json.loads(record_path.read_text(encoding="utf-8"))
        del data["signature"]
        record_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaises(PromoError):
            build_promo(self.project, "task-promo-src")

    def test_determinism_check_covers_async(self) -> None:
        # docs/MOTION.md forbids Math.random, Date.now, AND async; the
        # generated acceptance check must reject all three (a host review
        # caught the check covering only two).
        result = build_promo(self.project, "task-promo-src")
        check = next(
            a
            for a in result["promo_plan"]["acceptance"]
            if a["id"] == "determinism-contract"
        )
        # The generated index_html passes its own check: assert the content
        # directly in Python (no shell indirection — the shell probe was
        # fragile and hard to debug).
        index_html = next(
            s["content"]
            for s in result["promo_plan"]["steps"]
            if s["path"] == "promo/index.html"
        )
        self.assertNotIn("Math.random", index_html)
        self.assertNotIn("Date.now", index_html)
        self.assertNotIn("async", index_html)
        self.assertNotIn("setTimeout", index_html)
        self.assertNotIn("new Promise", index_html)
        self.assertIn("__timelines.root = tl", index_html)
        self.assertIn("paused: true", index_html)
        # The pattern genuinely covers async: an async index_html fails.
        promo_dir = self.project.root / "promo"
        promo_dir.mkdir(exist_ok=True)
        (promo_dir / "index.html").write_text(
            index_html + "\nconst x = async () => 1;\n", encoding="utf-8"
        )
        probe = subprocess.run(
            ["/bin/sh", "-c", check["command"]],
            capture_output=True, text=True, check=False,
            cwd=str(self.project.root),
        )
        self.assertNotEqual(probe.returncode, 0, "async slipped past the check")
        # A index_html with setTimeout or a missing timeline registration
        # also fails (a host review caught the check covering only part of
        # the contract).
        (promo_dir / "index.html").write_text(
            index_html + "\nsetTimeout(() => {}, 0);\n", encoding="utf-8"
        )
        probe = subprocess.run(
            ["/bin/sh", "-c", check["command"]],
            capture_output=True, text=True, check=False,
            cwd=str(self.project.root),
        )
        self.assertNotEqual(probe.returncode, 0, "setTimeout slipped past")
        no_tl = index_html.replace("window.__timelines.root = tl;", "")
        (promo_dir / "index.html").write_text(no_tl, encoding="utf-8")
        probe = subprocess.run(
            ["/bin/sh", "-c", check["command"]],
            capture_output=True, text=True, check=False,
            cwd=str(self.project.root),
        )
        self.assertNotEqual(probe.returncode, 0, "unregistered timeline slipped past")
        # And a missing index_html is not a vacuous pass.
        (promo_dir / "index.html").unlink()
        probe = subprocess.run(
            ["/bin/sh", "-c", check["command"]],
            capture_output=True, text=True, check=False,
            cwd=str(self.project.root),
        )
        self.assertNotEqual(probe.returncode, 0, "missing index_html passed vacuously")

    def test_cli_promo_on_done_task(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "aperio", "--project", str(self.project.root),
             "promo", "task-promo-src", "--json"],
            capture_output=True, text=True, check=False,
            cwd=str(ROOT),
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(SRC)),
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["sheet"]["duration_s"], 12)

    def test_cli_promo_refuses_undone_task(self) -> None:
        from aperio.model import Task

        tasks = self.project.tasks()
        tasks.append(Task(id="task-early2", title="early", request="r", status="planned"))
        self.project.save_tasks(tasks)
        result = subprocess.run(
            [sys.executable, "-m", "aperio", "--project", str(self.project.root),
             "promo", "task-early2"],
            capture_output=True, text=True, check=False,
            cwd=str(ROOT),
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(SRC)),
            timeout=60,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("done", result.stderr)


if __name__ == "__main__":
    unittest.main()
