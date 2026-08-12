# AgentGraph OS


Visual operating system for AI agents.


## Features


- Multi-agent workflows
- Local LLM support
- GPT integration
- Visual agent graph
- Memory system
- Tool execution
- Linux automation


## Architecture


Frontend:
React + React Flow


Backend:
Python + FastAPI + LangGraph


AI:
Ollama
OpenAI
OpenRouter


Memory:
Qdrant
Mem0


## Status

Phase 4 - Visual Interface is implemented with a React/Vite browser client over
the versioned remote API and event stream. See `docs/PHASE_4_MANUAL_ACCEPTANCE.md`
for the local browser acceptance procedure.

## Local model direction

- Default local: `qwen3-4b-nothink:latest`
- Local quality: `qwen3:4B`
- Local fast: `qwen3:0.6B`
- GPT Plus uses the optional local OpenCode Server bridge, not an OpenAI API key.

## Verification

Run the Foundation check from the repository root:

```bash
pnpm check
```

The check runs Foundation validation, Ruff, mypy, and mocked/isolated backend
tests. It does not call Ollama, OpenCode, or cloud providers.

## Backend Development

Install the locked backend dependencies:

```bash
uv sync --directory backend --all-groups
```

Apply the local SQLite migration and start the loopback-only backend:

```bash
uv run --directory backend alembic upgrade head
uv run --directory backend uvicorn agentgraph.app:app --host 127.0.0.1 --port 8000
```

The API includes `GET /health`, provider discovery at `GET /api/providers`,
agent lifecycle endpoints under `/api/agents`, and run lifecycle endpoints
under `/api/runs`. Optional provider credentials are configured only through
local environment variables based on `.env.example`.

## Frontend Development

Install workspace dependencies, then start the browser client:

```bash
pnpm install
pnpm dev
```

Vite proxies `/api` and `/ws` to the loopback backend. Build the production
assets with `pnpm build`; run the full repository gate with `pnpm check`.
