import asyncio
import time
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from agentgraph.app import create_app
from agentgraph.domain.remote import ApprovalStatus, RuntimeEvent, RuntimeEventType
from agentgraph.models.router import DisabledProvider, ModelRouter
from agentgraph.runtime.events import RuntimeEventBus, event_json
from agentgraph.runtime.graph import DeterministicGraphRuntime
from agentgraph.services.errors import LifecycleConflictError
from agentgraph.services.remote import ApprovalService
from agentgraph.settings import Settings

from .conftest import seed_test_session


@pytest.fixture
def remote_client(settings: Settings) -> Generator[TestClient, None, None]:
    configured_settings = settings.model_copy(
        update={
            "remote_control_enabled": True,
            "remote_control_policies": (
                '{"reader":["read"],"operator":["read","execute","control"],"approver":["approve"]}'
            ),
        }
    )
    router = ModelRouter(
        {provider_id: DisabledProvider(provider_id) for provider_id in ("ollama", "opencode", "openrouter")},
        "ollama://qwen3-4b-nothink:latest",
    )
    with TestClient(create_app(configured_settings, DeterministicGraphRuntime(), router)) as test_client:
        seed_test_session(test_client, configured_settings)
        yield test_client


def test_remote_control_and_legacy_api_are_disabled_by_default(settings: Settings) -> None:
    default_settings = settings.model_copy(update={"legacy_api_enabled": False})
    with TestClient(create_app(default_settings, DeterministicGraphRuntime())) as default_client:
        response = default_client.get("/api/v1/system")
        legacy = default_client.get("/api/agents")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert legacy.status_code == 404


def test_identity_header_cannot_spoof_a_session(remote_client: TestClient) -> None:
    remote_client.cookies.clear()

    response = remote_client.get("/api/v1/providers", headers={"x-agentgraph-identity": "owner"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_server_side_permissions_and_versioned_run_query(remote_client: TestClient) -> None:
    agent_response = remote_client.post(
        "/api/v1/agents",
        json={
            "name": "Remote test agent",
            "description": None,
            "model_ref": "auto://default",
            "graph_definition": {"nodes": [], "edges": []},
        },
    )
    agent_id = agent_response.json()["id"]

    remote_client.cookies.clear()
    denied = remote_client.post(
        f"/api/v1/agents/{agent_id}/runs", json={"input_text": "hello"}
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "FORBIDDEN"
    seed_test_session(remote_client, cast(Settings, cast(Any, remote_client).app.state.settings))

    started = remote_client.post(f"/api/v1/agents/{agent_id}/runs", json={"input_text": "hello"})
    assert started.status_code == 202

    run_id = started.json()["id"]
    queried = remote_client.get(f"/api/v1/runs/{run_id}")
    assert queried.status_code == 200
    assert queried.json()["id"] == run_id
    _wait_for_terminal_run(remote_client, run_id)


def test_remote_provider_visibility_and_error_contract(remote_client: TestClient) -> None:
    providers = remote_client.get("/api/v1/providers")
    missing_run = remote_client.get("/api/v1/runs/not-a-uuid")

    assert providers.status_code == 200
    assert all("api_key" not in provider for provider in providers.json())
    assert missing_run.status_code == 404
    assert missing_run.json() == {"error": {"code": "RUN_NOT_FOUND", "message": "Run was not found", "details": {}}}


def test_remote_agent_graph_is_saved_and_reloaded(remote_client: TestClient) -> None:
    created = remote_client.post(
        "/api/v1/agents",
        json={
            "name": "Graph agent",
            "description": None,
            "model_ref": "auto://default",
            "graph_definition": {"nodes": [], "edges": []},
        },
    )
    assert created.status_code == 201
    agent_id = created.json()["id"]
    graph = {"nodes": [{"id": "agent", "type": "agent", "label": "Agent", "position": [0, 0]}], "edges": []}

    updated = remote_client.patch(
        f"/api/v1/agents/{agent_id}/graph", json={"graph_definition": graph}
    )
    loaded = remote_client.get(f"/api/v1/agents/{agent_id}")

    assert updated.status_code == 200
    assert loaded.json()["graph_definition"] == graph


def test_approval_api_enforces_permission_and_publishes_events(remote_client: TestClient) -> None:
    payload = {"action": "run tool", "description": "Needs user approval"}
    remote_client.cookies.clear()
    denied = remote_client.post("/api/v1/approvals", json=payload)
    seed_test_session(remote_client, cast(Settings, cast(Any, remote_client).app.state.settings))
    created = remote_client.post("/api/v1/approvals", json=payload)

    assert denied.status_code == 403
    assert created.status_code == 200

    approved = remote_client.post(f"/api/v1/approvals/{created.json()['approval_id']}/approve")
    events = remote_client.get("/api/v1/events")

    assert approved.json()["status"] == "approved"
    assert [event["type"] for event in events.json()] == ["approval.required", "approval.approved"]


def test_runtime_events_are_serializable_and_redact_secrets() -> None:
    bus = RuntimeEventBus()
    event = RuntimeEvent.create(
        RuntimeEventType.PROVIDER_ERROR,
        "project_local",
        run_id="run_1",
        payload={"api_key": "secret-value", "nested": {"authorization": "Bearer secret"}},
    )

    asyncio.run(bus.publish(event))
    serialized = event_json(bus.history("run_1")[0])

    assert isinstance(serialized["event_id"], str)
    assert serialized["event_id"].startswith("evt_")
    assert serialized["run_id"] == "run_1"
    assert serialized["payload"] == {"api_key": "[redacted]", "nested": {"authorization": "[redacted]"}}


def test_event_subscriber_receives_event_without_becoming_runtime_dependency() -> None:
    async def receive() -> str:
        bus = RuntimeEventBus()
        subscription = bus.subscribe()

        async def wait_for_event() -> RuntimeEvent:
            return await anext(subscription)

        waiting = asyncio.create_task(wait_for_event())
        await asyncio.sleep(0)
        await bus.publish(RuntimeEvent.create(RuntimeEventType.RUN_STARTED, "project_local", run_id="run_1"))
        received = await asyncio.wait_for(waiting, timeout=1)
        await subscription.aclose()
        await bus.publish(RuntimeEvent.create(RuntimeEventType.RUN_COMPLETED, "project_local", run_id="run_1"))
        return received.id

    assert asyncio.run(receive()).startswith("evt_")


def test_approval_transitions_are_single_use_and_expire() -> None:
    approvals = ApprovalService()

    async def transition() -> ApprovalStatus:
        pending = await approvals.create(
            project_id="project_local", action="run tool", description="Requires review", requested_by="agent"
        )
        approved = await approvals.decide(pending.id, True)
        with pytest.raises(LifecycleConflictError):
            await approvals.decide(pending.id, True)

        expired = await approvals.create(
            project_id="project_local",
            action="run tool",
            description="Expired review",
            requested_by="agent",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        with pytest.raises(LifecycleConflictError, match="expired"):
            await approvals.decide(expired.id, True)
        assert expired.status is ApprovalStatus.EXPIRED
        return approved.status

    assert asyncio.run(transition()) is ApprovalStatus.APPROVED


def test_event_socket_requires_authorized_identity(remote_client: TestClient) -> None:
    remote_client.cookies.clear()
    with pytest.raises(WebSocketDisconnect):
        with remote_client.websocket_connect("/ws/events"):
            pass

    event = RuntimeEvent.create(RuntimeEventType.RUN_STARTED, "project_local", run_id="run_socket")
    seed_test_session(remote_client, cast(Settings, cast(Any, remote_client).app.state.settings))
    with remote_client.websocket_connect("/ws/events") as socket:
        portal = cast(Any, remote_client).portal
        app = cast(Any, remote_client.app)
        portal.call(app.state.event_bus.publish, event)
        received = socket.receive_json()

    assert received["event_id"] == event.id
    assert received["run_id"] == "run_socket"


def _wait_for_terminal_run(client: TestClient, run_id: str) -> None:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/runs/{run_id}")
        if response.json()["status"] in {"succeeded", "failed", "cancelled"}:
            return
        time.sleep(0.01)
    raise AssertionError("Run did not reach a terminal state")
