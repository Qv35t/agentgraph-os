# Phase 4 — Visual Interface

## Mission

Build the first usable React/TypeScript + React Flow visual workspace on top of stable backend/model contracts.

## Required scope direction

- frontend application shell;
- typed API client;
- graph canvas;
- typed node/edge configuration;
- create/select/configure agents;
- provider/model selection from backend discovery;
- start/stop run;
- run/agent status and error states;
- save/reload graph configuration through a deliberate backend contract;
- responsive/accessibility baseline;
- frontend tests for critical state transitions.

## Out of scope by default

- memory UI implementation before Phase 5;
- unrestricted tools;
- marketplace/plugin runtime;
- duplicating provider secrets/routing in frontend;
- replacing backend as source of truth for run status.

## Gate

A user can open the local UI, create/configure an agent graph, select a discovered model, start a run, observe result/status/error, stop an active run, and reload durable graph/agent state without the UI becoming runtime authority.

Refine this phase specification against the real Phase 3 API before implementation begins.
