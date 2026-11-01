"""The promo generator: a launch-video plan built from a completed task's evidence.

``build_promo`` reads a done task's recorded evidence — the plan, the changed
files, the acceptance checks, the signed review — and drafts the artifacts a
motion build needs per docs/MOTION.md: a shot sheet whose times sum to the
declared runtime, a closed color script, and a full promo plan JSON (an HTML
composition under the determinism contract plus a render step and
machine-checkable acceptance).

Aperio generates the PLAN; it does not render. The promo plan is an ordinary
Aperio plan: it goes through the same approval gate, runs under the same
bounds, and its acceptance checks (lint, validate, times-sum, artifact
exists) are enforced the same way. Rendering itself requires the HyperFrames
toolchain, which the owner installs through `aperio tool` — never a core
dependency.
"""

from __future__ import annotations

import html
import json
from typing import Any

from .runner import RunError
from .store import Project


class PromoError(ValueError):
    """The task is not eligible for a promo, or the draft is invalid."""


PROMO_PATHS = ["promo/"]
PALETTE = {
    "bg": "#0b0e14",
    "ink": "#e8ecf4",
    "accent": "#5b8cff",
    "muted": "#8a93a6",
}


def _changed_files(project: Project, task: Any) -> list[str]:
    """Files changed by the task's CURRENT run — not earlier runs (a host
    review caught the union across records citing stale files)."""
    if not task.run_id:
        return []
    for row in project.evidence_readonly(task.id):
        if row.get("run_id") == task.run_id:
            return sorted(set(row.get("changed_files") or []))
    return []


def _acceptance_summary(current: dict[str, Any]) -> list[dict[str, Any]]:
    """Checks from the CURRENT verification record only — never stale ones."""
    return [
        {
            "id": check.get("check_id"),
            "command": check.get("command"),
            "ok": check.get("ok"),
        }
        for check in current.get("checks", [])
    ]


def _sheet_scenes(
    task_title: str,
    request: str,
    changed: list[str],
    checks: list[dict[str, Any]],
    duration: int,
) -> list[dict[str, Any]]:
    """Five-beat structure: hook, establish, proof, craft, button.

    Times are proportional to the declared duration and sum to it exactly.
    """
    n_checks = min(len(checks), 3)
    # The button shot is the last two seconds (docs/MOTION.md): its duration
    # is capped at 2.0s and it ends exactly at the runtime. The other four
    # beats share the remainder proportionally.
    button_dur = min(2.0, max(1.2, round(duration * 0.15, 2)))
    rest = round(duration - button_dur, 2)
    fractions = [
        ("hook", 0.15 / 0.85),
        ("establish", 0.25 / 0.85),
        ("proof", 0.25 / 0.85),
        ("craft", 0.20 / 0.85),
    ]
    scenes: list[dict[str, Any]] = []
    cursor = 0.0
    for name, fraction in fractions:
        span = round(rest * fraction, 2)
        scene: dict[str, Any] = {
            "name": name,
            "start": round(cursor, 2),
            "duration": span,
            "kind": "text",
        }
        if name == "hook":
            scene["text"] = task_title
        elif name == "establish":
            scene["text"] = request if request else task_title
        elif name == "proof":
            scene["kind"] = "list"
            scene["items"] = [c.get("id") or "check" for c in checks[:n_checks]] or [
                "acceptance checks passed"
            ]
        elif name == "craft":
            scene["kind"] = "files"
            scene["items"] = changed[:4] or ["the delivered work"]
        scenes.append(scene)
        cursor = round(cursor + span, 2)
    # Rounding drift lands on craft (the last beat before the button) so the
    # times sum exactly and the button ends at the runtime.
    drift = round(rest - cursor, 2)
    if scenes and drift:
        scenes[-1]["duration"] = round(scenes[-1]["duration"] + drift, 2)
    scenes.append(
        {
            "name": "button",
            "start": round(duration - button_dur, 2),
            "duration": button_dur,
            "kind": "logo",
            "text": task_title,
        }
    )
    return scenes


def build_promo(
    project: Project,
    task_id: str,
    *,
    duration: int = 12,
    vertical: bool = False,
) -> dict[str, Any]:
    """Draft the promo shot sheet and plan for a completed task.

    The task must be done with a confirmed review: the promo showcases
    verified work, and the review signature is part of the sourced proof.
    """
    task = project.get_task(task_id)
    if task.status != "done":
        raise PromoError(
            f"task is {task.status}; a promo showcases completed work — fly the task to done first"
        )
    if not task.plan_id:
        raise PromoError("task has no plan; nothing to showcase")
    plan = project.get_plan(task.plan_id)
    review = task.review
    if review is None or review.verdict != "confirmed":
        raise PromoError("task has no confirmed review; the promo cannot cite one")
    # The cited review evidence must exist, match the task review, and carry
    # a valid signature — the same bar finish() applies (a host review
    # caught generation citing unvalidated review records).
    from .runner import RunError as RunnerRunError
    from .runner import _current_review

    try:
        review_evidence = _current_review(project, task)
    except RunnerRunError as exc:
        raise PromoError(f"the confirmed review's evidence is missing: {exc}") from exc
    if str(review_evidence.get("reviewer", "")).strip().lower() != review.reviewer.strip().lower():
        raise PromoError("the current review evidence does not match the task's review")
    signed_core = {
        k: review_evidence[k]
        for k in ("review_id", "task_id", "reviewer", "verdict", "notes", "at")
        if k in review_evidence
    }
    if not project.verify_review_signature(
        signed_core, review_evidence.get("signature", "")
    ):
        raise PromoError(
            "the recorded review verdict has no valid signature for this project; "
            "re-record the review through aperio review"
        )

    # The promo cites the CURRENT verification, validated for staleness:
    # a stale or failed record must never be presented as proof (a host
    # review caught generation trusting verify_id alone).
    from .runner import _current_verification

    try:
        current = _current_verification(project, task)
    except RunError as exc:
        raise PromoError(
            f"the task's verification is not current — re-verify before generating "
            f"the promo: {exc}"
        ) from exc
    changed = _changed_files(project, task)
    checks = _acceptance_summary(current)

    width, height = (1080, 1920) if vertical else (1920, 1080)
    if duration < 8 or duration > 30:
        raise PromoError("duration must be 8..30 seconds")

    scenes = _sheet_scenes(task.title, task.request, changed, checks, duration)
    total = round(sum(scene["duration"] for scene in scenes), 2)
    if abs(total - duration) > 0.01:
        raise PromoError(f"shot sheet times sum to {total}, not {duration}")

    sheet = {
        "logline": f"{task.title} — built and verified through the Aperio loop",
        "duration_s": duration,
        "fps": 30,
        "width": width,
        "height": height,
        "palette": PALETTE,
        "sakuga_shot": "craft",
        "scenes": scenes,
        "sourced_from": {
            "task_id": task.id,
            "plan_id": plan.id,
            "verify_id": current.get("check_id"),
            "review": {
                "review_id": review_evidence.get("review_id"),
                "reviewer": review.reviewer,
                "verdict": review.verdict,
            },
            "changed_files": changed,
            "acceptance_checks": checks,
        },
        "doctrine": "docs/MOTION.md",
    }

    composition = _composition_html(sheet)
    render_script = _render_script(width, height, duration)

    promo_plan = {
        "title": f"Promo video: {task.title}",
        "request": (
            f"Render the {duration}s launch promo for '{task.title}' from the approved "
            f"shot sheet in promo/shot-sheet.json (source task {task.id})."
        ),
        "builder": "promo-builder",
        "allowed_paths": ["promo/"],
        "steps": [
            _write_step("promo/shot-sheet.json", json.dumps(sheet, indent=2) + "\n"),
            _write_step("promo/composition.html", composition),
            _write_step("promo/check_video.py", _probe_script()),
            _write_step(
                "promo/fonts/README.md",
                "Place a licensed .woff2 font here named `promo.woff2`.\n"
                "The motion doctrine (docs/MOTION.md) forbids relying on system fonts:\n"
                "the render script fails closed without this file.\n",
            ),
            _write_step("promo/render.sh", render_script),
            {
                "id": "render-promo",
                "kind": "run",
                "command": "sh promo/render.sh",
                "writes": ["promo/promo.mp4"],
                "timeout_s": 600,
            },
        ],
        "acceptance": [
            _acceptance("sheet-times-sum", _times_sum_command(duration)),
            _acceptance("determinism-contract", NO_RANDOM_COMMAND),
            _acceptance("composition-declared", "grep -q 'name=\"hyperframes\"' promo/composition.html"),
            _acceptance("render-script-present", "test -f promo/render.sh"),
            _acceptance("video-rendered", VIDEO_CHECK_COMMAND.format(duration=duration, fps=30)),
        ],
    }
    return {
        "sheet": sheet,
        "promo_plan": promo_plan,
        "note": (
            "The promo plan is a normal Aperio plan: approve it, run it, verify it. "
            "Its render step executes promo/render.sh, which runs `npx hyperframes "
            "lint && validate && render` — install the HyperFrames toolchain (Node 22+) "
            "through `aperio tool` BEFORE running the plan; without it the render step "
            "fails closed. Rendering is a declared, owner-approved plan step, not an "
            "Aperio built-in."
        ),
    }


def _write_step(path: str, content: str) -> dict[str, Any]:
    """A write-step dict for the generated promo plan (kept as dicts so the
    generated plan is plain JSON the CLI can consume)."""
    return {"id": "write-" + path.replace("/", "-").replace(".", "-"), "kind": "write", "path": path, "content": content}


def _acceptance(cid: str, command: str) -> dict[str, Any]:
    return {"id": cid, "command": command}


# Guards on file existence first: grep on a missing file exits nonzero,
# which the negation would turn into a vacuous pass (a host review caught
# the acceptance check passing without the composition present).
# The full docs/MOTION.md determinism contract: no Math.random, Date.now,
# async, setTimeout, or Promise; the root timeline must be paused and
# registered at window.__timelines.root.
NO_RANDOM_COMMAND = (
    "test -f promo/composition.html && "
    "! grep -rnE 'Math\\.random|Date\\.now|\\basync\\b|setTimeout|new Promise' promo/composition.html && "
    "grep -q '__timelines.root = tl' promo/composition.html && "
    "grep -q 'paused: true' promo/composition.html"
)

# The rendered MP4 must exist and match the shot sheet's declared duration
# and fps (ffprobe-validated; a missing ffprobe fails the check rather than
# waving the file through).
VIDEO_CHECK_COMMAND = (
    "test -s promo/promo.mp4 && "
    "python3 promo/check_video.py promo/promo.mp4 {duration} {fps}"
)


def _times_sum_command(duration: int) -> str:
    return (
        "python3 -c \"import json; s=json.load(open('promo/shot-sheet.json')); "
        f"total=sum(sc['duration'] for sc in s['scenes']); "
        f"assert abs(total - {duration}) < 0.011, total; "
        "assert len(s['scenes']) >= 3\""
    )


def _composition_html(sheet: dict[str, Any]) -> str:
    """A deterministic starter composition under the docs/MOTION.md contract."""
    scenes = sheet["scenes"]
    width = sheet["width"]
    height = sheet["height"]
    duration = sheet["duration_s"]
    palette = sheet["palette"]
    scene_css = []
    scene_js = []
    for index, scene in enumerate(scenes):
        start = scene["start"]
        span = scene["duration"]
        selector = f".scene-{index}"
        scene_css.append(
            f"{selector} {{ position:absolute; inset:0; display:flex; "
            "align-items:center; justify-content:center; flex-direction:column; "
            f"opacity:0; }}\n{selector} .text {{ color: {palette['ink']}; "
            "font-family: 'AperioPromo', sans-serif; font-weight: 700; "
            f"font-size: {height // 12}px; }}\n{selector} .item {{ color: {palette['muted']}; "
            f"font-size: {height // 24}px; margin: 4px; }}"
        )
        scene_js.append(
            f"tl.fromTo('{selector}', {{opacity: 0, y: 40}}, "
            f"{{opacity: 1, y: 0, duration: 0.6, ease: 'power4.out'}}, {start});\n"
            f"tl.to('{selector}', {{opacity: 1, duration: {max(span - 0.6, 0.1)}}}, {start + 0.6});\n"
            f"tl.to('{selector}', {{opacity: 0, duration: 0.25, ease: 'power2.in'}}, {round(start + span - 0.25, 2)});"
        )
    # Evidence-derived text (task title, request, file names) is escaped:
    # unescaped interpolation would let task content inject markup or
    # scripts into the composition (a host review caught this).
    items_html = "".join(
        f"<div class='scene scene-{i}'>"
        + (
            f"<div class='text'>{html.escape(str(s.get('text', '')))}</div>"
            if s.get("text")
            else "".join(
                f"<div class='item'>{html.escape(str(item))}</div>"
                for item in s.get("items", [])
            )
        )
        + "</div>"
        for i, s in enumerate(scenes)
    )
    return (
        "<!doctype html>\n"
        f"<html lang=\"en\"><head><meta charset=\"utf-8\">\n"
        f"<meta name=\"hyperframes\" content=\"duration:{duration},fps:30,width:{width},height:{height}\">\n"
        "<title>Aperio promo</title>\n"
        "<style>\n"
        "@font-face { font-family: 'AperioPromo'; src: url('fonts/promo.woff2') format('woff2'); font-display: block; }\n"
        f"body {{ margin:0; background: {palette['bg']}; width:{width}px; height:{height}px; overflow:hidden; }}\n"
        + "\n".join(scene_css)
        + "\n</style></head><body>\n"
        + items_html
        + "\n<script src='https://cdn.jsdelivr.net/npm/gsap@3.14/dist/gsap.min.js'></script>\n"
        "<script>\n"
        "window.__timelines = window.__timelines || {};\n"
        "const tl = gsap.timeline({ paused: true, defaults: { ease: 'power4.out' } });\n"
        + "\n".join(scene_js)
        + "\nwindow.__timelines.root = tl;\n"
        "</script></body></html>\n"
    )


def _probe_script() -> str:
    return (
        "import json, math, subprocess, sys\n"
        "path, want_dur, want_fps = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])\n"
        "data = json.loads(subprocess.run(\n"
        "    ['ffprobe', '-v', 'error', '-select_streams', 'v:0',\n"
        "     '-show_entries', 'stream=avg_frame_rate:format=duration',\n"
        "     '-of', 'json', path], capture_output=True, text=True, check=True).stdout)\n"
        "dur = float(data['format']['duration'])\n"
        "num, den = data['streams'][0]['avg_frame_rate'].split('/')\n"
        "fps = float(num) / float(den)\n"
        "assert abs(dur - want_dur) <= 0.5, f'duration {dur} != {want_dur}'\n"
        "assert abs(fps - want_fps) < 0.01, f'fps {fps} != {want_fps}'\n"
        "print(f'video OK: {dur}s @ {fps}fps')\n"
    )


def _render_script(width: int, height: int, duration: int) -> str:
    return (
        "#!/bin/sh\n"
        "# Validate and render the promo with HyperFrames (installed via `aperio tool`).\n"
        "# The motion contract's gate is lint && validate before render; flags follow\n"
        "# the installed HyperFrames version and may need adjusting.\n"
        "set -e\n"
        "cd \"$(dirname \"$0\")\"\n"
        "if [ ! -f fonts/promo.woff2 ]; then\n"
        "  echo \"missing fonts/promo.woff2: place a licensed .woff2 there (docs/MOTION.md local-font rule)\" >&2\n"
        "  exit 1\n"
        "fi\n"
        "npx hyperframes lint composition.html\n"
        "npx hyperframes validate composition.html\n"
        f"npx hyperframes render composition.html --width {width} --height {height} "
        f"--duration {duration} --fps 30 --output promo.mp4\n"
        "echo \"rendered promo.mp4\"\n"
    )
