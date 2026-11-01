# Aperio Orchestrator: Product Requirements

**Version:** 2.0
**Date:** 2026-10-26
**Status:** Product contract for the v2 rebuild. It describes required behavior, not achieved behavior. The current implementation subset is recorded in `docs/STATUS.md`.
**Supersedes:** the pre-v2 canonical PRD and the Gemini v5.0 draft. The two source drafts remain historical inputs and are not part of this repository.
**Owner:** Shahid
**Mediator and main agent:** Hermes
**Change control:** only the owner approves changes to this document. Agents propose changes in a report; they do not silently rewrite it.

---

## 0. How to read this document

Every requirement has four separate states:

| State | Meaning |
|---|---|
| **Implemented** | Source code or a document exists. |
| **Wired** | The normal product workflow calls it. |
| **Verified** | A reproducible test, live run, or inspected artifact proves the behavior. |
| **Approved** | The owner has authorized the relevant scope, gate, or external action. |

These states are not interchangeable. A file is not a feature. A test is not a delivered project. A green validator is not owner acceptance.

The authority order is:

1. The owner's explicit instruction.
2. This PRD.
3. The approved plan for the active task.
4. Current source, tests, and measured evidence.
5. Historical reports and handoffs.

When a lower layer contradicts a higher one, the higher layer wins, and the contradiction is recorded rather than hidden.

This PRD does **not** authorize a public release, history rewrite, force-push, branch deletion, deployment, paid service, credential change, destructive cleanup, or copying client data into this repository.

### Scope decision: Aperio is not a CMS or deployment product

Aperio is a stack-neutral orchestrator. It does not ship a CMS, media system, visual editor, SEO product, or hosting/deployment runtime. A target project may choose those things; Aperio records the decision, checks readiness, and hands off. CMS and SEO requirements in this PRD apply only when the owner selects a CMS-backed target project, and they are delivered by that project, not by Aperio itself. Deployment execution is an owner/project action; Aperio records the deployment data and requires it before handoff.

---

## 1. Product definition

Aperio is a private, project-scoped engineering foreman and delivery system for coding agents. It sits between the owner's request and the agents' hands. It must:

- capture the request without losing amendments;
- establish the real project and its constraints;
- research before choosing an approach;
- require an approved written plan before code;
- route work to available hosts and models by capability;
- keep work moving through approved tasks;
- require independent verification rather than self-review;
- deliver the actual requested artifact in the actual target repository;
- leave a current, readable state that another host can resume.

Aperio has two connected responsibilities, but only one of them is shipped here.

**Workflow layer (Aperio):** intake, research, planning, approval gates, project memory, task queue, host/model selection, fan-out, peer communication, independent review, recovery, evidence, handoff.

**Delivery layer (target project, not Aperio):** design research, frontend implementation, CMS and backend integration, SEO, responsive and accessibility checks, tests, assets, release preparation, client handover.

Aperio orchestrates the delivery layer; it does not ship a CMS, CMS editor, deployment runtime, or SEO product. Neither layer substitutes for the other. Governance without delivery is failure. A pretty page without working controls, data, or proof is also failure.

---

## 2. Users and roles

### 2.1 Owner

Sets goals, scope, quality expectations, budgets, approvals, and protected boundaries. The owner is not required to read code or reconstruct logs to know what happened.

### 2.2 Mediator and main agent

Owns the canonical queue, assigns tasks, reconciles reports, decides when evidence is sufficient, serializes shared-state writes, and writes the final handoff. The mediator does not accept a builder's self-review as independent proof.

### 2.3 Builder

Implements one bounded task in the assigned repository and path set. Reports exact files, behavior, commands, results, and limitations.

### 2.4 Independent auditor

Reviews the builder's diff and evidence, reruns decisive checks, and classifies findings as `CONFIRMED`, `REFUTED`, or `NOT REPRODUCED`. The auditor is a different host, CLI, or model when available. If no independent reviewer is available, the task is `NEEDS_REVIEW`, not done.

### 2.5 Specialist roles

Research, UX and visual design, frontend architecture, backend and CMS, SEO, security, test engineering, content review, release engineering. Roles are assigned by capability, not by a fixed host name. A host name in a roster is not proof that the host is alive, permitted, or suitable.

### 2.6 Teacher and competency owner

Aperio is the teacher and gatekeeper for every executing agent. It owns the learning dossier, the teach-back review, the local proof, and the competency record. It may narrow, pause, or refuse a task when the agent has not demonstrated the required stack, design, security, or tooling knowledge.

---

## 3. Goals

1. Close the gap between what the owner asked for and what was delivered.
2. Deliver real, working artifacts in the target repository, not plans or templates about them.
3. Preserve intent across sessions, hosts, and model changes.
4. Use multiple agents only when it improves coverage, quality, or time, and prove that it did.
5. Make critical rules executable where feasible, with negative tests proving they can fail.
6. Produce domain-appropriate design and content, not generic template output.
7. When a target project requires a CMS, ship the public surface and admin controls together in that project; Aperio itself ships no CMS.
8. Make SEO, accessibility, performance, and security claims testable and scoped to the approved project contract.
9. Protect client data, credentials, private history, and owner work.
10. Force stack mastery and teaching evidence before implementation; a confident agent claim is not knowledge.
11. Keep the product portable across hosts, stacks, operating systems, and installation paths.
12. Keep the owner informed with plain-language status and exact evidence.
13. Leave maintainable state: one current handoff, one queue, one active plan, one requirement matrix, and archived history.

## 4. Non-goals

- A public multi-tenant SaaS product at this stage.
- Automatic public release or repository visibility changes.
- Unrestricted agent autonomy or unrestricted shell access.
- Automatic spending on models, APIs, hosting, dependencies, or services.
- A guarantee that every host has the same tools, context, permissions, or browser.
- A claim that a site is secure, production-ready, or Lighthouse 90+ without a real run.
- A forced universal frontend stack. Astro and Lumos are options, not laws.
- Replacing objective evidence with agent opinion.
- Treating this repository as a client project or copying client material into it.

---

## 5. Operating principles

1. **Owner intent over agent habit.** An explicit request beats a familiar pattern.
2. **Request, then plan, then code.** No production code before the applicable plan approval.
3. **Research before irreversible choices.** Record sources and dates for facts that can change.
4. **Known, assumed, unverified.** Label each claim. Do not turn an assumption into a fact.
5. **Keep working.** Continue all approved, unblocked tasks. Mark a real blocker and move to the next task.
6. **No self-audit.** A builder is not the sole verifier of its own work.
7. **Feature means behavior.** A registry row, template, button, or test name is not a feature.
8. **Evidence before done.** Use commands, exit codes, rendered output, screenshots, database effects, or live host runs as appropriate.
9. **No scope freelancing.** Do not add unrequested features or refactor unrelated code.
10. **No destructive shortcut.** Preserve user work and use backups, leases, and rollback.
11. **Private by default.** No publication without explicit owner approval after privacy checks.
12. **Portable paths.** No hard-coded home directory, checkout path, shell, or model path.
13. **One canonical source per artifact.** Do not create competing state files, queues, or plans.
14. **No paper gate.** A rule described as enforced must have a call path and a negative test.
15. **Respect exclusions.** Never use Kimi. Do not dispatch OpenCode until the recorded conflict is resolved. Use `codexx` when that is the intended host.

---

## 6. End-to-end workflow

### Stage 0: Resume and establish reality

1. Identify the target repository and whether it is Aperio itself or a separate client project.
2. Read the current handoff, queue, active plan, PRD, owner ledger, and applicable laws. Do not read every archive by default.
3. Verify host, model, tools, permissions, branch, HEAD, dirty state, CI state, and concurrent work.
4. Prove the intended skill or entrypoint is actually loaded. A stub or missing install is a boot failure.
5. Compare the new request with the ask ledger. Do not ask for an answer already recorded unless it is stale or contradictory.
6. Record the baseline before writing: branch, HEAD, changed files, protected paths, test baseline, and blockers.

### Stage 0.5: Discovery and research dossier (Gate 0)

For a new build or material redesign, create a dossier in the target project. It must include:

- purpose and measurable business outcome;
- audience and trust questions;
- content and feature inventory, including a do-not-change list;
- stack options and compatibility research;
- at least three real competitor teardowns;
- at least three source-backed design references with dates and lessons;
- a project-specific visual direction, token draft, type pairing with licensing, layout and spacing rules, motion guidance, and asset strategy;
- a negative brief of patterns that are wrong for the domain;
- CMS, backend, auth, data, privacy, SEO, accessibility, hosting, and cost constraints;
- assumptions, open questions, and a plain-language how-and-why summary.

`_Pending._`, generic filler, or a reference that was never opened fails the gate. Unknown items are `N/A: reason` or `Assumed: reason`, with the consequence stated.

### Gate 1: Scope and stack confirmation

Present the recommended stack, pages, features, CMS needs, SEO needs, design direction, risks, cost, and assumptions. The owner approves, amends, or asks questions. Scope is frozen after approval unless the owner changes it or a documented critical issue requires a change request.

Do not force Astro or Lumos. If Lumos is selected, determine whether the project uses the upstream framework or this repository's custom implementation, and never mix their token APIs.

### Gate 2: Written plan approval

The plan names requirement IDs, files and modules, acceptance criteria, verification commands, builder and independent auditor, dependencies, parallelizable work, risks, rollback, and owner decisions. No implementation before approval. Ordinary reversible choices inside the plan do not need repeated approval.

### Stage 3: Bounded vertical slices

Split work into independent chunks with scoped briefs, paths, inputs, outputs, acceptance commands, and ownership leases. A slice is done only when its visible surface, data, controls, error states, responsive behavior, and tests are integrated as required. Update the queue at every state change.

### Stage 4: Independent verification

The auditor receives the requirement, acceptance criteria, diff, source, and evidence. The auditor reruns the decisive checks. UI work is inspected at required viewports. CMS work includes real edit, save, publish, permission, and rollback checks. SEO work runs against built output. Report each finding as `CONFIRMED`, `REFUTED`, or `NOT REPRODUCED`.

### Gate 3: Section or release packet

Show what was built, what changed, which acceptance criteria passed or failed, the evidence, known limits, and the exact approval requested. Approval of one slice does not approve deployment or unrelated changes.

### Stage 5: Pre-delivery gate

Run the relevant full battery. Confirm the app builds, tests actually execute, mobile and desktop behavior work, accessibility and SEO results are real, CMS actions work, secrets are absent, and evidence matches its manifest. Recheck the owner requirements against the deliverable.

### Gate 4: Delivery and deployment

Produce a handoff with setup and run commands, environment variable names only, architecture, data model, CMS guide, deployment steps, test results, known limits, backup and rollback steps, and an ask-to-result matrix. Deployment, publication, protected-branch pushes, visibility changes, and destructive remote operations require explicit approval.

### Stage 6: Post-delivery support

For client work covered by the company policy, define the support window and SEO support period in the client's own project record. Keep client material out of Aperio's repository.

---

## 7. Functional requirements

Priority: **P0** is required for a trustworthy core loop; **P1** is required for quality project delivery; **P2** is later expansion.

### FR-01: Entrypoint and boot proof (P0)

The installed `/aperio` entrypoint must load the canonical `skill/aperio/SKILL.md` and its required rule files on every supported host. The product must not claim a governed run when the skill is missing, a plugin stub points at absent files, or the host loaded a different workflow.

**Acceptance:** a boot check prints the resolved skill path, version, and required-file status; a missing file fails closed with recovery steps; README, installer, plugin, and runtime agree.

### FR-02: Canonical state and cold-start resume (P0)

Maintain one current-state handoff, one active queue, one active plan, one decision ledger, and one archive policy. A cold-start host must reconstruct the task, state, blockers, approvals, baseline, and next action without private chat memory.

**Acceptance:** a fresh host reads the repository and resumes without asking answered questions; contradictory state is reported, not silently resolved.

### FR-03: Owner request ledger (P0)

Record every substantive owner instruction, amendment, constraint, rejection, and decision with a stable ID, source, date, scope, priority, status, dependency, and verification pointer. Keep raw and grouped records distinguishable. Repeated asks are grouped without losing the source trail.

**Acceptance:** a checker detects a missing or altered quoted ask; counts are reconciled against the raw corpus; no high-priority ask disappears silently.

### FR-04: Adaptive intake (P0)

Ask one question at a time and build a facet profile rather than forcing one project type. A project can combine change, surface, lifecycle, content, user, data, commerce, discovery, quality, delivery, AI, locale, integration, risk, stage, team, budget, and timeline facets. Collect purpose, audience, features, content, stack, CMS, auth, data, integrations, hosting, budget, localization, accessibility, SEO, maintenance, and deployment constraints. Do not use a form when a conversation is enough.

The question model, eighteen domains, 138 base fields, facet profiles, evidence levels, module gates, and program decomposition are specified in [Discovery and Evidence Intake](DISCOVERY.md).

**Acceptance:** every required answer is answered or explicitly marked `N/A` or `Assumed` with a reason; placeholders fail.

### FR-05: Research-first Gate 0 (P1)

Produce the dossier in Section 6. It must be specific to the domain and project, sourced, and actionable. Store it in the target project.

**Acceptance:** absent sections, placeholder text, unsourced references, generic negative briefs, or tokens not derived from the dossier fail.

### FR-06: Stack and skill selection (P0)

Choose the stack from the owner's requirements and current research, not from habit. The bundled skill map is a fallback, not a lock. Research current framework APIs, licenses, versions, and integrations before a significant choice. A missing skill or package is explained with purpose, source, version, license, permissions, and cost before installation. On refusal or failure, use a documented fallback and disclose the limitation.

**Acceptance:** the plan records the chosen stack and skills with reasons; no unavailable model or package is dispatched as ready; no duplicate orchestrator competes for control.

### FR-07: Plan and scope lock (P0)

Write an ordered plan with requirement IDs, files, dependencies, owners, acceptance commands, evidence, rollback, and approval points. State what is out of scope and which files are protected.

**Acceptance:** production-code writes are blocked without a valid approved plan; post-approval scope changes produce a visible change request.

### FR-08: Queue and keep-working behavior (P0)

Continue all approved, unblocked tasks. Mark blocked work with a specific reason and continue unrelated work. Do not bypass approval, security, or destructive-operation gates.

**Acceptance:** the queue has no unexplained missing task; a blocked task is not a reason to stop unrelated approved work; `DONE` requires evidence.

### FR-09: Requirement traceability (P0)

Map every owner ask to one or more requirements, implementation paths, tests, and evidence. Preserve chronology when a later ask changes an earlier one. Produce a coverage report before handoff.

**Acceptance:** every in-scope item is `DELIVERED+VERIFIED`, `DELIVERED+NOT VERIFIED`, `PARTIAL`, `NOT IMPLEMENTED`, `BLOCKED`, or `EXCLUDED WITH OWNER REASON`; zero silent high-priority omissions.

### FR-10: Live host and model registry (P0)

Maintain one registry with each host's adapter, launcher, models, context capability, cost status, permissions, filesystem reach, tools, health, and known failures. Probe liveness before dispatch. Choose models by task class and current availability. Honor Kimi exclusion and the OpenCode conflict. Do not silently substitute `codex` for `codexx`.

**Acceptance:** each routing decision records host, model, reason, capability evidence, and fallback; an unavailable host is skipped with a visible reason.

### FR-11: Safe parallel fan-out (P0)

Split work into genuinely independent chunks with scoped briefs, paths, inputs, outputs, acceptance commands, and ownership leases. Parallelize only when safe and useful. Keep the mediator's context clean by delegating large reading, implementation, and review.

**Acceptance:** a run record shows chunks, hosts, duration, outputs, integration status, conflicts, and failures; failed agents trigger a bounded fallback; fan-out is not called working until a real run used it to complete work.

### FR-12: Bidirectional mesh communication (P0)

Agents must send, read, reply, and retrieve messages across hosts. Messages need IDs, sender, recipient, role, model, task, thread, time, type, status, acknowledgments, and evidence links. The UI must read the same store the agents write. Persistence and migration must preserve SQLite WAL data. Use compact records with retention rules.

**Acceptance:** at least two real hosts exchange messages in both directions; replies land in the correct thread; restart and migration retain messages; a missing store fails clearly instead of returning an empty success.

### FR-13: Executable mediator (P0)

The mediator reads peer responses, checks claims against source and tests, reruns decisive checks, records dispositions, and serializes shared-state writes. A protocol document is not an implementation.

**Acceptance:** given conflicting builder and auditor reports, the mediator produces an evidence-based decision and records `CONFIRMED`, `REFUTED`, or `NOT REPRODUCED`.

### FR-14: Independent audit (P0)

Use a different host, CLI, or model for meaningful reviews when available. The auditor reviews the actual diff and reruns decisive tests. Check requirement omissions, regressions, security, false-green tests, and unrelated changes.

**Acceptance:** a task cannot reach `DONE` without the configured independent review, or the missing review is explicitly `NEEDS_REVIEW` or `BLOCKED_EXTERNAL` and policy permits the alternative.

### FR-15: Objective evidence (P0)

Evidence includes task and requirement IDs, plan revision, source revision, commands, environment, timestamps, exit codes, result summaries, screenshots or previews where relevant, transcript digests, reviewer identity, and known limits. Keep secrets out.

**Acceptance:** absent, malformed, stale, mismatched, or fabricated evidence fails closed. Reports distinguish unit tests, integration tests, simulations, browser checks, and live deployment.

### FR-16: Deliver the real target work (P0)

After approval, apply the work to the actual target repository and complete the requested changes. A prototype, template, demo, or report is not a substitute unless the owner asked for one.

**Acceptance:** the target project builds and runs as approved; the handoff contains working commands and artifacts in that repository; if the target is unavailable, the deliverable is `BLOCKED`, not claimed complete.

### FR-17: Design research and quality (P1)

Produce an intentional design system for the domain: references, type licensing, spacing, grid, surfaces, contrast, motion, imagery, negative brief, and section composition. Studio archetypes are starting points, not mandatory templates.

**Acceptance:** major design choices trace to the dossier and tokens. Full-canvas choreography, negative-space budgets, type locks, and section rhythm apply only when the approved design contract requires them. No generic three-column icon cards, default gradients, or unapproved stock placeholders.

### FR-18: Mobile-first and accessibility (P1)

Verify at 390x844 before desktop approval, then at 1440x900 or the project's approved desktop viewport. Require no horizontal overflow, touch targets at least 44x44 CSS pixels where applicable, keyboard navigation, visible focus, semantic HTML, labels, alt text, contrast, reduced motion, accessible dialogs, and meaningful validation errors.

**Acceptance:** automated checks and real browser inspection prove the selected breakpoints; failures are fixed or explicitly accepted by the owner. Do not claim an accessibility score without a real test.

### FR-19: Real CMS coupling (conditional on the target project; not Aperio scope)

Aperio does not ship a CMS. When the owner selects a CMS-backed target project,
that project's every CMS-managed frontend section ships with connected admin
controls, persisted content, authorization, validation, output safety, draft and
publish behavior, and tests in the same slice. No "CMS later." See the scope
decision near the top of this document.

**Acceptance:** edit a real field, save it, refresh the public route, and show the change; verify permission denial, validation errors, draft and publish, media, and rollback. Exclusions outside approved scope are stated.

### FR-20: Design-locked visual editor and blocks (P1; target project, not Aperio scope)

> The CMS/SEO requirements from FR-20 through FR-25 apply only when the owner selects a CMS-backed target project. Aperio does not ship this functionality. See the scope decision near the top of this document.

For applicable CMS projects, provide a split-screen editor with a control sidebar and interactive preview. Selecting a preview element focuses its field. Owners can add, toggle, and reorder approved blocks without breaking tokens or layout.

**Acceptance:** preview-to-field mapping is correct; edits persist; controls work on desktop and mobile; unauthorized users cannot edit; design constraints hold.

### FR-21: Media studio (P1)

Support safe uploads, WebP or AVIF conversion when available, responsive `srcset`, asset budgets, and focal-point positioning. Avoid unlicensed hotlinks and make assets replaceable.

**Acceptance:** tests validate MIME, size, permissions, variants, focal data, and budget failures; generated assets are inspected on target viewports.

### FR-22: CMS SEO assistant (P1)

Provide a live search snippet preview, Open Graph and messaging-card preview, and checks for title, description, alt text, and keyphrase presence, integrated with the SEO engine. Scores reflect real field state.

**Acceptance:** changing a field changes its preview and check; missing data warns meaningfully; structured data matches real entities.

### FR-23: Drafts, revisions, and rollback (P1)

CMS projects need explicit draft, published, scheduled if in scope, and archived states. Keep revision history and an understandable undo or restore workflow. Rollback must not delete unrelated content.

**Acceptance:** create, edit, publish, compare, restore, and verify against the database and public output; failure paths are tested.

### FR-24: Domain blueprints (P1)

Provide reusable, tested patterns for service clinics, news portals, custom e-commerce, and ERP or CRM, selected only when applicable.

**Acceptance:** each blueprint has schema, validation, roles, API or service surface, admin expectations, fixtures, and end-to-end tests. A catalogue entry is not production readiness.

### FR-25: SEO audit and growth pack (P1)

Audit the actual target build across technical, on-page, schema, indexing, media, and Core Web Vitals dimensions. Generate metadata, canonicals, Open Graph, robots, sitemap, and applicable JSON-LD. For an approved client package, produce a 30-day plan and four researched draft articles left in draft for human review.

**Acceptance:** run the audit against built output; validate files and schema; draft claims are sourced; no ranking or Lighthouse guarantee without measurement. A 90+ mobile Lighthouse gate applies only when the approved contract says so.

### FR-26: Prompt modifier transparency (P1)

Report whether a rewrite used a deterministic template, the current host, or a configured external model. Show the original prompt, rewritten text, additions, removals, structure changes, rationale, skipped items, and the exact proposed command on every surface. Never present a template as a model rewrite.

**Acceptance:** mode labels are truthful; missing providers are visible; no key or provider is invented; dry-run executes nothing.

### FR-27: Learning from repeated mistakes (P1)

Capture a repeated defect as a candidate lesson with evidence. Promotion requires review and, where policy requires, owner approval. A generated regression test is not automatically approved or committed.

**Acceptance:** each promoted lesson traces to evidence, a test, and an enforcement path; no silent rule change.

### FR-28: Progress and status UI (P1)

Expose current tasks, assigned hosts and models, live progress, last heartbeat, recent events, failures, blocked reasons, pending approvals, branch and CI status, and evidence links. A roster entry is not a heartbeat.

**Acceptance:** status updates from real events; stale hosts are visibly stale; disconnected hosts are not green; state recovers after restart; each owner directive is ingested once and acknowledged.

### FR-29: Git, CI, and merge (P0 for repository work)

Capture baseline, protect concurrent work, run focused tests and the relevant battery, inspect the diff, wait for required CI, and report exact branch, commit, and check status. Merge only after required checks pass and with the required approval.

**Acceptance:** CI status comes from the actual remote or workflow source; if unavailable, report `UNKNOWN` or `BLOCKED_EXTERNAL`; a local green suite is not permission to merge or push.

### FR-30: Install, update, and uninstall (P0 for distribution)

Installer and updater must be reproducible, conservative, cross-platform, and honest about network operations. Support dry-run, selection, backups, rollback, and clear logs. Do not delete user data or overwrite customizations without consent and a verified restore path. Bash and PowerShell behavior must agree or state the difference.

**Acceptance:** fresh install, update, failure and retry, rollback, uninstall, dirty-tree refusal, path traversal, symlink or reparse refusal, malformed manifest, and user-data preservation pass in the appropriate environments. Do not use the owner's machine as a destructive test.

### FR-31: Portability (P0)

The core must not depend on one absolute path, home directory, shell, model, provider, or host. New dependencies require a stated reason, license, portability, and cost.

**Acceptance:** a clean clone in a different path, another home, and a clean environment behaves predictably; missing optional tools produce a safe fallback, not a crash or false success.

### FR-32: Reports and handover (P0)

Every substantial audit, plan, verification, incident, or delivery has a Markdown report in the documented location. Reports are readable on mobile, state evidence and limits, and avoid dumping raw transcripts into active context. Archive old communications rather than deleting them.

**Acceptance:** a final report exists, lists exact work and evidence, has no fabricated claims, is linked from the handoff and queue, and says what is true now.

### FR-33: Directory and artifact hygiene (P0)

One documented canonical location per artifact class: owner input, current state, queue, plans, reports, communications, evidence, raw asks, grouped asks, source, generated output, archive, quarantine. Do not modify owner-authored input without permission. Do not use deletion as cleanup. Use the approved temp-root helper.

**Acceptance:** a directory audit detects orphaned or duplicate authoritative files, wrong references, oversized active communications, and test artifacts in source. Cleanup is reviewed before moving high-value data.

### FR-34: Image and video prompts (P2)

When the owner requests prompts for an external image or video platform, produce a structured prompt with subject, composition, camera, motion, style, lighting, continuity, exclusions, aspect ratio, and purpose. Historical ratios: images 1:1, 3:4, 4:3, 9:16, 16:9; video 9:16 and 16:9. Use licensed or owner-provided media and replaceable slots.

### FR-35: P17 local task runner (P0 architecture, gated execution)

P17 may accept a task, plan, discover authorized CLIs, choose deterministically, execute with bounded inputs and timeouts, verify, and record evidence. Real-agent execution remains disabled until a separately approved preventive isolation strategy passes review. Executable pinning is not OS confinement.

**Acceptance:** no gate means no probing or spawn; executable resolution is pinned or confined to trusted roots; digest rechecked before spawn; invalid configuration fails closed; timeouts terminate the intended process tree where supported; evidence reflects every result; limitations are disclosed.

### FR-36: Mandatory stack mastery and learning dossier (P0)

Aperio must force the executing agent to learn the work before it plans or codes. The plan is blocked until a **learning dossier** exists for the exact stack and surface class. The dossier records:

1. the exact runtime, language, framework, package manager, database, hosting, and integration versions;
2. official documentation, release notes, migration guides, and security advisories used, with source URLs, access dates, and versions;
3. the dedicated skill or skills for the stack, their source, version, license, and scope;
4. available MCP servers, tools, CLIs, and editor integrations, or an explicit `N/A` with a reason;
5. current constraints, deprecations, licensing, cost, and platform limits;
6. the local proof command that demonstrates the agent can run the stack, not just describe it;
7. the teach-back summary and unresolved questions.

A claim such as “the framework supports this” is not learning evidence. A blog post is not a substitute for official documentation. If an official source is unavailable, the dossier records the fallback source, why it is trusted, and the residual risk. The dossier is bound to the plan digest and expires when the stack or version changes.

**Acceptance:** a missing, stale, unsourced, or generic dossier blocks plan approval; the dossier names the exact stack and versions; a recorded local proof command runs; changing the stack after approval invalidates the plan; an owner waiver is explicit and dated.

### FR-37: Toolchain acquisition and project-scoped skill creation (P0)

Aperio must inventory the tools the work needs and acquire them safely:

- identify official MCP servers, CLIs, packages, and skills;
- record source, version or commit, license, maintainer, permissions, network access, credentials, and cost;
- prefer project-scoped installation; global installation, paid services, credential use, or elevated permissions require explicit owner approval;
- pin versions or digests where the ecosystem supports it, and verify the installed artifact;
- never install an unreviewed package or MCP merely because a model suggested it;
- if no dedicated skill exists, create a **project-scoped skill** with triggers, scope, required inputs, commands, safety rules, tests, version, and known limits;
- do not overwrite a foreign or globally installed skill; propose the change and wait for approval;
- record a fallback when an MCP, package, or skill is unavailable.

A created skill is not trusted until it loads in a fresh session, passes its own validation, and has a reproducible test. A skill that writes outside its scope or hides its commands fails.

**Acceptance:** installation without required approval is refused; the provenance record is complete; a fake or tampered package is rejected; a missing skill produces a tested project-scoped skill, not an unsupported claim; a global install is never implied by a project-local action.

### FR-38: Pre-flight, deployment, and after-sales data (P0)

Before implementation, collect and record the pre-flight facts:

- audience, jobs, success measures, and content owners;
- required, conditional, and out-of-scope features;
- integrations, data sources, contracts, and rate or quota limits;
- brand, content, media, locale, accessibility, SEO, and legal constraints;
- target surfaces and the application classes in scope;
- budget, timeline, review owners, and approval path.

Before deployment, collect and verify:

- hosting or platform, domains, DNS, TLS, and environment-variable **names**;
- build, migration, seed, backup, and restore commands;
- CI/CD, branch protection, release approval, and rollback path;
- monitoring, logging, alerting, privacy, retention, and access ownership;
- smoke checks and post-deploy verification steps.

For after-sales service, record:

- support window, response expectations, and escalation owner;
- logs, metrics, alerts, dashboards, and health checks;
- backup schedule, restore drill, and recovery ownership;
- update and dependency policy;
- administrator and credential-recovery procedure, without storing secret values in Aperio;
- user documentation, known limits, and change-request path.

These records live in the target project or an approved client record, not in Aperio's repository. Missing deployment or after-sales data blocks a production handoff unless the owner explicitly accepts the gap.

**Acceptance:** a pre-flight checklist exists before coding; a deployment checklist exists before release; the handoff contains an after-sales pack; missing items fail the gate or carry a dated owner waiver; no secret values are copied into reports.

### FR-39: Application-class design and architecture school (P1)

Aperio must teach and enforce design and architecture appropriate to the surface, not apply one template everywhere. At minimum it distinguishes:

- marketing and content sites;
- web applications and dashboards;
- CMS administration and publishing;
- CRM, ERP, and internal operations tools;
- mobile applications;
- desktop applications.

For the selected class, the agent must produce a design contract covering audience, hierarchy, navigation, typography, spacing, grid, color and contrast, imagery, motion, responsive behavior, empty/loading/error states, accessibility, content tone, and originality. Architecture must state module boundaries, data ownership, API or service contracts, error handling, observability, and the deployment shape.

“Award-winning” is a review standard, not a claim. It means the work has researched references, an intentional visual point of view, strong hierarchy and typography, disciplined spacing, accessible interaction, credible content, and measured performance. It does not mean copying an award site or asserting a prize. Dense CRM and desktop interfaces are judged on task speed, keyboard use, and information density; mobile interfaces on touch, viewport, and offline behavior; CMS interfaces on editing safety and publishing clarity.

**Acceptance:** the design contract and reference board exist before visual implementation; the applicable class checklist is used; mobile and desktop are inspected; accessibility and performance checks run against built output; generic template composition or unlicensed assets are rejected; no award claim is made without evidence.

### FR-40: Security baseline and threat model (P0)

Before implementation, produce a threat model for the actual system: assets, actors, trust boundaries, entry points, data flows, abuse cases, and the highest-impact failures. Apply, at minimum:

- authentication, session lifecycle, authorization, and least privilege;
- input validation, output encoding, injection prevention, and file-upload safety;
- secret handling, encryption in transit and at rest where applicable, and key rotation;
- dependency, package, and MCP supply-chain review;
- CSRF, SSRF, path traversal, unsafe deserialization, and rate-limit controls where applicable;
- security headers, TLS, error handling, logging, audit trails, and privacy retention;
- backup, restore, incident response, and administrator recovery.

Aperio must not claim a system is “impenetrable.” Security is proven by a threat model, negative tests, dependency and secret checks, an independent review, and disclosure of unresolved risk. Any unresolved critical or high finding blocks handoff and deployment unless the owner records an explicit, time-bound risk acceptance.

**Acceptance:** the threat model exists; authorization and injection negative tests pass; secrets and dependency scans are recorded; headers and transport are verified on the deployed shape; unresolved critical/high findings block completion; the report states what was not tested.

### FR-41: Work decomposition, per-task approval, and handoff readiness (P0)

Every approved project begins with a **todo list derived from the owner's request**. Every requested deliverable must appear as a concrete task; there is no “miscellaneous” bucket and no silent omission. Each task is the smallest independently reviewable unit of work, not an arbitrary time slice. A website, for example, is decomposed into initialization, shell/navigation design, each page or section, data or CMS wiring, tests, deployment preparation, and handoff as separate tasks.

Each task records: ID, deliverable, files or areas, acceptance command, evidence, dependencies, rollback note, estimated effort, approval owner, and status. The task is done only when its acceptance and evidence pass. The next task does not start until the current task is accepted and explicitly approved by the owner or the approver named in the approved plan. Trivial mechanical substeps may be grouped only with explicit approval.

File count, time, host runs, and spend are **safety ceilings**, not the decomposition method. Do not split work merely because a clock expired, and do not merge unrelated work merely because it touches few files. If a task cannot be stated with one clear acceptance test, it is still too large and must be split by work.

Every checkpoint records the diff, tests, evidence, learning updates, new risks, and the next action. Stop and ask when:

- a security, credential, destructive, deployment, or public-release boundary is reached;
- the same failure repeats twice without new evidence;
- the plan’s scope or stack must change;
- a safety ceiling or approved budget is reached;
- required data, access, or approval is missing.

Before handoff, verify: no unresolved TODO or placeholder, every todo item is accepted or explicitly deferred, dependencies and versions are recorded, tests and known limits are current, docs and commands match behavior, deployment and after-sales data exist, rollback is possible, and another agent can resume from repository state.

**Acceptance:** every owner ask maps to a todo item; no task is skipped; no task starts before its predecessor is accepted and approved; a task without one clear acceptance is split; the two-failure rule produces a replan rather than an endless retry; the handoff checklist is complete; a cold-start agent can resume without private chat history.

### FR-42: Teaching contract and competency evidence (P0)

Aperio acts as the teacher for every executing agent. Before work, it must explain the stack, the official sources, the design and security rules, the task boundaries, and the evidence required. The agent must return a concise teach-back and a small local proof. The competency record identifies what was learned, what remains uncertain, and what the agent is not allowed to do without help.

Teaching is not a document dump. A teach-back that repeats headings without demonstrating understanding fails. If the agent cannot complete the proof, Aperio narrows the task, requests a missing tool or source, or stops. A different host may resume from the competency record.

**Acceptance:** a task cannot start without a teach-back and proof; a fabricated or copy-pasted teach-back is rejected; the competency record survives restart; the next agent can see exactly what was and was not learned.

---

## 8. Non-functional requirements

### NFR-01: Reliability

Critical commands fail closed on malformed input, unreadable files, missing dependencies, stale state, invalid evidence, interrupted writes, and unavailable hosts. No checker prints pass when it skipped all checks, ran zero tests, or could not read its target.

### NFR-02: Portability

No hard-coded `/Users/...`, `/Volumes/...`, `/private/var/...`, home, cache, model, or checkout path. Test from a clean clone in another directory. Cover Bash and PowerShell where both are claimed.

### NFR-03: Security and privacy

Least privilege, default-deny write boundaries, no secrets in logs, client separation, explicit consent for sensitive tools, input validation, output safety, authentication and authorization, path and symlink protections, and safe subprocess invocation. A path helper is not an OS sandbox.

### NFR-04: Auditability

Every significant action has a task ID, actor, reason, timestamp, plan revision, paths, result, and evidence pointer. History is append-only where policy requires; corrections are explained.

### NFR-05: Performance and cost

Keep context compact. Delegate broad reading. Parallelize only safe independent work. Prefer free or already-paid tools. Do not create a new spend without approval. Measure wall-clock time and rework, not subagent count.

### NFR-06: Usability

Owner-facing gates and reports use plain language, show the decision, the reason, the evidence, and the next action. The owner should not need to inspect fifty files to know what happened.

### NFR-07: Maintainability

One canonical source should generate or validate duplicate registries and docs where feasible. Avoid giant modules with mixed responsibilities. Do not refactor stable code for style during a delivery task.

### NFR-08: Accessibility and design quality

Accounts for mobile, keyboard, contrast, reduced motion, touch targets, loading, error and empty states, and asset performance. Design gates are conditional on the approved stack and design contract.

---

## 9. Security and approvals

### 9.1 An agent may decide inside an approved plan

- internal module layout, test names, ordinary data structures, and CLI flags;
- choice among previously approved free tools and models, based on verified availability;
- fixes to code-owned defects inside authorized paths, with tests retained or strengthened;
- bounded retries for transient failures, with a record;
- marking a blocked task and continuing unrelated approved work;
- proposing new work for the queue without widening the active task.

### 9.2 Only the owner may approve

- public visibility, history rewrite, force-push, remote branch deletion, release, deployment, or publication;
- destructive data changes or actions that can overwrite user content, client data, global installs, uncommitted work, or protected files;
- spending money, creating paid accounts, obtaining credentials, or adding a paid provider;
- weakening, relabeling, or bypassing a security, approval, CI, or governance gate;
- enabling P17 real-agent execution while its security gates are open;
- changing client scope beyond the accepted plan or treating an assumption as an owner decision.

### 9.3 Keep-working boundary

Continue all authorized, unblocked work. Do not stop for routine choices already covered by the plan. Do not bypass explicit approval, security, or protected remote operations.

---

## 10. Definition of Done

A task is `DONE` only when all applicable statements are true:

1. The requirement is recorded and mapped to the approved plan.
2. The implementation exists in the intended repository and path.
3. The normal workflow calls it; no dead module is presented as a feature.
4. Happy path and relevant failure paths pass objective tests.
5. The test exercised the required behavior; no no-op, vacuous, stale, zero-test, or mock-only result is called full verification.
6. A separate reviewer inspected the diff and reproduced the decisive behavior, or the review blocker is recorded and policy permits the alternative.
7. Documentation and commands match actual behavior.
8. For a client site, the target project renders and runs; routes, forms, auth, data, and CMS actions work; mobile and desktop were inspected; SEO ran against built output; the result is maintainable.
9. Evidence is saved with commands, exit codes, environment, results, screenshots where relevant, and limits.
10. No open P0 or P1 blocker is disguised as complete; no approval-required action was performed without approval.
11. Current state, queue, and handoff are updated so a cold-start host can resume.
12. The owner summary states what is delivered, verified, not verified, blocked, deferred, and what still needs owner action.
13. The learning dossier, teach-back, local proof, and competency record are current for the exact stack.
14. Every installed MCP, package, CLI, or skill has provenance, permission, version, and fallback recorded; a created skill has a passing test.
15. The applicable application-class design contract, reference board, and review checklist exist; no award is claimed without evidence.
16. The threat model exists and no unresolved critical or high security finding is hidden.
17. Every todo task is accepted or explicitly deferred; no task started before its predecessor was approved; safety ceilings were respected.
18. Pre-flight, deployment, and after-sales data are complete, or the missing item has a dated owner waiver.

---

## 11. Acceptance scenarios

### E2E-1: Real project from ask to delivery

Use an owner-selected real project, separate from Aperio. Start from the actual entrypoint, capture the ask, research the project, produce Gate 0, get scope and plan approval, build the slices, verify independently, and deliver the target project. Use the owner's acceptance checklist, not a generic demo. Do not mark complete if the target is unchanged or uses the wrong stack.

Evidence: initial state, accepted scope, plan, diff, running build, mobile and desktop screenshots, tests, CMS edit/publish/rollback if required, SEO output if required, independent review, and ask-to-result matrix.

### E2E-2: Cold-start continuity

Stop one host after a plan and partial implementation. A different host resumes from repository state without re-asking answered questions, changing unrelated files, or losing approvals. It reports stale or contradictory state.

### E2E-3: Live mesh

Two actual hosts exchange a task and reply in both directions. The mediator records the result. Restart does not lose messages. An inaccessible host or database produces a truthful failure.

### E2E-4: Parallel build and independent audit

Split an approved task into at least two safe independent chunks, run them on available permitted hosts or models, integrate, and use a different host as reviewer. Show chunks, duration, conflicts, and integration. If parallelism is not beneficial, record why.

### E2E-5: Prompt rewrite transparency

Invoke the prompt modifier through every supported surface. Prove whether it used a template, the host, or an external model. Show original, rewrite, additions, removals, and the exact command. Dry-run executes nothing.

### E2E-6: Gate fails when broken

For each critical gate, break its checking path in a fixture and prove the gate fails. Restore it and prove pass. Do not alter protected baselines or weaken security.

### E2E-7: Fresh clone and new machine

Clone into a different path with a clean environment and no optional agents. Run setup, doctor, and core tests. Verify no absolute-path assumptions. Unsupported hosts are reported as unsupported, not green.

### E2E-8: Privacy before publication

Scan worktree, tracked content, reachable history, branches, and retained artifacts with the approved identity and secret tools. Confirm remote branch history and worktrees are clean. A clean scan is not publication approval.

### E2E-9: New stack learning, tooling, and skill creation

Give the system a task on a stack with no bundled skill. Prove that it refuses to code before producing the learning dossier, cites official sources, records MCP/package/skill provenance and permissions, creates a tested project-scoped skill if none exists, and completes a local proof. Remove or tamper with a source and prove the gate fails rather than filling the gap from memory.

### E2E-10: Design, security, chunking, and handoff

Run one vertical slice through the application-class design contract, threat model, and a todo list of minimal tasks. Force a task that is too coarse and a repeated failure; prove the system splits it by work, pauses at checkpoints, gets per-task approval, and replans rather than retrying forever. Verify the final handoff contains pre-flight, deployment, after-sales, rollback, known limits, and a cold-start competency record.

---

## 12. Roadmap

### P0: Make the current product work

1. Prove the installed entrypoint and required rule files on the owner's host.
2. Reconcile current state, queue, plan, owner ledger, and archived handoffs.
3. Build the ask-to-requirement-to-code-to-test-to-evidence matrix.
4. Repair the core loop: intake, plan, approval, bounded execution, independent verification, evidence, handoff.
5. Prove host and model routing and a real multi-host fan-out without Kimi; resolve OpenCode before dispatch.
6. Prove bidirectional mesh with real hosts, restart, and migration.
7. Complete prompt rewrite transparency and model mode labeling.
8. Deliver one real selected project end to end.
9. Enforce the learning dossier, teach-back, local proof, and competency record before plan approval.
10. Enforce toolchain provenance and project-scoped skill creation.
11. Enforce todo decomposition and per-task acceptance/approval before the next task.
12. Re-run tests and validators from the current checkout; label sandbox denials and stale checks.
13. Keep privacy and release operations blocked until the owner approves after evidence.

### P1: Make specialist code useful

1. Gate 0 and the Studio Council in the real project lifecycle.
2. Stack- and domain-aware design policy; Lumos opt-in; verify the chosen framework.
3. CMS editor, media, blocks, roles, persistence, revisions, publishing, rollback in real projects.
4. SEO audits and growth packs against built output and CMS drafts.
5. Design, viewport, mobile, accessibility, and product-proof gates in the delivery path.
6. Progress dashboard, heartbeat, status, cross-host handoff.
7. Installer, updater, uninstaller, recovery, and cross-platform parity.
8. Registry freshness and model selection by capability and cost.
9. Application-class design school, pre-flight/deployment/after-sales packs, and security threat-model gate.
10. Close the P1 audit-derived hardening backlog in `docs/PRD.md` Appendix A, starting with Z-02, Z-03, Z-04, and Z-05.

### P2: Expand

1. More domain blueprints and CMS features after the real-project loop passes.
2. Asset and video workflow expansion.
3. Learning factory and approved regression generation.
4. Performance and parallel speed measurement.
5. Broader packaging or public distribution only after security, privacy, install, portability, and release gates pass with owner approval.

---

## 13. Metrics

Track from actual runs, not estimates:

- ask coverage: in-scope requirements mapped to delivered behavior and evidence; target 100% before project completion;
- false-done rate: items marked done without current evidence; target 0%;
- gate integrity: declared hard gates with a call path and positive and negative tests; target 100% for gates described as enforced;
- real-project acceptance: project-specific criteria satisfied or owner-approved exclusions; target 100% of approved scope;
- independent review coverage: meaningful slices reviewed by a separate verifier; target 100% unless a documented policy exception exists;
- continuity: cold-start hosts resume without re-asking answered questions; target 100% in acceptance runs;
- mesh reliability: successful send, read, reply, restart retrieval per host pairing; never generalize beyond tested cells;
- fan-out: chunks parallelized, completed, failed, wall-clock, conflicts, integration overhead; not subagent count;
- prompt transparency: every rewrite shows mode and a full diff; target 100%;
- CMS functional coverage: edit, persist, render, publish, deny, media, revision, rollback; target 100% for required CMS scope;
- learning coverage: exact stack, official sources, dedicated skill/MCP status, local proof, and teach-back present before plan approval; target 100% of approved tasks;
- toolchain provenance: every installed or created tool has source, version, license, permissions, and fallback; target 100%;
- design coverage: design contract, reference board, class checklist, mobile/desktop inspection, and accessibility/performance checks; target 100% of applicable surfaces;
- security coverage: threat model, negative tests, secret/dependency scans, and unresolved critical/high findings; target zero hidden high-risk findings;
- chunk compliance: every owner ask appears in the todo list; tasks are accepted and approved one by one; safety ceilings are respected; target 100% or an explicit replan;
- handoff readiness: pre-flight, deployment, after-sales, rollback, docs, and cold-start resume data present; target 100% for production handoffs;
- test discovery integrity: no zero-test pass, no omitted module without a decision, counts match actual discovery;
- portability: explicit pass, fail, or unavailable per OS and shell;
- privacy: zero unauthorized identifiers or secrets in the required scan scope before publication; a clean scan is not approval;
- owner clarity: the final report answers what works, what does not, and how to verify it without reconstructing logs.

---

## 14. Source of truth

| Artifact | Purpose | Canonical path | Rule |
|---|---|---|---|
| Product requirements | What Aperio must do | `docs/PRD.md` | One current specification; amendments through a decision record |
| Handoff | Current entry point for the next agent | `HANDOFF.md` | Repository-only handoff; never rely on a chat transcript |
| Owner requests | What the owner asked and where it landed | `docs/OWNER-REQUESTS.md` | Reconstructed request ledger; code and STATUS win on conflict |
| Start page | Minimal boot guide | `START-HERE.md` | Links to current state; no stale install claims |
| Current state | What is true now | `docs/STATUS.md` | One authoritative status page; re-measure before relying on it |
| Active queue | Tasks and statuses | `.aperio/queue.json` (local) | `DONE` only after acceptance and review; do not commit project state |
| Active plan | Approved scope and sequence | `.aperio/plans/` (local) | One approved plan per task; changes are traceable |
| Owner input | Original instructions | `aperio ask` ledger (`.aperio/asks.jsonl`, local) | Owner-authored; agents do not rewrite without permission |
| Decisions and approvals | Owner-authorized actions | `docs/DECISIONS.md` and the plan approval record | Agent reports are not approval |
| Laws and enforcement | Rule, enforcement path, negative test | `src/aperio/policy.py`, `src/aperio/runner.py`, `tests/` | A hard rule requires a working check |
| Reports | Current evidence and known limits | `docs/STATUS.md` | Dated, measured, linked to a command or artifact |
| Communications | Peer messages | `.aperio/mesh/messages.sqlite3` (local) | Local durable store and mediator implemented; distributed transport not built |
| Tests | Executable checks | `tests/` | Run the suite; do not cite a file name as proof |
| Source | Implementation | `src/`, `skill/`, `install.sh` | No duplicate implementation unless mechanically checked |
| Evidence | Requirement-specific proof | `.aperio/evidence/` (local), target project | Each claim maps to a real file or output |
| Archive | Pre-v2 material | `docs/ARCHIVE.md` and the external archive | Preserve auditability; no casual deletion |

---

## 15. Current v2 evidence baseline

Measured on 2026-10-26 in the fresh v2 tree. Re-measure before relying on any row.

| Item | Result | Command or evidence |
|---|---|---|
| Core unit tests | **59 passed** | `PYTHONPATH=src python3 -m unittest discover -s tests -v` |
| Adapter tests | **24 passed** | same command; `tests/test_adapter.py` |
| Drift tests | **5 passed** | same command; `tests/test_drift.py` |
| Mesh tests | **5 passed** | same command; `tests/test_mesh.py` |
| Mediator tests | **6 passed** | same command; `tests/test_mediator.py` |
| CLI tests | **16 passed** | same command; `tests/test_cli.py` |
| Learning tests | **10 passed** | same command; `tests/test_learning.py` |
| Skill tests | **9 passed** | same command; `tests/test_skillgen.py` |
| Toolchain tests | **8 passed** | same command; `tests/test_toolchain.py` |
| Dashboard tests | **7 passed** | same command; `tests/test_dashboard.py` |
| Security tests | **8 passed** | same command; `tests/test_security.py` |
| Todo tests | **6 passed** | same command; `tests/test_todo.py` |
| Readiness tests | **5 passed** | same command; `tests/test_readiness.py` |
| Discovery tests | **25 passed** | same command; `tests/test_discovery.py` |
| Inspection tests | **14 passed** | same command; `tests/test_inspect.py` |
| Evidence tests | **6 passed** | same command; `tests/test_evidence.py` |
| Audit tests | **16 passed** | same command; `tests/test_audit.py` |
| Repo tests | **4 passed** | same command; `tests/test_repo.py` |
| Installer tests | **23 passed** | same command; `tests/test_installer.py` |
| Total test suite | **373 passed** | same command |
| CLI end-to-end | **passed**: unapproved run refused, approved run applied, acceptance passed, review confirmed, done | `tests/test_cli.py::test_full_cli_flow` |
| Demo project | **applied, verified, reviewed, done** | `examples/demo-site-plan.json` through the CLI |
| Rollback | **restores modified files and removes created files** | `tests/test_core.py::test_rollback_restores_modified_and_removes_created` |
| Path traversal / symlink escape | **refused**, including dangling symlink components | `tests/test_core.py` |
| Project state symlink | **refused** when opening a project | `tests/test_core.py::test_state_symlink_is_refused` |
| State file symlink | **refused**; external file untouched | `tests/test_core.py::test_state_file_symlink_is_refused` |
| Review tamper | **refused** if the reviewer changes the project | `tests/test_adapter.py::test_reviewer_cannot_change_the_project` |
| Control-state change | **fails** if a step alters project, queue, plan, or evidence | `_hash_control_state` |
| Protected-path glob | **fails** when a glob matches a protected path | `tests/test_core.py::test_glob_cannot_reach_a_protected_path` |
| Task ID traversal | **refused** for persisted task ids | `tests/test_core.py::test_task_id_traversal_is_refused` |
| Installer prefix canonicalization | **refused** when `/..` resolves to `/` | `tests/test_installer.py::test_prefix_that_resolves_to_root_is_refused` |
| Host deletion | **rejected** | `tests/test_adapter.py::test_host_deletion_is_rejected` |
| Undeclared shell write | **detected and failed** | `tests/test_core.py::test_command_outside_write_is_detected` |
| Verification timeout | **cannot pass**, even with `expected_exit: 124` | `tests/test_core.py::test_verification_timeout_cannot_pass` |
| Artifact binding | **review and done refuse** if the project changed after verification | `tests/test_core.py` artifact tests |
| Review evidence | **done refuses** if review evidence is missing | `tests/test_core.py::test_finish_requires_review_evidence` |
| Installer dry-run uninstall | **keeps files** and reports would-remove | `tests/test_installer.py::test_dry_run_uninstall_removes_nothing` |
| Installer user-file preservation | **uninstall keeps unrelated files** | `tests/test_installer.py::test_uninstall_preserves_user_files_in_the_skill_directory` |
| Self-approval | **refused** when approver equals run actor | `tests/test_core.py::test_approver_cannot_be_the_run_actor` |
| No-op acceptance | **refused** for `true` and `exit 0` | `tests/test_core.py::test_noop_acceptance_is_refused` |
| Acceptance mutation | **fails verification** if a check changes a project file | `tests/test_core.py::test_acceptance_check_cannot_mutate_the_project` |
| Installer dry run | **no files written** | `tests/test_installer.py::test_dry_run_writes_nothing` |
| Installer idempotency | **second run leaves one skill** | `tests/test_installer.py::test_install_is_idempotent_and_uninstalls` |
| Installer uninstall | **removes binary, library, and skill** | same test |
| Host detection | **reports installed names and versions** | `aperio hosts`; presence is not permission |
| `/aperio` entry point | **installed as a skill**; host load not verified; no duplicate command file | `~/.claude/skills/aperio/SKILL.md` |
| Skill file | **installed**; host load not verified | `~/.claude/skills/aperio/SKILL.md` |
| Claude host adapter | **real dispatch proven on current code**: produced `site/index.html`, acceptance passed, review confirmed, done | task `task-17fd7a83a6`, run `run-d8e491aeb4`, review `review-5cb1b3585d` |
| Host change outside plan | **rejected before apply** | `tests/test_adapter.py::test_host_change_outside_plan_is_rejected` |
| Host change outside step writes | **rejected before apply** | `tests/test_adapter.py::test_host_change_outside_step_writes_is_rejected` |
| Host symlink | **rejected without reading the target** | `tests/test_adapter.py::test_host_symlink_is_rejected` |
| Goose host adapter | **command path tested** with a fake binary; live call blocked by local bridge HTTP 500 | `tests/test_adapter.py::test_goose_adapter_builds_a_run_command` |
| dsh host adapter | **command path tested** with a fake binary; live call blocked by missing `RIVER_API_KEY` | `tests/test_adapter.py::test_dsh_adapter_builds_a_headless_command` |
| Codex host adapter | **real Codex built a page**; fresh Claude review confirmed and the task finished | task `task-116b1d078e`, run `run-d86056766a`, review `review-5fcf72b5e9` |
| Codex host review | **real Codex reviewer confirmed** a verified task | review `review-138f0f9a9f` |
| Fresh-context host review | **real Claude review confirmed** a verified task from a brief-only workspace | review `review-973d3a5fb8` in the temporary goldfish project |
| Documentation drift | **clean**: links and inline paths resolve | `aperio drift` |
| Local message store | **implemented**; real Claude and Codex processes read and replied | `tests/test_mesh.py`; `docs/HOST-PROOFS.md` |
| Mediator disposition | **implemented** from the current task state and latest evidence | `tests/test_mediator.py` |
| Host dispatch beyond Claude/Codex/dsh/Goose | **deferred**: adapters for OpenCode, KiloCode, Cline, and agy are command-shape tested; live proof is not a release blocker | `src/aperio/adapter.py`, `tests/test_adapter.py::test_extra_host_adapters_build_commands` |
| Distributed/live two-host mesh | **not built**; local durable message store and mediator are implemented | `src/aperio/mesh.py`, `src/aperio/mediator.py` |
| CMS / SEO / Astro delivery | **out of scope**; delivered by a target project, not Aperio | `README.md` scope decision |
| OS sandbox | **optional**; `plan.sandbox: true` uses `sandbox-exec` on macOS or `bwrap` on Linux for shell/read steps and host dispatch (the host's writable boundary is its disposable workspace) and fails closed if unavailable. | `src/aperio/sandbox.py`; `tests/test_core.py::test_sandboxed_run_records_active_isolation`; `tests/test_adapter.py::test_sandboxed_host_step_records_active_isolation` |
| Native Windows execution | **deferred**; `install.ps1` passes under `pwsh` 7.6.7 on macOS | `tests/test_installer.py::test_powershell_installer` |
| Public repository | **public** at `https://github.com/Aperio-Studios-Private/Aperio-Orchestrator` | `gh repo view Aperio-Studios-Private/Aperio-Orchestrator --json visibility,url` |
| GitHub Actions | **tests pass** on Python 3.10, 3.12, and 3.14 | [tests workflow](https://github.com/Aperio-Studios-Private/Aperio-Orchestrator/actions/workflows/tests.yml) |
| Remote deployment | **out of scope**; Aperio records readiness and hands off, but does not hold provider credentials or deploy | `README.md` scope decision |
| External audit of the whole repo | **seven Codex passes and one Claude audit; Claude F1/F3/F4/F5 fixed, F2 documented; owner approval pending** | `docs/AUDIT-CODEX-20261026.md`, `docs/AUDIT-CLAUDE-20261026.md` |

The v2 tree is intentionally small. It does not inherit the old repository's test count, branch state, or reports.

## 16. Review of the two source PRDs

### 16.1 What the Gemini v5.0 draft contributes

- A clear product vision and owner persona.
- Specific niches and negative briefs for clinic, e-commerce, news, ERP/CRM, portfolio, and desktop.
- Concrete installer, host bootstrapper, Lumos, CMS, SEO, and prompt-interceptor requirements.
- Useful detail on the anti-slop design problem.

### 16.2 What must be corrected in the Gemini draft

- It presents target-state claims as achieved: "100% idempotent", "beats WordPress", "30+ supported hosts". These are requirements, not evidence.
- It makes design rules universal: mandatory `100dvh`, 30% negative space, no Inter/Roboto, hard 90+ Lighthouse. The canonical contract makes them project-specific unless the approved design and performance contract says otherwise.
- It fixes hosts to roles (`agy` research, `claude` visual, `codexx` backend, `goose` QA). Hosts change; roles must be capability-based.
- It attributes Lumos to a person and assumes one API. The repository has a custom Lumos variant that is not compatible with the external framework. The project must record which implementation it uses and never mix them.
- It says every site or app must ship a CMS. CMS is conditional on the project.
- It treats "never WordPress or Shopify" as a product law. That is an owner preference for Aperio-built projects, not a universal product requirement.
- It specifies a Python TUI file that may not be the current implementation. The canonical contract requires the behavior, not a particular filename.

### 16.3 What the APERIO PRD v1.0 contributes

- Rigorous separation of implemented, wired, verified, and approved.
- Strong acceptance, negative-test, evidence, privacy, and release-boundary language.
- A complete requirement inventory and end-to-end scenarios.
- Honest treatment of stale reports and missing client targets.

### 16.4 What must be corrected in the APERIO PRD

- At 962 lines and 119 KB, it is too long to be the daily working contract. This document keeps the normative core and moves inventory detail to the repository map.
- Several snapshot counts are stale: it cites 2,973 tests and 102 pins; the old repository's measured baseline at the time was 3,039 tests and 106 pins. V2 does not inherit those counts; its measured baseline is in `docs/STATUS.md`.
- It repeats open owner questions that already have recorded defaults; this document resolves them unless the owner objects.
- It leaves the real target project undefined. E2E-1 must use an owner-selected target; the Aperio repository cannot substitute for it.
- It sometimes states design constraints as universal. They remain conditional on the approved project contract.

### 16.5 Canonical decisions

- One PRD is the contract. The two drafts are historical inputs.
- Roles are capability-based; host names are assignments, not definitions.
- CMS, Lumos, Lighthouse 90+, full-canvas design, and type locks are conditional on the approved project contract.
- No status is inherited from a document. Current evidence is re-measured.
- The mediator owns the queue and integration. Builders and auditors own their assigned slices and evidence.

---

## 17. Requirement traceability

Every completion report includes this table, filled from actual work:

> Rows with empty cells are not separately traced in this table. An empty cell is **not** a claim of implementation or completion. Use `docs/STATUS.md` and `HANDOFF.md` for the measured state; use `docs/OWNER-REQUESTS.md` for the owner request trail.

| Requirement | Owner ask | Implementation path | Wired call site | Test or live evidence | Status | Reviewer |
|---|---|---|---|---|---|---|
| FR-01 | entrypoint | | | | | |
| FR-02 | resume | | | | | |
| FR-03 | ask ledger | | | | | |
| FR-04 | intake | | | | | |
| FR-05 | research | | | | | |
| FR-06 | stack | | | | | |
| FR-07 | plan gate | | | | | |
| FR-08 | queue | | | | | |
| FR-09 | traceability | | | | | |
| FR-10 | hosts/models | | | | | |
| FR-11 | fan-out | | | | | |
| FR-12 | mesh | | | | | |
| FR-13 | mediator | | | | | |
| FR-14 | audit | | | | | |
| FR-15 | evidence | | | | | |
| FR-16 | real delivery | | | | | |
| FR-17 | design | | | | | |
| FR-18 | mobile/a11y | | | | | |
| FR-19 | CMS | — | — | — | — | EXCLUDED WITH OWNER REASON |
| FR-20 | visual editor | — | — | — | — | EXCLUDED WITH OWNER REASON |
| FR-21 | media | — | — | — | — | EXCLUDED WITH OWNER REASON |
| FR-22 | CMS SEO | — | — | — | — | EXCLUDED WITH OWNER REASON |
| FR-23 | revisions | — | — | — | — | EXCLUDED WITH OWNER REASON |
| FR-24 | blueprints | — | — | — | — | EXCLUDED WITH OWNER REASON |
| FR-25 | SEO pack | — | — | — | — | EXCLUDED WITH OWNER REASON |
| FR-26 | prompt | | | | | |
| FR-27 | learning | | | | | |
| FR-28 | status | `src/aperio/dashboard.py` | `aperio dashboard` | 7 dashboard tests; `--output` is no-clobber (`--force` overwrites) and cannot reach `.git`/`.aperio` or escape the project; generated HTML | IMPLEMENTED | |
| FR-29 | git/CI | | | | | |
| FR-30 | install | | | | | |
| FR-31 | portability | | | | | |
| FR-32 | reports | | | | | |
| FR-33 | hygiene | | | | | |
| FR-34 | assets | | | | | |
| FR-35 | P17 | | | | | |

Allowed status values: `IMPLEMENTED`, `WIRED`, `VERIFIED`, `DELIVERED+VERIFIED`, `DELIVERED+NOT VERIFIED`, `PARTIAL`, `NOT IMPLEMENTED`, `BLOCKED`, `EXCLUDED WITH OWNER REASON`.

---

## 18. Completion report format

Every substantive report has these headings:

1. Requested outcome, quoted or precisely summarized.
2. Scope and constraints: target repository, allowed paths, out-of-scope items, approvals.
3. What changed: exact files and user-visible behavior.
4. Implementation details: entrypoint, call path, data flow, failure handling.
5. Verification: commands, exit codes, counts, environment, screenshots or links, independent reviewer and verdict.
6. Ask-to-result matrix.
7. Known limitations: untested areas, environmental limits, open defects.
8. Recovery and rollback.
9. Next tasks with IDs and priority.
10. Owner action required, with a recommendation and consequence.

A report without the delivered code and verified behavior is not a successful build.

---

## 19. Immediate execution sequence

1. Rebaseline the checkout: root, status, HEAD, changed files, concurrent leases, Python and OS, test discovery.
2. Prove the installed entrypoint on the owner's host. Fix or document the boot failure before claiming a governed build.
3. Build the requirement coverage table from the owner ledger and current directives.
4. Recompute the law and gate matrix: runtime block, CLI validator, CI check, instruction only, or not implemented; include a negative test.
5. Reproduce the primary delivery failure on an owner-selected target, without copying client data.
6. Fix the smallest set of issues that prevents the normal entrypoint from fulfilling a request.
7. Run one vertical slice through the full path: request, dossier, approved plan, implementation, running product, tests, independent review, evidence, handoff.
8. Fan out independent work only after host availability and permission are verified. Never Kimi. Resolve OpenCode before dispatch.
9. Run the relevant full battery and real CI where available. Label sandbox denials, skips, unknowns, and stale results.
10. Write the report, update canonical state and queue, and state the next unblocked task and blockers.

Do not begin with a broad audit or a new feature. The first priority is a working core loop with evidence.

---

## 20. Open owner decisions

These are recorded with defaults so work can continue. The owner can override any of them.

1. **First real target project.** Needed for E2E-1. Default: use the owner's selected project, keep its code and data outside this repository, and capture only sanitized acceptance criteria here.
2. **Lumos implementation.** Default: use whichever implementation the target project's approved stack requires; never mix upstream and custom APIs.
3. **OpenCode.** Default: do not dispatch until the conflict between older "do not use" and newer allowlist entries is resolved by the owner.
4. **Public release.** Default: stay private until the owner approves after a clean history and branch audit. No force-push without explicit approval.
5. **Budget.** Default: zero new spend on models, APIs, hosting, or dependencies unless the owner approves an exception.
6. **Tool installation consent.** Default: project-scoped MCPs, packages, and skills may be installed after provenance and security checks when they need no credentials, elevated permissions, payment, or broad network access. Global installation, credential-bearing tools, paid services, and elevated permissions require explicit owner approval.
7. **Task decomposition.** Default: derive a todo list from the owner's request, split into the smallest independently reviewable work units, and require acceptance plus explicit approval before the next task. Do not split by an arbitrary clock; file, time, host-run, and spend limits are safety ceilings only.
8. **“Award-winning” standard.** Default: a researched design contract, reference board, originality review, accessibility, performance, and real mobile/desktop inspection. Never claim an award or a prize without evidence.
9. **Surface scope.** Default: teach the principles for marketing sites, web apps, CMS, CRM/ERP, mobile, and desktop; implement and prove only the surface classes the owner selects for the current project.

---

## 21. Final acceptance statement

Aperio succeeds when the owner can state a concrete outcome, leave the system to carry out approved work, return to a real artifact that matches the requirements, inspect what changed, see actual tests and independent review, and hand the work to another host without repeating himself.

Aperio must be able to explain any gap between the ask and the result. It must not say "done" while that gap remains.

The north-star question for every agent is:

> Does the delivered behavior in the intended repository satisfy what the owner actually asked for, and can another party reproduce the proof?

If the answer is no or unknown, Aperio is not done.

---

## Appendix A. ZCode audit-derived backlog (2026-10-26)

Source: external ZCode audit dated 2026-10-26 (archived outside the
repository; it is a historical snapshot, not a repository document). The
report is a snapshot: its `158` test count predates the current tree, and its
per-module table lists 15 inspection tests where the tree has 14. The findings
below were re-checked against code and commands.

Status vocabulary: **Planned** means recorded, not implemented. An item moves to
**Implemented** only when code exists, and to **Verified** only when a
reproducible test or command proves it. Listing an item here is not a claim.

### A.1 Findings and dispositions

| ID | Finding | Disposition | Evidence |
|---|---|---|---|
| Z-D1 | Directory-form step writes rejected files created by the step | **Verified fixed** | `27dcfb7`; `test_directory_write_accepts_files_created_by_a_run` |
| Z-D2 | `review --host` help advertised unsupported adapters | **Verified fixed** | `890eff6`; `test_review_help_lists_only_supported_hosts` |
| Z-D5 | Glob-form step writes rejected files created by the step (found by the 2026-10-27 independent re-audit) | **Verified fixed** | A/B: new tests fail on the pre-fix runner; `test_glob_write_accepts_files_created_by_a_run`, `test_glob_write_still_rejects_files_outside_the_pattern` |
| Z-D6 | Glob matching crossed `/`: `out/*.html` accepted `out/sub/escape.html` although `Path.glob` rejects it (found by a live Codex host review, task-sprint1) | **Verified fixed** | A/B: `test_glob_write_does_not_cross_directories` fails on the fnmatch version; segment-wise `_glob_matches` in `src/aperio/runner.py` |
| Z-D7 | STATUS.md per-suite rows drifted from the modules they count (core 50 vs 53, CLI 14 vs 16; found by the same host review) | **Verified fixed** | the doc-count guard now also checks per-suite rows: `tests/test_doc_counts.py::DocCountTests.test_status_per_suite_rows_match_the_measured_modules` |
| Z-D3 | Six stale documentation statements | **Verified fixed** | `0394f84`; `docs/STATUS.md`, `docs/TESTING.md` |
| Z-D4a | Evidence name filter missed `env` and `.env2` | **Verified fixed** | `src/aperio/evidence.py`; expanded refusal test |
| Z-D4b | Mesh `read(mark_read=True)` re-selected after commit | **Implemented** | `src/aperio/mesh.py`; `test_send_read_ack_and_reply` does not yet discriminate (passes against the pre-fix code too) |
| Z-D4c | Windows lock was a silent no-op | **Implemented; native Windows unverified** | `src/aperio/store.py` msvcrt fallback; no Windows runner |
| Z-D4d | Audit status reset after mutation | **Accepted intentional** | `src/aperio/audit.py`; regression test |
| Z-D4e | Codex hard-coded macOS path fallback | **Accepted; PATH checked first** | `src/aperio/hosts.py`; documented |

### A.2 Suggestions and acceptance criteria

Priority is implementation order, not severity. No suggestion below is
implemented merely by appearing in this table.

| ID | Suggestion | Priority | Acceptance proof |
|---|---|---|---|
| Z-01 | Optional OS sandbox for `run`/`read` shell steps and host dispatch using `sandbox-exec` or `bubblewrap` when available; the host's writable boundary is its disposable workspace | P1 | sandboxed and fallback tests; evidence shows whether isolation was active |
| Z-02 | Make `.git` and `.aperio` non-overridable protected paths, independent of project policy | P1 | plan/run attempts through those paths fail even if policy omits them |
| Z-03 | Add a read-only step kind for exploration and audit work | P1 | schema, runner, and policy tests prove the step cannot write |
| Z-04 | Add `type` and `version` to every mutable `.aperio` JSON document | P1 | migration/refusal tests; old and new documents read predictably |
| Z-05 | Make `events.jsonl` the recovery journal and add step checkpoints | P1 | crash/restart test reconstructs the queue or resumes safely |
| Z-06 | Optional MCP server facade with approval elicitation | P2 | tool-list and approval integration test against an MCP client |
| Z-07 | Emit OTel GenAI-named trace data from run events | P2 | trace shape test; no new runtime dependency required |
| Z-08 | Add monotonic evidence versions alongside SHA-256 | P2 | append-only evidence-chain test; tamper detection demonstrated |
| Z-09 | Add a project constitution checked during plan validation | P2 | a plan violating an invariant is refused before approval |
| Z-10 | Add `depends_on` so independent plan steps can run in waves | P2 | deterministic ordering and conflict tests; serial fallback remains |
| Z-11 | Add stall detection that forces replanning after repeated failures | P2 | repeated-failure test produces a replan request, not an endless retry |
| Z-12 | Add replay-based evaluation and an OWASP Agentic Top 10 gap analysis | P2 | recorded task evidence replays in CI; dated gap report |
| Z-13 | Add per-role handoff context filters and read target repository agent instructions during inspection | P2 | builder/reviewer briefs differ by role; inspection records the file |

### A.3 Execution rule

Implement P1 items in the order Z-02, Z-03, Z-04, Z-05, Z-01. Z-02
(non-overridable protected paths), Z-03 (read-only steps), and Z-04 (versioned
state) are verified. Z-05 has queue recovery, run checkpoints, and safe
snapshot-based `aperio resume`; Z-01 is implemented with `sandbox-exec` on macOS
and `bwrap` on Linux, both fail closed when requested but unavailable. The
`bwrap` path still needs a Linux run. Do not start P2 interop or observability
work before these P1 control-plane items are verified.
Each item gets a negative test and a `docs/STATUS.md` row. Owner approval is
still required for deployment, paid hosts, credentials, and public release.

### A.4 Implementation status

| Requirement | Status | Evidence | Remaining work |
|---|---|---|---|
| FR-36 learning dossier | **Implemented and verified** | `src/aperio/learning.py`; 10 learning tests; plan/approve/run gate; plan digest binding | Expire the dossier automatically on version change and re-run the proof |
| FR-37 toolchain and skill creation | **Implemented** | manifest validation, approval-gated argv install with verification, project skills; 8 toolchain tests and 8 skill tests | registry discovery and live host skill loading |
| FR-28 status dashboard | **Implemented** | generated read-only HTML from state; escaped text; protected output path; no scripts or network | live server or interactive controls |
| FR-38 pre-flight, deploy, after-sales | **Implemented for data readiness** | readiness validation; pre-flight plan gate; deployment, after-sales, design, and security facts required at done/handoff | deployment execution is out of scope; provider checks and SLA automation belong to the target project |
| FR-39 application design school | **Partial** | design contract, surface class, references, accessibility, responsive, originality fields | independent design critique and visual review workflow |
| FR-40 security threat model | **Partial** | threat model, trust boundaries, controls, scans, headers, incident fields; high/critical block; local secret scan | dependency-history scan, external penetration testing, and provider header verification |
| FR-41 todo and per-task approval | **Implemented and verified** | todo state machine; plan binding; run revalidation; 6 todo tests | automatic acceptance evidence capture and task-level UI |
| FR-42 teaching and competency | **Implemented and verified** | teach-back, local proof, competency record in the learning dossier | separate teacher UI and host-session loading proof |
