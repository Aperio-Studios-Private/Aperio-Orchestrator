"""Bounded dispatch to an installed coding host.

The host works in a disposable copy of the project. Aperio compares the copy
before and after, rejects changes outside the plan's allowed paths, and only
then applies text changes to the real project through the runner's snapshot and
evidence path. The host is not an OS sandbox; this is a reviewable boundary,
not a claim of isolation.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .hosts import resolve_host
from .model import Plan, Review, Step
from .paths import PathSafetyError
from .policy import PolicyError, assert_reviewer, step_allows
from .store import Project


class HostError(RuntimeError):
    """The host could not be resolved or its changes were not acceptable."""


EXCLUDED_DIRS = {
    ".git",
    ".aperio",
    ".host-home",
    ".tmp",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
}
MAX_WORKSPACE_FILES = 2_000
MAX_WORKSPACE_BYTES = 50 * 1024 * 1024
MAX_FILE_BYTES = 1_000_000
MAX_CAPTURE = 100_000


@dataclass
class HostChange:
    path: str
    op: str  # create, modify, delete
    content: bytes | None = None
    sha256: str | None = None


@dataclass
class HostResult:
    host: str
    status: str
    command: list[str]
    exit_code: int
    duration_s: float
    stdout: str
    stderr: str
    timed_out: bool
    changes: list[HostChange] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    workspace: str = ""
    prompt_sha256: str = ""
    error: str = ""
    sandbox: dict[str, Any] = field(default_factory=dict)

    def evidence(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "status": self.status,
            "command": self.command,
            "exit_code": self.exit_code,
            "duration_s": self.duration_s,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "timed_out": self.timed_out,
            "sandbox": self.sandbox,
            "changes": [
                {"path": c.path, "op": c.op, "sha256": c.sha256, "bytes": len(c.content or b"")}
                for c in self.changes
            ],
            "violations": self.violations,
            "workspace": self.workspace,
            "prompt_sha256": self.prompt_sha256,
            "error": self.error,
        }


def _binary_for(host: str) -> str:
    override = os.environ.get(f"APERIO_HOST_{host.upper()}")
    if override:
        if not Path(override).is_file():
            raise HostError(f"configured host binary does not exist: {override}")
        return override
    found = resolve_host(host)
    if not found:
        raise HostError(f"host is not installed on PATH or a known application path: {host}")
    return found


def _model_for(host: str) -> str:
    return os.environ.get(f"APERIO_MODEL_{host.upper()}", "").strip()


def _command_for(
    host: str, binary: str, prompt: str, step: Step, *, sandboxed: bool = False
) -> list[str]:
    """Build the host's argv. With `sandboxed` (plan.sandbox), hosts are
    granted their own workspace-write mode: Aperio's outer sandbox-exec has
    already confined writes to the disposable workspace, so the inner host
    sandbox can permit writes there — with both layers, the real project
    stays read-only to the host."""
    model = _model_for(host)
    if host == "claude":
        return [
            binary,
            "-p",
            prompt,
            "--permission-mode",
            "acceptEdits",
            "--max-budget-usd",
            f"{step.max_budget_usd:.2f}",
            "--output-format",
            "text",
        ]
    if host == "codex":
        return [
            binary,
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            "workspace-write",
            prompt,
        ]
    if host == "dsh":
        return [binary, "headless", prompt]
    if host == "goose":
        return [
            binary,
            "run",
            "--no-session",
            "--max-turns",
            "8",
            "--quiet",
            "--text",
            prompt,
        ]
    if host == "opencode":
        command = [binary, "run", "--auto"]
        if model:
            command.extend(["--model", model])
        return command + [prompt]
    if host == "kilocode":
        command = [binary, "run", "--auto"]
        if model:
            command.extend(["--model", model])
        return command + [prompt]
    if host == "cline":
        command = [binary, "--auto-approve", "true", "--provider", "cline"]
        if model:
            command.extend(["--model", model])
        return command + [prompt]
    if host == "agy":
        command = [binary, "-p", prompt, "--mode", "auto"]
        if model:
            command.extend(["--model", model])
        return command
    raise HostError(
        "no adapter for host: "
        f"{host} (supported: claude, codex, dsh, goose, opencode, kilocode, cline, agy)"
    )


def _prompt(project: Project, plan: Plan, step: Step) -> str:
    paths = "\n".join(f"- {p}" for p in step.writes)
    return f"""You are a coding host working inside a disposable copy of a project.

Project: {project.metadata.get('name', project.root.name)}
Task: {plan.title}
Request: {plan.request}

Step: {step.id}
{step.description}

You may create or modify files only under these declared paths:
{paths}

Rules:
- Stay inside the current working directory.
- Do not read or write outside the declared paths.
- Do not use the network.
- Do not run git commands.
- Do not install packages.
- Do not delete files.
- Do not print secrets, tokens, or client data.
- Make the smallest change that satisfies the request.
- When done, reply with a short summary of what you changed.

The orchestrator will reject any change outside the declared paths.
"""


def _iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if path.is_symlink():
                continue
            files.append(path)
    return files


def _copy_workspace(project: Project, workspace: Path) -> None:
    total = 0
    copied = 0
    for path in _iter_files(project.root):
        rel = path.relative_to(project.root)
        if path.is_symlink():
            continue
        size = path.stat().st_size
        total += size
        copied += 1
        if copied > MAX_WORKSPACE_FILES or total > MAX_WORKSPACE_BYTES:
            raise HostError("workspace copy limit exceeded")
        destination = workspace / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


_HOST_STATE_SEEDS = {
    "codex": ("config.toml", "auth.json"),
    "claude": (".claude.json", "settings.json"),
}


def _seed_host_state(host: str, host_home: Path) -> None:
    """Copy the host's real config files into the isolated host-home.

    Live hosts need their configuration and credentials to function; the
    sandboxed dispatch points CODEX_HOME/CLAUDE_CONFIG_DIR at an in-workspace
    directory, which must be seeded or the host fails at startup. Files that
    do not exist are skipped.
    """
    seeds = _HOST_STATE_SEEDS.get(host, ())
    real_home = Path.home() / HOST_STATE_DIRS_NAME.get(host, f".{host}")
    for name in seeds:
        source = real_home / name
        if source.is_file():
            target = host_home / name
            if not target.exists():
                shutil.copy2(source, target)


HOST_STATE_DIRS_NAME = {
    "codex": ".codex",
    "claude": ".claude",
    "dsh": ".dsh",
    "goose": ".goose",
}


def _scan(root: Path) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for path in _iter_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            result[rel] = ("file", hashlib.sha256(path.read_bytes()).hexdigest())
        except OSError:
            continue
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for name in list(dirnames) + list(filenames):
            path = Path(dirpath) / name
            if path.is_symlink():
                result[path.relative_to(root).as_posix()] = ("symlink", os.readlink(path))
    return result


def _diff(before: dict[str, tuple[str, str]], after: dict[str, tuple[str, str]]) -> list[tuple[str, str]]:
    changes: list[tuple[str, str]] = []
    for rel, record in after.items():
        if rel not in before:
            changes.append((rel, "create"))
        elif before[rel] != record:
            changes.append((rel, "modify"))
    for rel in before:
        if rel not in after:
            changes.append((rel, "delete"))
    return sorted(changes)


def _fingerprint(root: Path) -> dict[str, str]:
    """Hash every file and symlink under root for review tamper detection."""
    result: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in list(dirnames) + list(filenames):
            path = Path(dirpath) / name
            rel = path.relative_to(root).as_posix()
            try:
                if path.is_symlink():
                    result[rel] = "symlink:" + os.readlink(path)
                elif path.is_file():
                    result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
    return result


def _run_bounded(command: list[str], *, cwd: Path, env: dict[str, str], timeout: int) -> tuple[int, str, str, bool]:
    kwargs: dict[str, Any] = {
        "cwd": str(cwd),
        "env": env,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "errors": "replace",
    }
    if os.name != "nt":
        kwargs["start_new_session"] = True
    process = subprocess.Popen(command, **kwargs)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return int(process.returncode), stdout or "", stderr or "", False
    except subprocess.TimeoutExpired:
        if os.name != "nt":
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                pass
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
        return 124, stdout or "", stderr or "", True


def run_host_step(project: Project, plan: Plan, step: Step, run_id: str) -> HostResult:
    if not step.host or not step.prompt:
        raise HostError(f"step {step.id}: missing host or prompt")
    binary = _binary_for(step.host)
    prompt = _prompt(project, plan, step)
    command = _command_for(step.host, binary, prompt, step)
    workspace = project.state / "dispatch" / run_id / "workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    _copy_workspace(project, workspace)
    before = _scan(workspace)
    env = os.environ.copy()
    # Live AI hosts keep their state INSIDE the disposable workspace: the
    # sandbox's write boundary covers it, cleanup removes it with the
    # workspace, and the deliverable scan excludes it (a host's session
    # store is not a deliverable).
    host_home = workspace / ".host-home" / step.host
    host_home.mkdir(parents=True, exist_ok=True)
    # The host's temp dir moves into the workspace too: the sandbox profile
    # denies writes under the system TMPDIR (/var/folders/...), and the
    # host's patch tool stages there — without this redirect every patch
    # fails with Operation not permitted (the live run caught it).
    host_tmp = workspace / ".tmp"
    host_tmp.mkdir(parents=True, exist_ok=True)
    # Seed the isolated host state with the host's real config: an empty
    # CODEX_HOME means no auth or configuration, and the host fails before
    # doing any work (the live run caught it). Sessions and logs are still
    # created fresh inside the disposable workspace and cleaned with it.
    _seed_host_state(step.host, host_home)
    env.update(
        {
            "APERIO_TASK_ID": plan.task_id,
            "APERIO_PLAN_ID": plan.id,
            "APERIO_RUN_ID": run_id,
            "APERIO_WORKSPACE": str(workspace),
            "APERIO_ALLOWED_PATHS": os.pathsep.join(step.writes),
            "CODEX_HOME": str(host_home),
            "CLAUDE_CONFIG_DIR": str(host_home),
            "TMPDIR": str(host_tmp) + "/",
            "TMP": str(host_tmp) + "/",
            "TEMP": str(host_tmp) + "/",
        }
    )
    # Optional sandbox for host steps. Live hosts with native sandboxing
    # (codex) are dispatched in their own workspace-write mode with state
    # and TMPDIR redirected into the disposable workspace: nesting an outer
    # sandbox-exec around them breaks their tooling (sandbox_apply and the
    # patch tool fail — the live runs caught it), and their own sandbox
    # provides the boundary (proven: writes outside the workspace are
    # blocked, writes inside succeed). Hosts without native sandboxing fall
    # back to the outer sandbox-exec (workspace-only writes). Fail closed
    # when plan.sandbox is set and neither layer is available.
    sandbox_record: dict[str, object] = {"requested": False, "active": False, "kind": None}
    native_sandbox_hosts = {"codex"}
    if plan.sandbox and step.host in native_sandbox_hosts:
        sandbox_record = {
            "requested": True,
            "active": True,
            "kind": "host-native",
            "mode": "workspace-write",
            "note": (
                "the host's own workspace-write sandbox is the boundary; state "
                "and TMPDIR are redirected into the disposable workspace"
            ),
        }
    elif plan.sandbox:
        from .sandbox import SandboxError, wrap_argv

        try:
            # The writable boundary is the disposable WORKSPACE, not the
            # project: a host that can write the whole project could modify
            # real files directly, and the restore path only covers
            # snapshotted files (a host review caught this). The runner
            # applies reviewed changes into the real project afterwards.
            # The host binary's directory stays visible: it may live under
            # the real /tmp, which the dedicated tmp mount would otherwise
            # shadow (the Linux CI failure named it).
            command, sandbox_record = wrap_argv(
                command,
                workspace,
                workspace,
                extra_visible=[Path(binary).parent],
                host=step.host,
                protected=project.root,
            )
        except SandboxError as exc:
            raise HostError(f"step {step.id}: {exc}") from exc
    started = time.monotonic()
    exit_code, stdout, stderr, timed_out = _run_bounded(
        command,
        cwd=workspace,
        env=env,
        timeout=step.timeout_s,
    )
    duration = round(time.monotonic() - started, 3)
    after = _scan(workspace)
    diff = _diff(before, after)
    result = HostResult(
        host=step.host,
        status="running",
        command=command,
        exit_code=exit_code,
        duration_s=duration,
        stdout=stdout[-MAX_CAPTURE:],
        stderr=stderr[-MAX_CAPTURE:],
        timed_out=timed_out,
        workspace=str(workspace),
        prompt_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        sandbox=sandbox_record,
    )
    if exit_code != 0:
        result.status = "failed"
        result.error = f"host exited {exit_code}" + (" (timeout)" if timed_out else "")
        return result
    if not diff:
        result.status = "failed"
        result.error = "host made no changes"
        return result
    changes: list[HostChange] = []
    for rel, op in diff:
        path = workspace / rel
        if before.get(rel, ("", ""))[0] == "symlink" or path.is_symlink():
            result.violations.append(f"{rel}: symlink changes are not accepted")
            continue
        try:
            normalized = step_allows(rel, step, plan)
        except (PolicyError, PathSafetyError) as exc:
            result.violations.append(f"{rel}: {exc}")
            continue
        if op == "delete":
            result.violations.append(f"{rel}: host deletions are not accepted")
            continue
        data = path.read_bytes()
        if len(data) > MAX_FILE_BYTES:
            result.violations.append(f"{rel}: file exceeds {MAX_FILE_BYTES} bytes")
            continue
        if b"\x00" in data:
            result.violations.append(f"{rel}: binary file is not accepted by the text adapter")
            continue
        changes.append(
            HostChange(
                path=normalized,
                op=op,
                content=data,
                sha256=hashlib.sha256(data).hexdigest(),
            )
        )
    result.changes = changes
    if result.violations:
        result.status = "failed"
        result.error = "host changed paths outside the approved plan or wrote unacceptable files"
    elif not changes:
        result.status = "failed"
        result.error = "host produced no applicable text changes"
    else:
        result.status = "ok"
    return result


def _review_command(host: str, binary: str, prompt: str, timeout_s: int, budget_usd: float) -> list[str]:
    if host == "claude":
        return [
            binary,
            "-p",
            prompt,
            "--permission-mode",
            "plan",
            "--max-budget-usd",
            f"{budget_usd:.2f}",
            "--output-format",
            "text",
        ]
    if host == "codex":
        return [
            binary,
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            prompt,
        ]
    if host == "dsh":
        return [binary, "headless", prompt]
    if host == "goose":
        return [
            binary,
            "run",
            "--no-session",
            "--max-turns",
            "8",
            "--quiet",
            "--text",
            prompt,
        ]
    raise HostError(f"no reviewer adapter for host: {host} (supported: claude, codex, dsh, goose)")


def _parse_review(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise HostError("reviewer did not return a JSON object")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise HostError(f"reviewer returned invalid JSON: {exc}") from exc
    verdict = str(data.get("verdict", "")).lower()
    if verdict not in {"confirmed", "refuted"}:
        raise HostError("reviewer verdict must be confirmed or refuted")
    findings = data.get("findings", [])
    if not isinstance(findings, list):
        raise HostError("reviewer findings must be a list")
    return {"verdict": verdict, "findings": findings, "notes": str(data.get("notes", ""))}


def _review_brief(project: Project, task_id: str) -> tuple[Path, list[str]]:

    task = project.get_task(task_id)
    if not task.plan_id:
        raise HostError("task has no plan")
    plan = project.get_plan(task.plan_id)
    if task.status not in {"verified", "reviewed", "failed"}:
        raise HostError(f"task is {task.status}; verification must pass before review")
    if not task.run_id:
        raise HostError("task has no run evidence")
    run_rows = [row for row in project.evidence(task_id) if row.get("run_id") == task.run_id]
    if not run_rows or run_rows[-1].get("status") != "applied":
        raise HostError("last run did not apply cleanly")
    verify_rows = [row for row in project.evidence(task_id) if str(row.get("check_id", "")).startswith("verify-")]
    if not verify_rows or verify_rows[-1].get("status") != "passed":
        raise HostError("last verification did not pass")
    changed = [str(p) for p in run_rows[-1].get("changed_files", [])]
    if not changed:
        raise HostError("run evidence has no changed files")
    review_id = f"review-{uuid.uuid4().hex[:10]}"
    workspace = project.state / "reviews" / review_id
    tree = workspace / "tree"
    tree.mkdir(parents=True)
    included: list[str] = []
    for rel in changed:
        source = project.resolve_project_path(rel)
        if not source.is_file() or source.stat().st_size > MAX_FILE_BYTES:
            continue
        data = source.read_bytes()
        if b"\x00" in data:
            continue
        destination = tree / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        included.append(rel)
    brief = [
        "# Independent review brief",
        "",
        "You are a Goldfish reviewer. You have no builder conversation.",
        "Read this brief and the files under `tree/`. Do not edit anything.",
        "",
        # EXTRACT-without-CLAIM (doubt-driven-development): the reviewer sees
        # the artifact and the contract — the plan's steps, writes, and
        # acceptance — but NOT the builder's own request narrative, which
        # would bias the review toward the builder's conclusion.
        "## Contract\n\nJudge only what is written below and in `tree/`: the declared steps, the allowed paths, and the acceptance checks. The builder's request narrative is intentionally not included.\n",
        "",
        f"## Plan\n\n{plan.title}\n\nAllowed paths: {', '.join(plan.allowed_paths)}",
        "",
        "### Steps",
        "",
    ]
    for step in plan.steps:
        if step.kind == "write":
            brief.append(f"- write `{step.path}`")
        elif step.kind == "host":
            brief.append(f"- host `{step.host}` writes: {', '.join(step.writes)}")
        else:
            brief.append(f"- run `{step.command}`")
    brief.extend(["", "### Acceptance", ""])
    for check in plan.acceptance:
        brief.append(f"- `{check.id}`: `{check.command}` (expected exit {check.expected_exit})")
    brief.extend(["", "### Verification evidence", ""])
    for row in verify_rows[-1].get("checks", []):
        brief.append(f"- `{row.get('check_id')}`: {'passed' if row.get('ok') else 'FAILED'} exit {row.get('exit_code')}")
    brief.extend(["", "### Changed files", ""])
    for rel in included:
        brief.append(f"- `{rel}`")
    brief.extend(
        [
            "",
            "## What to return",
            "",
            "Return ONLY a JSON object:",
            "",
            "```json",
            '{"verdict":"confirmed|refuted","findings":[{"severity":"P0|P1|P2","claim":"...","evidence":"...","expected":"...","actual":"..."}],"notes":"..."}',
            "```",
            "",
            "Use `confirmed` only if the delivered artifact satisfies the stated request and the acceptance evidence is credible. Use `refuted` if it does not. Do not invent findings. Do not edit files. Do not use the network.",
        ]
    )
    (workspace / "BRIEF.md").write_text("\n".join(brief), encoding="utf-8")
    return workspace, included


def run_host_review(
    project: Project,
    task_id: str,
    host: str = "claude",
    *,
    timeout_s: int = 300,
    budget_usd: float = 1.50,
) -> dict[str, Any]:
    task = project.get_task(task_id)
    if not task.plan_id:
        raise HostError("task has no plan")
    plan = project.get_plan(task.plan_id)
    if not task.verify_id:
        raise HostError("task has no current verification")
    verify_rows = [row for row in project.evidence(task_id) if row.get("check_id") == task.verify_id]
    if not verify_rows or verify_rows[-1].get("status") != "passed":
        raise HostError("current verification did not pass; cannot review")
    from .runner import _artifact_digest as runner_artifact_digest
    from .runner import _plan_digest as runner_plan_digest

    if verify_rows[-1].get("artifact_digest") != runner_artifact_digest(project):
        raise HostError("project changed after verification; verify again")
    if verify_rows[-1].get("plan_digest") != runner_plan_digest(plan):
        raise HostError("plan changed after verification; verify again")
    try:
        assert_reviewer(plan.builder, host)
    except PolicyError as exc:
        raise HostError(str(exc)) from exc
    workspace, included = _review_brief(project, task_id)
    binary = _binary_for(host)
    prompt = (
        "You are an independent reviewer. Read `BRIEF.md` and the files under `tree/` in the current directory. "
        "Do not edit anything. Do not use the network. Return only the JSON object requested in BRIEF.md."
    )
    command = _review_command(host, binary, prompt, timeout_s, budget_usd)
    before = _fingerprint(project.root)
    started = time.monotonic()
    exit_code, stdout, stderr, timed_out = _run_bounded(
        command,
        cwd=workspace,
        env=os.environ.copy(),
        timeout=timeout_s,
    )
    duration = round(time.monotonic() - started, 3)
    after = _fingerprint(project.root)
    if after != before:
        changed = sorted(set(before) ^ set(after) | {rel for rel in before if after.get(rel) != before[rel]})
        raise HostError(f"reviewer changed the project: {', '.join(changed[:10])}")
    if exit_code != 0:
        raise HostError(f"reviewer exited {exit_code}: {(stderr or stdout)[-500:]}")
    parsed = _parse_review(stdout)
    review_id = f"review-{uuid.uuid4().hex[:10]}"
    evidence = {
        "review_id": review_id,
        "task_id": task_id,
        "host": host,
        "reviewer": host,
        "verdict": parsed["verdict"],
        "findings": parsed["findings"],
        "notes": parsed["notes"],
        "command": command,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_s": duration,
        "stdout": stdout[-MAX_CAPTURE:],
        "stderr": stderr[-MAX_CAPTURE:],
        "workspace": str(workspace),
        "included_files": included,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    # Sign the same six-field core that manual review() signs, so
    # finish()'s signature check treats host verdicts identically (the
    # unsigned-verdict test caught the host path missing the signature).
    signed_core = {
        k: evidence[k]
        for k in ("review_id", "task_id", "reviewer", "verdict", "notes", "at")
    }
    evidence["signature"] = project.sign_review(signed_core)
    path = project.save_evidence(task_id, review_id, evidence)
    task.review = Review(reviewer=host, verdict=parsed["verdict"], notes=parsed["notes"])
    task.status = "reviewed" if parsed["verdict"] == "confirmed" else "failed"
    task.evidence.append(str(path))
    project.put_task(task)
    project.append_event(
        "review.host",
        {"task_id": task_id, "host": host, "verdict": parsed["verdict"], "findings": len(parsed["findings"])},
    )
    return evidence

