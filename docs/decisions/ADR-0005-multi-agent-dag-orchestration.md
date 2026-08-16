# ADR-0005 - Graph-Defined Multi-Agent DAG Orchestration
Status: Accepted
Date: 2026-08-16

## Context

AgentGraph OS needs observable composition of existing agents without creating
a second lifecycle system or unbounded autonomous delegation.

## Decision

Use persisted version-2 `team-v1` DAGs that reference existing agents. Child
work remains normal `AgentRun` lifecycle work owned by `AgentManager` and is
linked with SQLite `run_delegations`. Scheduling, parallelism, context, depth,
and timeout are server-bounded. Team synthesis uses the parent ModelRouter
model route.

## Consequences

The system is local-first, inspectable after restart, and preserves worker
model/memory/tool isolation. It intentionally defers free-form supervisors,
dynamic graph mutation, distributed workers, and checkpoint/resume.

## Alternatives considered

Free-form autonomous swarm planning was rejected because models would control
execution topology. A separate orchestration database/runtime was rejected
because it would duplicate lifecycle authority. SQLite remains sufficient for
the bounded local modular monolith.
