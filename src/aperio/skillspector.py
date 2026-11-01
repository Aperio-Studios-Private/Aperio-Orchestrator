"""SkillSpector-style static verification for agent skills.

A stdlib-only port of the load-bearing stage-1 detection categories from
NVIDIA's SkillSpector (https://github.com/NVIDIA/SkillSpector, Apache-2.0),
adapted for Aperio's zero-dependency constraint. It statically scans a skill
directory (SKILL.md plus bundled files) BEFORE that skill is installed, and
reports findings with severities, a weighted risk score, and an install
recommendation.

Attribution: detection categories, severity weights, score bands, and the
gate mapping are adapted from NVIDIA SkillSpector (Apache-2.0). This is a
defense-in-depth scanner, not a sandbox: it is static-only, English-centric,
and cannot see into encrypted or binary content. It never executes the
scanned skill.

Gate mapping (the integrating tool decides strictness; Aperio's policy):
SAFE -> allow; CAUTION -> surface to the owner; DO NOT INSTALL -> block.
"""

from __future__ import annotations

import ast
import math
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MAX_FILE_BYTES = 1_000_000
MAX_FILES = 500

SEVERITY_WEIGHTS = {"CRITICAL": 50, "HIGH": 25, "MEDIUM": 10, "LOW": 5}
EXECUTABLE_MULTIPLIER = 1.3

# Bands (SkillSpector contract): 0-20 SAFE, 21-50 CAUTION, 51-80/81+ DO NOT INSTALL.
def band_for(score: float) -> tuple[str, str]:
    if score <= 20:
        return "SAFE", "allow"
    if score <= 50:
        return "CAUTION", "surface to the owner before installing"
    return "DO NOT INSTALL", "block installation"


class _P:
    """One detection rule: category id, severity, description, regex."""

    def __init__(self, cid: str, severity: str, description: str, pattern: str):
        self.cid = cid
        self.severity = severity
        self.description = description
        self.regex = re.compile(pattern, re.IGNORECASE)


# Prompt injection and anti-refusal patterns (adapted from SkillSpector's
# static_patterns_prompt_injection.py categories P1/AR1-AR3).
_INJECTION_PATTERNS: list[_P] = [
    _P("P1", "HIGH", "instruction override", r"ignore\s+(?:all\s+)?previous\s+instructions?"),
    _P("P1", "HIGH", "safety override", r"ignore\s+(?:all\s+)?(?:safety|security)\s+(?:rules?|constraints?|guidelines?)"),
    _P("P1", "HIGH", "safety override", r"(?:bypass|override)\s+(?:safety|security|restrictions?|constraints?)"),
    _P("P1", "HIGH", "instruction wipe", r"(?:disregard|forget)\s+(?:all\s+)?(?:previous|your)\s+instructions?"),
    _P("P1", "HIGH", "jailbreak mode", r"you\s+are\s+now\s+(?:in\s+)?(?:jailbreak|unrestricted|unfiltered)\s+mode"),
    _P("P1", "MEDIUM", "elevated mode", r"enable\s+(?:developer|debug|admin|root)\s+mode"),
    _P("AR1", "HIGH", "refusal suppression", r"(?:never\s+refuse|always\s+comply|do\s+not\s+refuse)\b"),
    _P("AR2", "HIGH", "disclaimer suppression", r"(?:no\s+disclaimers?|do\s+not\s+moralize|skip\s+the\s+disclaimer)"),
    _P("AR3", "HIGH", "policy nullification", r"(?:you\s+have\s+no\s+restrictions?|do\s+anything\s+now|no\s+limits?\s+mode)"),
    # Data exfiltration (E1-E3) and credential access (PE3).
    _P("E1", "MEDIUM", "external transmission", r"(?:curl|wget|fetch)\s+https?://\S+\s*\|\s*(?:ba)?sh"),
    _P("E2", "HIGH", "env variable harvesting", r"(?:collect|send|steal|exfiltrate|upload)\s+(?:\S+\s+)*(?:env|environment|secrets?|tokens?|credentials?)"),
    _P("E3", "MEDIUM", "sensitive file enumeration", r"(?:find|scan|locate)\s+(?:\S+\s+)*(?:ssh\s+keys?|\.ssh|\.aws|credentials|passwords?|wallet)"),
    _P("PE3", "HIGH", "credential access", r"(?:read|cat|exfiltrate|copy)\w*\s+(?:\S+\s+)*(?:id_rsa|\.ssh\b|\.aws/credentials|\.netrc|\.env\b)"),
    # Supply chain (SC2, SC3) and rogue agent (RA1-2).
    _P("SC2", "HIGH", "remote script execution", r"(?:curl|wget)\s+https?://\S+\s*\|\s*(?:sudo\s+)?(?:ba)?sh"),
    _P("SC3", "HIGH", "obfuscated execution", r"(?:base64\s+-d|fromhex|codecs\.decode)\s*\(?\s*['\"][A-Za-z0-9+/=]{40,}"),
    _P("RA1", "CRITICAL", "self-modification", r"(?:modify|rewrite|patch)\s+(?:this\s+)?(?:skill|own\s+code|own\s+configuration)"),
    _P("RA2", "HIGH", "session persistence", r"(?:crontab|launchd|systemd|startup\s+script|persistence\s+hook)"),
    # Excessive agency (EA1-EA3) and tool misuse (TM1).
    _P("EA1", "HIGH", "unrestricted tool access", r"(?:all\s+tools|unrestricted\s+(?:tool|shell)\s+access|any\s+tool\s+without)"),
    _P("EA2", "HIGH", "autonomous decisions", r"(?:without\s+(?:human|owner)\s+(?:approval|confirmation)|autonomously\s+decide)"),
    _P("TM1", "HIGH", "shell true", r"shell\s*=\s*True"),
]

# Invisible-character attacks (P2/TP2): bidi controls (CVE-2021-42574),
# zero-width and joining characters, and unusual invisible separators.
_BIDI_RE = re.compile(r"[\u202a-\u202e\u2066-\u2069]")
_INVISIBLE_RE = re.compile(r"[\u200b-\u200f\u2060\u2061\u2062\ufeff]")
# Whitespace padding (P9): long runs of trailing whitespace or blank lines
# that can hide instructions below the visible fold.
_PADDING_RE = re.compile(r"[ \t]{40,}\S")


def _unicode_findings(path: Path, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if _BIDI_RE.search(text):
        findings.append(
            {
                "category": "TP2",
                "severity": "HIGH",
                "description": "bidirectional control characters (Trojan Source, CVE-2021-42574)",
                "file": str(path),
            }
        )
    if _INVISIBLE_RE.search(text):
        findings.append(
            {
                "category": "P2",
                "severity": "HIGH",
                "description": "zero-width or invisible characters hiding instructions",
                "file": str(path),
            }
        )
    if _PADDING_RE.search(text):
        findings.append(
            {
                "category": "P9",
                "severity": "MEDIUM",
                "description": "long whitespace padding that can hide content",
                "file": str(path),
            }
        )
    return findings


# AST rules for bundled Python files (SkillSpector behavioral_ast AST1-AST7,
# AST9): dangerous calls and reflective evasions, detected structurally.
_AST_CALL_RULES = [
    ("AST1", "CRITICAL", "exec() call", ("exec",)),
    ("AST2", "HIGH", "eval() call", ("eval",)),
    ("AST6", "MEDIUM", "compile() call", ("compile",)),
    ("AST3", "HIGH", "dynamic import", ("__import__",)),
]


def _ast_findings(path: Path, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return findings
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name is None:
                continue
            for cid, severity, description, targets in _AST_CALL_RULES:
                if name in targets:
                    findings.append(
                        {
                            "category": cid,
                            "severity": severity,
                            "description": f"{description} at line {node.lineno}",
                            "file": str(path),
                        }
                    )
            # AST5: os.system / os.popen family.
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.attr in {"system", "popen"}
                and func.value.id == "os"
            ):
                    findings.append(
                        {
                            "category": "AST5",
                            "severity": "HIGH",
                            "description": f"os.{func.attr} call at line {node.lineno}",
                            "file": str(path),
                        }
                    )
            # AST9: reflective getattr(os, "system") evasion.
            if (
                isinstance(func, ast.Name)
                and func.id == "getattr"
                and node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id in {"os", "sys", "subprocess", "builtins"}
            ):
                findings.append(
                    {
                        "category": "AST9",
                        "severity": "HIGH",
                        "description": f"reflective getattr on {node.args[0].id} at line {node.lineno}",
                        "file": str(path),
                    }
                )
        # AST4: subprocess usage at all (the skill bundle should not need it).
        if (
            isinstance(node, ast.Attribute)
            and node.attr in {"run", "Popen", "call", "check_output"}
            and isinstance(node.value, ast.Name)
            and node.value.id == "subprocess"
        ):
                findings.append(
                    {
                        "category": "AST4",
                        "severity": "HIGH",
                        "description": f"subprocess.{node.attr} at line {node.lineno}",
                        "file": str(path),
                    }
                )
    return findings


def _iter_skill_files(target: Path) -> list[Path]:
    files: list[Path] = []
    if target.is_file():
        return [target]
    for path in sorted(target.rglob("*")):
        if path.is_file() and not path.is_symlink():
            files.append(path)
        if len(files) >= MAX_FILES:
            break
    return files


def scan(target: str | Path) -> dict[str, Any]:
    """Statically verify a skill directory (or single file). Never executes it.

    Returns the SkillSpector-shaped report: risk_assessment (score, severity,
    recommendation), components, and issues with category/severity/location.
    """
    root = Path(target).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"no such skill path: {root}")
    files = _iter_skill_files(root)
    issues: list[dict[str, Any]] = []
    components: list[dict[str, Any]] = []
    has_executable = False

    for path in files:
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                issues.append(
                    {
                        "category": "OH3",
                        "severity": "MEDIUM",
                        "description": f"file exceeds {MAX_FILE_BYTES} bytes; content not fully scanned",
                        "file": str(path),
                    }
                )
                continue
            raw = path.read_bytes()
        except OSError as exc:
            issues.append(
                {
                    "category": "OH3",
                    "severity": "MEDIUM",
                    "description": f"unreadable: {exc}",
                    "file": str(path),
                }
            )
            continue
        rel = str(path.relative_to(root)) if path != root else path.name
        text = raw.decode("utf-8", errors="replace")
        executable = path.suffix in {".py", ".sh", ".js", ".ts"}
        components.append({"path": rel, "type": path.suffix or "file", "executable": executable})
        if executable:
            has_executable = True

        # Unicode attacks first: invisible characters evade the regex rules.
        issues.extend(_unicode_findings(path, text))

        if path.suffix == ".py":
            issues.extend(_ast_findings(path, text))

        for rule in _INJECTION_PATTERNS:
            match = rule.regex.search(text)
            if match:
                issues.append(
                    {
                        "category": rule.cid,
                        "severity": rule.severity,
                        "description": rule.description,
                        "file": rel,
                        "line": text[: match.start()].count("\n") + 1,
                    }
                )

    # Weighted score with the executable multiplier (SkillSpector contract).
    score = 0.0
    for issue in issues:
        score += SEVERITY_WEIGHTS[issue["severity"]]
    if has_executable and issues:
        score = math.ceil(score * EXECUTABLE_MULTIPLIER)
    severity, recommendation = band_for(score)

    return {
        "schema": SCHEMA_VERSION,
        "skill": str(root),
        "risk_assessment": {
            "score": int(score),
            "severity": severity,
            "recommendation": recommendation,
        },
        "components": components,
        "issues": issues,
        "metadata": {
            "has_executable_scripts": has_executable,
            "static_only": True,
            "adapted_from": "NVIDIA SkillSpector (Apache-2.0)",
        },
    }


def format_report(report: dict[str, Any]) -> str:
    risk = report["risk_assessment"]
    lines = [
        f"SKILLSPECTOR: {risk['severity']} (score {risk['score']}) — {risk['recommendation']}",
        f"skill: {report['skill']}",
    ]
    if report["issues"]:
        lines.append(f"findings: {len(report['issues'])}")
        for issue in report["issues"][:20]:
            location = f"{issue['file']}:{issue.get('line', 0)}" if issue.get("line") else issue["file"]
            lines.append(f"  [{issue['severity']}] {issue['category']} {issue['description']} ({location})")
    else:
        lines.append("findings: none")
    lines.append(
        "gate: SAFE=allow, CAUTION=surface to the owner, DO NOT INSTALL=block "
        "(static analysis adapted from NVIDIA SkillSpector; defense-in-depth, not a sandbox)"
    )
    return "\n".join(lines)
