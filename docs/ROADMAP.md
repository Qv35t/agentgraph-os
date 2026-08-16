# AgentGraph OS Roadmap

Phase files define implementation scope and gates. Phases 1-7 are historical implemented work. Phase 8 establishes the approved target baseline; later phases are planned and must not be described as implemented.

## Completed History

### Phase 1 - Foundation

**Status:** DONE. Established the repository, local-first modular-monolith direction, documentation, non-secret configuration, and `pnpm check`.

### Phase 2 - Backend Core

**Status:** DONE. Delivered FastAPI lifecycle APIs, SQLite/Alembic persistence, deterministic LangGraph execution, cancellation, restart-failure recovery, and isolated tests.

### Phase 3 - Model Router and Real LLM Providers

**Status:** DONE. Delivered provider-neutral routing, Ollama, local OpenCode model bridge, optional OpenAI-compatible transport, model metadata, and live Ollama verification. Credential-dependent live checks remain `NOT RUN`.

### Remote Interface Foundation

**Status:** IMPLEMENTED alongside Phase 3. Delivered versioned REST/WebSocket contracts, normalized events and commands, server-side authorization foundation, and process-local approvals. It did not implement remote access.

### Phase 4 - Visual Interface

**Status:** DONE. Delivered the React/Vite browser workspace, persisted visual graphs, run/provider/approval observation, and owner-confirmed manual browser acceptance.

### Phase 5 - Multimodal Vision Layer

**Status:** DONE. Delivered local multimodal observation, secure asset and folder boundaries, persisted analyses, and owner-confirmed acceptance.

### Phase 6 - Lexi Integration

**Status:** DONE. Delivered Lexi workflow, scoped SQLite Memory MVP, controlled Tool MVP, `/lexi` browser UI, live local Ollama smoke, and owner acceptance.

### Phase 7 - Multi-Agent Graph Orchestration and Delegation

**Status:** DONE. Delivered validated static `team-v1` DAGs, persisted child runs, bounded delegation, run-tree inspection, local Ollama smokes, and owner browser acceptance. It did not implement autonomous planning or workers.

## Active Documentation Baseline

### Phase 8 - Future Architecture and Roadmap Baseline

**Status:** DONE. Documentation work, `pnpm check`, and owner cross-document
review are complete.

Objective: establish the Post-Phase-7 future vision, current-versus-target architecture map, risk register, ADR baseline, and dependency-ordered plan.

Deliverables: canonical vision, glossary, specialized target records, updated architecture/status/rules, ADRs, and owner cross-document review.

Dependencies: Phases 1-7 complete.

Security: formalizes authorization-first autonomy, Local Only routing boundary, trust, approvals, credential handling, and recovery risks without implementing them.

Gate: documentation consistency review, `pnpm check`, and owner baseline review passed.

## Planned Implementation Sequence

### Phase 9 - Distributed Core Foundation

**Status:** DONE. Automated verification, same-machine Core/Worker lifecycle,
and owner-confirmed browser Nodes acceptance passed on 2026-08-17. Physical
two-machine validation remains recommended, not blocking.

Objective: introduce a secure, single-writer Core/Node protocol for an explicit Core and registered workers.

Deliverables: persistent node registration/capabilities, Core-owned state boundary, heartbeat/health model, bounded v1 probe dispatch, authorized Nodes API/UI, and observability. Core failover and backup promotion remain deferred.

Dependencies: Phase 8.

Security: node identity and least-privilege capabilities; no public remote control.

Gate: typed protocol/security tests, migrations, frontend checks/build, browser
Nodes acceptance, and same-machine lifecycle acceptance passed. Failover
promotion remains a later phase and is not enabled.

### Phase 10 - Resilience, Checkpoints, and Recovery

Objective: make long-running work recoverable without replaying unsafe effects.

Deliverables: versioned checkpoints, action ledger, incomplete-run recovery, fenced failover procedure, recovery observability, and explicit rollback limits.

Dependencies: Phase 9.

Security: uncertain side effects stop for approval; split-brain and duplicate execution protections are tested.

Gate: fault-injection tests cover restart, interrupted actions, corrupt checkpoints, and safe recovery decisions.

### Phase 11 - Identity, Trust, Approvals, and Credentials

Objective: establish durable user/device trust and action authorization.

Deliverables: durable approvals/grants, trusted-device lifecycle, passkey/2FA design and implementation, audit, credential broker/vault boundary, revocation, and emergency lockdown.

Dependencies: Phases 9-10.

Security: this is the security foundation for privileged automation and broader remote access.

Gate: authorization, expiry, revocation, lockdown, credential-redaction, and adversarial access tests pass.

### Phase 12 - Lexi Orchestrator and Project State

Objective: evolve Lexi from the MVP workflow into a bounded Main Agent for approved project work.

Deliverables: Goals/Projects/Phases/Tasks/Runs hierarchy, brief/detailed plans, bounded temporary graphs, retry/blocker policy, reusable-workflow proposal flow, project-state provenance, and run-history views.

Dependencies: Phases 10-11.

Security: planning cannot expand scope; execution remains subject to approvals and grants.

Gate: end-to-end scoped task tests prove planning, pause/resume decisions, and blocker escalation without implicit user-impacting execution.

### Phase 13 - Persistent Memory Graph and Policy Routing

Objective: add provenance-aware long-term memory and enforce model-routing profiles.

Deliverables: working/episodic/knowledge/personal memory contracts, entity relations, provenance/supersession, memory workspace, Local Only/Balanced/Best Quality/Cheapest policies, cost/limit observability.

Dependencies: Phases 11-12.

Security: Local Only blocks AI-provider data egress; memory remains scoped, reviewable, and untrusted.

Gate: provenance, correction, revocation, poisoned-memory, and denied-egress tests pass.

### Phase 14 - OpenCode First-Class Coder Agent

Objective: coordinate approved development work through an observable Coder Agent without weakening repository or credential boundaries.

Deliverables: project-context handoff, session state/reporting, diff/test/review artifacts, user-decision escalation, cancellation, and multi-session isolation policy.

Dependencies: Phases 11-13.

Security: OpenCode credentials remain owned by OpenCode; repository access and concurrent ownership are bounded.

Gate: isolated repository and conflict tests prove no raw secret access, unauthorized phase progression, or uncoordinated conflicting changes.

### Phase 15 - Device Scheduling and Multi-Node Execution

Objective: schedule approved graph work across registered workers.

Deliverables: capability/resource-aware scheduler, durable device assignment, multi-node graph execution, resource limits, health-aware placement, and cancellation/recovery integration.

Dependencies: Phases 9-14.

Security: workers execute only assigned capability-scoped work and cannot escalate authority.

Gate: deterministic multi-node tests cover assignment, loss, cancellation, recovery, and resource-limit behavior.

### Phase 16 - Voice and Proactive Assistant

Objective: add policy-preserving voice interaction and significant-event recommendations.

Deliverables: push-to-talk/wake-word evaluation, local-first ASR/TTS path, voice identity/approval flow, notification policy, and bounded proactive briefs.

Dependencies: Phases 11-15.

Security: speech is not implicit authorization; proactive recommendations do not perform actions.

Gate: voice and text paths demonstrate equivalent authorization, privacy, and low-bandwidth status behavior.

### Phase 17 - Remote, PWA, Notifications, and Remote View

Objective: safely extend user access beyond the local browser.

Deliverables: installable PWA, Web Push, Telegram fallback/control policy, low-bandwidth mode, notification routing/severity, and read-oriented Remote View.

Dependencies: Phases 11, 15-16.

Security: strong remote identity, device trust, rate limits, audit, and revocation are mandatory; Remote View does not imply control.

Gate: cross-device access, disconnect, revocation, approval, and degraded-network tests pass without a client becoming lifecycle authority.

### Phase 18 - Unified Files and Semantic Search

Objective: provide a truthful logical workspace over registered storage.

Deliverables: physical-location-aware files, registered indexing roots, metadata and content search, semantic search policy, and memory/project links.

Dependencies: Phases 11, 13, 15, 17.

Security: indexing and retrieval honor location, user access, Local Only, and privacy boundaries.

Gate: authorization, remote-location, deletion, index privacy, and stale-index tests pass.

### Phase 19 - Backup and Disaster Recovery Hardening

Objective: validate recoverability of Core data and user-owned state.

Deliverables: backup lifecycle, encryption/key-recovery design, integrity checks, retention, restore tooling, and replacement-machine recovery procedure.

Dependencies: Phases 10-18.

Security: backups and restored credentials use least exposure; restoration is auditable.

Gate: repeated disaster-recovery drills restore a valid isolated environment and truthfully report non-recoverable external dependencies.

### Phase 20 - Advanced Dashboard and Context-Aware UX

Objective: make system state and Lexi understandable without moving authority into the client.

Deliverables: customizable dashboards, widgets, structured UI context, Goals/Tasks/Devices/Memory/Run views, and accessible responsive workflows.

Dependencies: Phases 12-19.

Security: UI context is typed, minimized, and cannot grant permissions or alter server truth.

Gate: current-state, approval, device, and error views remain accurate across desktop and mobile layouts.

### Phase 21 - Higher Autonomy Within Policy

Objective: expand unattended work only after the preceding safety, recovery, identity, observability, and control foundations are proven.

Deliverables: explicit autonomy policies, budgets, delayed/background task controls, automatic safe remediation candidates, and reviewable autonomy audit.

Dependencies: Phases 9-20.

Security: every automated action remains policy-, scope-, approval-, and lockdown-aware; no autonomous scope expansion.

Gate: scenario, fault, adversarial, cost, and owner acceptance tests show safe stop, recovery, and escalation behavior.
