import asyncio
import time
from typing import cast

from fastapi.testclient import TestClient

from agentgraph.app import create_app
from agentgraph.models.contracts import ModelRequest, ModelResponse, ProviderStatus
from agentgraph.models.router import ModelProvider, ModelRouter
from agentgraph.settings import Settings

from .conftest import seed_test_session, upgrade_database


def _settings(database_url: str) -> Settings:
    return Settings(
        database_url=database_url,
        remote_control_enabled=True,
        remote_control_policies='{"operator":["read","execute","control"]}',
        orchestration_child_timeout_seconds=2,
    )


def _wait(client: TestClient, run_id: str) -> dict[str, object]:
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        body = cast(dict[str, object], client.get(f"/api/v1/runs/{run_id}").json())
        if body["status"] in {"succeeded", "failed", "cancelled"}:
            return body
        time.sleep(0.01)
    raise AssertionError("run did not complete")


def _worker(name: str) -> dict[str, object]:
    return {
        "name": name,
        "description": None,
        "model_ref": "ollama://test",
        "graph_definition": {"version": 1, "runtime": "model-v1", "nodes": [], "edges": []},
    }


def _team(workers: list[dict[str, object]], edges: list[dict[str, str]] | None = None) -> dict[str, object]:
    return {
        "name": "Team",
        "description": None,
        "model_ref": "ollama://test",
        "graph_definition": {
            "version": 2,
            "runtime": "team-v1",
            "nodes": workers,
            "edges": edges or [],
        },
    }


class RecordingProvider(ModelProvider):
    provider_id = "ollama"

    def __init__(self) -> None:
        self.active = 0
        self.maximum = 0
        self.requests: list[str] = []

    async def complete(self, request: ModelRequest) -> ModelResponse:
        content = request.messages[0].content
        self.requests.append(content)
        self.active += 1
        self.maximum = max(self.maximum, self.active)
        try:
            await asyncio.sleep(0.03)
            return ModelResponse(
                "synthesis" if "Synthesize" in content else f"worker:{len(self.requests)}", "ollama", "test"
            )
        finally:
            self.active -= 1

    async def status(self) -> ProviderStatus:
        return ProviderStatus(self.provider_id, True, True)


def test_team_graph_rejects_invalid_refs_cycles_and_worker_limit(database_url: str) -> None:
    upgrade_database(database_url)
    router = ModelRouter({"ollama": RecordingProvider()}, "ollama://test")
    settings = _settings(database_url)
    with TestClient(create_app(settings, configured_router=router)) as client:
        seed_test_session(client, settings)
        missing = _team(
            [
                {
                    "id": "a",
                    "type": "agent-ref",
                    "label": "A",
                    "position": [0, 0],
                    "agent_id": "00000000-0000-0000-0000-000000000000",
                }
            ]
        )
        response = client.post("/api/v1/agents", json=missing)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "MISSING_AGENT_REFERENCE"

        created = client.post("/api/v1/agents", json=_worker("Worker")).json()
        worker_id = created["id"]
        cycle = _team(
            [
                {"id": "a", "type": "agent-ref", "label": "A", "position": [0, 0], "agent_id": worker_id},
                {"id": "b", "type": "agent-ref", "label": "B", "position": [1, 0], "agent_id": worker_id},
            ],
            [{"id": "ab", "source": "a", "target": "b"}, {"id": "ba", "source": "b", "target": "a"}],
        )
        assert client.post("/api/v1/agents", json=cycle).status_code == 422


def test_team_runs_children_in_parallel_persists_tree_and_authorizes_read(database_url: str) -> None:
    upgrade_database(database_url)
    provider = RecordingProvider()
    router = ModelRouter({"ollama": provider}, "ollama://test")
    settings = _settings(database_url)
    with TestClient(create_app(settings, configured_router=router)) as client:
        seed_test_session(client, settings)
        first = client.post("/api/v1/agents", json=_worker("Research")).json()
        second = client.post("/api/v1/agents", json=_worker("Review")).json()
        team = client.post(
            "/api/v1/agents",
            json=_team(
                [
                    {
                        "id": "research",
                        "type": "agent-ref",
                        "label": "Research",
                        "position": [0, 0],
                        "agent_id": first["id"],
                        "instructions": "research",
                    },
                    {
                        "id": "review",
                        "type": "agent-ref",
                        "label": "Review",
                        "position": [1, 0],
                        "agent_id": second["id"],
                        "instructions": "review",
                    },
                ]
            ),
        ).json()
        started = client.post(
            f"/api/v1/agents/{team['id']}/runs", json={"input_text": "task"}
        ).json()
        assert _wait(client, started["id"])["status"] == "succeeded"
        tree = client.get(f"/api/v1/runs/{started['id']}/tree")
        assert tree.status_code == 200
        assert {item["node_id"] for item in tree.json()["children"]} == {"research", "review"}
        assert all(item["run"]["status"] == "succeeded" for item in tree.json()["children"])
        assert provider.maximum == 2
        client.cookies.clear()
        assert client.get(f"/api/v1/runs/{started['id']}/tree").status_code == 403


def test_team_runs_dependencies_sequentially_and_passes_delimited_context(database_url: str) -> None:
    upgrade_database(database_url)
    provider = RecordingProvider()
    router = ModelRouter({"ollama": provider}, "ollama://test")
    settings = _settings(database_url)
    with TestClient(create_app(settings, configured_router=router)) as client:
        seed_test_session(client, settings)
        first = client.post("/api/v1/agents", json=_worker("First")).json()
        second = client.post("/api/v1/agents", json=_worker("Second")).json()
        team = client.post(
            "/api/v1/agents",
            json=_team(
                [
                    {"id": "first", "type": "agent-ref", "label": "First", "position": [0, 0], "agent_id": first["id"]},
                    {
                        "id": "second",
                        "type": "agent-ref",
                        "label": "Second",
                        "position": [1, 0],
                        "agent_id": second["id"],
                    },
                ],
                [{"id": "first-second", "source": "first", "target": "second"}],
            ),
        ).json()
        started = client.post(
            f"/api/v1/agents/{team['id']}/runs", json={"input_text": "task"}
        ).json()
        assert _wait(client, started["id"])["output_text"] == "synthesis"
        assert any("<agentgraph_upstream_results>" in request for request in provider.requests)


def test_stopping_team_cancels_live_children(database_url: str) -> None:
    class SlowProvider(RecordingProvider):
        async def complete(self, request: ModelRequest) -> ModelResponse:
            self.active += 1
            try:
                await asyncio.sleep(1)
                return ModelResponse("late", "ollama", "test")
            finally:
                self.active -= 1

    upgrade_database(database_url)
    router = ModelRouter({"ollama": SlowProvider()}, "ollama://test")
    settings = _settings(database_url)
    with TestClient(create_app(settings, configured_router=router)) as client:
        seed_test_session(client, settings)
        worker = client.post("/api/v1/agents", json=_worker("Slow")).json()
        team = client.post(
            "/api/v1/agents",
            json=_team(
                [
                    {
                        "id": "slow",
                        "type": "agent-ref",
                        "label": "Slow",
                        "position": [0, 0],
                        "agent_id": worker["id"],
                    }
                ]
            ),
        ).json()
        started = client.post(
            f"/api/v1/agents/{team['id']}/runs", json={"input_text": "cancel"}
        ).json()
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            if client.get(f"/api/v1/runs/{started['id']}/tree").json()["children"]:
                break
            time.sleep(0.01)
        stopped = client.post(f"/api/v1/runs/{started['id']}/stop")
        assert stopped.json()["status"] == "cancelled"
        tree = client.get(f"/api/v1/runs/{started['id']}/tree").json()
        assert tree["children"][0]["run"]["status"] == "cancelled"
