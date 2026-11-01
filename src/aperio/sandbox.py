"""Optional OS-level isolation for shell steps.

Aperio's path policy detects writes after a command. This module adds an
opt-in boundary where the operating system supports one. It is deliberately
strict: when `plan.sandbox` is true and no supported sandbox exists, the run is
refused rather than silently downgraded.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path


class SandboxError(RuntimeError):
    """The requested OS sandbox is unavailable or cannot be constructed."""


def kind() -> str | None:
    if sys.platform == "darwin" and shutil.which("sandbox-exec"):
        return "sandbox-exec"
    if sys.platform.startswith("linux") and shutil.which("bwrap"):
        return "bwrap"
    return None


def _profile(root: Path) -> str:
    # Read-only access to the host is intentional: compilers and interpreters
    # need system libraries. Writes are limited to the project and temporary
    # directories. Network access is denied.
    escaped = str(root.resolve()).replace("\\", "\\\\").replace('"', '\\"')
    return (
        "(version 1)\n"
        "(deny default)\n"
        "(allow process*)\n"
        "(allow sysctl-read)\n"
        "(allow mach-lookup)\n"
        "(allow file-read*)\n"
        "(allow file-write* "
        f'(subpath "{escaped}") '
        '(subpath "/private/tmp") '
        '(subpath "/tmp"))\n'
    )


def _escape(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace('"', '\\"')


# Known per-host state directories: live AI hosts need their session/config
# stores writable to function (Codex: ~/.codex sessions and PATH aliases;
# Claude: ~/.claude). Everything outside workspace + state dirs + tmp stays
# read-only — that is the boundary that protects the real project.
HOST_STATE_DIRS = {
    "codex": ".codex",
    "claude": ".claude",
    "dsh": ".dsh",
    "goose": ".goose",
}


def host_profile(workspace: Path, protected: Path | None = None) -> str:
    """Profile for live AI hosts under `plan.sandbox: true`.

    Deny-default profiles broke live hosts in ways that produced no denial
    logs and even broke the hosts' own nested sandbox_apply, while an
    allow-default sandbox worked — so the host profile inverts the recipe:
    everything is allowed EXCEPT file writes under the REAL project root,
    which are denied explicitly (SBPL: later, more-specific rules win, so
    the re-allow for the disposable workspace — nested inside the project —
    overrides the deny). The protected asset is the project itself: the
    sandboxed host cannot touch the work it is meant to review or extend,
    while every operation a live host needs (XPC, IPC, preferences, its own
    state dir, network for the model API) remains available. The host's own
    `--sandbox workspace-write` mode provides the second layer, blocking
    writes outside its working directory.
    """
    rules = ["(version 1)\n", "(allow default)\n"]
    if protected is not None:
        rules.append(f'(deny file-write* (subpath "{_escape(protected)}"))\n')
    rules.append(f'(allow file-write* (subpath "{_escape(workspace)}"))\n')
    return "".join(rules)


def wrap(command: str, root: Path, cwd: Path) -> tuple[list[str], dict[str, object]]:
    """Return an argv wrapper and an evidence record for an isolated command."""
    backend = kind()
    if backend is None:
        raise SandboxError("no supported OS sandbox (sandbox-exec or bwrap) is available")
    if backend == "sandbox-exec":
        if not Path("/usr/bin/sandbox-exec").is_file():
            raise SandboxError("sandbox-exec is not installed at /usr/bin/sandbox-exec")
        argv = ["/usr/bin/sandbox-exec", "-p", _profile(root), "/bin/sh", "-c", command]
        return argv, {"requested": True, "active": True, "kind": backend}
    argv = [
        "bwrap",
        "--ro-bind",
        "/",
        "/",
        "--bind",
        str(root),
        str(root),
        "--chdir",
        str(cwd),
        "--unshare-net",
        "/bin/sh",
        "-c",
        command,
    ]
    return argv, {"requested": True, "active": True, "kind": backend}


def wrap_argv(
    command: list[str],
    root: Path,
    cwd: Path,
    *,
    extra_visible: list[Path] | None = None,
    host: str | None = None,
    protected: Path | None = None,
) -> tuple[list[str], dict[str, object]]:
    """Wrap an argv-list command (host dispatch) in the OS sandbox.

    Live AI hosts get the tuned host profile (state dir writable, network
    allowed for the model API, workspace as the only project-adjacent write
    boundary); everything else uses the strict profile. Fail-closed rules
    are identical.
    """
    backend = kind()
    if backend is None:
        raise SandboxError("no supported OS sandbox (sandbox-exec or bwrap) is available")
    if backend == "sandbox-exec":
        if not Path("/usr/bin/sandbox-exec").is_file():
            raise SandboxError("sandbox-exec is not installed at /usr/bin/sandbox-exec")
        profile = _profile(root)
        if host is not None:
            profile = host_profile(root, protected=protected)
        argv = ["/usr/bin/sandbox-exec", "-p", profile, *command]
        return argv, {"requested": True, "active": True, "kind": backend, "profile": "host" if host is not None else "strict"}
    # A dedicated writable tmp dir instead of all of /tmp: binding /tmp
    # wholesale would make the project writable too whenever the project
    # lives under /tmp (CI runners do exactly that), defeating the boundary
    # (a host review + a Linux CI failure caught this). The dedicated dir is
    # mounted AT /tmp, and the project root is re-bound READ-ONLY at its
    # real path afterwards so it stays visible under the new /tmp mount
    # (bwrap binds apply in order; the later, more specific bind wins).
    # The workspace — inside the project — is then bound writable at its
    # own path, which is the host's only writable project boundary.
    # extra_visible paths (e.g. the host binary's directory, which may live
    # under the real /tmp) are re-bound read-only last, for the same reason.
    dedicated_tmp = Path(tempfile.mkdtemp(prefix="aperio-sandbox-"))
    argv = [
        "bwrap",
        "--ro-bind",
        "/",
        "/",
        "--bind",
        str(dedicated_tmp),
        "/tmp",
        "--ro-bind",
        str(root),
        str(root),
    ]
    for path in extra_visible or []:
        argv += ["--ro-bind", str(path), str(path)]
    # The workspace bind goes LAST: bwrap's later, more specific binds win,
    # and the workspace must be writable even though it sits inside the
    # read-only project root bind.
    argv += [
        "--bind",
        str(cwd),
        str(cwd),
        "--chdir",
        str(cwd),
        "--unshare-net",
        *command,
    ]
    return argv, {"requested": True, "active": True, "kind": backend}


def unavailable_record() -> dict[str, object]:
    return {"requested": True, "active": False, "kind": None, "reason": "no supported sandbox"}
