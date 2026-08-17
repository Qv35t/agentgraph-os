# AgentGraph OS Future Vision

Status: approved target architecture. This document is not a statement of implemented functionality.

## North Star

AgentGraph OS is a personal distributed AI operating environment available to its user around the clock from their devices. Lexi is the primary assistant and orchestrator for specialized agents, applications, devices, models, memory, and long-running work.

The intended experience is a user who can inspect or continue a goal from a desktop, browser, PWA, voice interface, or limited messaging channel without losing the work's context, decisions, approvals, or history. A smartphone is primarily a conversational and approval interface, not a mandatory remote desktop replacement.

## Priority Order

Future design and implementation decisions must preserve this order:

1. Never perform an action the user did not authorize.
2. Never lose user data.
3. Remain available when infrastructure permits.
4. Execute work efficiently.
5. Increase autonomy only within explicitly granted boundaries.

Safety and user control take precedence over autonomy, convenience, visual polish, and performance.

## Lexi and Autonomy

Lexi is the Main Agent. It may understand a stated goal, propose brief or detailed plans, construct bounded temporary graphs, select permitted specialized agents, research alternatives, observe progress, retry within a configured budget, and recommend a next action.

Lexi must not create a new user goal, expand task scope, treat a recommendation as authorization, perform a dangerous action without approval, or begin an unapproved development phase. It may recommend proactively, but user-impacting execution remains constrained by task scope, policy, and approvals. See [`architecture/LEXI.md`](architecture/LEXI.md) and [`architecture/SECURITY_AND_TRUST.md`](architecture/SECURITY_AND_TRUST.md).

The target hierarchy is `Goal -> Project -> Phase -> Task -> Run`. A Run keeps its execution history; a reusable Workflow is a saved, versioned template and is not itself a user goal.

## Target Topology

The target primary topology is a NAS-hosted Primary Core with eligible backup nodes, plus worker nodes such as a main PC and laptop. The Core coordinates state, policy, scheduling, and history; workers provide explicitly registered capabilities. The NAS, backup eligibility, scheduling, and failover portions are target architecture; the current Phase 9 foundation has one Core and bounded registered Workers only. See [`architecture/DISTRIBUTED_RUNTIME.md`](architecture/DISTRIBUTED_RUNTIME.md).

## What Exists Today

Phases 1-10 implemented a local-first modular monolith: FastAPI and SQLite persistence, provider-neutral model routing, a browser UI, vision observation, Lexi MVP with scoped SQLite memory and controlled tools, bounded static multi-agent DAGs, a persistent Core-owned Worker registry with safe probe transport, and accepted local durable checkpoint/no-replay recovery. The default service remains loopback-only. The canonical current-state record is [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

## Not Implemented

The following are planned target capabilities, not present runtime guarantees:

- NAS Core deployment, failover, scheduling, checkpoints, resume, rollback ledger, or disaster recovery.
- Durable approvals, passkeys, trusted-device identity, credential broker, secrets vault, or emergency lockdown.
- Autonomous Lexi planning, goals/projects/tasks, reusable workflows, or proactive execution.
- First-class OpenCode coding sessions or multi-session coordination.
- Semantic memory graph, voice, PWA offline support, Telegram control, Remote View, unified files, semantic file search, or advanced dashboard.

The dependency-ordered implementation plan is [`ROADMAP.md`](ROADMAP.md). The high-level current and target boundary map is [`ARCHITECTURE.md`](ARCHITECTURE.md).
