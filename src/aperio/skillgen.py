"""Project-scoped skill scaffolding.

A generated skill is a project artifact, not a silently installed global skill.
It is written with explicit scope, triggers, commands, safety rules, and a
verification section. Host loading remains unverified until a fresh session
actually loads it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .model import ModelError, utc_now
from .paths import replace_text_atomic
from .store import Project

SCHEMA_VERSION = 1
SKILLS_DIR = ".aperio/skills"
REGISTRY_NAME = "registry.json"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")


class SkillError(ModelError):
    """A generated skill is unsafe, malformed, or would overwrite a foreign skill."""


def _root(project: Project) -> Path:
    return project.root / SKILLS_DIR


def _registry_path(project: Project) -> Path:
    return _root(project) / REGISTRY_NAME


def _read_registry(project: Project) -> dict[str, Any]:
    path = _registry_path(project)
    if not path.is_file():
        return {"schema": SCHEMA_VERSION, "skills": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SkillError(f"skill registry is unreadable: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("skills"), list):
        raise SkillError("skill registry is malformed")
    if data.get("schema") != SCHEMA_VERSION:
        raise SkillError("skill registry has an unsupported schema")
    return data


def _write_registry(project: Project, data: dict[str, Any]) -> None:
    _registry_path(project).parent.mkdir(parents=True, exist_ok=True)
    data["schema"] = SCHEMA_VERSION
    data["updated_at"] = utc_now()
    replace_text_atomic(_registry_path(project), json.dumps(data, indent=2, sort_keys=True) + "\n")


def _skill_md(name: str, purpose: str, triggers: list[str], body: str) -> str:
    trigger_text = "\n".join(f"- {item}" for item in triggers)
    extra = body.strip()
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {json.dumps(purpose, ensure_ascii=False)}\n"
        "version: 0.1.0\n"
        "scope: project\n"
        "---\n\n"
        f"# {name}\n\n"
        "## When to use\n\n"
        f"{trigger_text}\n\n"
        "## Purpose\n\n"
        f"{purpose}\n\n"
        "## Inputs and outputs\n\n"
        "Record the required inputs, the expected artifact, and the consumer of that artifact before running the skill.\n\n"
        "## Commands\n\n"
        "Record exact commands, working directories, and expected exit codes. Do not hide a command behind an opaque wrapper.\n\n"
        "## Safety\n\n"
        "Stay inside the project. Do not use credentials, global installs, destructive commands, or deployment actions without explicit owner approval.\n\n"
        "## Verification\n\n"
        "Run a reproducible check and record the command, exit code, and result. A skill that cannot prove its output is a draft, not a trusted tool.\n\n"
        "## Limits\n\n"
        "This is a project-scoped scaffold. Host loading is not proven until a fresh session loads it.\n"
        + (f"\n## Notes\n\n{extra}\n" if extra else "")
    )


def create(
    project: Project,
    name: str,
    *,
    purpose: str,
    triggers: list[str],
    body: str = "",
    replace: bool = False,
) -> dict[str, Any]:
    name = name.strip()
    purpose = purpose.strip()
    cleaned = [item.strip() for item in triggers if item.strip()]
    if not NAME_RE.fullmatch(name):
        raise SkillError("skill name must be 2-63 lowercase letters, digits, or hyphens")
    if not purpose:
        raise SkillError("skill purpose is required")
    if not cleaned:
        raise SkillError("at least one skill trigger is required")
    target = _root(project) / name
    skill_file = target / "SKILL.md"
    with project.lock():
        # read and mutate under one lock: a concurrent create must not silently
        # overwrite this update's registry entry
        data = _read_registry(project)
        existing = next((item for item in data["skills"] if item.get("name") == name), None)
        if skill_file.exists() and not replace:
            raise SkillError(f"skill already exists: {name}; pass --replace to update an owned skill")
        if skill_file.exists() and existing is None:
            raise SkillError("refusing to overwrite a skill not owned by this project registry")
        target.mkdir(parents=True, exist_ok=True)
        replace_text_atomic(skill_file, _skill_md(name, purpose, cleaned, body))
        # SkillSpector gate: verify the generated skill before saving it to
        # the registry (the owner's directive: before installing any skill,
        # the agent must verify it). Generated scaffolds should always pass,
        # but a body carrying user-supplied content could trip the detector.
        from .skillspector import scan

        report = scan(target)
        if report["risk_assessment"]["severity"] == "DO NOT INSTALL":
            raise SkillError(
                f"skill '{name}' failed the SkillSpector verification gate: "
                f"score {report['risk_assessment']['score']}, "
                f"{len(report['issues'])} finding(s); remove the flagged content and retry"
            )
        record = {
            "name": name,
            "purpose": purpose,
            "triggers": cleaned,
            "path": f"{SKILLS_DIR}/{name}",
            "scope": "project",
            "version": "0.1.0",
            "status": "draft",
            "created_at": existing.get("created_at") if existing else utc_now(),
            "updated_at": utc_now(),
        }
        data["skills"] = [item for item in data["skills"] if item.get("name") != name]
        data["skills"].append(record)
        data["skills"].sort(key=lambda item: item["name"])
        _write_registry(project, data)
        project.append_event("skill.created", {"name": name, "path": record["path"]})
    return record


def validate(project: Project, name: str) -> list[str]:
    data = _read_registry(project)
    record = next((item for item in data["skills"] if item.get("name") == name), None)
    if record is None:
        return [f"skill is not in the project registry: {name}"]
    path = project.root / str(record.get("path", ""))
    skill_file = path / "SKILL.md"
    issues: list[str] = []
    if not skill_file.is_file():
        return [f"skill file is missing: {name}"]
    text = skill_file.read_text(encoding="utf-8")
    for heading in ("## When to use", "## Purpose", "## Commands", "## Safety", "## Verification"):
        if heading not in text:
            issues.append(f"skill is missing {heading}")
    if not text.startswith("---\n"):
        issues.append("skill frontmatter is missing")
        return issues
    # the frontmatter is emitted by _skill_md with a JSON-encoded description;
    # re-derive it here so a hand-tampered or malformed header is flagged
    lines = text.splitlines()
    closing = next((index for index, line in enumerate(lines[1:], start=1) if line == "---"), None)
    if closing is None:
        issues.append("skill frontmatter is not closed")
        return issues
    meta: dict[str, str] = {}
    for line in lines[1:closing]:
        key, separator, value = line.partition(": ")
        if separator:
            meta[key.strip()] = value
    if meta.get("name") != name:
        issues.append("skill frontmatter name does not match the registry")
    if meta.get("scope") != "project":
        issues.append("skill frontmatter scope must be project")
    if meta.get("version") != str(record.get("version", "")):
        issues.append("skill frontmatter version does not match the registry")
    try:
        described = json.loads(meta.get("description", ""))
    except ValueError:
        issues.append("skill description is not a valid quoted string")
        described = None
    if described is not None and described != record.get("purpose"):
        issues.append("skill description does not match the registry purpose")
    return issues


def list_skills(project: Project) -> dict[str, Any]:
    data = _read_registry(project)
    return {"schema": SCHEMA_VERSION, "skills": data["skills"]}
