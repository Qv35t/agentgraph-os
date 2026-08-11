# AgentGraph OS — Roadmap

This roadmap preserves the original six-phase project sequence. Phase files define implementation details and gates.

## Phase 1 — Foundation

**Status:** DONE. Foundation artifacts and `pnpm check` were independently
verified on 2026-08-11.

Goal: establish repository, architecture direction, documentation, configuration skeleton, license, CI/developer structure, and empty component boundaries without building product business logic.

Core outputs:

- repository `agentgraph-os`;
- top-level project structure;
- React/React Flow frontend direction;
- Python/FastAPI/LangGraph backend direction;
- local/cloud model configuration direction;
- documentation skeleton;
- Git hygiene and secret exclusions.
- offline Foundation verification through `pnpm check`.

## Phase 2 — Backend Core

**Status:** DONE. Lifecycle API, SQLite/Alembic persistence, deterministic
LangGraph execution, cancellation, restart recovery, tests, and `pnpm check`
were verified on 2026-08-11.

Goal: turn the foundation into a real local backend lifecycle.

Deliver:

- FastAPI application and health endpoint;
- Agent and AgentRun domain/persistence models;
- SQLite + SQLAlchemy + Alembic;
- repositories and `AgentManager`;
- process-local run registry and real cancellation;
- restart recovery;
- real minimal LangGraph execution without LLM dependency;
- lifecycle API and tests.

Gate: `docs/phases/PHASE_02_BACKEND_CORE.md`.

## Phase 3 — Model Router & Real LLM Providers

**Status:** DONE. Provider-neutral routing, Ollama, OpenCode bridge,
OpenAI-compatible transport, LLM graph integration, metadata, and provider
visibility were verified on 2026-08-11. Live Ollama passed; credential-dependent
OpenCode/cloud live checks were `NOT RUN`.

Goal: replace deterministic model behavior with provider-agnostic real LLM execution.

Deliver:

- `ModelRef` and normalized model contracts;
- ProviderRegistry + ModelRouter;
- Ollama provider;
- OpenCode local bridge for already-configured ChatGPT subscription provider auth;
- generic OpenAI-compatible provider / OpenRouter configuration;
- provider health/discovery, timeouts, cancellation, normalized errors;
- run metadata without secret leakage;
- real LLM node inside LangGraph.

Gate: `docs/phases/PHASE_03_MODEL_ROUTER_REAL_LLM_PROVIDERS.md`.

## Phase 4 — Visual Interface

**Status:** PLANNED.

Goal: create the first practical React/TypeScript + React Flow workspace over the stable backend contracts.

Deliver:

- application shell;
- graph canvas and typed node/edge representation;
- agent creation/configuration UI;
- run/start/stop/status observability;
- provider/model selection based on backend discovery;
- error and loading states;
- responsive/accessibility baseline.

Do not move orchestration business logic into the browser.

## Phase 5 — Memory

**Status:** PLANNED.

Goal: introduce explicit local-first memory contracts and retrieval without coupling all runtime code to one vector vendor.

Deliver direction:

- memory domain contract;
- agent/workspace namespaces;
- short/long-term lifecycle policy;
- local vector storage integration (Qdrant direction);
- optional Mem0 integration behind project-owned boundary;
- retrieval injected deliberately into graph state;
- retention/deletion controls;
- deterministic tests with no required cloud service.

## Phase 6 — Lexi Integration

**Status:** PLANNED.

Goal: integrate Lexi as the first real end-to-end assistant/workflow on top of AgentGraph OS boundaries.

Deliver direction:

- Lexi agent/workflow definition;
- model routing through AgentGraph contracts;
- memory integration where approved;
- controlled Linux/assistant tool boundary rather than arbitrary shell;
- observable runs and cancellation;
- frontend representation of the Lexi workflow;
- end-to-end local-first acceptance flow.

## Post-MVP tracks — not numbered commitments

Only after Phase 6 review:

- richer multi-agent orchestration;
- MCP/tool registry and plugin runtime;
- workflow templates/marketplace concepts;
- scheduling/background jobs;
- desktop packaging;
- remote access/Telegram integrations;
- optional distributed workers or external databases when justified by measured need.

These items must not be pulled into earlier phases by default.
