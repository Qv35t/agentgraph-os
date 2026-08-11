# ADR-0003 — Provider-Agnostic Model Router

Status: Accepted  
Date: 2026-08-11

## Context

AgentGraph OS is expected to use local Ollama plus optional GPT/OpenRouter-capable paths. Direct provider branching in agent/runtime code would create vendor coupling and make routing/security hard to reason about.

## Decision

All model execution flows through project-owned model contracts and a ModelRouter/ProviderRegistry. Providers adapt external APIs to normalized project responses/errors.

## Consequences

- Agent/runtime code does not import provider HTTP semantics.
- New compatible providers can be added behind an adapter.
- Routing/fallback policy is centralized and testable.
- Provider discovery/health can be exposed without leaking secrets.
