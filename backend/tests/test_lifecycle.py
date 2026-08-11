import asyncio
import time
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from agentgraph.app import create_app
from agentgraph.domain.entities import AgentRun, AgentStatus, RunStatus
from agentgraph.models.contracts import ModelResponse
from agentgraph.persistence.database import create_database_engine, create_session_factory
from agentgraph.persistence.models import AgentRecord, AgentRunRecord
from agentgraph.runtime.graph import DeterministicGraphRuntime
from agentgraph.runtime.registry import RunRegistry
from agentgraph.services.errors import LifecycleConflictError
from agentgraph.services.manager import AgentManager
from agentgraph.settings import Settings

from .conftest import upgrade_database


def create_agent(client: TestClient, name: str = "Planner") -> dict[str, object]:
    response = client.post(
        "/api/agents/create",
        json={"name": name, "description": "Deterministic lifecycle test"},
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


def wait_for_terminal_run(client: TestClient, run_id: str) -> dict[str, object]:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        response = client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"succeeded", "failed", "cancelled"}:
            return cast(dict[str, object], payload)
        time.sleep(0.01)
    raise AssertionError("Run did not reach a terminal state")


def test_health_and_agent_crud(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    agent = create_agent(client)

    listed = client.get("/api/agents")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [agent["id"]]

    fetched = client.get(f"/api/agents/{agent['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "idle"

    deleted = client.delete(f"/api/agents/{agent['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/agents/{agent['id']}").status_code == 404


def test_run_executes_real_compiled_langgraph(client: TestClient) -> None:
    agent = create_agent(client)
    started = client.post("/api/agents/run", json={"agent_id": agent["id"], "input_text": "hello"})
    assert started.status_code == 202

    run = wait_for_terminal_run(client, started.json()["id"])
    assert run["status"] == "succeeded"
    assert run["output_text"] == "Processed: hello"
    assert run["started_at"] is not None
    assert run["finished_at"] is not None
    assert run["provider_id"] == "deterministic"
    assert run["model_id"] == "phase2"

    history = client.get(f"/api/agents/{agent['id']}/runs")
    assert history.status_code == 200
    assert [item["id"] for item in history.json()] == [run["id"]]


def test_active_run_conflict_and_real_cancellation(database_url: str) -> None:
    settings = Settings(database_url=database_url, runtime_delay_seconds=1)
    upgrade_database(database_url)

    with TestClient(create_app(settings, DeterministicGraphRuntime())) as client:
        agent = create_agent(client)
        started = client.post("/api/agents/run", json={"agent_id": agent["id"], "input_text": "wait"})
        assert started.status_code == 202
        run_id = started.json()["id"]

        second = client.post("/api/agents/run", json={"agent_id": agent["id"], "input_text": "again"})
        assert second.status_code == 409

        stopped = client.post(f"/api/runs/{run_id}/stop")
        assert stopped.status_code == 200
        assert stopped.json()["status"] == "cancelled"
        assert stopped.json()["finished_at"] is not None

        agent_status = client.get(f"/api/agents/{agent['id']}/status")
        assert agent_status.json()["status"] == "idle"


def test_active_run_constraint_covers_distinct_managers(database_url: str) -> None:
    upgrade_database(database_url)

    async def start_concurrently() -> tuple[AgentRun | BaseException, AgentRun | BaseException]:
        engine = create_database_engine(database_url)
        session_factory = create_session_factory(engine)
        first_manager = AgentManager(
            session_factory,
            DeterministicGraphRuntime(),
            RunRegistry(),
            runtime_delay_seconds=1,
            cancellation_timeout_seconds=1,
        )
        second_manager = AgentManager(
            session_factory,
            DeterministicGraphRuntime(),
            RunRegistry(),
            runtime_delay_seconds=1,
            cancellation_timeout_seconds=1,
        )
        agent = await first_manager.create_agent(
            name="Shared",
            description=None,
            model_ref="auto://default",
            graph_definition={},
        )
        results = await asyncio.gather(
            first_manager.start_run(agent_id=agent.id, input_text="first"),
            second_manager.start_run(agent_id=agent.id, input_text="second"),
            return_exceptions=True,
        )
        await first_manager.shutdown()
        await second_manager.shutdown()
        await engine.dispose()
        return results

    results = asyncio.run(start_concurrently())
    assert sum(isinstance(result, AgentRun) for result in results) == 1
    assert sum(isinstance(result, LifecycleConflictError) for result in results) == 1


def test_active_run_partial_index_rejects_duplicate_rows(database_url: str) -> None:
    upgrade_database(database_url)

    async def insert_duplicate_active_runs() -> None:
        engine = create_database_engine(database_url)
        session_factory = create_session_factory(engine)
        agent_id = str(uuid4())
        async with session_factory() as session:
            session.add(
                AgentRecord(
                    id=agent_id,
                    name="Indexed",
                    status=AgentStatus.IDLE,
                    model_ref="auto://default",
                    graph_definition={},
                )
            )
            await session.commit()
            session.add(
                AgentRunRecord(
                    id=str(uuid4()),
                    agent_id=agent_id,
                    status=RunStatus.QUEUED,
                    input_text="first",
                )
            )
            await session.commit()
            session.add(
                AgentRunRecord(
                    id=str(uuid4()),
                    agent_id=agent_id,
                    status=RunStatus.RUNNING,
                    input_text="second",
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
        await engine.dispose()

    asyncio.run(insert_duplicate_active_runs())


def test_stop_run_timeout_leaves_live_run_active(database_url: str) -> None:
    upgrade_database(database_url)

    class CancellationResistantRuntime:
        def __init__(self) -> None:
            self.release = asyncio.Event()
            self.entered = asyncio.Event()

        async def invoke(self, *, agent_id: UUID, run_id: UUID, input_text: str, model_ref: str) -> ModelResponse:
            del agent_id, run_id, input_text, model_ref
            self.entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                await self.release.wait()
            return ModelResponse(content="late completion", provider_id="test", model_id="test")

    async def stop_with_timeout() -> None:
        engine = create_database_engine(database_url)
        session_factory = create_session_factory(engine)
        runtime = CancellationResistantRuntime()
        manager = AgentManager(
            session_factory,
            cast(DeterministicGraphRuntime, runtime),
            RunRegistry(),
            runtime_delay_seconds=0,
            cancellation_timeout_seconds=0.01,
        )
        agent = await manager.create_agent(
            name="Cancellation resistant",
            description=None,
            model_ref="auto://default",
            graph_definition={},
        )
        run = await manager.start_run(agent_id=agent.id, input_text="wait")
        await runtime.entered.wait()

        with pytest.raises(LifecycleConflictError, match="timed out"):
            await manager.stop_run(run.id)
        assert (await manager.get_run(run.id)).status == RunStatus.RUNNING

        runtime.release.set()
        await asyncio.sleep(0.01)
        await manager.shutdown()
        await engine.dispose()

    asyncio.run(stop_with_timeout())


def test_persistence_survives_application_restart(settings: Settings) -> None:
    with TestClient(create_app(settings, DeterministicGraphRuntime())) as first_client:
        agent = create_agent(first_client, name="Persistent")

    with TestClient(create_app(settings, DeterministicGraphRuntime())) as second_client:
        fetched = second_client.get(f"/api/agents/{agent['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["name"] == "Persistent"


def test_startup_recovers_stale_run(database_url: str) -> None:
    upgrade_database(database_url)
    agent_id = str(uuid4())
    run_id = str(uuid4())
    queued_agent_id = str(uuid4())
    queued_run_id = str(uuid4())

    async def seed_stale_run() -> None:
        engine = create_database_engine(database_url)
        session_factory = create_session_factory(engine)
        async with session_factory() as session:
            now = datetime.now(UTC)
            session.add(
                AgentRecord(
                    id=agent_id,
                    name="Interrupted",
                    status=AgentStatus.RUNNING,
                    model_ref="auto://default",
                    graph_definition={},
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                AgentRunRecord(
                    id=run_id,
                    agent_id=agent_id,
                    status=RunStatus.RUNNING,
                    input_text="unfinished",
                    created_at=now,
                    started_at=now,
                )
            )
            session.add(
                AgentRecord(
                    id=queued_agent_id,
                    name="Queued interruption",
                    status=AgentStatus.RUNNING,
                    model_ref="auto://default",
                    graph_definition={},
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                AgentRunRecord(
                    id=queued_run_id,
                    agent_id=queued_agent_id,
                    status=RunStatus.QUEUED,
                    input_text="queued unfinished",
                    created_at=now,
                )
            )
            await session.commit()
        await engine.dispose()

    asyncio.run(seed_stale_run())

    with TestClient(create_app(Settings(database_url=database_url), DeterministicGraphRuntime())) as client:
        recovered_run = client.get(f"/api/runs/{run_id}")
        assert recovered_run.status_code == 200
        assert recovered_run.json()["status"] == "failed"
        assert recovered_run.json()["error"] == "Run interrupted by application restart"
        assert recovered_run.json()["finished_at"] is not None

        recovered_agent = client.get(f"/api/agents/{agent_id}")
        assert recovered_agent.json()["status"] == "error"

        recovered_queued_run = client.get(f"/api/runs/{queued_run_id}")
        assert recovered_queued_run.json()["status"] == "failed"
        assert recovered_queued_run.json()["finished_at"] is not None
        recovered_queued_agent = client.get(f"/api/agents/{queued_agent_id}")
        assert recovered_queued_agent.json()["status"] == "error"


def test_invalid_input_and_missing_entities(client: TestClient) -> None:
    assert client.post("/api/agents/create", json={"name": ""}).status_code == 422
    assert client.post("/api/agents/create", json={"name": "   "}).status_code == 422
    assert (
        client.post(
            "/api/agents/create", json={"name": "Unsafe", "graph_definition": {"api_key": "secret"}}
        ).status_code
        == 422
    )
    assert (
        client.post("/api/agents/create", json={"name": "Bad model", "model_ref": "unknown://model"}).status_code == 422
    )
    assert client.post("/api/agents/run", json={"agent_id": str(uuid4()), "input_text": "x"}).status_code == 404
    assert client.get(f"/api/runs/{uuid4()}").status_code == 404


def test_provider_visibility_keeps_backend_health_independent(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/api/providers")
    assert response.status_code == 200
    providers = {item["provider_id"]: item for item in response.json()}
    assert set(providers) == {"ollama", "opencode", "openrouter"}
    assert providers["opencode"]["enabled"] is False
    assert providers["openrouter"]["enabled"] is False
    assert providers["opencode"]["capabilities"] == {"chat": False, "discovery": False}
