# Status

**Measured:** 2026-10-26, on the v2 rebuild tree.
**Rule:** this page reports what was run. It is not a roadmap and not a promise.
**Context:** `docs/REBUILD-REPORT-20261026.md` explains the rebuild and the archive.

## Verified

| Item | Result | Evidence |
|---|---|---|
| Core unit tests | 59 passed | `PYTHONPATH=src python3 -m unittest discover -s tests -v` |
| Adapter tests | 24 passed | same command; `tests/test_adapter.py` |
| Drift tests | 5 passed | same command; `tests/test_drift.py` |
| Mesh tests | 5 passed | same command; `tests/test_mesh.py` |
| Mediator tests | 6 passed | same command; `tests/test_mediator.py` |
| CLI tests | 16 passed | same command; `tests/test_cli.py` |
| Learning tests | 10 passed | same command; `tests/test_learning.py` |
| Skill tests | 9 passed | same command; `tests/test_skillgen.py` |
| Toolchain tests | 8 passed | same command; `tests/test_toolchain.py` |
| Dashboard tests | 7 passed | same command; `tests/test_dashboard.py` |
| Security tests | 8 passed | same command; `tests/test_security.py` |
| Todo tests | 6 passed | same command; `tests/test_todo.py` |
| Readiness tests | 5 passed | same command; `tests/test_readiness.py` |
| Discovery tests | 25 passed | same command; `tests/test_discovery.py` |
| Inspection tests | 14 passed | same command; `tests/test_inspect.py` |
| Evidence tests | 6 passed | same command; `tests/test_evidence.py` |
| Audit tests | 16 passed | same command; `tests/test_audit.py` |
| Repo tests | 4 passed | same command; `tests/test_repo.py` |
| Next advisor tests | 35 passed | same command; `tests/test_next.py` |
| Explainer tests | 12 passed | same command; `tests/test_explain.py` |
| Tutorial tests | 9 passed | same command; `tests/test_tutorial.py` |
| Independent host review of the MCP facade | fresh-context Codex review confirmed after 4 refuted rounds; the loop drove doctor's parse validation, the CLI --project default, strict request validation with per-line error containment, and the approval-phrase redaction over RPC | review `review-402597ba02`, task `task-mcp1` in the temporary goldfish project; commits `c5dfbbd` through `bf80f6e` |
| MCP facade | `apero mcp` serves Aperio's read-only advisors over JSON-RPC 2.0 on stdio with zero dependencies: initialize/tools-list/tools-call for aperio_next, aperio_explain, aperio_status, aperio_lessons, aperio_doctor. Write tools are excluded by design — the approval phrase never travels through an RPC pipe; tool errors surface as isError content, not protocol errors | `src/aperio/mcp.py`; `src/aperio/cli.py::cmd_mcp`; `tests/test_mcp.py` |
| Lessons ledger | `apero lesson add/list/remove` records what went wrong bound to a task and plain project paths (globs, absolute, and traversal refused); `plan` surfaces lessons whose paths intersect the plan's allowed paths as warnings — teach, never block; lessons live in schema-gated `.aperio/lessons.json` with a 500-entry bound | `src/aperio/lessons.py`; `src/aperio/cli.py::cmd_lesson`; `tests/test_lessons.py` |
| Independent host review of the evidence hardening | fresh-context Codex review confirmed, zero findings; the acceptance evidence ran the four discriminating cases (chain tamper, multi-flight, signed finish, unsigned refusal) | review `review-b25548f9ea`, task `task-evd1` in the temporary goldfish project |
| Tamper-evident evidence and signed verdicts | every evidence record carries the SHA-256 of its own body (doctor's verify_chain recomputes and reports any record edited after the fact; a prev-link design was attempted and withdrawn — random record ids mislinked across flights); review verdicts carry an HMAC under a per-project key generated at init — finish() refuses a verdict whose signature is missing or invalid, and the host-review path signs the same core | `src/aperio/store.py::verify_chain/sign_review/verify_review_signature`; `src/aperio/runner.py::review/finish`; `src/aperio/adapter.py` (host signing); `tests/test_core.py::test_evidence_chain_*`, `test_review_verdict_is_signed_and_verified`, `test_finish_refuses_an_unsigned_verdict` |
| Independent host review of the lessons ledger | fresh-context Codex review confirmed first round, zero findings; the acceptance evidence ran the lessons suite plus live round-trip and plan-surfacing flows | review `review-ad5fbf52f3`, task `task-les1` in the temporary goldfish project |
| Promo generator | `apero promo <task-id>` drafts a launch-video shot sheet and a complete promo plan from a done task's recorded evidence (current verification with plan+artifact digests, current run's changed files, signed review — all validated before citing). The sheet's five-beat times sum exactly to the declared duration (8..30s, horizontal or vertical) with the button shot capped in the final two seconds; the generated promo plan validates through the Aperio model, writes only under promo/, includes a render run step (hyperframes lint && validate && render, fail-closed on a missing local font), and machine-checkable acceptance: times-sum, the full determinism contract (no random/now/async/setTimeout/Promise, paused registered timeline), meta declared, ffprobe-validated video duration+fps. Aperio generates the plan; rendering stays with the HyperFrames toolchain installed via `apero tool` — never a core dependency | `src/aperio/promo.py`; `src/aperio/cli.py::cmd_promo`; `tests/test_promo.py`; doctrine `docs/MOTION.md` |
| Independent host review of the promo generator | fresh-context Codex review confirmed after 5 refuted rounds; the loop drove the render+validation gates into the generated plan, HTML escaping of evidence-derived text, current-verification/current-run/signed-review sourcing, button-shot placement, the full determinism contract, and command spellings | review `review-166c5cbd1d`, task `task-prm1` in the temporary goldfish project; commits `8bbf9ad` through `fcf1d31` |
| Independent host review of the SkillSpector verifier | fresh-context Codex review confirmed first round, zero findings; the acceptance evidence ran the verifier suite plus a LIVE scan of a malicious fixture (injection + credential access + exec) that was blocked with exit 1 and per-category findings, and a clean skill that passed SAFE | review `review-4f4c0fd71a`, task `task-ss1` in the temporary goldfish project |
| Retro | `apero retro <task-id>` audits a completed task's environment: classifies violations into improvement actions, identifies existence-only acceptance checks, surfaces active lessons, and reports gate coverage gaps. Read-only: a test asserts no writes. Accepts any non-planned task — the retro is most useful on failed tasks | `src/aperio/retro.py`; `src/aperio/cli.py::cmd_retro`; `tests/test_retro.py` |
| SkillSpector verifier | `apero skill verify <dir>` statically scans a skill directory BEFORE installation (never executes it): prompt-injection/anti-refusal/exfiltration/credential regex categories, Trojan-Source bidi and zero-width character detection, whitespace padding, AST behavioral rules for bundled Python (exec/eval/compile/__import__/subprocess/os.system/reflective getattr), weighted risk score with the executable multiplier, and the SkillSpector gate mapping (SAFE=allow, CAUTION=surface to owner, DO NOT INSTALL=block with exit 1). Adapted from NVIDIA SkillSpector (Apache-2.0) as a stdlib-only port (attribution in module docstring); static-only limits documented | `src/aperio/skillspector.py`; `src/aperio/cli.py::cmd_skill_verify`; `tests/test_skillspector.py` |
| Promo tests | 14 passed | same command; `tests/test_promo.py` |
| SkillSpector tests | 14 passed |
| Retro tests | 8 passed |
| Lessons tests | 8 passed | same command; `tests/test_lessons.py` |
| MCP tests | 14 passed | same command; `tests/test_mcp.py` |
| Installer tests | 23 passed | same command; `tests/test_installer.py` |
| PowerShell installer | install, launcher version, uninstall, check, update with backup, and rollback pass under `pwsh` 7.6.7 on macOS | `tests/test_installer.py::test_powershell_installer`, `test_powershell_update_check_and_rollback` |
| Total test suite | 368 passed | same command |
| CLI end-to-end | passed | `tests/test_cli.py::test_full_cli_flow` |
| Discovery core | 10 universal + 10 conditional questions persist; evidence, research requests, explicit owner waivers with review dates, and readiness survive restart | `tests/test_discovery.py`; `aperio discover status` |
| Discovery plan gate | a valid plan is refused until discovery is ready; an explicit owner waiver allows it with a warning; a plan is invalidated if discovery changes before approval or run; plan body and discovery digest are checked again at run | `tests/test_cli.py::test_plan_without_discovery_is_refused`; `tests/test_discovery.py::test_plan_is_invalidated_by_discovery_change`, `test_plan_body_tamper_after_approval_is_refused` |
| Learning plan gate | `plan`, `approve`, and `run` refuse until the dossier is ready; imported proof text is ignored and `aperio learn proof` must run a local command; stack, official source, skill/MCP, teach-back, and competency are validated; the plan records the dossier digest and refuses approval/run after it changes | `src/aperio/learning.py`; `src/aperio/model.py`; `tests/test_learning.py`; `tests/test_cli.py::test_plan_without_learning_is_refused` |
| Todo and approval gate | `plan` refuses an empty todo list and requires exactly one in-progress task, recording its `todo_id`; `run` revalidates that the linked task is in progress or accepted; a task cannot start until its predecessor is accepted or deferred; acceptance requires an approver, evidence, and the exact confirmation phrase | `src/aperio/todo.py`; `src/aperio/model.py`; `tests/test_todo.py`; `tests/test_cli.py::test_plan_without_todo_is_refused` |
| Project readiness record | Pre-flight is a hard plan gate; deployment, after-sales, design, and security facts are required for `done` and `handoff`; high/critical unresolved security risk blocks full readiness | `src/aperio/readiness.py`; `tests/test_readiness.py`; `tests/test_cli.py::test_plan_without_preflight_is_refused` |
| Plan approval binding | approval records a SHA-256 of the plan body; changing steps or allowed paths after approval is refused | `src/aperio/model.py::plan_body_digest`; `tests/test_discovery.py` |
| Read-only inspection | folder stack, tests, docs, CI, deployment, env names; URL title, meta, H1, safe canonical, security headers; private URLs, credential URLs, and symlinked inputs refused; redirects revalidated; query and fragment values redacted | `tests/test_inspect.py`; `aperio inspect` |
| Evidence manifest | file path, size, and SHA-256 recorded; contents not copied; outside paths, symlinks, hard links, secret-bearing names, and real `.env` files refused | `tests/test_evidence.py`; `aperio evidence list` |
| Security audit ledger | bounded coverage units; host brief and atomic bulk ingest; confirmed findings need boundary, severity, source line, and anchored evidence; a separate verifier records confirmed/refuted/not-reproduced evidence; `needs_validation` cannot carry severity; invalid ledgers are refused; report marks open, truncated, changed-source, unverified, contradicted, or unresolved findings incomplete | `tests/test_audit.py`; `aperio audit start`; `docs/AUDIT.md` |
| Demo project | applied, verified, reviewed, done | `examples/demo-site-plan.json` through the CLI |
| Rollback | restores modified files and removes created files | `tests/test_core.py::test_rollback_restores_modified_and_removes_created` |
| Path traversal and symlink escape | refused, including dangling symlink components | `tests/test_core.py` |
| Project state symlink | opening a project whose `.aperio` is a symlink is refused | `tests/test_core.py::test_state_symlink_is_refused` |
| State file symlink | a symlinked queue file is refused and the external file is untouched | `tests/test_core.py::test_state_file_symlink_is_refused` |
| Review tamper | a reviewer that changes the project is refused | `tests/test_adapter.py::test_reviewer_cannot_change_the_project` |
| Control-state change | a step that alters project, queue, plan, evidence, discovery, or inspection fails | `_hash_control_state`; `tests/test_discovery.py::test_run_cannot_rewrite_discovery_control_state`; `tests/test_core.py` |
| Protected-path glob | matching a protected path fails even through a glob | `tests/test_core.py::test_glob_cannot_reach_a_protected_path` |
| Non-overridable protected paths | `.git` and `.aperio` remain protected even when a policy passes an empty or custom protected-path list | `src/aperio/policy.py::PROTECTED_PATHS`; `tests/test_core.py::test_protected_paths_cannot_be_removed_by_policy` |
| Read-only step | `kind: read` runs a command and fails if the project changes; it cannot declare writes | `src/aperio/runner.py`; refusal at `src/aperio/model.py::Step.validate`; `tests/test_core.py::test_read_step_records_output_without_changes`, `test_read_step_cannot_change_the_project`, `test_read_step_shape_is_rejected_by_the_model` |
| Versioned state | every `.aperio` JSON state file carries `schema`; a missing schema is migrated on read, an unknown future schema is refused | `src/aperio/store.py::_read_state_json`; `tests/test_core.py::test_legacy_queue_schema_is_migrated`, `test_future_queue_schema_is_refused`, `test_future_project_schema_is_refused` |
| Run revalidates readiness | the plan pins the readiness record's digest at plan time; `approve`, `run`, and `resume` refuse if the record vanished or changed after planning | `src/aperio/cli.py::_require_current_readiness`; `tests/test_cli.py::test_run_rejects_readiness_that_vanished_after_approval`, `test_readiness_change_invalidates_the_plan`, `test_plan_without_readiness_binding_is_refused_at_approval` |
| Skill frontmatter integrity | generated skill descriptions are JSON-quoted and validation checks name, scope, version, and purpose against the registry | `src/aperio/skillgen.py`; `tests/test_skillgen.py::test_frontmatter_survives_quotes_and_newlines_in_purpose` |
| Queue recovery journal | every queue save is appended as a `queue.saved` event; `aperio recover` restores a missing/corrupt queue and refuses a future schema | `src/aperio/store.py::recover_queue`; `tests/test_core.py::test_queue_recovers_from_event_journal`, `test_queue_recovery_refuses_future_schema` |
| Dashboard output safety | `--output` must stay inside the project and cannot overwrite `.git` or `.aperio`; traversal is refused; an existing non-state `--output` requires `--force` | `src/aperio/dashboard.py::write`; `tests/test_dashboard.py::test_write_refuses_to_clobber_the_control_plane`, `test_write_refuses_traversal`, `test_dashboard_output_does_not_clobber_tracked_files` |
| Security scan | bounded local scan for private keys, high-confidence tokens, sensitive filenames, and assigned secrets; excludes generated and VCS directories | `src/aperio/security.py`; `tests/test_security.py` |
| Toolchain installer | manifests declare source, version, license, scope, permissions, risk flags, cost, install argv, and verify argv; risky tools require exact owner confirmation; failed verification never records an install | `src/aperio/toolchain.py`; `tests/test_toolchain.py` |
| Resume interrupted run | `aperio resume` restores the pre-run snapshot, clears stale verification/review, and reruns the same approved plan; it refuses when no run is interrupted | `src/aperio/runner.py::resume_plan`; `tests/test_core.py::test_resume_restores_the_interrupted_snapshot_before_rerunning`, `test_resume_refuses_when_no_run_is_interrupted` |
| Optional OS sandbox | `plan.sandbox: true` wraps shell/read commands AND host dispatch with `sandbox-exec` (macOS) or `bwrap` (Linux); a missing backend fails closed; evidence records whether isolation was active | `src/aperio/sandbox.py`; `tests/test_core.py::test_sandboxed_run_records_active_isolation`, `test_sandboxed_read_records_active_isolation`, `test_sandbox_blocks_a_write_outside_the_project`, `test_sandbox_request_without_a_backend_fails_closed` |
| Run checkpoint | every run writes a checkpoint file under `.aperio/runs/` before steps and after completion; it is outside the control-state hash | `src/aperio/runner.py::_write_checkpoint`; `tests/test_core.py::test_run_writes_a_step_checkpoint` |
| Task ID traversal | persisted task ids cannot contain path separators | `tests/test_core.py::test_task_id_traversal_is_refused` |
| Installer prefix canonicalization | `/..` resolves to `/` and is refused | `tests/test_installer.py::test_prefix_that_resolves_to_root_is_refused` |
| Host deletion | host deletions are rejected | `tests/test_adapter.py::test_host_deletion_is_rejected` |
| Undeclared shell write | detected and failed | `tests/test_core.py::test_command_outside_write_is_detected` |
| Verification timeout | cannot pass, even with `expected_exit: 124` | `tests/test_core.py::test_verification_timeout_cannot_pass` |
| Artifact binding | review and done refuse if the project changes after verification | `tests/test_core.py::test_review_refuses_a_project_changed_after_verification`; `test_finish_refuses...` |
| Review evidence | done refuses if the review evidence file is missing | `tests/test_core.py::test_finish_requires_review_evidence` |
| Installer dry-run uninstall | reports would-remove and keeps files | `tests/test_installer.py::test_dry_run_uninstall_removes_nothing` |
| Installer user-file preservation | uninstall leaves unrelated files in the skill directory | `tests/test_installer.py::test_uninstall_preserves_user_files_in_the_skill_directory` |
| Installer update/recovery | `--check`, `--update` with a bounded library backup, and `--rollback` restore; Bash and PowerShell both covered | `tests/test_installer.py::test_check_reports_version_without_writing`, `test_update_backs_up_and_rolls_back`, `test_powershell_update_check_and_rollback` |
| Self-approval | the approver cannot also be the run actor | `tests/test_core.py::test_approver_cannot_be_the_run_actor` |
| No-op acceptance | `true` and `exit 0` are refused as acceptance checks | `tests/test_core.py::test_noop_acceptance_is_refused` |
| Acceptance mutation | a check that changes a project file fails verification | `tests/test_core.py::test_acceptance_check_cannot_mutate_the_project` |
| Installer dry run | no files written | `tests/test_installer.py::test_dry_run_writes_nothing` |
| Installer idempotency | second run leaves one skill | `tests/test_installer.py::test_install_is_idempotent_and_uninstalls` |
| Installer paths with spaces | install and launcher version pass | `tests/test_installer.py::test_prefix_with_spaces` |
| Installer uninstall | removes binary, library, and skill | same test |
| Host detection | reads installed host names and versions | `aperio hosts`; presence is not permission |
| Claude host adapter | real host produced `site/index.html` in a disposable copy; acceptance passed; review and done completed on current code | task `task-17fd7a83a6`, run `run-d8e491aeb4`, review `review-5cb1b3585d`; earlier run `run-2d57f0f091` |
| Goose host adapter | command path tested with a fake binary; live Goose call failed with HTTP 500 from the local bridge | `tests/test_adapter.py::test_goose_adapter_builds_a_run_command`; live probe output |
| dsh host adapter | command path tested with a fake binary; live dsh blocked by missing `RIVER_API_KEY` | `tests/test_adapter.py::test_dsh_adapter_builds_a_headless_command`; live probe output |
| OpenCode, KiloCode, Cline, agy adapters | command shapes tested with a fake binary; live runs not yet proven | `tests/test_adapter.py::test_extra_host_adapters_build_commands` |
| Host change outside the plan | rejected before it reached the real project | `tests/test_adapter.py::test_host_change_outside_plan_is_rejected` |
| Host change outside step writes | rejected before it reached the real project | `tests/test_adapter.py::test_host_change_outside_step_writes_is_rejected` |
| Host symlink | rejected; no target content is read or copied | `tests/test_adapter.py::test_host_symlink_is_rejected` |
| Codex host adapter | real Codex built `site/index.html`; fresh Claude review confirmed; task done | task `task-116b1d078e`, run `run-d86056766a`, review `review-5fcf72b5e9` |
| Codex host review | real Codex reviewer confirmed a verified task with no findings | review `review-138f0f9a9f`, task `task-1b8dcd0ca2` |
| Fresh-context host review | real Claude reviewer saw only the brief, changed files, acceptance, and evidence; verdict confirmed | review `review-973d3a5fb8` in the temporary goldfish project |
| Self-review refusal | a host cannot review its own build | `tests/test_adapter.py::test_host_cannot_review_its_own_build` |
| Documentation drift | Docs links and inline paths resolve; repo check clean | `aperio drift`; `tests/test_drift.py` |
| Git facts | branch, short commit, dirty state, changed count, and credential-stripped origin are read-only and shown in status/handoff | `tests/test_repo.py`; `aperio status` |
| Local message store | send, read, reply, ack, filters, restart persistence; real Claude and Codex processes each used it | `tests/test_mesh.py`; `docs/HOST-PROOFS.md` |
| Mediator disposition | records CONFIRMED, REFUTED, or BLOCKED from the current task state and latest evidence | `tests/test_mediator.py`; `aperio mediate` |
| `/aperio` entry point | supplied by the installed skill | `~/.claude/skills/aperio/SKILL.md`; no duplicate command file; host load not verified |
| Skill file | installed by the installer | `~/.claude/skills/aperio/SKILL.md`; host load not verified |
| Real-home install | binary and skill present; legacy command removed; CLI runs | `bash install.sh`; `aperio --version`; `aperio doctor` |
| Static checks | ruff and shellcheck pass | `ruff check src tests`; `shellcheck install.sh` |
| Public repository | public at `https://github.com/Aperio-Studios-Private/Aperio-Orchestrator` | `gh repo view Aperio-Studios-Private/Aperio-Orchestrator --json visibility,url` |
| GitHub Actions | tests pass on Python 3.10, 3.12, and 3.14 | [tests workflow](https://github.com/Aperio-Studios-Private/Aperio-Orchestrator/actions/workflows/tests.yml) |
| Handoff | `HANDOFF.md` is the incoming-agent entry point; `docs/OWNER-REQUESTS.md` maps owner requests to docs/tests | `HANDOFF.md`; `docs/OWNER-REQUESTS.md` |
| Documentation drift | clean: links and inline paths resolve | `aperio drift` |
| Independent host review of the next-action advisor | fresh-context Codex review confirmed after 15 refuted rounds; the loop drove 13 fixes (binary name across 21 commands, gate order, stale/missing bindings, preflight vs full readiness, handoff completion, task-selection mismatches, shell-safe paths, placeholder quoting, legacy-plan discovery exemption) | review `review-a8def7727b`, task `task-next1` in the temporary goldfish project; commits `3a50af7` through `751de0c` |
| Independent host review of the tutorial slice | fresh-context Codex review `review-` (task-tut1): static inspection found no defect; the reviewer's read-only sandbox could not create temp dirs, so runtime re-verification was environment-blocked — the recorded acceptance evidence (executed at verify time) covers the full flight, the wrong-phrase and self-review refusals, and the tutorial test suite | task `task-tut1` in the temporary goldfish project; commits `15c72a0` through `a5f77e0` |
| Tutorial flight simulator | `aperio tutorial build <dir>` creates a practice fixture with every plan gate pre-satisfied (discovery, learning proof, todo started, readiness) plus a starter plan and CHECKLIST; the learner flies plan→approve→run→verify→review→done→handoff; `aperio tutorial check <dir>` grades the flight from real state (read-only: a test asserts no writes) | `src/aperio/tutorial.py`; `src/aperio/cli.py::cmd_tutorial`; `tests/test_tutorial.py` |
| Independent host review of the skill-adoption sprint | fresh-context Codex review confirmed first round, zero findings | review `review-36c8f07ccd`, task `task-sprA` in the temporary goldfish project |
| Skill-format adoption (audit of public agent skills) | frontmatter upgraded per the agent-skills spec and Anthropic's skill-creator guidance (pushy trigger-rich description, compatibility, metadata, license); TEACHING.md ships inside the skill as references/ (both installers copy it); claim→evidence table and rationalization tables added to TEACHING.md from this repo's own review-loop history; the Floor (new suppression/stub/skip markers in changed files fail verification); review brief is EXTRACT-without-CLAIM (builder request narrative removed) | `skill/aperio/SKILL.md`; `skill/aperio/references/TEACHING.md`; `docs/TEACHING.md`; `src/aperio/runner.py::_floor_violations`; `src/aperio/adapter.py::_review_brief`; `tests/test_core.py::test_floor_*`; `tests/test_adapter.py::test_review_brief_omits_the_builder_claim` |
| Independent host review of host-step sandboxing | fresh-context Codex review confirmed after 2 refuted rounds; the loop drove the workspace-scoped write boundary (the whole project was writable to the sandboxed host), the ordered bwrap recipe (dedicated tmp, read-only project, writable workspace last), and the visibility binds that keep the host binary and the project tree reachable under the tmp shadow | review `review-e9a447121e`, task `task-sbx1` in the temporary goldfish project; commits `a858538` through `71fdee3` |
| Independent host review of the explainer slice | fresh-context Codex review confirmed after 17 refuted rounds; the loop drove 20+ verified fixes across explain/TEACHING and two shipped-code bugs (plan sandbox field dropped by cmd_plan; host glob validation crossing `/`) | review `review-bc9c259b4a`, task `task-explain2` in the temporary goldfish project; commits `a56dd37` through `7cadf8e` |
| Gate explainer | `aperio explain <topic>` explains discovery, learning, todo, readiness, approval, writes, and review: what each checks, the incident that motivated it, and live project status; read-only (a test asserts no state change); every printed command uses the real binary name | `src/aperio/explain.py`; `src/aperio/cli.py::cmd_explain`; `tests/test_explain.py`; craft page `docs/TEACHING.md` |
| Next-action advisor | `aperio next` / `aperio next --json` computes the single next legal action from state (learning, todo, preflight readiness, discovery — the order cmd_plan refuses in, preflight-only before planning — then the task lifecycle with stale-binding and missing-binding detection; full readiness before done/handoff; --project on every suggested command); read-only: a test asserts it writes nothing | `src/aperio/nextstep.py`; `src/aperio/cli.py::cmd_next`; `tests/test_next.py` |
| Independent host review of the hygiene sprint | fresh-context Codex review confirmed after 3 refuted rounds; 3 verified findings fixed (glob crossing `/`, STATUS per-suite drift, PRD table drift) | review `review-61c27b51d5`, task `task-sprint1` in the temporary goldfish project; earlier rounds `review-62d4842164` (2×P1), plus two P2 rounds; commits `01018bc`, `d317d42`, `68611b9`, `01c0ad8` |

## Not built

- An automated vulnerability scanner or exploit runner. `aperio audit` records a bounded source review and its evidence; it does not execute target code or prove exploitability.
- Live host dispatch for OpenCode, KiloCode, Cline, and agy; their command shapes are tested, but live runs are deferred until those hosts are actually used.
- A distributed or live two-host mesh; the current message store is local and persistent.
- A real host-to-host exchange over that store.
- Live sandboxed-host proof, updated 2026-11-01: a real Codex dispatch under `plan.sandbox: true` on macOS is now PRODUCTIVE under the tuned host sandbox — run applied with zero violations, the host's own workspace-write sandbox blocked the attempted outside write (the victim file was never created), and the built page was applied to the project. The path there was measured: deny-default and deny-all-writes profiles broke Codex's own sandbox_apply and patch tool, so live hosts with native sandboxing (codex) are dispatched in their own workspace-write mode with state (CODEX_HOME) and TMPDIR redirected into the disposable workspace, and the outer sandbox-exec is dropped for them (nested seatbelts broke the host's tooling); hosts without native sandboxing keep the outer sandbox-exec. An earlier measured attempt (2026-10-29) under the deny-default profile had the boundary hold while the host was not productive — that history is why the tuned profile exists.ran with active sandbox-exec isolation and was blocked from writing outside the project (the outside victim file was never created), but the host itself exited 1 — sandbox-exec's deny-default profile denies operations Codex needs (PATH aliases, in-process app-server client). The boundary held; the host is not yet productive under it. A profile tuned for real hosts (or bwrap on Linux) is future work. Evidence: run recorded in the temporary project `aperio-sbx-live-*` (not retained).
- Native Windows execution of `aperio.cmd`; the PowerShell installer and update/rollback pass under `pwsh` on macOS.
- Full 138-field discovery module catalog and expanded read-only inspectors; the `discover` command records 10 universal and 10 conditional questions, evidence references, research requests, explicit owner waivers with review dates, readiness, and blocks `plan` until discovery is ready. The full domain catalog is not loaded.

## Out of scope

- **CMS, media, SEO, and Astro/Lumos delivery.** These belong to a target project, not Aperio. `docs/CMS-ROADMAP.md` is a separate method reference.
- **Deployment execution.** Aperio records deployment readiness and writes the handoff; it does not hold provider credentials or deploy applications. Deployment is an owner/project action.

## Known limits

- Independent Claude and adversarial subagent audits found and narrowed the boundary issues; the remaining limits are documented in `SECURITY.md`. The 368-test suite is not a whole-repository audit. Reviewer identity is a label, not a cryptographic identity. Discovery answers are recorded by the agent on the owner's behalf; owner identity is not cryptographically verified. See `docs/AUDIT-CODEX-20261026.md` and `docs/AUDIT-CLAUDE-20261026.md`.
- Host steps are OS-sandboxed only when a plan sets `sandbox: true` (same boundary as shell/read steps); otherwise changes are detected after execution. Sandboxed host dispatch is proven with the fake host; a live host under the sandbox is not yet recorded.
- `review --host` supports only the reviewer adapters (claude, codex, dsh, goose); opencode, kilocode, cline, and agy are dispatch-only adapters for `run`.
- URL inspection rejects private and credential URLs and revalidates redirects, but DNS rebinding during host resolution is not fully prevented.
- Claude dispatch used a budget of 1.50 USD; a smaller budget was rejected by the host.
- Snapshot limits are 5,000 files and 50 MB.
- The project lock is best-effort. POSIX uses `fcntl`; Windows uses an `msvcrt` byte-lock fallback that is implemented but unverified natively.
- `aperio learn proof` executes the supplied command in the project root without an OS sandbox; use a non-destructive proof command and inspect it first.
- The learning dossier validates structure, not whether an external documentation page actually supports the claim; a human or independent reviewer must check source quality.
- The learning gate is enforced by `plan`, `approve`, and `run`; direct `apply_plan` library callers bypass it unless they check `learning.status` themselves.
- The todo gate is enforced at `plan` and `run`; `plan` records the active `todo_id`, and `run` revalidates that the linked task is in progress or accepted.
- The readiness record's pre-flight section is a hard `plan` gate, and full readiness is required by `done` and `handoff`. `run` itself does not require the deployment/after-sales sections; deployment remains a separate owner-approved action.
- Automated MCP/package installation is implemented only for declared argv manifests with verification; there is no registry discovery, GUI, or automatic trust decision.
- Host detection reports presence and version, not authentication or model access.
- The demo site is a build fixture, not a design or CMS proof.

## Next measured milestone

M2: independent multi-host review. One host builds, a different host reviews from a fresh context, and the mediator records `confirmed`, `refuted`, or `not reproduced` with evidence. Completion requires a recorded evidence file and a reproducible command, not a status paragraph.
