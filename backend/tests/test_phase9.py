from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from agentgraph.app import create_app
from agentgraph.domain.distributed import NodeStatus, ResourceSnapshot, TaskResult, WorkerCapabilities, WorkerHello
from agentgraph.models.router import DisabledProvider, ModelRouter
from agentgraph.runtime.graph import DeterministicGraphRuntime
from agentgraph.services.nodes import (
    NodeError,
    NodeService,
    NodeTaskDisconnectedError,
    NodeTaskDuplicateError,
    NodeTaskTimeoutError,
)
from agentgraph.settings import Settings
from agentgraph.worker import load_node_id, safe_capabilities


def _headers(identity: str) -> dict[str, str]:
    return {"x-agentgraph-identity": identity}


def _hello(node_id: str = "node_phase9_test") -> WorkerHello:
    return WorkerHello(
        node_id=node_id,
        node_name="Phase 9 test worker",
        capabilities=WorkerCapabilities(
            platform="Linux",
            architecture="x86_64",
            agentgraph_version="0.1.0",
            resources=ResourceSnapshot(
                cpu_count=4, load_average=0, memory_total_bytes=1024, memory_available_bytes=512
            ),
        ),
    )


@pytest.fixture
def distributed_client(settings: Settings) -> Generator[TestClient, None, None]:
    configured = settings.model_copy(
        update={
            "remote_control_enabled": True,
            "remote_control_policies": '{"reader":["read"],"operator":["read","execute","control"]}',
            "worker_enrollment_secret": "test-enrollment-secret",
            "worker_task_timeout_seconds": 0.05,
        }
    )
    router = ModelRouter(
        {provider_id: DisabledProvider(provider_id) for provider_id in ("ollama", "opencode", "openrouter")},
        "ollama://qwen3-4b-nothink:latest",
    )
    with TestClient(create_app(configured, DeterministicGraphRuntime(), router)) as test_client:
        yield test_client


def _service(client: TestClient) -> tuple[Any, NodeService]:
    app = cast(Any, client.app)
    return cast(Any, client).portal, cast(NodeService, app.state.node_service)


def _enroll(client: TestClient, node_id: str = "node_phase9_test") -> tuple[Any, NodeService, WorkerHello]:
    portal, service = _service(client)
    hello = _hello(node_id)
    proof = NodeService.enrollment_proof("test-enrollment-secret", node_id)
    portal.call(service.enroll, hello, proof)
    return portal, service, hello


def test_worker_websocket_denies_auth_mismatch_protocol_and_oversize(distributed_client: TestClient) -> None:
    hello = _hello()
    with pytest.raises(WebSocketDisconnect):
        with distributed_client.websocket_connect("/ws/internal/workers") as socket:
            socket.send_json(hello.model_dump(mode="json"))
            socket.receive_json()

    proof = NodeService.enrollment_proof("test-enrollment-secret", hello.node_id)
    with pytest.raises(WebSocketDisconnect):
        with distributed_client.websocket_connect(
            "/ws/internal/workers", headers={"x-agentgraph-worker-proof": proof}
        ) as socket:
            socket.send_json({})
            socket.receive_json()
    with pytest.raises(WebSocketDisconnect):
        with distributed_client.websocket_connect(
            "/ws/internal/workers", headers={"x-agentgraph-worker-proof": proof}
        ) as socket:
            socket.send_json({**hello.model_dump(mode="json"), "protocol_version": 2})
            socket.receive_json()
    with pytest.raises(WebSocketDisconnect):
        with distributed_client.websocket_connect(
            "/ws/internal/workers", headers={"x-agentgraph-worker-proof": proof}
        ) as socket:
            socket.send_text("x" * 64_001)
            socket.receive_json()


def test_worker_websocket_enrollment_heartbeat_and_reconnect_identity(distributed_client: TestClient) -> None:
    hello = _hello()
    proof = NodeService.enrollment_proof("test-enrollment-secret", hello.node_id)
    with distributed_client.websocket_connect(
        "/ws/internal/workers", headers={"x-agentgraph-worker-proof": proof}
    ) as socket:
        socket.send_json(hello.model_dump(mode="json"))
        assert socket.receive_json()["type"] == "worker.registered"
        socket.send_json(
            {"type": "worker.heartbeat", "protocol_version": 1, "resources": hello.capabilities.resources.model_dump()}
        )
    with distributed_client.websocket_connect(
        "/ws/internal/workers", headers={"x-agentgraph-worker-proof": proof}
    ) as socket:
        socket.send_json(hello.model_dump(mode="json"))
        assert socket.receive_json()["node_id"] == hello.node_id
    nodes = distributed_client.get("/api/v1/nodes", headers=_headers("reader"))
    assert nodes.status_code == 200
    workers = [node for node in nodes.json() if node["role"] == "worker"]
    assert len(workers) == 1
    assert workers[0]["node_id"] == hello.node_id


def test_node_service_dispatch_duplicate_timeout_and_disconnect(distributed_client: TestClient) -> None:
    portal, service, hello = _enroll(distributed_client)
    queue = portal.call(service.connect, hello.node_id)

    pending = portal.start_task_soon(service.probe, hello.node_id, 1, "tsk_phase9_once")
    request = portal.call(queue.get)
    assert request.operation == "system.probe"
    with pytest.raises(NodeTaskDuplicateError):
        portal.call(service.probe, hello.node_id, 1, "tsk_phase9_once")
    portal.call(service.receive_result, hello.node_id, TaskResult(task_id=request.task_id, result={"ok": True}))
    assert pending.result(timeout=1).result == {"ok": True}

    timed_out = portal.start_task_soon(service.probe, hello.node_id, 0.01, "tsk_phase9_timeout")
    with pytest.raises(NodeTaskTimeoutError):
        timed_out.result(timeout=1)
    assert portal.call(queue.get).task_id == "tsk_phase9_timeout"
    assert portal.call(queue.get).task_id == "tsk_phase9_timeout"
    disconnected = portal.start_task_soon(service.probe, hello.node_id, 1, "tsk_phase9_disconnect")
    portal.call(queue.get)
    portal.call(service.disconnect, hello.node_id)
    with pytest.raises(NodeTaskDisconnectedError):
        disconnected.result(timeout=1)


def test_node_api_permissions_disable_and_persistence(distributed_client: TestClient) -> None:
    _, _, hello = _enroll(distributed_client)
    denied = distributed_client.post(f"/api/v1/nodes/{hello.node_id}/disable", headers=_headers("reader"))
    denied_probe = distributed_client.post(f"/api/v1/nodes/{hello.node_id}/probe", headers=_headers("reader"))
    disabled = distributed_client.post(f"/api/v1/nodes/{hello.node_id}/disable", headers=_headers("operator"))
    probe = distributed_client.post(f"/api/v1/nodes/{hello.node_id}/probe", headers=_headers("operator"))
    enabled = distributed_client.post(f"/api/v1/nodes/{hello.node_id}/enable", headers=_headers("operator"))

    assert denied.status_code == 403
    assert denied_probe.status_code == 403
    assert disabled.json()["status"] == "disabled"
    assert probe.status_code == 409
    assert probe.json()["error"]["code"] == "NODE_DISABLED"
    assert enabled.json()["enabled"] is True
    assert distributed_client.get(f"/api/v1/nodes/{hello.node_id}", headers=_headers("reader")).status_code == 200


def test_node_identity_and_safe_capabilities_are_bounded(tmp_path: Path) -> None:
    first = load_node_id(str(tmp_path / "worker-id"))
    assert first == load_node_id(str(tmp_path / "worker-id"))
    capabilities = safe_capabilities()
    assert capabilities.resources.cpu_count >= 0
    assert "system.probe" in capabilities.features


def test_enrollment_rejects_unknown_proof(distributed_client: TestClient) -> None:
    _, service = _service(distributed_client)
    with pytest.raises(NodeError):
        cast(Any, distributed_client).portal.call(service.enroll, _hello(), "incorrect-proof")


def test_heartbeat_timeout_transitions_worker_offline(distributed_client: TestClient) -> None:
    portal, service, hello = _enroll(distributed_client)

    async def expire_heartbeat() -> None:
        async with service._sessions() as session:
            record = await service._repository.get(session, hello.node_id)
            assert record is not None
            record.last_seen_at = datetime.now(UTC) - timedelta(minutes=1)
            await session.commit()
        await service.mark_stale_offline()

    portal.call(expire_heartbeat)
    assert portal.call(service.get, hello.node_id).status is NodeStatus.OFFLINE
