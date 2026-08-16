# ADR-0008 - OpenCode as a First-Class Coder Agent
Status: Accepted target architecture
Date: 2026-08-16

## Context

The existing OpenCode bridge provides model transport but does not represent coding work, repository ownership, sessions, tests, or review in AgentGraph OS.

## Decision

Treat OpenCode as a future specialized Coder Agent coordinated by Lexi through project-owned task and reporting contracts. Preserve ADR-0004: OpenCode owns its provider authentication and AgentGraph never copies its credentials.

## Consequences

Future work must define approved task handoff, session lifecycle, bounded project context, progress/reporting, conflict isolation, cancellation, and multi-session coordination. This does not authorize command execution or implementation in Phase 8.

## Alternatives considered

Treating OpenCode only as an opaque terminal process was rejected because it would not provide safe observable coordination or repository ownership.
