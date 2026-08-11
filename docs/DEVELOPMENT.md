# AgentGraph OS — Development Workflow

## Principles

- Native/local development first.
- Reuse the dependency workflow already present in each component.
- Do not introduce `poetry`, `uv`, `pip-tools`, npm/yarn/pnpm alternatives in parallel without a reason.
- Keep environment-specific secrets outside Git.
- Prefer small vertical slices with tests over broad scaffolding.

## Before work

```bash
git status --short
git branch --show-current
```

Then inspect the relevant manifests and README files. Do not assume commands that are not actually configured.

## Foundation check

Run this command from the repository root to verify Foundation artifacts:

```bash
pnpm check
```

It is offline and validates repository structure, required documentation,
non-secret configuration, and the known local model metadata. It does not run
Ollama, OpenCode, provider, backend, or frontend checks.

## Python backend baseline

Backend dependencies are managed with `uv` from `backend/pyproject.toml`.
Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, LangGraph, HTTPX,
and pytest are implemented through Phase 3.

Canonical commands:

```bash
uv sync --directory backend --all-groups
uv run --directory backend alembic upgrade head
uv run --directory backend uvicorn agentgraph.app:app --host 127.0.0.1 --port 8000
uv run --directory backend pytest
uv run --directory backend ruff check .
uv run --directory backend mypy
pnpm check
```

`pnpm check` is the root quality gate. It runs Foundation validation plus
backend lint, type checks, and tests without requiring local models, cloud
credentials, or external services.

Provider live checks are separate. Ollama defaults to
`http://127.0.0.1:11434`; OpenCode and OpenAI-compatible settings remain empty
until configured locally from `.env.example`.

## Frontend baseline

Expected direction: React + TypeScript + React Flow. Package manager and exact scripts must follow the actual committed frontend manifest.

## Change workflow

1. Read active phase and relevant rules.
2. Inspect existing implementation/tests.
3. Make the smallest coherent change.
4. Run the nearest focused test(s).
5. Run broader phase quality checks.
6. Update docs/contracts only if behavior changed.
7. Report exact checks run and remaining gaps.

## Migrations

Once Alembic is introduced:

- migrations are committed;
- never ignore migration scripts;
- schema changes require a migration and test/upgrade verification;
- do not replace migrations with runtime `create_all()` as the production lifecycle.

## Generated/local data

Never commit:

- `.env` secrets;
- SQLite runtime DBs;
- logs;
- model weights/caches;
- Qdrant local storage;
- credentials/keys;
- build outputs and package caches.
