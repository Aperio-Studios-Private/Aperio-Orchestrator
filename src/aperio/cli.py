"""Aperio v2 command line. Standard library only."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .adapter import HostError, run_host_review
from .audit import (
    FINDING_STATUSES,
    FINDING_VERDICTS,
    PROFILES,
    SEVERITIES,
    UNIT_STATUSES,
    AuditError,
)
from .audit import add_finding as audit_add_finding
from .audit import brief as audit_brief
from .audit import ingest as audit_ingest
from .audit import latest as audit_latest
from .audit import report as audit_report
from .audit import set_unit as audit_set_unit
from .audit import start as audit_start
from .audit import status as audit_status
from .audit import validate as audit_validate
from .audit import verify_finding as audit_verify_finding
from .dashboard import write as write_dashboard
from .discovery import (
    QUESTION_BY_ID,
    DiscoveryError,
    answer_question,
    as_json,
    format_next,
    format_status,
    next_question,
    parse_choices,
    waive_question,
)
from .discovery import (
    digest as discovery_digest,
)
from .discovery import (
    status as discovery_status,
)
from .discovery import (
    summary as discovery_summary,
)
from .drift import check as drift_check
from .drift import format_findings as format_drift
from .evidence import add as evidence_add
from .evidence import entries as evidence_entries
from .evidence import format_entries as format_evidence
from .explain import TOPICS as EXPLAIN_TOPICS
from .explain import explain
from .handoff import write_handoff
from .hosts import detect_hosts
from .inspect import InspectionError
from .inspect import collect as collect_inspection
from .inspect import format_report as format_inspection
from .inspect import hints as inspection_hints
from .learning import LearningError
from .learning import format_status as format_learning
from .learning import import_dossier as import_learning
from .learning import record_proof as record_learning_proof
from .learning import status as learning_status
from .lessons import add as lesson_add
from .lessons import format_list as format_lessons
from .lessons import read_lessons, relevant_lessons
from .lessons import remove as lesson_remove
from .mcp import serve as mcp_serve
from .mediator import MediationError, mediate
from .mesh import MeshError, MeshStore
from .model import (
    Acceptance,
    Approval,
    ModelError,
    Plan,
    Step,
    Task,
    new_id,
    plan_body_digest,
)
from .nextstep import next_action
from .policy import PolicyError
from .promo import PromoError, build_promo
from .readiness import ReadinessError, import_readiness, validate_preflight
from .readiness import format_status as format_readiness
from .readiness import status as readiness_status
from .repo import facts as repo_facts
from .repo import format_facts as format_git
from .runner import (
    RunError,
    apply_plan,
    finish,
    resume_plan,
    review,
    rollback,
    verify,
)
from .security import format_findings as format_security
from .security import scan as security_scan
from .skillgen import SkillError, list_skills
from .skillgen import create as skill_create
from .skillgen import validate as skill_validate
from .skillspector import format_report as format_skillspector
from .skillspector import scan as skillspector_scan
from .store import Project, StoreError
from .todo import accept as todo_accept
from .todo import add as todo_add
from .todo import defer as todo_defer
from .todo import format_status as format_todo
from .todo import start as todo_start
from .todo import status as todo_status
from .toolchain import ToolError
from .toolchain import format_status as format_toolchain
from .toolchain import import_manifest as import_toolchain
from .toolchain import install as install_tool
from .toolchain import status as toolchain_status
from .toolchain import validate_manifest as validate_toolchain
from .tutorial import build as tutorial_build
from .tutorial import check as tutorial_check


def _project(args: argparse.Namespace) -> Project:
    return Project.open(args.project)


def _require_learning(project: Project) -> dict[str, Any]:
    progress = learning_status(project)
    if progress["ready"]:
        return progress
    issues = "; ".join(progress["issues"][:6])
    raise LearningError(
        "learning dossier is required before planning, approval, or run; run aperio learn status"
        + (f": {issues}" if issues else "")
    )


def _require_current_learning(project: Project, plan: Plan) -> None:
    if not plan.learning_digest:
        raise LearningError("plan has no learning binding; recreate the plan")
    current = learning_status(project)
    if not current["ready"] or current["digest"] != plan.learning_digest:
        raise LearningError("learning dossier changed after this plan was created; make a new plan")


def _require_todo(project: Project) -> None:
    data = todo_status(project)
    if data["count"] == 0:
        raise ModelError(
            "todo list is empty; add the smallest independently reviewable tasks with aperio todo add"
        )


def _active_todo(project: Project) -> str:
    data = todo_status(project)
    active = [item for item in data["tasks"] if item["status"] == "in_progress"]
    if len(active) != 1:
        raise ModelError("start exactly one todo task before planning a slice")
    return str(active[0]["id"])


def _require_preflight(project: Project) -> None:
    issues = validate_preflight(project)
    if issues:
        raise ReadinessError(
            "pre-flight readiness is required before planning, approval, or run: " + "; ".join(issues[:6])
        )


def _require_current_readiness(project: Project, plan: Plan) -> None:
    if not plan.readiness_digest:
        raise ReadinessError("plan has no readiness binding; recreate the plan")
    from .readiness import digest as readiness_digest

    current = readiness_digest(project)
    if current != plan.readiness_digest:
        raise ReadinessError("readiness record changed after this plan was created; make a new plan")


def _print_task(task: Task) -> None:
    print(f"{task.id}  {task.status:11}  {task.title}")
    if task.plan_id:
        print(f"  plan: {task.plan_id}")
    if task.run_id:
        print(f"  run:  {task.run_id}")


def cmd_init(args: argparse.Namespace) -> int:
    project = Project.init(args.path, name=args.name)
    print(f"Initialized Aperio project at {project.root}")
    print(f"State: {project.state}")
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    project = _project(args)
    text = sys.stdin.read() if args.text == "-" else args.text
    ask = project.add_ask(text, source=args.source)
    print(f"{ask.id}  recorded")
    return 0


def _load_plan_data(path: str) -> dict[str, Any]:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ModelError(f"plan is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ModelError("plan must be a JSON object")
    return data


def cmd_plan(args: argparse.Namespace) -> int:
    project = _project(args)
    _require_learning(project)
    _require_todo(project)
    _require_preflight(project)
    todo_id = _active_todo(project)
    learning = learning_status(project)
    from .readiness import digest as readiness_digest_at_plan

    readiness_digest_value = readiness_digest_at_plan(project)
    data = _load_plan_data(args.file)
    task = Task(
        id=new_id("task"),
        title=str(data.get("title", "")).strip(),
        request=str(data.get("request", "")).strip(),
        status="planned",
    )
    if not task.title or not task.request:
        raise ModelError("plan needs title and request")
    allowed_raw = data.get("allowed_paths", [])
    if not isinstance(allowed_raw, list) or not all(isinstance(item, str) for item in allowed_raw):
        raise ModelError("plan allowed_paths must be a list of strings")
    steps_raw = data.get("steps", [])
    if not isinstance(steps_raw, list) or not all(isinstance(item, dict) for item in steps_raw):
        raise ModelError("plan steps must be a list of objects")
    acceptance_raw = data.get("acceptance", [])
    if not isinstance(acceptance_raw, list) or not all(isinstance(item, dict) for item in acceptance_raw):
        raise ModelError("plan acceptance must be a list of objects")
    try:
        steps = [Step.from_dict(item) for item in steps_raw]
        acceptance = [Acceptance.from_dict(item) for item in acceptance_raw]
    except ModelError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ModelError(f"plan step or acceptance is malformed: {exc}") from exc
    plan = Plan(
        id=new_id("plan"),
        task_id=task.id,
        title=task.title,
        request=task.request,
        allowed_paths=list(allowed_raw),
        steps=steps,
        acceptance=acceptance,
        builder=str(data.get("builder", "agent")),
        todo_id=todo_id,
        learning_digest=str(learning.get("digest") or ""),
        readiness_digest=readiness_digest_value,
        sandbox=bool(data.get("sandbox", False)),
    )
    plan.validate()
    if not plan.acceptance:
        raise ModelError("plan needs at least one acceptance check")

    progress = discovery_status(project)
    if not progress["ready"]:
        if progress["missing"]:
            missing = ", ".join(progress["missing"])
            raise DiscoveryError(
                "discovery is required before planning; finish or waive: " + missing
            )
        if progress["research"]:
            research = ", ".join(progress["research"])
            raise DiscoveryError(
                "discovery has unresolved research answers; record a decision first: " + research
            )
        if progress["expired"]:
            expired = ", ".join(progress["expired"])
            raise DiscoveryError(
                "discovery waivers expired; renew or answer: " + expired
            )
        raise DiscoveryError("discovery is not ready")
    if progress["waived"]:
        print(
            "WARNING: discovery waivers accepted: " + ", ".join(progress["waived"]),
            file=sys.stderr,
        )

    plan.discovery_digest = discovery_digest(project)
    task.plan_id = plan.id
    with project.lock():
        project.save_plan(plan)
        project.put_task(task)
        project.append_event("plan.created", {"task_id": task.id, "plan_id": plan.id})
    print(f"{task.id}  {plan.id}  planned")
    lessons = relevant_lessons(project, list(allowed_raw))
    for lesson in lessons:
        print(
            f"LESSON {lesson['id']} applies to this plan's paths: {lesson['text']}",
            file=sys.stderr,
        )
    print("Approve it before running: aperio approve " + plan.id)
    return 0


def _require_current_discovery(project: Project, plan: Plan) -> None:
    if not plan.discovery_digest:
        if project.discovery() is not None:
            raise DiscoveryError(
                "plan has no discovery binding; recreate the plan before approval"
            )
        return
    current = discovery_digest(project)
    if current != plan.discovery_digest:
        raise DiscoveryError(
            "discovery changed after this plan was created; make a new plan"
        )
    progress = discovery_status(project)
    if not progress["ready"]:
        if progress["expired"]:
            raise DiscoveryError(
                "discovery waivers expired; renew or answer: " + ", ".join(progress["expired"])
            )
        raise DiscoveryError("discovery is no longer ready; make a new plan")


def cmd_approve(args: argparse.Namespace) -> int:
    project = _project(args)
    _require_learning(project)
    if args.confirm != "I approve this plan":
        raise ModelError('approval requires --confirm "I approve this plan"')
    plan = project.get_plan(args.plan_id)
    _require_current_learning(project, plan)
    _require_current_discovery(project, plan)
    _require_current_readiness(project, plan)
    task = project.get_task(plan.task_id)
    if task.status not in {"planned", "approved", "failed"}:
        raise ModelError(f"task is {task.status}; an approved, verified, or done task cannot be re-approved")
    plan.approval = Approval(
        approved_by=args.by,
        note=args.note,
        plan_sha256=plan_body_digest(plan),
    )
    task.status = "approved"
    with project.lock():
        project.save_plan(plan)
        project.put_task(task)
        project.append_event("plan.approved", {"plan_id": plan.id, "by": args.by})
    print(f"{plan.id}  approved by {args.by}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    project = _project(args)
    _require_learning(project)
    task = project.get_task(args.task_id)
    if not task.plan_id:
        raise RunError("task has no plan")
    plan = project.get_plan(task.plan_id)
    _require_current_learning(project, plan)
    _require_current_discovery(project, plan)
    _require_current_readiness(project, plan)
    _require_preflight(project)
    if plan.todo_id:
        todo = todo_status(project)
        linked = next((item for item in todo["tasks"] if item["id"] == plan.todo_id), None)
        if linked is None:
            raise ModelError("plan is linked to a missing todo task")
        if linked["status"] not in {"in_progress", "accepted"}:
            raise ModelError(
                f"linked todo task is {linked['status']}; start or accept it before running the plan"
            )
    evidence = apply_plan(project, plan, actor=args.actor)
    print(f"{evidence['run_id']}  {evidence['status']}")
    if evidence.get("changed_files"):
        print("changed: " + ", ".join(evidence["changed_files"][:20]))
    if evidence.get("violations"):
        for violation in evidence["violations"][:10]:
            print("violation: " + violation)
        return 1
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    project = _project(args)
    _require_learning(project)
    task = project.get_task(args.task_id)
    if not task.plan_id:
        raise RunError("task has no plan")
    plan = project.get_plan(task.plan_id)
    _require_current_learning(project, plan)
    _require_current_discovery(project, plan)
    _require_current_readiness(project, plan)
    _require_preflight(project)
    if plan.todo_id:
        todo = todo_status(project)
        linked = next((item for item in todo["tasks"] if item["id"] == plan.todo_id), None)
        if linked is None:
            raise ModelError("plan is linked to a missing todo task")
        if linked["status"] not in {"in_progress", "accepted"}:
            raise ModelError(
                f"linked todo task is {linked['status']}; start or accept it before resuming the plan"
            )
    evidence = resume_plan(project, args.task_id, actor=args.actor)
    print(f"{evidence['run_id']}  {evidence['status']}")
    if evidence.get("violations"):
        for violation in evidence["violations"][:10]:
            print("violation: " + violation)
        return 1
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    project = _project(args)
    evidence = verify(project, args.task_id)
    print(f"{evidence['check_id']}  {evidence['status']}")
    for check in evidence["checks"]:
        print(f"  {check['check_id']}: {'ok' if check['ok'] else 'FAILED'} (exit {check['exit_code']})")
    return 0 if evidence["status"] == "passed" else 1


def cmd_review(args: argparse.Namespace) -> int:
    project = _project(args)
    if args.host:
        result = run_host_review(
            project,
            args.task_id,
            host=args.host,
            timeout_s=args.timeout,
            budget_usd=args.budget,
        )
        print(f"{args.task_id}  review {result['verdict']} by {result['host']}")
        for finding in result.get("findings", [])[:10]:
            print(f"  {finding.get('severity', '?')}: {finding.get('claim', '')}")
        return 0 if result["verdict"] == "confirmed" else 1
    if not args.reviewer or not args.verdict:
        raise ModelError("manual review needs --reviewer and --verdict, or use --host")
    result = review(project, args.task_id, args.reviewer, args.verdict, notes=args.notes)
    print(f"{args.task_id}  review {result['verdict']} by {result['reviewer']}")
    return 0 if result["verdict"] == "confirmed" else 1


def _require_full_readiness(project: Project) -> None:
    progress = readiness_status(project)
    if progress["ready"]:
        return
    issues = "; ".join(progress["issues"][:6])
    raise ReadinessError(
        "full project readiness is required before done or handoff" + (f": {issues}" if issues else "")
    )


def cmd_done(args: argparse.Namespace) -> int:
    project = _project(args)
    _require_full_readiness(project)
    task = finish(project, args.task_id)
    print(f"{task['id']}  done")
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    project = _project(args)
    if not args.yes:
        raise ModelError("rollback requires --yes")
    restored = rollback(project, args.task_id)
    print(f"{args.task_id}  rolled back {len(restored)} file(s)")
    return 0


def _audit_status_safe(project: Project) -> dict[str, Any] | None:
    try:
        return audit_latest(project)
    except AuditError as exc:
        return {"invalid": str(exc)}


def cmd_status(args: argparse.Namespace) -> int:
    project = _project(args)
    if args.task_id:
        task = project.get_task(args.task_id)
        data = task.to_dict()
        if task.plan_id:
            plan = project.get_plan(task.plan_id)
            data["plan"] = plan.to_dict()
        data["evidence"] = project.evidence(task.id)
        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            _print_task(task)
            if task.review:
                print(f"  review: {task.review.verdict} by {task.review.reviewer}")
            for note in task.notes:
                print(f"  note: {note}")
        return 0
    tasks = project.tasks()
    audit = _audit_status_safe(project)
    repository = repo_facts(project)
    if args.json:
        discovery = project.discovery()
        progress = discovery_status(project) if discovery is not None else None
        print(
            json.dumps(
                {
                    "project": str(project.root),
                    "state": str(project.state),
                    "git": repository,
                    "discovery": progress,
                    "audit": audit,
                    "tasks": [task.to_dict() for task in tasks],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"Project: {project.root}")
        print(f"State:   {project.state}")
        print(f"Git:     {format_git(repository)}")
        discovery = project.discovery()
        if discovery is not None:
            progress = discovery_status(project)
            print(
                f"Discovery: {progress['answered']}/{progress['total']} answered"
                f" · {progress['research']} need research"
                f" · ready={'yes' if progress['ready'] else 'no'}"
            )
        if audit is None:
            print("Audit: not recorded")
        elif "invalid" in audit:
            print(f"Audit: INVALID — {audit['invalid']}")
        else:
            print(
                f"Audit: {audit.get('audit_id', '')} · {audit.get('run_status', 'unknown')}"
                f" · {audit.get('checked', 0)}/{audit.get('units', 0)} checked"
                f" · {audit.get('confirmed', 0)} confirmed"
                f" · {audit.get('needs_validation', 0)} needs validation"
            )
        if not tasks:
            print("No tasks. Add an ask or a plan.")
        for task in tasks:
            _print_task(task)
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    project = _project(args)
    step = next_action(project)
    if args.json:
        print(json.dumps(step, indent=2, sort_keys=True))
    else:
        print(f"next: {step['action']}")
        print(f"  command: {step['command']}")
        print(f"  why: {step['why']}")
        for key in ("question", "todo_id", "task_id", "plan_id"):
            if key in step:
                print(f"  {key}: {step[key]}")
        if step.get("issues"):
            print("  issues:")
            for issue in step["issues"][:6]:
                print(f"    - {issue}")
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    project = None
    try:
        project = _project(args)
    except StoreError:
        project = None  # explaining gates works without a project
    info = explain(args.topic, project)
    if args.json:
        print(json.dumps(info, indent=2, sort_keys=True))
    else:
        print(info["text"])
    return 0


def cmd_tutorial(args: argparse.Namespace) -> int:
    if args.tutorial_command == "build":
        result = tutorial_build(args.directory)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"Tutorial ready: {result['project']}")
            print(f"  checklist: {result['checklist']}")
            print("  fly the loop, then: aperio tutorial check <dir>")
        return 0
    result = tutorial_check(args.directory)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Flight: {result['grade']} ({result['passed']}/{result['total']})")
        for entry in result["steps"]:
            mark = "x" if entry["done"] else " "
            print(f"  [{mark}] {entry['step']}")
            if not entry["done"]:
                print(f"      hint: {entry['hint']}")
    return 0


def cmd_promo(args: argparse.Namespace) -> int:
    project = _project(args)
    try:
        result = build_promo(
            project,
            args.task_id,
            duration=args.duration,
            vertical=args.vertical,
        )
    except PromoError as exc:
        print(f"apero: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        sheet = result["sheet"]
        print(f"Promo draft for task {args.task_id}")
        print(f"  {sheet['duration_s']}s @ {sheet['fps']}fps  {sheet['width']}x{sheet['height']}")
        for scene in sheet["scenes"]:
            print(f"  {scene['start']:>6.2f}s  {scene['name']:<10} {scene.get('text', '')}")
        print("  next: approve and run the generated promo plan (see --json)")
    return 0


def cmd_mcp(args: argparse.Namespace) -> int:
    """Serve Aperio's read-only advisors over JSON-RPC 2.0 on stdio."""
    mcp_serve(default_project=args.project or "")
    return 0


def cmd_skill_verify(args: argparse.Namespace) -> int:
    if getattr(args, "skill_command", None) == "verify":
        target = Path(args.path).expanduser()
        try:
            report = skillspector_scan(target)
        except FileNotFoundError as exc:
            print(f"apero: {exc}", file=sys.stderr)
            return 2
        risk = report["risk_assessment"]
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(format_skillspector(report))
        # Gate: DO NOT INSTALL blocks (exit 1); CAUTION warns but allows.
        return 1 if risk["recommendation"] == "block installation" else 0
    raise ModelError(f"unknown skill action: {getattr(args, 'skill_command', None)!r}")


def cmd_lesson(args: argparse.Namespace) -> int:
    project = _project(args)
    if args.lesson_command == "add":
        entry = lesson_add(
            project,
            args.text,
            task_id=args.task or "",
            paths=args.paths.split(",") if args.paths else [],
            source=args.source,
        )
        print(f"{entry['id']}  recorded")
        return 0
    if args.lesson_command == "remove":
        result = lesson_remove(project, args.lesson_id)
        print(f"{result['removed']}  removed; {result['remaining']} remaining")
        return 0
    data = read_lessons(project)
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(format_lessons(data))
    return 0


def cmd_handoff(args: argparse.Namespace) -> int:
    project = _project(args)
    _require_full_readiness(project)
    path = write_handoff(project, args.task_id)
    print(path)
    if args.print:
        print(path.read_text(encoding="utf-8"))
    return 0


def cmd_hosts(args: argparse.Namespace) -> int:
    hosts = detect_hosts()
    if args.json:
        print(json.dumps([h.__dict__ for h in hosts], indent=2, sort_keys=True))
        return 0
    print(f"{'name':12} {'status':10} {'version':48} path")
    for host in hosts:
        print(f"{host.name:12} {host.status:10} {host.version[:48]:48} {host.path or ''}")
    print("\nPresence is not permission. Authentication, model access, and cost are unverified.")
    return 0


def cmd_recover(args: argparse.Namespace) -> int:
    project = Project.open(args.root or args.project)
    tasks = project.recover_queue()
    if tasks is None:
        print("no saved queue snapshot in the event journal; nothing changed", file=sys.stderr)
        return 2
    for task in tasks:
        print(f"{task.id}\t{task.status}\t{task.title}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    project = _project(args)
    checks: list[tuple[str, bool, str]] = [
        ("python", sys.version_info >= (3, 10), sys.version.split()[0]),
        ("project state", project.state.is_dir(), str(project.state)),
        ("project metadata", (project.state / "project.json").is_file(), "project.json"),
        ("queue", (project.state / "queue.json").is_file(), "queue.json"),
        ("write access", os.access(project.state, os.W_OK), str(project.state)),
    ]
    failed = False
    for name, ok, detail in checks:
        print(f"{'OK  ' if ok else 'FAIL'} {name}: {detail}")
        failed = failed or not ok
    discovery = None
    try:
        discovery = project.discovery()
        if discovery is not None:
            progress = discovery_status(project)
            print(
                "INFO discovery: "
                f"{progress['answered']}/{progress['total']} answered, "
                f"{progress['research']} need research, "
                f"{len(progress['expired'])} expired waivers, "
                f"ready={'yes' if progress['ready'] else 'no'}"
            )
    except (StoreError, DiscoveryError) as exc:
        print(f"FAIL discovery: {exc}")
        failed = True
    try:
        project.tasks()
        print("OK queue: parsed")
    except (StoreError, ModelError) as exc:
        print(f"FAIL queue: {exc}")
        failed = True
    return 1 if failed else 0


def cmd_drift(args: argparse.Namespace) -> int:
    findings = drift_check(args.project)
    if args.json:
        print(json.dumps([finding.to_dict() for finding in findings], indent=2, sort_keys=True))
    else:
        print(format_drift(findings))
    return 1 if findings else 0


def _question_payload(project: Project, question: Any) -> dict[str, Any]:
    progress = discovery_status(project)
    return {
        "id": question.id,
        "domain": question.domain,
        "prompt": question.prompt,
        "why": question.why,
        "multi": question.multi,
        "allow_text": question.allow_text,
        "options": [
            {"number": number, "value": choice.value, "label": choice.label}
            for number, choice in enumerate(question.choices, 1)
        ],
        "progress": {
            "answered": progress["answered"],
            "total": progress["total"],
            "research": progress["research"],
            "missing": progress["missing"],
            "waived": progress["waived"],
            "waived_research": progress["waived_research"],
            "expired": progress["expired"],
            "ready": progress["ready"],
        },
        "hints": inspection_hints(project, question.id),
    }


def cmd_discover(args: argparse.Namespace) -> int:
    project = _project(args)
    if args.discover_command == "next":
        question = next_question(project)
        if question is None:
            progress = discovery_status(project)
            if args.json:
                print(as_json({"ready": True, "status": progress, "question": None}))
            else:
                print(format_status(project))
            return 0
        if args.json:
            print(
                as_json(
                    {
                        "ready": False,
                        "status": discovery_status(project),
                        "question": _question_payload(project, question),
                    }
                )
            )
        else:
            print(format_next(project))
            hints = inspection_hints(project, question.id)
            if hints:
                print("\nInspection hints:")
                for hint in hints:
                    print(f"- {hint}")
        return 0
    if args.discover_command == "answer":
        question = QUESTION_BY_ID.get(args.question_id)
        if question is None:
            raise DiscoveryError(f"unknown question: {args.question_id}")
        values = parse_choices(question, args.choice or "")
        answer = answer_question(
            project,
            args.question_id,
            choices=values,
            text=args.text or "",
            evidence=args.evidence or "",
        )
        progress = discovery_status(project)
        if args.json:
            print(
                as_json(
                    {
                        "answer": answer,
                        "next": progress["next"],
                        "ready": progress["ready"],
                        "status": progress,
                    }
                )
            )
        else:
            print(f"{args.question_id} recorded")
            if progress["next"]:
                print(format_next(project))
            else:
                print(format_status(project))
        return 0
    if args.discover_command == "waive":
        waiver = waive_question(
            project,
            args.question_id,
            by=args.by,
            risk=args.risk,
            confirm=args.confirm,
            review_at=args.review_at,
        )
        if args.json:
            print(as_json({"waiver": waiver, "status": discovery_status(project)}))
        else:
            print(f"{args.question_id} waived by {waiver['by']}")
            print(format_status(project))
        return 0
    if args.discover_command == "status":
        progress = discovery_status(project)
        print(as_json(progress) if args.json else format_status(project))
        return 0
    if args.discover_command == "summary":
        print(discovery_summary(project))
        return 0
    raise DiscoveryError("unknown discover command")


def cmd_inspect(args: argparse.Namespace) -> int:
    project = _project(args)
    data = collect_inspection(project, url=args.url, allow_private=args.allow_private)
    print(as_json(data) if args.json else format_inspection(data))
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    project = _project(args)
    if args.evidence_command == "add":
        entry = evidence_add(project, args.path, label=args.label)
        if args.json:
            print(as_json(entry))
        else:
            print(f"{entry['id']}  {entry['path']}  {entry['sha256']}")
        return 0
    data = evidence_entries(project)
    print(as_json(data) if args.json else format_evidence(data))
    return 0


def cmd_learn(args: argparse.Namespace) -> int:
    project = _project(args)
    if args.learn_command == "import":
        data = import_learning(project, args.file, replace=args.replace)
    elif args.learn_command == "proof":
        data = record_learning_proof(project, args.command, timeout=args.timeout)
    else:
        data = learning_status(project)
    print(as_json(data) if args.json else format_learning(data))
    if args.learn_command == "status":
        return 0
    return 0 if data["ready"] else 1


def cmd_todo(args: argparse.Namespace) -> int:
    project = _project(args)
    if args.todo_command == "add":
        result = todo_add(
            project,
            args.title,
            deliverable=args.deliverable,
            acceptance=args.acceptance,
        )
        print(as_json(result) if args.json else f"{result['id']}  {result['status']}  {result['title']}")
        return 0
    if args.todo_command == "start":
        result = todo_start(project, args.task_id)
        print(as_json(result) if args.json else f"{result['id']}  {result['status']}  {result['title']}")
        return 0
    if args.todo_command == "accept":
        result = todo_accept(
            project,
            args.task_id,
            by=args.by,
            evidence=args.evidence,
            confirm=args.confirm,
        )
        print(as_json(result) if args.json else f"{result['id']}  {result['status']}  {result['title']}")
        return 0
    if args.todo_command == "defer":
        result = todo_defer(project, args.task_id, by=args.by, reason=args.reason)
        print(as_json(result) if args.json else f"{result['id']}  {result['status']}  {result['title']}")
        return 0
    result = todo_status(project)
    print(as_json(result) if args.json else format_todo(result))
    return 0


def cmd_readiness(args: argparse.Namespace) -> int:
    project = _project(args)
    if args.readiness_command == "import":
        result = import_readiness(project, args.file, replace=args.replace)
    else:
        result = readiness_status(project)
    print(as_json(result) if args.json else format_readiness(result))
    if args.readiness_command == "status":
        return 0
    return 0 if result["ready"] else 1


def cmd_skill(args: argparse.Namespace) -> int:
    project = _project(args)
    if args.skill_command == "create":
        record = skill_create(
            project,
            args.name,
            purpose=args.purpose,
            triggers=args.trigger,
            body=args.body,
            replace=args.replace,
        )
        print(as_json(record) if args.json else f"{record['name']}  {record['status']}  {record['path']}")
        return 0
    if args.skill_command == "validate":
        issues = skill_validate(project, args.name)
        result = {"name": args.name, "ready": not issues, "issues": issues}
        print(as_json(result) if args.json else ("\n".join(issues) if issues else f"{args.name}  ready"))
        return 0 if not issues else 1
    data = list_skills(project)
    print(as_json(data) if args.json else "\n".join(item["name"] for item in data["skills"]) or "No project skills.")
    return 0


def cmd_security(args: argparse.Namespace) -> int:
    project = _project(args)
    findings = security_scan(project, include_tests=args.include_tests)
    if args.json:
        print(json.dumps({"findings": findings, "count": len(findings)}, indent=2, sort_keys=True))
    else:
        print(format_security(findings))
    return 1 if any(item["severity"] in {"high", "critical"} for item in findings) else 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    project = _project(args)
    path = write_dashboard(project, args.output, force=args.force)
    print(path)
    return 0


def cmd_tool(args: argparse.Namespace) -> int:
    project = _project(args)
    if args.tool_command == "import":
        result = import_toolchain(project, args.file, replace=args.replace)
        print(as_json(result) if args.json else format_toolchain(result))
        return 0
    if args.tool_command == "validate":
        data = json.loads(Path(args.file).read_text(encoding="utf-8"))
        issues = validate_toolchain(data)
        result = {"file": args.file, "ready": not issues, "issues": issues}
        print(as_json(result) if args.json else ("\n".join(issues) if issues else "toolchain  ready"))
        return 0 if not issues else 1
    if args.tool_command == "install":
        result = install_tool(
            project,
            args.name,
            approved_by=args.by,
            confirm=args.confirm,
            timeout=args.timeout,
        )
        print(as_json(result) if args.json else f"{result['name']}  installed  {result['version']}")
        return 0
    data = toolchain_status(project)
    print(as_json(data) if args.json else format_toolchain(data))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    project = _project(args)
    with project.lock():
        return _cmd_audit_locked(project, args)


def _cmd_audit_locked(project: Project, args: argparse.Namespace) -> int:
    if args.audit_command == "start":
        result = audit_start(project, scope=args.scope, profile=args.profile)
        print(as_json(result) if args.json else f"{result['audit_id']}  {result['units']} units  {result['path']}")
        return 0
    if args.audit_command == "add":
        finding = audit_add_finding(
            project,
            title=args.title,
            status=args.status,
            unit_id=args.unit or "",
            path=args.path or "",
            line=args.line,
            severity=args.severity or "",
            boundary=args.boundary or "",
            evidence=args.evidence,
            audit_id=args.audit_id or "",
        )
        print(as_json(finding) if args.json else f"{finding['id']}  {finding['status']}  {finding['title']}")
        return 0
    if args.audit_command == "unit":
        unit = audit_set_unit(
            project,
            unit_id=args.unit_id,
            status=args.status,
            note=args.note or "",
            audit_id=args.audit_id or "",
        )
        print(as_json(unit) if args.json else f"{unit['id']}  {unit['status']}  {unit['path']}")
        return 0
    if args.audit_command == "brief":
        result = audit_brief(project, args.audit_id or "")
        print(as_json(result) if args.json else result["brief"])
        return 0
    if args.audit_command == "ingest":
        result = audit_ingest(project, args.file, args.audit_id or "")
        print(as_json(result) if args.json else f"{result['imported']} findings imported into {result['audit_id']}")
        return 0
    if args.audit_command == "verify":
        finding = audit_verify_finding(
            project,
            args.finding_id,
            by=args.by,
            verdict=args.verdict,
            evidence=args.evidence,
            audit_id=args.audit_id or "",
        )
        print(as_json(finding) if args.json else f"{finding['id']}  {finding['verification']['verdict']} by {finding['verification']['by']}")
        return 0
    if args.audit_command == "validate":
        errors = audit_validate(project, args.audit_id or "")
        if args.json:
            print(as_json({"ok": not errors, "errors": errors}))
        else:
            print("AUDIT LEDGER: valid" if not errors else "\n".join(f"FAIL: {error}" for error in errors))
        return 0 if not errors else 1
    if args.audit_command == "report":
        result = audit_report(project, args.audit_id or "")
        print(as_json(result) if args.json else result["report"])
        return 0 if result["run_status"] == "complete" else 1
    result = audit_status(project, args.audit_id or "")
    print(as_json(result) if args.json else "\n".join(f"{key}: {value}" for key, value in result.items()))
    return 0


def cmd_message(args: argparse.Namespace) -> int:
    project = _project(args)
    store = MeshStore(project)
    try:
        if args.message_command == "send":
            message = store.send(
                args.sender,
                args.to,
                args.body,
                task_id=args.task,
                kind=args.kind,
                thread_id=args.thread,
                reply_to=args.reply_to,
            )
            print(json.dumps(message, indent=2, sort_keys=True))
            return 0
        if args.message_command == "read":
            messages = store.read(
                recipient=args.to,
                task_id=args.task,
                thread_id=args.thread,
                since_id=args.since,
                limit=args.limit,
                mark_read=args.mark_read,
            )
            if args.json:
                print(json.dumps(messages, indent=2, sort_keys=True))
            else:
                for message in messages:
                    print(f"{message['id']}  {message['thread_id']}  {message['sender']} -> {message['recipient']}: {message['body']}")
            return 0
        if args.message_command == "ack":
            print(json.dumps(store.ack(args.message_id, args.by), indent=2, sort_keys=True))
            return 0
        if args.message_command == "stats":
            print(json.dumps(store.stats(), indent=2, sort_keys=True))
            return 0
    finally:
        store.close()
    raise ModelError(f"unknown message command: {args.message_command}")


def cmd_mediate(args: argparse.Namespace) -> int:
    project = _project(args)
    record = mediate(project, args.task_id)
    print(f"{record['disposition']}: {record['reason']}")
    print(record["evidence_path"])
    return 0 if record["disposition"] == "CONFIRMED" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aperio",
        description="Aperio v2: a bounded, evidence-first project orchestrator.",
    )
    parser.add_argument("--version", action="version", version=f"aperio {__version__}")
    parser.add_argument("--project", default=os.getcwd(), help="project root (default: current directory)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="initialize a project")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--name", default="")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("ask", help="record an owner ask")
    p.add_argument("text", help="ask text, or - to read stdin")
    p.add_argument("--source", default="manual")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("plan", help="create a plan from JSON")
    p.add_argument("file", help="plan JSON path, or - to read stdin")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("approve", help="approve a plan as the owner")
    p.add_argument("plan_id")
    p.add_argument("--by", default=os.environ.get("USER", "owner"))
    p.add_argument("--note", default="")
    p.add_argument("--confirm", required=True)
    p.set_defaults(func=cmd_approve)

    p = sub.add_parser("run", help="apply an approved plan")
    p.add_argument("task_id")
    p.add_argument("--actor", default="agent")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("resume", help="restore an interrupted run and rerun its approved plan")
    p.add_argument("task_id")
    p.add_argument("--actor", default="agent")
    p.set_defaults(func=cmd_resume)

    p = sub.add_parser("verify", help="run the plan's acceptance checks")
    p.add_argument("task_id")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("review", help="record an independent review")
    p.add_argument("task_id")
    p.add_argument("--reviewer", default=None)
    p.add_argument("--verdict", choices=["confirmed", "refuted"], default=None)
    p.add_argument("--notes", default="")
    p.add_argument("--host", default=None, help="run a fresh-context host review (claude, codex, dsh, goose)")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--budget", type=float, default=1.50)
    p.set_defaults(func=cmd_review)

    p = sub.add_parser("done", help="mark a task done after review")
    p.add_argument("task_id")
    p.set_defaults(func=cmd_done)

    p = sub.add_parser("rollback", help="restore a run's files from its backup")
    p.add_argument("task_id")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_rollback)

    p = sub.add_parser("status", help="show project or task state")
    p.add_argument("task_id", nargs="?")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser(
        "next",
        help="show the next legal action, its exact command, and why (read-only)",
    )
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_next)

    p = sub.add_parser(
        "explain",
        help="explain a gate: what it checks, why it exists, live status (read-only)",
    )
    p.add_argument("topic", choices=EXPLAIN_TOPICS)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_explain)

    p = sub.add_parser(
        "tutorial",
        help="build a practice fixture and fly the loop, or grade a flight (read-only check)",
    )
    tutorial_sub = p.add_subparsers(dest="tutorial_command", required=True)
    tutorial_build_parser = tutorial_sub.add_parser("build", help="create the practice fixture")
    tutorial_build_parser.add_argument("directory")
    tutorial_build_parser.add_argument("--json", action="store_true")
    tutorial_build_parser.set_defaults(func=cmd_tutorial)
    tutorial_check_parser = tutorial_sub.add_parser("check", help="grade a flight from real state (read-only)")
    tutorial_check_parser.add_argument("directory")
    tutorial_check_parser.add_argument("--json", action="store_true")
    tutorial_check_parser.set_defaults(func=cmd_tutorial)

    p = sub.add_parser("lesson", help="the project's lessons ledger: what went wrong, surfaced before it matters")
    lesson_sub = p.add_subparsers(dest="lesson_command", required=True)
    lesson_add_parser = lesson_sub.add_parser("add", help="record a lesson")
    lesson_add_parser.add_argument("text")
    lesson_add_parser.add_argument("--task", default="", help="the task that taught this lesson")
    lesson_add_parser.add_argument("--paths", default="", help="comma-separated project paths the lesson concerns")
    lesson_add_parser.add_argument("--source", default="manual")
    lesson_add_parser.set_defaults(func=cmd_lesson)
    lesson_list_parser = lesson_sub.add_parser("list", help="list recorded lessons")
    lesson_list_parser.add_argument("--json", action="store_true")
    lesson_list_parser.set_defaults(func=cmd_lesson)
    lesson_remove_parser = lesson_sub.add_parser("remove", help="remove a lesson by id")
    lesson_remove_parser.add_argument("lesson_id")
    lesson_remove_parser.set_defaults(func=cmd_lesson)

    p = sub.add_parser(
        "mcp",
        help="serve Aperio's read-only advisors over JSON-RPC 2.0 on stdio (MCP)",
    )
    p.set_defaults(func=cmd_mcp)

    p = sub.add_parser(
        "promo",
        help="draft a launch-video shot sheet and promo plan from a completed task",
    )
    p.add_argument("task_id")
    p.add_argument("--duration", type=int, default=12, help="seconds, 8..30 (default 12)")
    p.add_argument("--vertical", action="store_true", help="1080x1920 instead of 1920x1080")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_promo)

    p = sub.add_parser("handoff", help="write the owner handoff")
    p.add_argument("task_id")
    p.add_argument("--print", action="store_true")
    p.set_defaults(func=cmd_handoff)

    p = sub.add_parser("hosts", help="detect installed hosts (read-only)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_hosts)

    p = sub.add_parser("doctor", help="check the project state")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("recover", help="restore a missing or corrupt queue from the event journal")
    p.add_argument("root", nargs="?", default=None, help="project root; defaults to the --project value (default: current directory)")
    p.set_defaults(func=cmd_recover)

    p = sub.add_parser("drift", help="check docs for links and paths that do not exist")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_drift)

    p = sub.add_parser("discover", help="structured, persistent discovery interview")
    discover = p.add_subparsers(dest="discover_command", required=True)
    discover_next = discover.add_parser("next", help="show the next question")
    discover_next.add_argument("--json", action="store_true")
    discover_next.set_defaults(func=cmd_discover)
    discover_answer = discover.add_parser("answer", help="record an answer")
    discover_answer.add_argument("question_id")
    discover_answer.add_argument("--choice", default="", help="comma-separated option numbers or values")
    discover_answer.add_argument("--text", default="", help="free-text answer or clarification")
    discover_answer.add_argument("--evidence", default="", help="path, URL, or reference")
    discover_answer.add_argument("--json", action="store_true")
    discover_answer.set_defaults(func=cmd_discover)
    discover_waive = discover.add_parser("waive", help="record an explicit owner waiver")
    discover_waive.add_argument("question_id")
    discover_waive.add_argument("--by", required=True)
    discover_waive.add_argument("--risk", required=True)
    discover_waive.add_argument("--review-at", required=True)
    discover_waive.add_argument("--confirm", required=True)
    discover_waive.add_argument("--json", action="store_true")
    discover_waive.set_defaults(func=cmd_discover)
    discover_status = discover.add_parser("status", help="show discovery coverage")
    discover_status.add_argument("--json", action="store_true")
    discover_status.set_defaults(func=cmd_discover)
    discover_summary = discover.add_parser("summary", help="show recorded answers")
    discover_summary.set_defaults(func=cmd_discover)

    p = sub.add_parser("inspect", help="read-only folder and URL inspection")
    p.add_argument("--url", default=None, help="public URL to inspect read-only")
    p.add_argument("--allow-private", action="store_true", help="allow a private or loopback URL")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("evidence", help="record file evidence as a path and hash")
    evidence = p.add_subparsers(dest="evidence_command", required=True)
    evidence_add = evidence.add_parser("add", help="record a file reference and hash")
    evidence_add.add_argument("path")
    evidence_add.add_argument("--label", default="")
    evidence_add.add_argument("--json", action="store_true")
    evidence_add.set_defaults(func=cmd_evidence)
    evidence_list = evidence.add_parser("list", help="show recorded evidence files")
    evidence_list.add_argument("--json", action="store_true")
    evidence_list.set_defaults(func=cmd_evidence)

    p = sub.add_parser("learn", help="stack-mastery dossier, local proof, and competency gate")
    learn = p.add_subparsers(dest="learn_command", required=True)
    learn_import = learn.add_parser("import", help="import a learning dossier JSON file")
    learn_import.add_argument("file")
    learn_import.add_argument("--replace", action="store_true")
    learn_import.add_argument("--json", action="store_true")
    learn_import.set_defaults(func=cmd_learn)
    learn_proof = learn.add_parser("proof", help="run and record a local stack proof")
    learn_proof.add_argument("--command", required=True)
    learn_proof.add_argument("--timeout", type=int, default=120)
    learn_proof.add_argument("--json", action="store_true")
    learn_proof.set_defaults(func=cmd_learn)
    learn_status = learn.add_parser("status", help="show learning readiness")
    learn_status.add_argument("--json", action="store_true")
    learn_status.set_defaults(func=cmd_learn)
    learn_validate = learn.add_parser("validate", help="validate the dossier; exit 1 when not ready")
    learn_validate.add_argument("--json", action="store_true")
    learn_validate.set_defaults(func=cmd_learn)

    p = sub.add_parser("todo", help="one-task-at-a-time todo and approval ledger")
    todo = p.add_subparsers(dest="todo_command", required=True)
    todo_add_parser = todo.add_parser("add", help="add an independently reviewable task")
    todo_add_parser.add_argument("title")
    todo_add_parser.add_argument("--deliverable", required=True)
    todo_add_parser.add_argument("--acceptance", required=True)
    todo_add_parser.add_argument("--json", action="store_true")
    todo_add_parser.set_defaults(func=cmd_todo)
    todo_start_parser = todo.add_parser("start", help="start the next pending task")
    todo_start_parser.add_argument("task_id")
    todo_start_parser.add_argument("--json", action="store_true")
    todo_start_parser.set_defaults(func=cmd_todo)
    todo_accept_parser = todo.add_parser("accept", help="accept an in-progress task and record evidence")
    todo_accept_parser.add_argument("task_id")
    todo_accept_parser.add_argument("--by", required=True)
    todo_accept_parser.add_argument("--evidence", required=True)
    todo_accept_parser.add_argument("--confirm", required=True)
    todo_accept_parser.add_argument("--json", action="store_true")
    todo_accept_parser.set_defaults(func=cmd_todo)
    todo_defer_parser = todo.add_parser("defer", help="defer a pending or in-progress task with a reason")
    todo_defer_parser.add_argument("task_id")
    todo_defer_parser.add_argument("--by", required=True)
    todo_defer_parser.add_argument("--reason", required=True)
    todo_defer_parser.add_argument("--json", action="store_true")
    todo_defer_parser.set_defaults(func=cmd_todo)
    todo_list = todo.add_parser("list", help="show the todo ledger")
    todo_list.add_argument("--json", action="store_true")
    todo_list.set_defaults(func=cmd_todo)

    p = sub.add_parser("readiness", help="pre-flight, deploy, after-sales, design, and security checks")
    readiness = p.add_subparsers(dest="readiness_command", required=True)
    readiness_import = readiness.add_parser("import", help="import a readiness JSON record")
    readiness_import.add_argument("file")
    readiness_import.add_argument("--replace", action="store_true")
    readiness_import.add_argument("--json", action="store_true")
    readiness_import.set_defaults(func=cmd_readiness)
    readiness_status_parser = readiness.add_parser("status", help="show readiness")
    readiness_status_parser.add_argument("--json", action="store_true")
    readiness_status_parser.set_defaults(func=cmd_readiness)
    readiness_validate = readiness.add_parser("validate", help="validate the record; exit 1 when not ready")
    readiness_validate.add_argument("--json", action="store_true")
    readiness_validate.set_defaults(func=cmd_readiness)

    p = sub.add_parser("skill", help="project-scoped skill scaffolding")
    skill = p.add_subparsers(dest="skill_command", required=True)
    skill_create_parser = skill.add_parser("create", help="create or update an owned project skill")
    skill_create_parser.add_argument("name")
    skill_create_parser.add_argument("--purpose", required=True)
    skill_create_parser.add_argument("--trigger", action="append", required=True)
    skill_create_parser.add_argument("--body", default="")
    skill_create_parser.add_argument("--replace", action="store_true")
    skill_create_parser.add_argument("--json", action="store_true")
    skill_create_parser.set_defaults(func=cmd_skill)
    skill_list = skill.add_parser("list", help="list project skills")
    skill_list.add_argument("--json", action="store_true")
    skill_list.set_defaults(func=cmd_skill)
    skill_validate_parser = skill.add_parser("validate", help="validate a project skill")
    skill_validate_parser.add_argument("name")
    skill_validate_parser.add_argument("--json", action="store_true")
    skill_validate_parser.set_defaults(func=cmd_skill)
    skill_verify_parser = skill.add_parser(
        "verify",
        help="SkillSpector-style security verification of a skill directory before installing it",
    )
    skill_verify_parser.add_argument("path", help="skill directory (or single SKILL.md) to scan")
    skill_verify_parser.add_argument("--json", action="store_true")
    skill_verify_parser.set_defaults(func=cmd_skill_verify)

    p = sub.add_parser("security", help="bounded local secret scan")
    security = p.add_subparsers(dest="security_command", required=True)
    security_scan_parser = security.add_parser("scan", help="scan project files for obvious secrets")
    security_scan_parser.add_argument("--json", action="store_true")
    security_scan_parser.add_argument("--include-tests", action="store_true")
    security_scan_parser.set_defaults(func=cmd_security)

    p = sub.add_parser("dashboard", help="write a self-contained status dashboard")
    p.add_argument("--output", default="")
    p.add_argument("--force", action="store_true", help="overwrite an existing --output file")
    p.set_defaults(func=cmd_dashboard)

    p = sub.add_parser("tool", help="approval-gated toolchain and MCP manifest")
    tool = p.add_subparsers(dest="tool_command", required=True)
    tool_import = tool.add_parser("import", help="import a toolchain JSON manifest")
    tool_import.add_argument("file")
    tool_import.add_argument("--replace", action="store_true")
    tool_import.add_argument("--json", action="store_true")
    tool_import.set_defaults(func=cmd_tool)
    tool_validate = tool.add_parser("validate", help="validate a manifest without importing it")
    tool_validate.add_argument("file")
    tool_validate.add_argument("--json", action="store_true")
    tool_validate.set_defaults(func=cmd_tool)
    tool_install = tool.add_parser("install", help="install and verify one declared tool")
    tool_install.add_argument("name")
    tool_install.add_argument("--by", default="")
    tool_install.add_argument("--confirm", default="")
    tool_install.add_argument("--timeout", type=int, default=300)
    tool_install.add_argument("--json", action="store_true")
    tool_install.set_defaults(func=cmd_tool)
    tool_status = tool.add_parser("status", help="show declared and installed tools")
    tool_status.add_argument("--json", action="store_true")
    tool_status.set_defaults(func=cmd_tool)

    p = sub.add_parser("audit", help="source-anchored security audit ledger")
    audit = p.add_subparsers(dest="audit_command", required=True)
    audit_start_parser = audit.add_parser("start", help="create an audit ledger")
    audit_start_parser.add_argument("--scope", default=".")
    audit_start_parser.add_argument("--profile", choices=sorted(PROFILES), default="quick")
    audit_start_parser.add_argument("--json", action="store_true")
    audit_start_parser.set_defaults(func=cmd_audit)
    audit_add = audit.add_parser("add", help="record a finding")
    audit_add.add_argument("--title", required=True)
    audit_add.add_argument("--status", choices=sorted(FINDING_STATUSES), required=True)
    audit_add.add_argument("--evidence", required=True)
    audit_add.add_argument("--unit", default="")
    audit_add.add_argument("--path", default="")
    audit_add.add_argument("--line", type=int, default=None)
    audit_add.add_argument("--severity", choices=sorted(SEVERITIES), default="")
    audit_add.add_argument("--boundary", default="")
    audit_add.add_argument("--audit-id", default="")
    audit_add.add_argument("--json", action="store_true")
    audit_add.set_defaults(func=cmd_audit)
    audit_unit = audit.add_parser("unit", help="mark a coverage unit")
    audit_unit.add_argument("--unit-id", required=True)
    audit_unit.add_argument("--status", choices=sorted(UNIT_STATUSES), required=True)
    audit_unit.add_argument("--note", default="")
    audit_unit.add_argument("--audit-id", default="")
    audit_unit.add_argument("--json", action="store_true")
    audit_unit.set_defaults(func=cmd_audit)
    audit_brief_parser = audit.add_parser("brief", help="write a host audit brief")
    audit_brief_parser.add_argument("--audit-id", default="")
    audit_brief_parser.add_argument("--json", action="store_true")
    audit_brief_parser.set_defaults(func=cmd_audit)
    audit_ingest_parser = audit.add_parser("ingest", help="import host findings atomically")
    audit_ingest_parser.add_argument("--file", required=True)
    audit_ingest_parser.add_argument("--audit-id", default="")
    audit_ingest_parser.add_argument("--json", action="store_true")
    audit_ingest_parser.set_defaults(func=cmd_audit)
    audit_verify_parser = audit.add_parser("verify", help="record a fresh verification verdict")
    audit_verify_parser.add_argument("--finding-id", required=True)
    audit_verify_parser.add_argument("--by", required=True)
    audit_verify_parser.add_argument("--verdict", choices=sorted(FINDING_VERDICTS), required=True)
    audit_verify_parser.add_argument("--evidence", required=True)
    audit_verify_parser.add_argument("--audit-id", default="")
    audit_verify_parser.add_argument("--json", action="store_true")
    audit_verify_parser.set_defaults(func=cmd_audit)
    for name, help_text in (
        ("validate", "validate the ledger and findings"),
        ("report", "write the audit report"),
        ("status", "show the latest audit"),
    ):
        audit_parser = audit.add_parser(name, help=help_text)
        audit_parser.add_argument("--audit-id", default="")
        audit_parser.add_argument("--json", action="store_true")
        audit_parser.set_defaults(func=cmd_audit)

    p = sub.add_parser("message", help="local durable message store")
    msg = p.add_subparsers(dest="message_command", required=True)
    send = msg.add_parser("send", help="send a message")
    send.add_argument("--from", dest="sender", required=True)
    send.add_argument("--to", required=True)
    send.add_argument("--body", required=True)
    send.add_argument("--task", default=None)
    send.add_argument("--kind", default="note", choices=["note", "task", "reply", "review", "status"])
    send.add_argument("--thread", default=None)
    send.add_argument("--reply-to", type=int, default=None)
    send.set_defaults(func=cmd_message)
    read = msg.add_parser("read", help="read messages")
    read.add_argument("--to", default=None)
    read.add_argument("--task", default=None)
    read.add_argument("--thread", default=None)
    read.add_argument("--since", type=int, default=0)
    read.add_argument("--limit", type=int, default=100)
    read.add_argument("--mark-read", action="store_true")
    read.add_argument("--json", action="store_true")
    read.set_defaults(func=cmd_message)
    ack = msg.add_parser("ack", help="acknowledge a message")
    ack.add_argument("message_id", type=int)
    ack.add_argument("--by", required=True)
    ack.set_defaults(func=cmd_message)
    stats = msg.add_parser("stats", help="message counts")
    stats.set_defaults(func=cmd_message)

    p = sub.add_parser("mediate", help="record a disposition from task evidence")
    p.add_argument("task_id")
    p.set_defaults(func=cmd_mediate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (
        StoreError,
        RunError,
        PolicyError,
        ModelError,
        HostError,
        MeshError,
        MediationError,
        DiscoveryError,
        InspectionError,
        LearningError,
        ReadinessError,
        SkillError,
        ToolError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        print(f"aperio: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
