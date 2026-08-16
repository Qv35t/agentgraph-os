# ADR-0007 - User Authorization Over Autonomy
Status: Accepted target architecture
Date: 2026-08-16

## Context

Lexi needs to plan and support long-running work without extending user intent or silently executing user-impacting actions.

## Decision

Lexi may plan, recommend, research, select permitted agents, and retry within bounded policy. Execution remains limited by explicit user goal/task scope, server-side authorization, approval policy, and scoped temporary grants.

## Consequences

Approval and grant state become durable, auditable target domain concepts. Proactive recommendation does not authorize action. Existing controlled-tool and process-local approval boundaries remain current behavior.

## Alternatives considered

Unbounded autonomous operation was rejected because model confidence does not replace user authorization or safety controls.
