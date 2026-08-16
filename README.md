# AgentGraph OS

Local-first visual operating environment for AI agents.

## Current Implementation

- React/Vite + React Flow browser workspace over versioned backend contracts.
- Python, FastAPI, LangGraph, SQLite, SQLAlchemy, and Alembic backend.
- Provider-neutral routing for local Ollama, an optional local OpenCode model bridge, and an optional OpenAI-compatible provider.
- Local vision observation, scoped SQLite Memory MVP, controlled typed tools, Lexi workflow, and bounded static multi-agent DAGs.

The backend binds to loopback by default. OpenCode bridge mode is model transport only; it does not copy OpenCode credentials or provide a first-class Coder Agent. See [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for verified current behavior and limitations.

## Future Direction

Phase 8 has prepared the Post-Phase-7 documentation baseline and is awaiting owner review. NAS Core/failover, durable recovery and approvals, trusted remote access, autonomous Lexi planning, voice, PWA/Telegram, OpenCode orchestration, semantic memory/files, and advanced dashboard are planned target capabilities, not implemented features.

Read [`docs/FUTURE_VISION.md`](docs/FUTURE_VISION.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), and [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Local Model Direction

- Default local: `qwen3-4b-nothink:latest`
- Local quality: `qwen3:4B`
- Local fast: `qwen3:0.6B`
- GPT Plus uses the optional local OpenCode Server bridge, not an OpenAI API key.

## Verification

Run the repository quality gate from the root:

```bash
pnpm check
```

It runs frontend checks plus backend Ruff, mypy, and isolated tests. It does not call Ollama, OpenCode, or cloud providers.

## Backend Development

Install locked backend dependencies:

```bash
uv sync --directory backend --all-groups
```

Apply the local SQLite migration and start the loopback backend:

```bash
uv run --directory backend alembic upgrade head
uv run --directory backend uvicorn agentgraph.app:app --host 127.0.0.1 --port 8000
```

The versioned API includes health, provider discovery, agent/run lifecycle, and other implemented contracts. Optional provider credentials are local environment configuration only.

## Frontend Development

```bash
pnpm install
pnpm dev
```

Vite proxies `/api` and `/ws` to the loopback backend. Build with `pnpm build`; run the repository gate with `pnpm check`.

## Desktop Launcher

On Linux, run `./launch-agentgraph-os.sh` or open `AgentGraph-OS.desktop`. The launcher applies migrations, starts local backend/frontend processes, writes local logs to `.run/`, and opens the browser.
