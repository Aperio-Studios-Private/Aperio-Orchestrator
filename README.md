# Aperio Orchestrator v2

Aperio turns an owner request into a bounded, approved plan, applies it, runs acceptance checks, requires an independent review, and writes evidence and a handoff.

**Status: handoff-ready for the local tool.** The core loop and installer work. Discovery, learning, readiness, todo approval, optional shell sandboxing, toolchain installation, secret scanning, and a generated read-only dashboard are implemented. CMS/SEO delivery and deployment execution are outside Aperio's scope. Do not describe this as feature-complete.

## Why this rebuild exists

The previous repository accumulated a large layer of reports, audits, generated PRDs, and status documents that did not reliably match the code. This repository starts with a small canonical documentation set and a tested core.

## Quick start

```bash
git clone https://github.com/Aperio-Studios-Private/Aperio-Orchestrator.git
cd aperio-orchestrator
./install.sh
aperio --version
./install.sh --check
./install.sh --update
./install.sh --rollback
```

PowerShell 7:

```sh
pwsh -File install.ps1
```

The installer copies the package to `~/.local/share/aperio`, creates `~/.local/bin/aperio`, and installs the skill under `~/.claude/skills/aperio`. The `/aperio` entry point is the skill; no duplicate slash-command file is installed. The installer does not edit host settings, use sudo, or download anything. The host's ability to load the skill is not yet independently verified.

To test without installing:

```bash
PYTHONPATH=src python3 -m aperio --help
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## The loop

```bash
aperio init . --name "My project"
aperio ask "Build a one-page site with a working contact form" --source owner
aperio inspect
aperio evidence add notes.md --label "Owner brief"
aperio audit start --scope src --profile quick
aperio audit brief
aperio audit ingest --file findings.json
aperio audit add --title "..." --status needs_validation --path src/app.py --evidence "Missing deployment fact"
aperio audit verify --finding-id finding-0001 --by peer-reviewer --verdict confirmed --evidence "Reproduced from source"
aperio audit unit --unit-id unit-0001 --status checked
aperio audit validate
aperio audit report
aperio discover next
aperio discover answer <question-id> --choice 1,3 --text "..."
aperio discover status
aperio security scan
aperio dashboard
aperio learn import examples/learning-dossier.json
aperio learn proof --command "python3 -V"
aperio learn validate
aperio todo add "Initialize the project" --deliverable "A working initialization" --acceptance "The initialization command exits 0"
aperio todo start <todo-id>
aperio readiness import readiness.json
aperio readiness validate
aperio skill create custom-stack --purpose "..." --trigger "When the custom stack is used"
aperio skill validate custom-stack
aperio tool import examples/toolchain.json
aperio tool install custom-tool --by owner --confirm "I approve this tool install"
aperio plan plan.json
aperio approve <plan-id> --by owner --confirm "I approve this plan"
aperio run <task-id> --actor builder
aperio resume <task-id> --actor builder
aperio verify <task-id>
aperio review <task-id> --host claude
aperio done <task-id>
aperio todo accept <todo-id> --by owner --evidence "command exit 0" --confirm "I accept this task"
aperio next            # read-only GPS: next legal action + exact command + why
aperio explain <topic>  # read-only: what a gate checks, why, live status
aperio tutorial build <dir>  # practice fixture + checklist, then fly the loop yourself
aperio handoff <task-id> --print
aperio recover
aperio drift
aperio message send --from builder --to reviewer --body "please review" --task <task-id>
aperio mediate <task-id>
```

A plan is JSON. Before `plan`, `approve`, or `run`, Aperio requires a ready learning dossier: stack and versions, official sources, skill/MCP decisions, a real local proof recorded by `aperio learn proof`, a teach-back, and a competency record. `aperio learn import` exits 1 until the proof is recorded. A plan is shown below; a host step is shown in `examples/host-plan.json`.

```json
{
  "title": "Build a page",
  "request": "The owner's request in their terms.",
  "builder": "builder",
  "allowed_paths": ["site/"],
  "steps": [
    {"id": "write", "kind": "write", "path": "site/index.html", "content": "..."}
  ],
  "acceptance": [
    {"id": "check", "command": "python3 -c \"from pathlib import Path; assert Path('site/index.html').is_file()\""}
  ]
}
```

## Proof

See [docs/HOST-PROOFS.md](docs/HOST-PROOFS.md) for the exact host commands and output recorded on 2026-10-26. The external audits and dispositions are in [docs/AUDIT-CODEX-20261026.md](docs/AUDIT-CODEX-20261026.md) and [docs/AUDIT-CLAUDE-20261026.md](docs/AUDIT-CLAUDE-20261026.md).

## What works now

- Project initialization and append-only owner asks.
- Mandatory learning dossier with stack/version, official-source, skill/MCP, local-proof, teach-back, and competency validation; `plan`, `approve`, and `run` refuse until it is ready.
- Owner-visible todo ledger with ordered, minimal tasks; `plan` refuses an empty todo list, and the next task cannot start until the previous task is accepted with evidence.
- Readiness record for pre-flight, deployment, after-sales, design, and security facts; `aperio readiness validate` refuses gaps and high/critical unresolved risk.
- Project-scoped skill creation: `aperio skill create` writes a validated scaffold under `.aperio/skills/` and refuses to overwrite a foreign skill.
- Bounded local secret scan: `aperio security scan` flags high-confidence tokens, private keys, sensitive filenames, and assigned secrets; it does not replace a dependency or history scanner.
- Lessons ledger: `apero lesson add` records what went wrong bound to task and paths; `plan` surfaces lessons whose paths intersect the plan — the project's mistakes compound instead of repeating.
- MCP facade: `apero mcp` serves the read-only advisors (next, explain, status, lessons, doctor) over JSON-RPC 2.0 on stdio with zero dependencies — any MCP-capable host can consult Aperio's gates. Write tools are excluded by design.
- Tutorial flight simulator: `aperio tutorial build <dir>` creates a practice fixture with every gate pre-satisfied; the learner flies the loop; `aperio tutorial check <dir>` grades the flight from real state.
- Retro: `apero retro <task-id>` audits a completed task's environment — classifies violations into improvement actions and reports gate coverage gaps. Read-only.
- SkillSpector verifier: `apero skill verify <dir>` statically scans any skill BEFORE installation (adapted from NVIDIA SkillSpector): prompt injection, anti-refusal, exfiltration, Trojan-Source characters, AST behavioral rules for bundled scripts, weighted risk score and the SAFE/CAUTION/DO-NOT-INSTALL install gate.
- Gate explainer: `aperio explain <topic>` teaches each gate — what it checks, why it exists, and this project's live status; strictly read-only.
- Next-action advisor: `aperio next` reads the state and names the single next legal action, the exact command, and which gate requires it; strictly read-only.
- Generated read-only status dashboard: `aperio dashboard` writes self-contained HTML from the state files with no scripts or network.
- Manifest-driven toolchain installation: `aperio tool import` validates source, version, license, permissions, risk flags, cost, install argv, and verify argv; risky tools require exact owner confirmation.
- Non-overridable `.git` and `.aperio` protection, plus a read-only `kind: read` step that fails on any project change.
- Plan creation, explicit approval, bounded writes, and shell steps with timeouts.
- Host dispatch through a disposable project copy for the Claude, Codex, dsh, Goose, OpenCode, KiloCode, Cline, and agy adapters. Claude and Codex are proven on current code. dsh and Goose command paths are tested, but their live runs are blocked by a missing credential and an HTTP 500 bridge, respectively. The OpenCode, KiloCode, Cline, and agy command shapes are tested with a fake binary; live runs are not yet proven.
- Fresh-context host review. `aperio review <task> --host claude` gets only the plan, changed files, acceptance results, and evidence, with no builder conversation. Real Claude reviewers confirmed verified work on current code; earlier Codex review evidence is historical.
- Change detection for writes outside the declared plan.
- Acceptance checks and recorded evidence.
- Source-anchored security audit ledger: bounded coverage units, host brief, atomic bulk ingest, structured findings, `needs_validation` for unresolved facts, independent verification verdicts, and a generated report. Handoff and project status always surface the latest audit, including open or source-changed coverage. It never executes the target and never treats an unproven finding as confirmed.
- Independent review enforcement by reviewer name.
- Rollback of files captured before a run.
- Handoff generation from actual state.
- Deterministic documentation drift checks: links and inline paths that do not exist fail `aperio drift`.
- Read-only Git facts in project status and handoff: branch, commit, dirty state, changed count, and credential-stripped origin.
- Local durable message store with send, read, reply, ack, filters, and restart persistence. Real Claude and Codex processes both read and replied through it; Codex is historical evidence, not the current trusted host set.
- Mediator disposition from run, verify, and review evidence: `CONFIRMED`, `REFUTED`, or `BLOCKED`.
- Installer, idempotent reinstall, dry run, uninstall, version check, update backup, and rollback.
- PowerShell installer and update/rollback tested under `pwsh` 7.6.7 on macOS; native Windows `.cmd` execution is not tested.
- Read-only host detection.

## What is not built

- Live host dispatch for OpenCode, KiloCode, Cline, and agy; their command shapes are tested, but live runs are deferred until those hosts are actually used.
- A distributed or live two-host mesh; the current store is local.
- A web dashboard server or interactive controls; the generated `aperio dashboard` page is read-only.
- Native Windows execution of `aperio.cmd`; the PowerShell installer is tested under `pwsh` on macOS.
- Automated MCP or package discovery. Installation works only from a declared toolchain manifest with an explicit argv and verification command; risky tools still require owner approval.
- Automatic public release.

## Out of scope

- **CMS and SEO delivery.** Aperio may orchestrate a project that uses a CMS, but it does not ship a CMS, editor, media system, or SEO product. Those belong to the target project. `docs/CMS-ROADMAP.md` is a separate method reference, not an Aperio feature.
- **Deployment execution.** Aperio records deployment readiness and writes the handoff. It does not hold provider credentials or deploy applications. Deployment is an owner/project action.

## Safety model

Aperio is deliberately conservative:

- no plan, approval, or run without a ready learning dossier and a recorded local proof;
- no plan without at least one todo task; the todo ledger requires evidence and approval before the next task starts;
- no done or handoff without full pre-flight, deployment, after-sales, design, and security readiness;
- writes must stay inside the plan's allowed paths;
- protected paths such as `.git` and `.aperio` are refused;
- symlink components and parent traversal are refused;
- shell changes inside the scanned project are recorded as violations; writes outside the project or under excluded directories are not observed;
- a builder label cannot be the only reviewer label; this is not authenticated identity, so use `review --host` when a separate process matters;
- a task is `done` only after acceptance checks pass, the verified artifact and plan still match, and matching review evidence is confirmed.

The shell limitation is real. A command can change a file before Aperio detects it, and a write outside the scanned project is not detected at all. A plan can set `sandbox: true` to require `sandbox-exec` (macOS) or `bwrap` (Linux); if neither is available the run refuses rather than silently downgrading. With the sandbox on, host dispatch runs inside its disposable workspace as the writable boundary — the host cannot reach the real project; Aperio applies the reviewed changes afterwards. Without the sandbox, host changes are detected after execution only.

## Documentation

- `HANDOFF.md`: authoritative handoff for the next agent; read this first.
- `docs/OWNER-REQUESTS.md`: owner request trail and where each item is recorded.
- `docs/PRD.md`: full product requirements and scope decisions.
- `docs/DISCOVERY.md`: discovery domains, first questionnaire, facet profiles, evidence model, and module gates.
- `docs/ARCHITECTURE.md`: components, state layout, and safety boundaries.
- `docs/AUDIT.md`: source-anchored security audit ledger, schema, and limits.
- `docs/CMS-ROADMAP.md`: separate stack-neutral CMS method for a target project; not an Aperio feature.
- `docs/COORDINATION.md`: builder/auditor durable message channel, commands, and rules.
- `docs/ROADMAP.md`: rebuild order.
- `docs/STATUS.md`: what was measured, not what is claimed.
- `docs/TESTING.md`: how to reproduce the tests.
- `docs/AGENTS.md`: roles and task handover.
- `docs/DECISIONS.md`: decisions that shaped v2.
- `docs/ARCHIVE.md`: where the old repository and documents live.
- `docs/REBUILD-REPORT-20261026.md`: what changed in the rebuild and what remains.
- `docs/EGM-ASSESSMENT.md`: what the Elephant-Goldfish Model is and what Aperio should adopt from it.

## License

MIT. See `LICENSE`.
