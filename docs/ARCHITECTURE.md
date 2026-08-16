# AgentGraph OS — Architecture

Status: living architecture document. Update it when implemented boundaries change, not for speculative code.

## 1. Architectural style

AgentGraph OS starts as a **local-first modular monolith** with clear internal boundaries.

```text
┌─────────────────────────────────────────────────────────────┐
│                       AgentGraph OS                         │
│                                                             │
│  Frontend / Visual Graph                                    │
│        │                                                    │
│        ▼                                                    │
│  HTTP API (FastAPI)                                         │
│        │                                                    │
│        ▼                                                    │
│  AgentManager / Application Services                        │
│        │                                                    │
│        ├────────► Persistence (SQLite early phase)          │
│        │                                                    │
│        ▼                                                    │
│  LangGraph Runtime                                          │
│        │                                                    │
│        ├────────► ModelRouter ─► Provider adapters          │
│        │                  ├─ Ollama                         │
│        │                  ├─ OpenCode local bridge         │
│        │                  └─ OpenAI-compatible provider    │
│        │                                                    │
│        ├────────► MemoryService (SQLite Phase 6 MVP)        │
│        │                                                    │
│        └────────► ToolService / ApprovalService             │
└─────────────────────────────────────────────────────────────┘
```

## 2. Dependency direction

Dependencies should point inward toward project-owned contracts.

```text
API/UI
  ↓
Application services
  ↓
Domain + runtime contracts
  ↓
Adapters / persistence / providers
```

Rules:

- API routers do not perform raw persistence queries.
- `AgentManager` does not know provider-specific HTTP schemas.
- LangGraph nodes depend on model/memory/tool contracts, not vendor SDK details.
- Provider adapters may depend on `httpx` and external protocols.
- Persistence models must not leak across the full application as the only domain representation.

## 3. Core components

### 3.1 Frontend

Planned React + TypeScript + React Flow workspace. It visualizes agents, graphs, runs, provider state, and eventually memory/tool boundaries. It is a client of backend contracts and must not duplicate backend orchestration logic.

### 3.2 API

FastAPI provides local HTTP contracts for agent lifecycle, runs, providers, and later graph/memory operations. The default listener is loopback-only.

Phase 2 implementation: `backend/agentgraph/app.py` is the canonical app
factory. Its lifespan creates the async SQLite engine, session factory,
`AgentManager`, deterministic LangGraph runtime, and process-local
`RunRegistry`; it recovers stale runs before serving requests and cancels live
runs during shutdown.

### 3.3 AgentManager

Application service responsible for agent lifecycle and orchestration across repositories, runtime execution, cancellation, and status transitions.

Phase 2 implementation: `AgentManager` coordinates `AgentRepository`,
`RunRepository`, SQLite transactions, the live `RunRegistry`, and the runtime.
Only process-local `asyncio.Task` handles live execution; SQLite records durable
agent and run state. Stop and shutdown cancellation are bounded; a stop timeout
leaves the run active rather than falsely reporting it as cancelled.
Shared HTTP/database resources are not closed underneath a cancellation-
resistant task; its durable row is first marked failed and a deferred finalizer
closes resources after the live task exits.

### 3.3.1 Remote interface foundation

The same application remains the source of truth for future Web, TUI, and
messaging clients. `RemoteCommandService` applies server-side authorization to
supported versioned remote operations, while `RuntimeEventBus` fans out
normalized, secret-redacted lifecycle events to the REST history and WebSocket
transport. Remote control is disabled by default and approval state is currently
process-local. See `docs/architecture/REMOTE_INTERFACES.md` for the exact
contracts and explicit deferrals.

### 3.3.2 Visual interface

Phase 4 adds the React/Vite browser client in `frontend/`. It uses versioned
remote contracts and the event stream exclusively, presents a persistent graph
editor backed by the remote agent graph API, and never becomes lifecycle or
authorization authority. See `docs/architecture/VISUAL_INTERFACE.md`.

### 3.4 LangGraph runtime

Executes typed graph state. The current `ModelGraphRuntime` calls `ModelRouter`
from a typed `START -> generate -> END` graph without exposing provider HTTP
details to lifecycle code.

The current graph is compiled from `START -> execute -> END`. It accepts typed
run state and returns the stable output `Processed: <input_text>` without any
provider call.

### 3.5 Persistence

Early backend uses SQLite, SQLAlchemy 2.x, and Alembic. Persistent run state is separate from process-local execution handles.

The Phase 2 schema is maintained by Alembic migration `20260811_0001`. It
contains `agents` and `agent_runs`; active runs found at startup are marked
`failed` with a restart-interruption error and their agents become `error`.
A SQLite partial unique index enforces at most one `queued` or `running` run
per agent, including across separate backend processes.

### 3.6 Model Router

A project-owned provider-agnostic layer. It resolves `model_ref`, applies explicit routing/fallback policy, invokes providers, normalizes results/errors, and exposes provider health/model discovery without leaking secrets.

Phase 3 implements strict references, local-only `auto://default`, normalized
responses/errors, safe provider visibility, and persistent normalized run
metadata through Alembic migration `20260811_0002`.

### 3.7 Providers

Initial provider directions:

- Ollama — local model execution.
- OpenCode Bridge — local OpenCode Server used as an LLM transport when subscription auth is already owned/configured by OpenCode.
- OpenAI-compatible adapter — optional path for OpenRouter and compatible APIs.

All three adapters are implemented. Ollama is enabled by default on loopback;
OpenCode and OpenAI-compatible adapters remain disabled until their environment
configuration is supplied.

### 3.8 Multimodal vision

Phase 5 adds local image observation through typed multimodal ModelRouter
messages, validated generated asset storage, persisted analyses, and a
fail-closed registered-folder boundary. Vision remains provider-agnostic and
observation-only; see `docs/architecture/VISION.md`. Memory remains a future
local-first extension and does not share Vision storage implicitly.

### 3.9 Lexi, memory, and tools

Phase 6 adds Lexi as an ordinary AgentGraph agent with allowlisted
`runtime: "lexi-v1"` metadata. AgentManager remains lifecycle authority while
the Lexi LangGraph calls MemoryService, ModelRouter, and ToolService. The
browser `/lexi` workspace calls normal versioned AgentGraph run APIs and only
observes events; it does not own orchestration. See `docs/architecture/LEXI.md`.

Memory is persisted in SQLite and scoped by project and agent. Retrieval is
bounded lexical matching, not semantic/vector search. It is explicit to create
and can be deleted through the versioned API.

ToolService contains only registered, typed tools. It is disabled by default;
the only control action resolves a configured application alias to a server-owned
argument vector, requires approval, and never invokes a shell.

### 3.10 Tools and automation

Model text does not execute tools implicitly. Tool invocation requires typed definitions, allowlists/policy, explicit runtime handling, observable input/output, cancellation, timeouts, and security review.

### 3.11 Multi-agent orchestration

Phase 7 adds validated version-2 `team-v1` DAGs. `TeamGraphRuntime` schedules
bounded agent references through `AgentManager`, which retains durable run and
cancellation authority. SQLite persists parent-child links in `run_delegations`;
the authorized v1 run-tree endpoint and UI expose history. See
`docs/architecture/MULTI_AGENT_ORCHESTRATION.md`.

## 4. Runtime state vs persistent state

Persistent state records durable agent/run history. Process-local registries track live execution handles such as `asyncio.Task` objects. After restart, persisted `running` state must be recovered to a truthful terminal state rather than assumed to still be active.

## 5. Data and secrets boundary

Allowed persistent data can include agent definitions, graph definitions, run metadata, normalized model metadata, memory records, and user-owned project state.

Do not persist provider OAuth tokens, API keys, Basic Auth passwords, Authorization headers, or copied OpenCode credential files.

## 6. Network boundary

Default local services:

- AgentGraph backend: `127.0.0.1`.
- Ollama: normally local loopback.
- OpenCode Server bridge: loopback endpoint managed separately from AgentGraph.

External provider traffic is opt-in and must not be required for application startup.

## 7. Future architecture

Post-MVP work may add richer tool/plugin/MCP surfaces, multi-agent orchestration, packaging, and optional service separation. These are not current architectural commitments until recorded in ADRs.
