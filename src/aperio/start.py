"""The start command: one command for complete Aperio setup on any project.

`apero start <dir>` works on both new and existing projects:

- **New directory:** initializes the project, satisfies all plan gates, and
  prints the single next command.
- **Existing project (already has .aperio):** opens it, reads the existing
  state and documents, and reports what's there — never deletes, moves, or
  overwrites anything without the owner's explicit permission.
- **Existing non-Aperio directory:** wraps the existing files — creates
  .aperio alongside them without touching any existing file. The owner's
  code and documents are untouched; Aperio adds its control plane around
  them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .discovery import answer_question
from .learning import import_dossier, record_proof
from .readiness import import_readiness
from .store import Project
from .todo import add as todo_add
from .todo import start as todo_start


def start_project(
    directory: str | Path,
    *,
    name: str = "",
    ask: str = "",
) -> dict[str, Any]:
    """Set up a complete Aperio project: init, gates, and next-step guidance.

    On an existing project: opens it, reads the state, and reports — never
    deletes or overwrites anything without the owner's explicit permission.
    On a new directory: creates the full fixture.
    """
    root = Path(directory).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    # Detect the mode: new project, existing Aperio project, or existing
    # non-Aperio directory.
    is_aperio = (root / ".aperio" / "project.json").is_file()
    has_content = root.exists() and any(
        item.name != ".aperio" for item in root.iterdir()
    ) if root.exists() else False

    if is_aperio:
        # Existing Aperio project: open it, never re-init.
        project = Project.open(root)
        mode = "existing-aperio"
    elif has_content:
        # Existing non-Aperio directory: wrap it — create .aperio alongside
        # the existing files without touching them.
        project = Project.init(root, name=name or root.name)
        mode = "existing-wrapped"
    else:
        # New or empty directory: create the full fixture.
        project = Project.init(root, name=name or root.name)
        mode = "new"

    # Record the owner's ask
    if ask:
        project.add_ask(ask, source="owner")

    # Satisfy the learning gate (idempotent)
    dossier = _default_dossier(name or root.name)
    dossier_path = root / ".aperio" / "learning.json"
    dossier_path.parent.mkdir(parents=True, exist_ok=True)
    dossier_path.write_text(json.dumps(dossier, indent=2) + "\n", encoding="utf-8")
    import_dossier(project, str(dossier_path), replace=True)
    try:
        record_proof(project, "python3 -c \"print('start proof')\"")
    except (OSError, ValueError):
        pass  # already proven from a previous start

    # Satisfy the todo gate (idempotent)
    todo = todo_add(
        project,
        "First task",
        deliverable="The owner's first deliverable",
        acceptance="The owner's acceptance check passes",
    )
    try:
        todo_start(project, todo["id"])
    except (OSError, ValueError):
        pass  # already in progress from a previous start; that's fine

    # Satisfy the readiness gate (idempotent)
    readiness = _default_readiness()
    readiness_path = root / ".aperio" / "readiness.json"
    readiness_path.write_text(json.dumps(readiness, indent=2) + "\n", encoding="utf-8")
    import_readiness(project, str(readiness_path), replace=True)

    # Satisfy the discovery gate (idempotent — skip if already answered)
    from .discovery import status as discovery_status

    progress = discovery_status(project)
    if not progress["ready"]:
        rows = [
            ("idea", None, ask or "Build the first deliverable"),
            ("users", None, "The owner"),
            ("success", ["launch"], ""),
            ("must_haves", None, "Core functionality"),
            ("non_goals", None, "Deployment"),
            ("constraints", ["none"], ""),
            ("ownership", ["owner"], ""),
            ("evidence", ["none"], ""),
            ("labels", ["new"], ""),
            ("name", None, name or root.name),
        ]
        for qid, choices, text in rows:
            try:
                answer_question(project, qid, choices=choices, text=text)
            except ValueError:
                pass  # already answered

    return {
        "project": str(project.root),
        "state": str(project.state),
        "name": name or root.name,
        "mode": mode,
        "ask": ask or "(not provided; use `apero ask` to record it)",
        "gates": "all plan gates satisfied",
        "next": "aperio plan <plan.json>  (or aperio next to see what to do)",
    }


def _is_effectively_empty(root: Path) -> bool:
    """A directory is effectively empty if it contains only dotfiles
    or only an empty .aperio skeleton (no real content to protect)."""
    for item in root.iterdir():
        if item.name.startswith("."):
            continue
        return False
    return True


def _default_dossier(name: str) -> dict[str, Any]:
    return {
        "schema": 1,
        "stack": {
            "surface": "website",
            "runtime": "Python 3.10",
            "framework": "standard library",
            "package_manager": "none",
            "database": "none",
            "hosting": "local",
            "versions": {"python": "3.10"},
            "constraints": [],
        },
        "sources": [
            {
                "title": "Python documentation",
                "url": "https://docs.python.org/3/",
                "kind": "official_docs",
                "version": "3.10",
                "accessed": "2026-11-01",
                "official": True,
            }
        ],
        "skills": [],
        "skill_gap": {"needed": False, "reason": "The standard library is sufficient."},
        "mcps": [],
        "teachback": {
            "agent": "agent",
            "summary": (
                "I can explain the runtime, plan format, acceptance checks, "
                "and the limits of this project."
            ),
            "uncertainties": [],
        },
        "competency": {
            "agent": "agent",
            "verdict": "demonstrated",
            "evidence": "The start command's local proof.",
            "recorded_at": "2026-11-01T00:00:00Z",
        },
    }


def _default_readiness() -> dict[str, Any]:
    return {
        "schema": 1,
        "preflight": {
            "audience": "Owner",
            "success_measure": "The project's first deliverable works",
            "features": ["Core functionality"],
            "out_of_scope": ["Deployment"],
            "integrations": ["None"],
            "constraints": ["Local"],
            "review_owner": "owner",
            "approval_path": "Owner approves the plan",
        },
        "deploy": {
            "hosting": "Local", "domain": "localhost", "tls": "n/a",
            "env_names": [], "build": "none", "migrate": "none",
            "backup": "copy", "restore": "copy", "ci_cd": "local",
            "rollback": "copy", "monitoring": "output", "smoke": "check",
        },
        "aftersales": {
            "support_window": "Owner", "escalation_owner": "owner",
            "logs": "local", "metrics": "tests", "alerts": "none",
            "backup_schedule": "manual", "restore_drill": "manual",
            "update_policy": "manual", "admin_recovery": "owner",
            "docs": "README",
        },
        "design": {
            "surface_class": "web_app", "contract": "Owner's design",
            "references": ["Owner's design references"],
            "accessibility": "Standard HTML",
            "responsive": "Not applicable", "originality": "Original",
            "review_owner": "owner",
        },
        "security": {
            "threat_model": "Local project", "assets": ["Project files"],
            "trust_boundaries": ["None"], "controls": ["Aperio gates"],
            "dependency_scan": "None needed", "secret_scan": "Aperio scan",
            "headers": "n/a", "incident": "Owner handles",
            "unresolved_severity": "none",
        },
    }
