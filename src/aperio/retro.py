"""The retrospective: an environment audit that turns failures into improvements.

``retro`` reads a done task's evidence — violations, floor findings, lesson
matches, review findings — and classifies each into an improvement action:
mechanical violations become suggested automated checks; judgement calls
become suggested lessons or documentation. The output is a concrete list of
what to change about the environment so the next task's gates catch what
this one's didn't.

This implements the retro doctrine (adapted from mattpocock's retro skill):
the implementer has the most context pressure and the reviewer the least,
so the reviewer enforces standards — and the retro closes the loop by
asking "would a check have caught this?" for every failure.
"""

from __future__ import annotations

from typing import Any

from .store import Project


class RetroError(ValueError):
    """The task is not eligible for a retrospective."""


def retro(project: Project, task_id: str) -> dict[str, Any]:
    """Audit the environment after a task reaches done. Read-only."""
    task = project.get_task(task_id)
    if task.status == "planned":
        raise RetroError(
            "task is planned; no work was done — nothing to audit"
        )
    plan = project.get_plan(task.plan_id) if task.plan_id else None
    evidence = project.evidence_readonly(task_id)

    improvements: list[dict[str, Any]] = []
    stats: dict[str, int] = {
        "violations": 0,
        "floor_violations": 0,
        "lessons_matched": 0,
        "findings": 0,
        "checks_run": 0,
    }

    # 1. Run violations → would a check have caught each one?
    for row in evidence:
        for violation in row.get("violations", []):
            stats["violations"] += 1
            improvements.append(
                {
                    "source": "violation",
                    "finding": violation,
                    "action": _classify_violation(violation),
                }
            )

    # 2. Floor violations → the check that would have caught it.
    for row in evidence:
        for fv in row.get("floor_violations", []):
            stats["floor_violations"] += 1
            improvements.append(
                {
                    "source": "floor",
                    "finding": fv,
                    "action": "add a pre-commit hook or linter rule that catches this pattern before it enters a commit",
                }
            )

    # 3. Lessons that matched this task's paths → were they heeded?
    if plan is not None:
        from .lessons import relevant_lessons

        matched = relevant_lessons(project, plan.allowed_paths)
        stats["lessons_matched"] = len(matched)
        for lesson in matched:
            improvements.append(
                {
                    "source": "lesson",
                    "finding": f"lesson {lesson['id']} was active for this task's paths: {lesson['text']}",
                    "action": "verify the lesson was heeded; if it was not, record a follow-up lesson about why",
                }
            )

    # 4. Review findings → each classified finding is an improvement signal.
    if task.review is not None:
        for row in evidence:
            if row.get("review_id") and row.get("verdict") == "confirmed":
                for finding in row.get("findings", []):
                    stats["findings"] += 1
                    improvements.append(
                        {
                            "source": "review",
                            "finding": f"[{finding.get('severity', '?')}] {finding.get('claim', '')[:120]}",
                            "action": _classify_review_finding(finding),
                        }
                    )

    # 5. Acceptance check coverage → are the checks behaviour-level?
    if plan is not None:
        for check in plan.acceptance:
            stats["checks_run"] += 1
            cmd = check.command.strip()
            if cmd.startswith(("test -f ", "test -d ", "test -s ")):
                improvements.append(
                    {
                        "source": "coverage",
                        "finding": f"acceptance check '{check.id}' is existence-only: {cmd}",
                        "action": "add a check that asserts content or behavior, not just presence",
                    }
                )

    # 6. Gate coverage gaps → what the gates didn't catch.
    gate_gaps: list[str] = []
    if stats["violations"] > 0 and not stats["floor_violations"]:
        gate_gaps.append(
            "violations occurred but no floor findings: consider expanding the Floor patterns"
        )
    if stats["lessons_matched"] == 0 and stats["violations"] > 0:
        gate_gaps.append(
            "violations occurred with no matching lessons: record lessons from this task"
        )
    if stats["checks_run"] > 0 and all(
        isinstance(imp, dict) and imp.get("source") == "coverage"
        for imp in improvements
        if imp.get("source") == "coverage"
    ) and improvements:
        gate_gaps.append(
            "all acceptance checks are existence-only: add behaviour-level checks"
        )

    return {
        "task_id": task_id,
        "status": task.status,
        "stats": stats,
        "improvements": improvements,
        "gate_gaps": gate_gaps,
        "read_only": True,
    }


def _classify_violation(violation: str) -> str:
    """Classify a run violation into an improvement action."""
    lower = violation.lower()
    if "outside declared writes" in lower or "outside the plan" in lower:
        return "narrow the plan's allowed_paths or add the path to the step's writes"
    if "protected path" in lower or "control state" in lower:
        return "the protected-path gate fired correctly; no environment change needed"
    if "no supported os sandbox" in lower:
        return "install the sandbox toolchain (sandbox-exec or bwrap) for this platform"
    if "timeout" in lower:
        return "increase the step's timeout_s or split the step into smaller slices"
    return "add an acceptance check that would have caught this violation before the run"


def _classify_review_finding(finding: dict[str, Any]) -> str:
    """Classify a review finding into an improvement action."""
    severity = finding.get("severity", "")
    if severity == "P0":
        return "P0: fix immediately and add a regression test that fails without the fix"
    if severity == "P1":
        return "P1: fix before the next slice; add a discriminating test"
    if severity == "P2":
        return "P2: fix or document as a valid trade-off; consider a check if mechanical"
    return "classify the finding: contract misread, valid+actionable, valid trade-off, or noise"


def format_retro(report: dict[str, Any]) -> str:
    lines = [
        f"RETRO: {report['task_id']} ({report['status']})",
        f"  stats: {report['stats']}",
    ]
    if report["improvements"]:
        lines.append(f"  improvements ({len(report['improvements'])}):")
        for imp in report["improvements"]:
            lines.append(f"    [{imp['source']}] {imp['finding']}")
            lines.append(f"      → {imp['action']}")
    else:
        lines.append("  no improvements identified: the gates caught everything")
    if report["gate_gaps"]:
        lines.append("  gate gaps:")
        for gap in report["gate_gaps"]:
            lines.append(f"    - {gap}")
    return "\n".join(lines)
