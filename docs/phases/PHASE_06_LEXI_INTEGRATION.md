# Phase 6 — Lexi Integration

## Mission

Use Lexi as the first end-to-end assistant/workflow proving that AgentGraph OS can combine model routing, graph execution, memory, UI observability, and controlled Linux-assistant actions.

## Required direction

- Lexi represented as an AgentGraph agent/workflow rather than a parallel runtime;
- model selection through ModelRouter;
- durable, scoped Memory MVP introduced in Phase 6;
- visible run status/history in AgentGraph UI;
- controlled, typed assistant/tool operations;
- cancellation/timeouts and clear failures;
- local-first end-to-end path;
- integration tests around contracts plus manual real-system acceptance.

## Critical safety rule

Do not solve Lexi PC control by exposing a generic unrestricted shell tool to the model. Add narrow allowlisted capabilities and policy. A generic shell capability requires its own later ADR/security design.

## Gate direction

A representative Lexi workflow can be launched/observed from AgentGraph OS, use a configured local model path, access scoped memory, invoke at least one approved controlled assistant capability, and complete/cancel truthfully.

Exact voice/desktop capabilities should be mapped from the current Lexi project at Phase 6 start rather than guessed now.

## Current implementation status

The backend workflow, SQLite memory MVP, controlled tools MVP, and `/lexi`
browser workspace are implemented. Automated verification passed on 2026-08-15,
the local Ollama smoke passed with `qwen3-4b-nothink:latest`, and owner manual
browser acceptance is confirmed complete. Phase 5 is Vision, not Memory.
