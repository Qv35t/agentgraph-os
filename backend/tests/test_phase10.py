import asyncio
import json
import sqlite3
import time
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from agentgraph.app import create_app
from agentgraph.domain.entities import AgentStatus, RunStatus
from agentgraph.domain.recovery import ActionLedgerStatus, CheckpointReason, checkpoint_checksum
from agentgraph.models.router import DisabledProvider, ModelRouter
from agentgraph.persistence.database import create_database_engine, create_session_factory
from agentgraph.persistence.models import (
    AgentRecord,
    AgentRunRecord,
    RunActionLedgerEntryRecord,
    RunCheckpointRecord,
)
from agentgraph.runtime.graph import DeterministicGraphRuntime
from agentgraph.services.tools import ToolService
from agentgraph.settings import Settings

from .conftest import seed_test_session, upgrade_database


@pytest.fixture
def recovery_client(settings: Settings) -> Generator[TestClient, None, None]:
    configured = settings.model_copy(
        update={
            "remote_control_enabled": True,
            "remote_control_policies": '{"operator":["read","execute","control"]}',
            "tools_enabled": True,
        }
    )
    router = ModelRouter(
        {provider_id: DisabledProvider(provider_id) for provider_id in ("ollama", "opencode", "openrouter")},
        "ollama://qwen3-4b-nothink:latest",
    )
    with TestClient(create_app(configured, DeterministicGraphRuntime(), router)) as client:
        seed_test_session(client, configured)
        yield client


def _settings(database_url: str) -> Settings:
    return Settings(
        database_url=database_url,
        remote_control_enabled=True,
        remote_control_policies='{"operator":["read","execute","control"]}',
    )


def _create_agent(client: TestClient, label: str = "Original") -> dict[str, object]:
    return cast(
        dict[str, object],
        client.post(
            "/api/v1/agents",
            json={
                "name": "Recovery agent",
                "description": None,
                "model_ref": "auto://default",
                "graph_definition": {
                    "version": 1,
                    "runtime": "model-v1",
                    "nodes": [{"id": "node", "type": "agent", "label": label, "position": [0, 0]}],
                    "edges": [],
                },
            },
        ).json(),
    )


def test_run_creates_immutable_checkpoints_and_recovery_api(recovery_client: TestClient, database_path: Path) -> None:
    agent = _create_agent(recovery_client)
    run = recovery_client.post(
        f"/api/v1/agents/{agent['id']}/runs", json={"input_text": "recover me"}
    ).json()
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        if recovery_client.get(f"/api/v1/runs/{run['id']}").json()["status"] == "succeeded":
            break
        time.sleep(0.01)
    recovery = recovery_client.get(f"/api/v1/runs/{run['id']}/recovery")

    assert recovery.status_code == 200
    assert [item["reason"] for item in recovery.json()["checkpoints"]] == ["succeeded", "running", "created"]
    assert recovery.json()["limits"]["automatic_resume"] is False
    assert recovery.json()["limits"]["automatic_rollback"] is False

    recovery_client.patch(
        f"/api/v1/agents/{agent['id']}/graph",
        json={
            "graph_definition": {
                "version": 1,
                "runtime": "model-v1",
                "nodes": [{"id": "node", "type": "agent", "label": "Changed", "position": [0, 0]}],
                "edges": [],
            }
        },
    )
    with sqlite3.connect(database_path) as connection:
        state = json.loads(
            connection.execute(
                "SELECT state FROM run_checkpoints WHERE run_id = ? AND sequence = 1", (run["id"],)
            ).fetchone()[0]
        )
    assert state["execution_spec"]["graph_definition"]["nodes"][0]["label"] == "Original"


def test_startup_records_conservative_recovery_outcomes(database_url: str) -> None:
    run_ids = {
        "missing": str(uuid4()),
        "corrupt": str(uuid4()),
        "structural": str(uuid4()),
        "uncertain": str(uuid4()),
        "valid": str(uuid4()),
    }
    upgrade_database(database_url)

    async def seed() -> None:
        engine = create_database_engine(database_url)
        sessions = create_session_factory(engine)
        async with sessions() as session:
            now = datetime.now(UTC)
            for outcome, run_id in run_ids.items():
                agent_id = str(uuid4())
                session.add(
                    AgentRecord(
                        id=agent_id,
                        name=outcome,
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
                        input_text=outcome,
                        created_at=now,
                        started_at=now,
                    )
                )
                if outcome != "missing":
                    state = {"format_version": 1, "run_id": run_id, "execution_spec": {}, "run_status": "running"}
                    if outcome == "structural":
                        state = cast(dict[str, object], [])
                    session.add(
                        RunCheckpointRecord(
                            run_id=run_id,
                            sequence=1,
                            reason=CheckpointReason.CREATED,
                            state=state,
                            checksum="corrupt" if outcome == "corrupt" else checkpoint_checksum(state),
                        )
                    )
                if outcome == "uncertain":
                    session.add(
                        RunActionLedgerEntryRecord(
                            run_id=run_id,
                            action_type="desktop.open_application",
                            risk="control",
                            status=ActionLedgerStatus.STARTED,
                            action_details={},
                            rollback_status="not_supported",
                            created_at=now,
                            started_at=now,
                        )
                    )
            await session.commit()
        await engine.dispose()

    asyncio.run(seed())
    settings = _settings(database_url)
    with TestClient(create_app(settings, DeterministicGraphRuntime())) as client:
        seed_test_session(client, settings)
        for name, expected in (
            ("missing", "blocked_no_checkpoint"),
            ("corrupt", "blocked_corrupt_checkpoint"),
            ("structural", "blocked_corrupt_checkpoint"),
            ("uncertain", "blocked_uncertain_action"),
            ("valid", "stopped_no_replay"),
        ):
            report = client.get(f"/api/v1/runs/{run_ids[name]}/recovery")
            assert report.status_code == 200
            assert report.json()["decisions"][0]["outcome"] == expected
            assert report.json()["checkpoints"][0]["reason"] == "failed"
            assert client.get(f"/api/v1/runs/{run_ids[name]}").json()["status"] == "failed"


def test_startup_survives_unreadable_checkpoint_json(database_url: str, database_path: Path) -> None:
    run_id = str(uuid4())
    agent_id = str(uuid4())
    upgrade_database(database_url)

    async def seed() -> None:
        engine = create_database_engine(database_url)
        sessions = create_session_factory(engine)
        async with sessions() as session:
            now = datetime.now(UTC)
            session.add(
                AgentRecord(
                    id=agent_id,
                    name="unreadable",
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
                    input_text="unreadable",
                    created_at=now,
                    started_at=now,
                )
            )
            state = {"format_version": 1, "run_id": run_id, "execution_spec": {}, "run_status": "running"}
            session.add(
                RunCheckpointRecord(
                    run_id=run_id,
                    sequence=1,
                    reason=CheckpointReason.CREATED,
                    state=state,
                    checksum=checkpoint_checksum(state),
                )
            )
            await session.commit()
        await engine.dispose()

    asyncio.run(seed())
    with sqlite3.connect(database_path) as connection:
        connection.execute("UPDATE run_checkpoints SET state = ? WHERE run_id = ?", ("not JSON", run_id))
        connection.commit()

    settings = _settings(database_url)
    with TestClient(create_app(settings, DeterministicGraphRuntime())) as client:
        seed_test_session(client, settings)
        report = client.get(f"/api/v1/runs/{run_id}/recovery")

    assert report.status_code == 200
    assert report.json()["decisions"][0]["outcome"] == "blocked_corrupt_checkpoint"
    assert report.json()["checkpoints"][0]["reason"] == "failed"


def test_startup_and_report_survive_corrupt_checkpoint_metadata(database_url: str, database_path: Path) -> None:
    run_id = str(uuid4())
    agent_id = str(uuid4())
    upgrade_database(database_url)

    async def seed() -> None:
        engine = create_database_engine(database_url)
        sessions = create_session_factory(engine)
        async with sessions() as session:
            now = datetime.now(UTC)
            session.add(
                AgentRecord(
                    id=agent_id,
                    name="corrupt metadata",
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
                    input_text="corrupt metadata",
                    created_at=now,
                    started_at=now,
                )
            )
            state = {"format_version": 1, "run_id": run_id, "execution_spec": {}, "run_status": "running"}
            session.add(
                RunCheckpointRecord(
                    run_id=run_id,
                    sequence=1,
                    reason=CheckpointReason.CREATED,
                    state=state,
                    checksum=checkpoint_checksum(state),
                )
            )
            await session.commit()
        await engine.dispose()

    asyncio.run(seed())
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE run_checkpoints SET sequence = ?, reason = ? WHERE run_id = ?", ("invalid", "invalid", run_id)
        )
        connection.commit()

    settings = _settings(database_url)
    with TestClient(create_app(settings, DeterministicGraphRuntime())) as client:
        seed_test_session(client, settings)
        report = client.get(f"/api/v1/runs/{run_id}/recovery")

    assert report.status_code == 200
    assert report.json()["decisions"][0]["outcome"] == "blocked_corrupt_checkpoint"
    assert report.json()["checkpoints"][0]["reason"] == "failed"
    assert report.json()["checkpoints"][1]["sequence"] is None
    assert report.json()["checkpoints"][1]["reason"] == "invalid"


def test_recovery_report_requires_read_permission(recovery_client: TestClient) -> None:
    agent = _create_agent(recovery_client)
    run = recovery_client.post(
        f"/api/v1/agents/{agent['id']}/runs", json={"input_text": "authorization"}
    ).json()

    recovery_client.cookies.clear()
    denied = recovery_client.get(f"/api/v1/runs/{run['id']}/recovery")
    assert denied.status_code == 403


def test_controlled_tool_writes_confirmed_action_ledger_entry(recovery_client: TestClient) -> None:
    agent = _create_agent(recovery_client)
    run = recovery_client.post(
        f"/api/v1/agents/{agent['id']}/runs", json={"input_text": "tool ledger"}
    ).json()
    service = cast(ToolService, cast(Any, recovery_client.app).state.tool_service)
    portal = cast(Any, recovery_client).portal

    async def execute_tool() -> object:
        return await service.execute(run_id=UUID(str(run["id"])), tool_id="system.current_time", arguments={})

    result = portal.call(execute_tool)
    report = recovery_client.get(f"/api/v1/runs/{run['id']}/recovery").json()

    assert cast(Any, result).status.value == "succeeded"
    assert len(report["actions"]) == 1
    assert report["actions"][0]["action_type"] == "system.current_time"
    assert report["actions"][0]["status"] == "confirmed"
    assert report["actions"][0]["rollback_status"] == "not_supported"
