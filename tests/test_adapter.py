from __future__ import annotations

import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aperio.adapter import HostError, _command_for, run_host_review
from aperio.handoff import write_handoff
from aperio.model import Acceptance, Approval, ModelError, Plan, Step, Task
from aperio.runner import RunError, apply_plan, finish, review, verify
from aperio.sandbox import kind as sandbox_kind
from aperio.store import Project


def make_plan(project: Project, *, host: str = "claude", prompt: str, writes: list[str], sandbox: bool = False) -> tuple[Task, Plan]:
    task = Task(id="task-host", title="Host task", request="Use a host to write one file", status="planned")
    plan = Plan(
        id="plan-host",
        task_id=task.id,
        title=task.title,
        request=task.request,
        allowed_paths=["site/"],
        sandbox=sandbox,
        steps=[
            Step(
                id="host-step",
                kind="host",
                host=host,
                prompt=prompt,
                writes=writes,
                timeout_s=30,
                max_budget_usd=0.10,
            )
        ],
        acceptance=[
            Acceptance(
                id="check",
                command=f'{sys.executable} -c "from pathlib import Path; assert Path(\'site/index.html\').is_file()"',
            )
        ],
        builder="builder",
    )
    plan.validate()
    plan.approval = Approval(approved_by="owner")
    task.plan_id = plan.id
    task.status = "approved"
    project.save_plan(plan)
    project.put_task(task)
    return task, plan


class AdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="aperio-adapter-")
        self.root = Path(self.temp.name)
        self.external = self.root.parent / f"{self.root.name}-binaries"
        self.external.mkdir()
        self.project = Project.init(self.root, name="adapter-test")
        self.host = self.root / "fake-host"
        self.host.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "root = Path.cwd()\n"
            "(root / 'site').mkdir(exist_ok=True)\n"
            "(root / 'site' / 'index.html').write_text('<h1>from host</h1>')\n"
            "print('host done')\n",
            encoding="utf-8",
        )
        self.host.chmod(self.host.stat().st_mode | stat.S_IXUSR)
        self.env = mock.patch.dict(os.environ, {"APERIO_HOST_CLAUDE": str(self.host)})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.temp.cleanup()
        shutil.rmtree(self.external, ignore_errors=True)

    def test_host_step_applies_then_verifies_reviews_and_finishes(self) -> None:
        task, plan = make_plan(
            self.project,
            prompt="Create site/index.html with the exact text from host.",
            writes=["site/index.html"],
        )
        result = apply_plan(self.project, plan, actor="builder")
        self.assertEqual(result["status"], "applied", result)
        self.assertEqual((self.root / "site/index.html").read_text(), "<h1>from host</h1>")
        self.assertEqual(result["steps"][0]["kind"], "host")
        self.assertEqual(result["steps"][0]["host"], "claude")
        self.assertIn("host done", result["steps"][0]["stdout"])

        self.assertEqual(verify(self.project, task.id)["status"], "passed")
        self.assertEqual(review(self.project, task.id, reviewer="qa", verdict="confirmed")["verdict"], "confirmed")
        self.assertEqual(finish(self.project, task.id)["status"], "done")
        handoff_text = write_handoff(self.project, task.id).read_text()
        self.assertIn("host `claude`", handoff_text)
        self.assertIn("host claude exit 0", handoff_text)

    def test_goose_adapter_builds_a_run_command(self) -> None:
        with mock.patch.dict(os.environ, {"APERIO_HOST_GOOSE": str(self.host)}):
            _task, plan = make_plan(self.project, host="goose", prompt="Create the page.", writes=["site/index.html"])
            result = apply_plan(self.project, plan)
            self.assertEqual(result["status"], "applied", result)
            self.assertEqual(result["steps"][0]["host"], "goose")
            self.assertIn("run", result["steps"][0]["command"])
            self.assertIn("--no-session", result["steps"][0]["command"])
            self.assertEqual((self.root / "site/index.html").read_text(), "<h1>from host</h1>")

    def test_codex_adapter_builds_an_exec_command(self) -> None:
        with mock.patch.dict(os.environ, {"APERIO_HOST_CODEX": str(self.host)}):
            _task, plan = make_plan(self.project, host="codex", prompt="Create the page.", writes=["site/index.html"])
            result = apply_plan(self.project, plan)
            self.assertEqual(result["status"], "applied", result)
            self.assertEqual(result["steps"][0]["host"], "codex")
            self.assertIn("exec", result["steps"][0]["command"])
            self.assertIn("--sandbox", result["steps"][0]["command"])
            self.assertIn("workspace-write", result["steps"][0]["command"])
            self.assertEqual((self.root / "site/index.html").read_text(), "<h1>from host</h1>")

    def test_dsh_adapter_builds_a_headless_command(self) -> None:
        with mock.patch.dict(os.environ, {"APERIO_HOST_DSH": str(self.host)}):
            _task, plan = make_plan(
                self.project,
                host="dsh",
                prompt="Create the page.",
                writes=["site/index.html"],
            )
            result = apply_plan(self.project, plan)
        self.assertEqual(result["status"], "applied", result)
        self.assertEqual(result["steps"][0]["host"], "dsh")
        self.assertIn("headless", result["steps"][0]["command"])

    def test_extra_host_adapters_build_commands(self) -> None:
        step = Step(
            id="host-step",
            kind="host",
            host="opencode",
            prompt="Create the page.",
            writes=["site/index.html"],
            timeout_s=30,
            max_budget_usd=0.10,
        )
        with mock.patch.dict(os.environ, {"APERIO_MODEL_OPENCODE": "opencode/test-model"}):
            command = _command_for("opencode", "/bin/host", "prompt", step)
        self.assertEqual(command[:4], ["/bin/host", "run", "--auto", "--model"])
        self.assertIn("opencode/test-model", command)
        for host in ("cline", "agy"):
            command = _command_for(host, "/bin/host", "prompt", step)
            self.assertEqual(command[0], "/bin/host")
            self.assertIn("prompt", command)
        # kilocode 7.8.15 observed behavior, not a claim about yargs flag scope:
        #   kilo run --auto "<prompt>" -> exit 0, session completed
        #   kilo --auto run "<prompt>" -> exit 1 instantly (usage dump)
        self.assertEqual(
            _command_for("kilocode", "/bin/host", "prompt", step),
            ["/bin/host", "run", "--auto", "prompt"],
        )
        with mock.patch.dict(os.environ, {"APERIO_MODEL_KILOCODE": "kilocode/test-model"}):
            with_model = _command_for("kilocode", "/bin/host", "prompt", step)
        self.assertEqual(
            with_model,
            ["/bin/host", "run", "--auto", "--model", "kilocode/test-model", "prompt"],
        )
        self.assertIn("--auto-approve", _command_for("cline", "/bin/host", "prompt", step))
        self.assertIn("--provider", _command_for("cline", "/bin/host", "prompt", step))
        self.assertIn("--mode", _command_for("agy", "/bin/host", "prompt", step))

    def test_host_review_confirms_a_verified_task(self) -> None:
        task, plan = make_plan(
            self.project,
            prompt="Create the page.",
            writes=["site/index.html"],
        )
        apply_plan(self.project, plan)
        verify(self.project, task.id)
        reviewer = self.external / "fake-reviewer"
        reviewer.write_text(
            "#!/usr/bin/env python3\n"
            "print('{\"verdict\":\"confirmed\",\"findings\":[],\"notes\":\"checked\"}')\n",
            encoding="utf-8",
        )
        reviewer.chmod(reviewer.stat().st_mode | stat.S_IXUSR)
        with mock.patch.dict(os.environ, {"APERIO_HOST_CLAUDE": str(reviewer)}):
            result = run_host_review(self.project, task.id, host="claude", budget_usd=0.10)
        self.assertEqual(result["verdict"], "confirmed")
        stored = self.project.get_task(task.id)
        self.assertEqual(stored.status, "reviewed")
        self.assertIsNotNone(stored.review)
        assert stored.review is not None
        self.assertEqual(stored.review.reviewer, "claude")
        self.assertEqual(finish(self.project, task.id)["status"], "done")

    def test_reviewer_cannot_change_the_project(self) -> None:
        task, plan = make_plan(self.project, prompt="Create the page.", writes=["site/index.html"])
        apply_plan(self.project, plan)
        verify(self.project, task.id)
        reviewer = self.external / "fake-reviewer-tamper"
        reviewer.write_text(
            "#!/usr/bin/env python3\n"
            "import os\n"
            "from pathlib import Path\n"
            "Path(os.environ['APERIO_TEST_PROJECT'], 'tampered.txt').write_text('bad')\n"
            "print('{\\\"verdict\\\":\\\"confirmed\\\",\\\"findings\\\":[],\\\"notes\\\":\\\"checked\\\"}')\n",
            encoding="utf-8",
        )
        reviewer.chmod(reviewer.stat().st_mode | stat.S_IXUSR)
        with mock.patch.dict(
            os.environ,
            {"APERIO_HOST_CLAUDE": str(reviewer), "APERIO_TEST_PROJECT": str(self.root)},
        ), self.assertRaises(HostError):
            run_host_review(self.project, task.id, host="claude", budget_usd=0.10)
        self.assertTrue((self.root / "tampered.txt").exists())

    def test_host_review_refutation_sets_failed(self) -> None:
        task, plan = make_plan(self.project, prompt="Create the page.", writes=["site/index.html"])
        apply_plan(self.project, plan)
        verify(self.project, task.id)
        reviewer = self.external / "fake-reviewer-refute"
        reviewer.write_text(
            "#!/usr/bin/env python3\n"
            "print('{\"verdict\":\"refuted\",\"findings\":[{\"severity\":\"P1\",\"claim\":\"missing heading\"}],\"notes\":\"not acceptable\"}')\n",
            encoding="utf-8",
        )
        reviewer.chmod(reviewer.stat().st_mode | stat.S_IXUSR)
        with mock.patch.dict(os.environ, {"APERIO_HOST_CLAUDE": str(reviewer)}):
            result = run_host_review(self.project, task.id, host="claude", budget_usd=0.10)
        self.assertEqual(result["verdict"], "refuted")
        self.assertEqual(self.project.get_task(task.id).status, "failed")
        self.assertEqual(len(result["findings"]), 1)

    def test_host_review_malformed_output_fails(self) -> None:
        task, plan = make_plan(self.project, prompt="Create the page.", writes=["site/index.html"])
        apply_plan(self.project, plan)
        verify(self.project, task.id)
        reviewer = self.external / "fake-reviewer-bad"
        reviewer.write_text("#!/usr/bin/env python3\nprint('not json')\n", encoding="utf-8")
        reviewer.chmod(reviewer.stat().st_mode | stat.S_IXUSR)
        with mock.patch.dict(os.environ, {"APERIO_HOST_CLAUDE": str(reviewer)}), self.assertRaises(HostError):
            run_host_review(self.project, task.id, host="claude", budget_usd=0.10)

    def test_host_cannot_review_its_own_build(self) -> None:
        task, plan = make_plan(self.project, prompt="Create the page.", writes=["site/index.html"])
        plan.builder = "claude"
        self.project.save_plan(plan)
        apply_plan(self.project, plan)
        verify(self.project, task.id)
        with self.assertRaises(HostError):
            run_host_review(self.project, task.id, host="claude", budget_usd=0.10)

    def test_host_change_outside_plan_is_rejected(self) -> None:
        self.host.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('outside.txt').write_text('bad')\n"
            "print('escaped')\n",
            encoding="utf-8",
        )
        self.host.chmod(self.host.stat().st_mode | stat.S_IXUSR)
        task, plan = make_plan(self.project, prompt="Write outside.", writes=["site/index.html"])
        result = apply_plan(self.project, plan)
        self.assertEqual(result["status"], "failed")
        self.assertFalse((self.root / "outside.txt").exists())
        self.assertTrue(any("outside.txt" in v for v in result["violations"]))
        with self.assertRaises(RunError):
            verify(self.project, task.id)

    def test_host_change_outside_step_writes_is_rejected(self) -> None:
        self.host.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('site').mkdir(exist_ok=True)\n"
            "Path('site/index.html').write_text('<h1>ok</h1>')\n"
            "Path('site/extra.html').write_text('undeclared')\n"
            "print('wrote extra')\n",
            encoding="utf-8",
        )
        self.host.chmod(self.host.stat().st_mode | stat.S_IXUSR)
        _task, plan = make_plan(self.project, prompt="Write one page.", writes=["site/index.html"])
        result = apply_plan(self.project, plan)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("site/extra.html" in v for v in result["violations"]))
        self.assertFalse((self.root / "site/extra.html").exists())
        self.assertFalse((self.root / "site/index.html").exists())

    def test_host_change_under_glob_does_not_cross_directories(self) -> None:
        # A host review caught policy._matches using raw fnmatch, whose *
        # crosses /: a host change to site/sub/x.html passed a declaration of
        # site/*.html and was applied before the post-run scan failed the
        # run. Host validation must use the same segment-aware matcher as
        # the post-run check and reject the nested path before applying it.
        self.host.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('site/sub').mkdir(parents=True, exist_ok=True)\n"
            "Path('site/sub/x.html').write_text('nested')\n"
            "print('wrote nested')\n",
            encoding="utf-8",
        )
        self.host.chmod(self.host.stat().st_mode | stat.S_IXUSR)
        _task, plan = make_plan(self.project, prompt="Write nested.", writes=["site/*.html"])
        result = apply_plan(self.project, plan)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(
            any("site/sub/x.html" in v for v in result["violations"]),
            result["violations"],
        )
        self.assertFalse((self.root / "site/sub/x.html").exists())

    def test_host_change_matching_the_glob_is_applied(self) -> None:
        # The inverse: a direct child matching the glob must still apply, so
        # the segment-aware fix is not an allow-nothing regression.
        self.host.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('site').mkdir(exist_ok=True)\n"
            "Path('site/new.html').write_text('<h1>ok</h1>')\n"
            "print('wrote page')\n",
            encoding="utf-8",
        )
        self.host.chmod(self.host.stat().st_mode | stat.S_IXUSR)
        _task, plan = make_plan(self.project, prompt="Write page.", writes=["site/*.html"])
        result = apply_plan(self.project, plan)
        self.assertEqual(result["status"], "applied", result["violations"])
        self.assertTrue((self.root / "site/new.html").is_file())

    def test_sandboxed_host_step_records_active_isolation(self) -> None:
        # plan.sandbox now covers host steps: the dispatch runs under the OS
        # sandbox and the evidence records that isolation was active.
        _task, plan = make_plan(
            self.project,
            prompt="Create site/index.html with the exact text from host.",
            writes=["site/index.html"],
            sandbox=True,
        )
        result = apply_plan(self.project, plan, actor="builder")
        self.assertEqual(
            result["status"], "applied",
            f"violations={result['violations']} stderr={result['steps'][0].get('stderr', '')[-400:]}",
        )
        record = result["steps"][0]["sandbox"]
        self.assertTrue(record["active"])

        self.assertEqual(record["kind"], sandbox_kind())

    def test_sandboxed_host_step_cannot_write_outside_the_workspace(self) -> None:
        # The unsandboxed case only DETECTS outside writes; the sandboxed
        # case must PREVENT them. The claude host here has no native
        # sandboxing, so it gets the outer sandbox-exec with the workspace as
        # its only project-adjacent write boundary: a write to a REAL project
        # file outside the workspace must be blocked, and the victim file
        # must survive byte-identical.
        victim = self.root / "victim.txt"
        victim.write_text("untouched", encoding="utf-8")
        self.host.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            f"Path({str(victim)!r}).write_text('pwned')\n"
            "print('attempted')\n",
            encoding="utf-8",
        )
        self.host.chmod(self.host.stat().st_mode | stat.S_IXUSR)
        _task, plan = make_plan(
            self.project,
            prompt="Try to write outside the workspace.",
            writes=["site/index.html"],
            sandbox=True,
        )
        result = apply_plan(self.project, plan, actor="builder")
        self.assertEqual(
            victim.read_text(encoding="utf-8"), "untouched", "sandbox did not block the outside write"
        )
        self.assertEqual(result["status"], "failed", result)
        # Prove the host actually ran under active isolation (a host review
        # caught this test passing vacuously when no backend exists).
        record = result["steps"][0]["sandbox"]
        self.assertTrue(record["active"], record)

        self.assertEqual(record["kind"], sandbox_kind())

    def test_codex_native_sandbox_used_for_codex_host(self) -> None:
        # Nested seatbelts break live codex tooling (sandbox_apply and the
        # patch tool fail under an outer sandbox-exec — the live runs caught
        # it), so codex is dispatched with its own workspace-write sandbox
        # instead: the command carries workspace-write, no sandbox-exec
        # wrapper, and the record names the native boundary.
        codex_host = self.root / "fake-codex"
        codex_host.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "(root := Path.cwd()).mkdir(exist_ok=True)\n"
            "(Path.cwd() / 'site').mkdir(exist_ok=True)\n"
            "(Path.cwd() / 'site' / 'index.html').write_text('<h1>from codex</h1>')\n"
            "print('codex done')\n",
            encoding="utf-8",
        )
        codex_host.chmod(codex_host.stat().st_mode | stat.S_IXUSR)
        with mock.patch.dict(os.environ, {"APERIO_HOST_CODEX": str(codex_host)}):
            _task, plan = make_plan(
                self.project,
                host="codex",
                prompt="Create site/index.html with the exact text from host.",
                writes=["site/index.html"],
                sandbox=True,
            )
            result = apply_plan(self.project, plan, actor="builder")
        self.assertEqual(result["status"], "applied", result)
        record = result["steps"][0]["sandbox"]
        self.assertEqual(record["kind"], "host-native")
        self.assertEqual(record["mode"], "workspace-write")
        command = result["steps"][0]["command"]
        self.assertIn("workspace-write", command)
        self.assertNotIn("sandbox-exec", command)

    def test_sandbox_without_backend_fails_closed_for_host_steps(self) -> None:
        # A sandboxed host step with no sandbox backend must be refused, not
        # silently downgraded.
        from unittest import mock

        from aperio import sandbox as sandbox_module

        _task, plan = make_plan(
            self.project,
            prompt="Create site/index.html.",
            writes=["site/index.html"],
            sandbox=True,
        )
        with mock.patch.object(sandbox_module, "kind", return_value=None):
            result = apply_plan(self.project, plan, actor="builder")
        self.assertEqual(result["status"], "failed")
        self.assertTrue(
            any("no supported OS sandbox" in v for v in result["violations"]),
            result["violations"],
        )
        self.assertEqual(self.project.get_task(plan.task_id).status, "failed")

    def test_review_brief_omits_the_builder_claim(self) -> None:
        # EXTRACT-without-CLAIM (doubt-driven-development): the reviewer sees
        # the artifact and the contract, not the builder's request narrative
        # — passing the builder's conclusion biases the review toward
        # agreement. Build a real brief and assert the request text and the
        # handoff-style summary are absent while the contract is present.
        _task, plan = make_plan(
            self.project,
            prompt="Create the page.",
            writes=["site/index.html"],
        )
        apply_plan(self.project, plan, actor="builder")
        verify(self.project, plan.task_id)
        review(self.project, plan.task_id, reviewer="qa", verdict="confirmed")
        from aperio.adapter import _review_brief

        workspace, _included = _review_brief(self.project, plan.task_id)
        brief = (workspace / "BRIEF.md").read_text(encoding="utf-8")
        self.assertNotIn("Use a host to write one file", brief, "builder claim leaked into the brief")
        self.assertIn("## Contract", brief)
        self.assertIn("Allowed paths: site/", brief)

    def test_host_symlink_is_rejected(self) -> None:
        self.host.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('site').mkdir(exist_ok=True)\n"
            "Path('site/link').symlink_to('/etc/passwd')\n"
            "print('made link')\n",
            encoding="utf-8",
        )
        self.host.chmod(self.host.stat().st_mode | stat.S_IXUSR)
        _task, plan = make_plan(self.project, prompt="Make a link.", writes=["site/link"])
        result = apply_plan(self.project, plan)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("symlink" in v for v in result["violations"]))
        self.assertFalse((self.root / "site/link").exists())

    def test_host_deletion_is_rejected(self) -> None:
        (self.root / "site").mkdir()
        (self.root / "site" / "index.html").write_text("original", encoding="utf-8")
        self.host.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('site/index.html').unlink()\n"
            "print('deleted')\n",
            encoding="utf-8",
        )
        self.host.chmod(self.host.stat().st_mode | stat.S_IXUSR)
        _task, plan = make_plan(self.project, prompt="Delete the page.", writes=["site/index.html"])
        result = apply_plan(self.project, plan)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("deletions" in v for v in result["violations"]))
        self.assertTrue((self.root / "site" / "index.html").exists())

    def test_host_without_changes_fails(self) -> None:
        self.host.write_text("#!/usr/bin/env python3\nprint('no change')\n", encoding="utf-8")
        self.host.chmod(self.host.stat().st_mode | stat.S_IXUSR)
        _task, plan = make_plan(self.project, prompt="Do nothing.", writes=["site/index.html"])
        result = apply_plan(self.project, plan)
        self.assertEqual(result["status"], "failed")
        self.assertIn("no changes", " ".join(result["violations"]))

    def test_missing_host_fails_closed(self) -> None:
        _task, plan = make_plan(
            self.project,
            host="definitely-not-installed",
            prompt="Write.",
            writes=["site/index.html"],
        )
        result = apply_plan(self.project, plan)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("not installed" in v for v in result["violations"]))
        self.assertFalse((self.root / "site/index.html").exists())

    def test_host_plan_rejects_empty_writes(self) -> None:
        with self.assertRaises(ModelError):
            Step(id="h", kind="host", host="claude", prompt="x", writes=[]).validate()


if __name__ == "__main__":
    unittest.main()
