# Phase 2 - Backend Core

## Status

DONE. The Phase 2 verification gate passed on 2026-08-11. Phase 3 is planned
but has not started.

## Mission

Turn the Foundation skeleton into a useful local backend that creates agents,
persists durable state, executes a minimal real LangGraph workflow, tracks and
cancels live runs, recovers truthful state after restart, and exposes the
lifecycle through a loopback-only HTTP API.

This phase deliberately contains no real LLM invocation.

## Approved Technical Settings

Use these settings for Phase 2 development and local operation:

```text
Python:                        3.12+
Python dependency workflow:    uv with backend/pyproject.toml and backend/uv.lock
HTTP framework:                FastAPI
Validation:                    Pydantic v2 and pydantic-settings
Persistence:                   SQLite, SQLAlchemy 2.x, Alembic
Runtime:                       LangGraph 1.x
Default host:                  127.0.0.1
Default port:                  8000
Default database URL:          sqlite+aiosqlite:///./agentgraph.db
Default run delay:             0 seconds
Default cancellation timeout:  5 seconds
```

Relevant optional environment variables:

```text
AGENTGRAPH_DATABASE_URL=
AGENTGRAPH_HOST=
AGENTGRAPH_PORT=
AGENTGRAPH_RUNTIME_DELAY_SECONDS=
AGENTGRAPH_CANCELLATION_TIMEOUT_SECONDS=
```

The local SQLite database is ignored by Git. Production-like operation requires
an explicit `alembic upgrade head`; the application does not replace migrations
with `create_all()`.

## Implemented Structure

```text
backend/
├── pyproject.toml
├── uv.lock
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/20260811_0001_backend_core.py
├── agentgraph/
│   ├── app.py
│   ├── settings.py
│   ├── api/
│   ├── domain/
│   ├── persistence/
│   ├── repositories/
│   ├── runtime/
│   └── services/
└── tests/
```

Responsibilities:

- `app.py` is the canonical FastAPI application factory and lifespan owner.
- `api/` contains typed HTTP DTOs and thin lifecycle handlers.
- `domain/` contains durable status enums and domain entities.
- `persistence/` owns the async SQLite engine and SQLAlchemy records.
- `repositories/` owns database queries and mutations.
- `services/AgentManager` owns lifecycle orchestration and state transitions.
- `runtime/` owns the compiled LangGraph workflow and process-local task
  registry.

## Data Contracts

### Agent

```text
id: UUID
name: non-empty, normalized string
description: optional string
status: idle | running | error
model_ref: string, default auto://default
graph_definition: empty Phase 2 declarative object only
created_at: UTC timestamp
updated_at: UTC timestamp
```

`model_ref` is declarative only. `auto://default` does not invoke Ollama,
OpenCode, OpenAI, or any other provider in this phase.

`graph_definition` rejects extra fields. This prevents secret-bearing provider
or tool configuration from being persisted or returned by the API before those
contracts exist.

### AgentRun

```text
id: UUID
agent_id: UUID
status: queued | running | succeeded | failed | cancelled
input_text: string
output_text: optional string
error: optional normalized error message
created_at: UTC timestamp
started_at: optional UTC timestamp
finished_at: optional UTC timestamp
```

The Alembic schema creates `agents` and `agent_runs`. A SQLite partial unique
index permits only one `queued` or `running` run per agent, including when
separate backend processes use the same database.

## Runtime Lifecycle

```text
HTTP API
   -> AgentManager
      -> AgentRepository / RunRepository
      -> RunRegistry for live asyncio.Task handles
      -> compiled LangGraph runtime
   -> SQLite durable state
```

### Start

1. Validate that the agent exists.
2. Serialize the SQLite active-run check with `BEGIN IMMEDIATE`.
3. Reject a second active run with HTTP 409.
4. Persist a `queued` run and mark the agent `running`.
5. Create and register a real `asyncio.Task`.
6. Transition the run to `running` and invoke the compiled graph.

### Deterministic LangGraph Proof

The runtime constructs, compiles, and invokes this graph:

```text
START -> execute -> END
```

The typed state contains the agent ID, run ID, input text, and output text. The
stable Phase 2 result is:

```text
Processed: <input_text>
```

This is a real LangGraph invocation, not a replacement plain function.

### Completion and Failure

- Successful runs persist `succeeded`, output, and `finished_at`; the agent
  becomes `idle`.
- Runtime failures persist `failed`, a normalized error, and `finished_at`; the
  agent becomes `error`.
- Errors exposed through HTTP do not include tracebacks or raw exception bodies.

### Stop and Shutdown

- Stopping a run cancels the actual registered task, not only a database row.
- Task cancellation waits only up to the configured timeout.
- A stop timeout leaves the run active and returns a conflict rather than
  falsely recording `cancelled`.
- Shutdown cancels live tasks with the same bounded timeout. A task still live
  when the process shuts down is persisted as `failed` because it cannot survive
  the restart.
- Engine disposal executes even if shutdown cleanup raises.

### Restart Recovery

At startup, persisted `queued` and `running` runs are changed to `failed` with
`Run interrupted by application restart`; `finished_at` is set and affected
agents become `error`.

## HTTP API

```text
GET    /health
POST   /api/agents/create
GET    /api/agents
GET    /api/agents/{agent_id}
DELETE /api/agents/{agent_id}
GET    /api/agents/{agent_id}/status
POST   /api/agents/run
GET    /api/runs/{run_id}
POST   /api/runs/{run_id}/stop
GET    /api/agents/{agent_id}/runs
```

Behavior:

- `GET /health` is cheap and never calls a provider.
- Input is validated with typed Pydantic schemas.
- Unknown resources return 404.
- Invalid input returns 422.
- Active-run and lifecycle conflicts return 409.
- Deleting an agent with an active run returns 409.
- Agent and run identifiers are UUIDs.
- API handlers do not expose secrets or tracebacks.

## Recommended Commands

Install locked development dependencies:

```bash
uv sync --directory backend --all-groups
```

Apply the local schema and run the backend:

```bash
uv run --directory backend alembic upgrade head
uv run --directory backend uvicorn agentgraph.app:app --host 127.0.0.1 --port 8000
```

Run focused checks:

```bash
uv run --directory backend pytest
uv run --directory backend ruff check .
uv run --directory backend mypy
```

Run the full repository gate:

```bash
pnpm check
```

`pnpm check` runs Foundation validation, Ruff, mypy, and isolated backend tests.
After dependencies are installed, it does not call Ollama, OpenCode, GPT Plus,
cloud providers, or download models.

## Security and Isolation

- The backend defaults to `127.0.0.1`.
- Tests use temporary databases only.
- No provider credentials are required, stored, logged, or returned.
- No pickle is used for graph state or persistence.
- No model output executes code, shell commands, tools, filesystem operations,
  or network actions.
- Provider, memory, tool, and frontend boundaries remain unimplemented.

## Explicitly Out of Scope

- Ollama, OpenCode, OpenAI, OpenRouter, or any real model call.
- ModelRouter, ProviderRegistry, provider discovery, health, or fallback.
- React, TypeScript, React Flow, or any frontend implementation.
- Qdrant, Mem0, embeddings, retrieval, RAG, or memory.
- Shell, browser, filesystem, MCP, or Linux automation tools.
- Lexi, multi-agent orchestration, plugin runtime, scheduler, or workers.
- Redis, Celery, Kafka, PostgreSQL, Kubernetes, or mandatory Docker.

## Verification Gate

The following was observed before completion:

1. Alembic upgraded clean temporary SQLite databases.
2. `pnpm check` passed.
3. Ruff and mypy passed.
4. The isolated lifecycle suite passed with 11 tests.
5. Tests cover CRUD, deterministic LangGraph output, cancellation, cancellation
   timeout, cross-manager active-run conflict, database unique-index enforcement,
   persistence across restart, and stale `queued` and `running` recovery.
6. Manual loopback smoke checks confirmed `/health`, agent creation, successful
   deterministic execution, delayed-run cancellation, and persistence after
   restart.
7. No provider, frontend, memory, tool, or Lexi capability was introduced.

## Completion

Phase 2 is complete. Phase 3 may start only with an explicit owner instruction.
