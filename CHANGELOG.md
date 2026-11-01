# Changelog

## 2.0.0.dev0 - 2026-10-26

Initial clean rebuild.

- `apero retro <task-id>`: an environment retrospective that audits a completed task's evidence and suggests concrete improvements to the project's checks, lessons, and gate coverage.
- `aperio tutorial build/check`: a flight simulator — a practice fixture with every gate pre-satisfied, a starter plan and checklist, and a read-only grader that scores the learner's real flight from project state.
- `aperio explain <topic>`: a read-only gate explainer — what each gate checks, the incident that motivated it, and the project's live status; plus `docs/TEACHING.md`, an incident-anchored craft page for plan-writing, acceptance checks, and review.
- `aperio next` and `aperio next --json`: a read-only next-action advisor that names the single next legal action, its exact command, and the gate that requires it, from first contact through handoff.
- Added a standard-library core for asks, plans, approval, bounded apply, verification, independent review, finish, rollback, and handoff.
- Added path safety for relative paths, parent traversal, and symlink components.
- Added declared-write enforcement for shell steps. Undeclared changes are recorded as violations.
- Added a JSON project state under `.aperio/` with atomic writes and append-only asks and events.
- Added a read-only host detector.
- Added a shell installer with dry run, idempotent reinstall, skill installation, and uninstall.
- Added unit, CLI, and installer tests.
- Added a runnable demo plan that creates and verifies a static page.
- Added a persistent discovery interview, learning dossier/proof gate, ordered todo ledger, readiness record, project-scoped skill scaffold, and toolchain manifest with approval-gated installation.
- Added versioned `.aperio` state, queue recovery from the event journal, run checkpoints, safe `resume`, and an optional OS sandbox for shell/read steps.
- Added a bounded local secret scan and a generated read-only status dashboard.
- Replaced the old documentation set with one PRD, one architecture document, one status page, one roadmap, one testing guide, one agent protocol, and one decision log.

### Known limits

- Shell/read steps are OS-sandboxed only when a plan sets `sandbox: true`; host steps are not jailed. Undeclared changes are otherwise detected after execution.
- Host adapters are implemented for Claude, Codex, Goose, dsh, OpenCode, KiloCode, Cline, and agy; Claude and Codex are live-proven, Goose/dsh live calls were blocked, and the extra adapters are command-shape tested only.
- The local message store and mediator are implemented; a distributed two-host transport is not built.
- CMS, SEO, deployment execution, and a live dashboard server are target-project/owner concerns and outside Aperio's scope.
- The PowerShell installer is implemented and tested under `pwsh` on macOS; native Windows `.cmd` execution is not tested.
