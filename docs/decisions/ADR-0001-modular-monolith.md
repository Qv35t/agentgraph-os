# ADR-0001 — Start as a Modular Monolith

Status: Accepted  
Date: 2026-08-11

## Context

AgentGraph OS spans API, agent runtime, providers, memory, tools, and UI. Splitting these into distributed services during early development would add deployment, consistency, observability, and failure complexity before there is measured need.

## Decision

Build the backend as a modular monolith with explicit internal boundaries. External local services such as Ollama or Qdrant are adapters/capabilities, not reasons to fragment AgentGraph itself.

## Consequences

- Faster local development and testing.
- One core lifecycle and persistence boundary initially.
- Modules must still avoid circular/vendor-specific coupling.
- Service separation may happen later only after measured need and a new ADR.
