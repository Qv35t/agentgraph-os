# ADR-0004 — OpenCode Owns Its Provider Authentication

Status: Accepted for Phase 3 direction  
Date: 2026-08-11

## Context

AgentGraph OS may use a local OpenCode Server as a transport path to models authenticated inside OpenCode. Copying OpenCode OAuth credentials into AgentGraph would duplicate secret ownership and weaken the trust boundary.

## Decision

AgentGraph communicates only with the configured local OpenCode Server. It does not read, copy, persist, or expose OpenCode's OAuth credential store. Optional Basic Auth protecting the local server is supplied to AgentGraph via local environment configuration only.

## Consequences

- Authentication setup remains an explicit OpenCode prerequisite.
- AgentGraph can use the bridge without becoming a credential extractor.
- OpenCode server API version drift is isolated to the bridge adapter.
