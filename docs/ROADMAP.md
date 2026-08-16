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

## Remote Interface Foundation

**Status:** Implemented as a compatibility foundation alongside the completed
Phase 3 backend; it does not start Phase 4.

Delivered: normalized remote events and commands, a transport-neutral event bus,
versioned REST and WebSocket contracts, server-side authorization, and a
process-local approval contract. Future work builds on these shared contracts:

- Web interface, responsive/mobile UI, approvals UI, logs, and PWA support;
- messaging gateway, Telegram notifications/control/approvals, then Discord,
  WhatsApp, and Slack adapters;
- a thin TUI dashboard for runs, providers, logs, and approvals.

These clients must not duplicate orchestration or become a runtime authority.

## Phase 4 — Visual Interface

**Status:** DONE. Automated checks and owner-confirmed browser manual acceptance
were completed on 2026-08-12.

Goal: create the first practical React/TypeScript + React Flow workspace over the stable backend contracts.

Deliver:

- application shell;
- graph canvas and typed node/edge representation;
- agent creation/configuration UI;
- run/start/stop/status observability;
- provider/model selection based on backend discovery;
- error and loading states;
- responsive/accessibility baseline.

Delivered:

- Vite/React browser workspace with typed API client and normalized WebSocket events;
- dashboard, projects, agents, persisted visual graphs, run workspace, approvals,
  providers, events, and client preferences;
- responsive dark technical layout, state/error handling, and frontend tests;
- API graph persistence operation secured through the shared command boundary.

Do not move orchestration business logic into the browser.

## Phase 5 — Multimodal Vision Layer

**Status:** DONE. Automated checks and owner-confirmed manual acceptance are complete.

Goal: introduce local-first, provider-agnostic image observation through the
existing model router without computer-control actions.

Deliver direction:

- typed multimodal model messages and Ollama image support;
- persisted image assets and analysis history;
- secure upload and registered-folder scanning;
- normalized vision events and browser Vision workspace;
- no required model download for automated tests.

## Phase 6 — Lexi Integration

**Status:** DONE. Lexi workflow, Memory MVP, controlled Tool MVP, browser
workspace, automated verification, local Ollama smoke, and owner manual
acceptance are complete.

Goal: integrate Lexi as the first real end-to-end assistant/workflow on top of AgentGraph OS boundaries.

Deliver direction:

- Lexi agent/workflow definition;
- model routing through AgentGraph contracts;
- durable scoped SQLite Memory MVP;
- controlled Linux/assistant tool boundary rather than arbitrary shell;
- observable runs and cancellation;
- frontend representation of the Lexi workflow;
- end-to-end local-first acceptance flow.

## Phase 7 — Multi-Agent Graph Orchestration and Delegation

**Status:** DONE. Automated verification, real local Ollama team smokes, and
owner manual browser acceptance are complete.

Phase 7 is the first numbered post-MVP phase. It adds validated static team
DAGs, normal persisted child runs, bounded scheduling/delegation, run-tree
inspection, and browser composition/inspection without autonomous planning.

## Remaining post-MVP tracks

Only after Phase 6 review:

- MCP/tool registry and plugin runtime;
- workflow templates/marketplace concepts;
- scheduling/background jobs;
- desktop packaging;
- remote access/Telegram integrations;
- optional distributed workers or external databases when justified by measured need.

These items must not be pulled into earlier phases by default.
