# Handoff: Aperio Orchestrator v2

**Read this file first. Do not rely on any previous chat, transcript, or agent memory.**

This repository is the handoff boundary. Everything an incoming agent needs must be
in the repository: the code, tests, PRD, status page, decisions, owner-request
ledger, architecture note, and this file. If a claim is not in the repository and
is not reproducible by a command, do not treat it as true.

## 1. Repository identity

| Item | Value |
|---|---|
| Product | Aperio Orchestrator v2 |
| Remote | `https://github.com/Aperio-Studios-Private/Aperio-Orchestrator` (public) |
| Branch | `main` |
| Handoff HEAD | Read `git rev-parse HEAD` and `git status --short` before starting; do not trust a hash copied from this page. |
| Python | 3.10+ (CPU-independent, standard library only) |
| License | MIT; see `LICENSE` |
| Old repository | Private archive; do not force-push, publish, or copy its history. See `docs/ARCHIVE.md` |
| Current tests | 367 passing at handoff; re-run them, do not cite this number from memory |

## 2. What Aperio is

Aperio is a **local, stack-neutral orchestrator** that turns an owner request into a
bounded, approved plan, applies it, runs acceptance checks, requires an independent
review, records evidence, and writes a handoff.

It is **not**:

- a CMS, media system, visual editor, or SEO product;
- a deployment runtime, hosting provider, or credential store;
- a judge that can prove an arbitrary host or model is truthful;
- a replacement for an OS sandbox, a dependency scanner, or a penetration test.

CMS/SEO delivery and deployment execution belong to a target project and its
owner. Aperio records readiness and hands off; it does not deliver or deploy.
This is a recorded owner decision; see `docs/PRD.md` ("Scope decision") and
`docs/OWNER-REQUESTS.md`.

## 3. Verified baseline

Run these from the repository root:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
ruff check src tests
PYTHONPATH=src python3 -m aperio drift
git diff --check
```

Expected at handoff:

- **367 tests pass**
- `ruff check src tests` exits 0
- `aperio drift` prints `DRIFT CHECK: clean`
- `git diff --check` is silent
- CI runs the same suite on Python 3.10, 3.12, and 3.14

The current test distribution is in `docs/STATUS.md` and `docs/TESTING.md`. The
suite includes real local commands, host command-shape adapters, installer
checks, sandbox tests on macOS, and failure-path tests. Passing tests are not a
whole-repository security audit.

## 4. Architecture map

| Area | Files | Responsibility |
|---|---|---|
| State | `src/aperio/store.py`, `paths.py` | Atomic JSON, schema checks, append-only events, queue recovery, symlink/path safety |
| Model | `src/aperio/model.py` | Task, step, plan, approval, review, acceptance, plan digest |
| Policy | `src/aperio/policy.py`, `sandbox.py` | Allowed/protected paths, command checks, optional OS isolation |
| Execution | `src/aperio/runner.py` | Apply, change detection, verify, review, finish, rollback, resume, checkpoints |
| Hosts | `src/aperio/adapter.py`, `hosts.py` | Disposable host workspace, command shapes, host reviews |
| Gates | `discovery.py`, `learning.py`, `readiness.py`, `todo.py` | Persistent discovery, stack proof, readiness, one-task approval |
| Tooling | `skillgen.py`, `toolchain.py` | Project-scoped skills and approval-gated tool/MCP installation |
| Reporting | `dashboard.py`, `handoff.py`, `repo.py`, `drift.py` | Read-only dashboard, handoff, Git facts, docs drift |
| Audit/evidence | `audit.py`, `evidence.py`, `inspect.py` | Bounded audit ledger, evidence manifests, read-only inspection |
| Coordination | `mesh.py`, `mediator.py` | Local durable message store and disposition |
| CLI | `cli.py`, `__main__.py` | Commands and exit codes |

Full details are in `docs/ARCHITECTURE.md`. Do not duplicate an implementation in
a second module; change the canonical module and its tests.

## 5. Required workflow and gates

```text
ask -> discover -> learn -> todo -> readiness -> plan -> approve -> run
    -> verify -> independent review -> done -> handoff
```

A plan is refused unless:

- discovery is ready (or an explicit, dated owner waiver is recorded);
- the learning dossier is ready and a real local proof was recorded;
- a todo list exists and exactly one task is in progress;
- pre-flight readiness is valid;
- the plan is approved with the exact owner phrase.

`run` revalidates the learning digest, discovery digest, pre-flight readiness, the
linked todo task, and the plan body. `done` and `handoff` require full readiness.
The todo task is accepted only after evidence and the exact confirmation phrase.

## 6. State and safety boundaries

- State lives in `.aperio/`; it is local project state and is not committed.
- `.git` and `.aperio` are **non-overridable** protected paths.
- Shell/read steps are optionally OS-sandboxed when `plan.sandbox` is true.
  `sandbox-exec` is tested on macOS; `bwrap` is implemented but not live-tested
  on Linux. Host steps are not OS-sandboxed.
- Undeclared writes are detected after execution inside the scanned project.
  Writes outside the project or to excluded directories are not observed.
- Review/finish refute a project that changed after verification.
- Reviewer identity is a label, not cryptographic authentication.
- `aperio audit` is a bounded source-review ledger, not an exploit runner.
- `aperio security scan` is a bounded local secret scan, not a dependency-history
  scanner or a penetration test.
- `aperio tool install` runs only declared argv commands and records verification;
  risky tools require exact owner confirmation.

Read `SECURITY.md`, `docs/ARCHITECTURE.md`, and `docs/STATUS.md` before changing a
boundary.

## 7. Commands an incoming agent will need

```bash
# Install / check
./install.sh
aperio --version
aperio doctor

# Project lifecycle
aperio init <dir> --name "<name>"
aperio ask "<request>" --source owner
aperio discover next
aperio discover answer <id> --choice 1,3 --text "..."
aperio learn import examples/learning-dossier.json
aperio learn proof --command "python3 -V"
aperio learn validate
aperio todo add "<task>" --deliverable "<artifact>" --acceptance "<check>"
aperio todo start <todo-id>
aperio readiness import readiness.json
aperio readiness validate
aperio plan plan.json
aperio approve <plan-id> --by owner --confirm "I approve this plan"
aperio run <task-id> --actor builder
aperio resume <task-id> --actor builder
aperio verify <task-id>
aperio review <task-id> --host claude
aperio done <task-id>
aperio handoff <task-id> --print
aperio todo accept <todo-id> --by owner --evidence "..." --confirm "I accept this task"

# Inspection / support
aperio status --json
aperio dashboard
aperio security scan
aperio rollback <task-id> --yes
aperio recover
aperio tool import examples/toolchain.json
aperio tool status
aperio drift
```

Use `aperio <command> --help` for the exact current flags. Do not infer a flag from
this list.

## 8. Owner decisions and request trail

The owner's substantive requests and where each is recorded are in
`docs/OWNER-REQUESTS.md`. The short version:

- evidence over claims; documentation may not outrun code;
- no client data or credentials in the repository;
- use the private `Aperio-Studios-Private` organization;
- keep the old repository private; never force-push or publish its history;
- CMS and SEO delivery are target-project concerns, not Aperio features;
- deployment execution is out of scope; Aperio records readiness and hands off;
- live extra-host, native Windows, and Linux `bwrap` proofs are deferred, not
  release blockers;
- an independent reviewer is required; the auditor is report-only.

If a new request conflicts with these, stop and ask the owner rather than silently
changing scope.

## 9. What is verified, deferred, or out of scope

### Verified on this machine

- Core loop: init, ask, discovery, learning proof, todo, readiness, plan, approve,
  run, verify, review, done, rollback, handoff.
- Claude and Codex host dispatch and reviews on current code where recorded in
  `docs/HOST-PROOFS.md`; treat historical host evidence as historical.
- Local mesh store, mediator, installer, PowerShell installer under `pwsh` on macOS.
- Optional `sandbox-exec` shell isolation and fail-closed behavior.
- Toolchain installer, dashboard, secret scan, versioned state, recovery, resume.
- Full suite: 367 tests; CI on Python 3.10/3.12/3.14.

### Deferred, not blockers

- Live runs for OpenCode, KiloCode, Cline, and agy adapters.
- Native Windows `.cmd` execution.
- Linux `bwrap` live proof.
- Goose/dsh live dispatch (Goose bridge HTTP 500; dsh missing `RIVER_API_KEY`).
- Live host skill loading and teacher UI.
- External penetration testing and dependency-history scanning.

### Out of scope

- CMS, media, editorial workflow, visual editor, and SEO delivery.
- Deployment execution, provider credentials, and hosting operations.
- Automatic public release or force-push.

## 10. Directory hygiene

At handoff the tracked tree is clean. The following are intentionally not tracked:

- `.aperio/` local project state;
- `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`, `.DS_Store`;
- the external archive and local audit state.

Before handing off again:

```bash
git status --short --branch
git status --ignored --short
```

If local state exists, archive it outside the repository rather than committing
it. Never include `.aperio/`, credentials, client data, or generated caches in a
commit.

## 11. Incoming-agent start procedure

1. Read this file, `START-HERE.md`, `docs/PROJECT-HISTORY.md`, `docs/STATUS.md`, `docs/PRD.md`, `docs/TEACHING.md`,
   `docs/OWNER-REQUESTS.md`, `docs/AGENTS.md`, and `docs/ARCHITECTURE.md`.
2. Measure the tree: `git rev-parse HEAD`, `git status --short`, remote.
3. Run the baseline in section 3. If it differs from this page, record the
   mismatch; do not smooth it over.
4. Read `docs/STATUS.md` for the current measured state and `docs/PRD.md` for
   requirements. Do not use old chat or old reports as current status.
5. Choose one unblocked, bounded task. State its allowed paths and acceptance
   check before editing.
6. Make the smallest change; add a failing test first where practical; run the
   full baseline; commit locally with evidence.
7. Push only when the owner requested it or the current task explicitly allows it.
   Run CI after a push and report the result.
8. Update `docs/STATUS.md` only with measured facts. Do not claim a deferred or
   out-of-scope item as done.

## 12. Handoff acceptance

- [ ] `git status --short` is clean.
- [ ] `git rev-parse HEAD` equals `origin/main`.
- [ ] 367 tests pass locally (or the difference is recorded).
- [ ] Ruff, drift, and diff checks pass.
- [ ] CI result is recorded for the HEAD being handed off.
- [ ] `docs/STATUS.md` has no claim that the code contradicts.
- [ ] `docs/OWNER-REQUESTS.md` has no missing owner request.
- [ ] No credentials, client identifiers, local paths, or `.aperio` state are tracked.
- [ ] `docs/HANDOFF` points the next agent at the repository, not at a chat.

If you cannot check an item, say so explicitly.
