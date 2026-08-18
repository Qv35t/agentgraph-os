import asyncio
import time
from typing import cast

from fastapi.testclient import TestClient

from agentgraph.app import create_app
from agentgraph.domain.remote import RuntimeEventType
from agentgraph.models.contracts import ModelRequest, ModelResponse, ProviderStatus
from agentgraph.models.router import ModelProvider, ModelRouter
from agentgraph.persistence.database import create_database_engine, create_session_factory
from agentgraph.runtime.events import RuntimeEventBus
from agentgraph.runtime.graph import DeterministicGraphRuntime
from agentgraph.runtime.registry import RunRegistry
from agentgraph.services.manager import AgentManager
from agentgraph.services.remote import ApprovalService
from agentgraph.services.tools import DesktopLauncher, ToolService
from agentgraph.settings import Settings

from .conftest import seed_test_session, upgrade_database


def _remote_settings(database_url: str) -> Settings:
    return Settings(
        database_url=database_url,
        remote_control_enabled=True,
        remote_control_policies='{"operator":["read","execute","control","approve"]}',
    )


def _wait_for_run(client: TestClient, run_id: str) -> dict[str, object]:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/runs/{run_id}")
        body = cast(dict[str, object], response.json())
        if body["status"] in {"succeeded", "failed", "cancelled"}:
            return body
        time.sleep(0.01)
    raise AssertionError("Run did not reach a terminal state")


def test_memory_api_scopes_and_persists_run_usage(database_url: str) -> None:
    class ResponseProvider(ModelProvider):
        provider_id = "ollama"

        async def complete(self, request: ModelRequest) -> ModelResponse:
            assert "Aurora-17" in request.messages[1].content
            return ModelResponse('{"kind":"respond","message":"Aurora-17"}', "ollama", request.model_ref.model_id)

        async def status(self) -> ProviderStatus:
            return ProviderStatus(self.provider_id, True, True)

    upgrade_database(database_url)
    router = ModelRouter({"ollama": ResponseProvider()}, "ollama://qwen3-4b-nothink:latest")
    configured = _remote_settings(database_url)
    with TestClient(create_app(configured, configured_router=router)) as client:
        seed_test_session(client, configured)
        lexi = client.post("/api/v1/lexi/bootstrap")
        assert lexi.status_code == 201
        agent_id = lexi.json()["agent"]["id"]
        created = client.post(
            "/api/v1/memory",
            json={
                "agent_id": agent_id,
                "kind": "fact",
                "content": "Test project codename: Aurora-17",
                "tags": ["test"],
            },
        )
        assert created.status_code == 201
        memory_id = created.json()["id"]

        started = client.post(f"/api/v1/agents/{agent_id}/runs", json={"input_text": "codename"})
        assert started.status_code == 202
        completed = _wait_for_run(client, started.json()["id"])
        assert completed["output_text"] == "Aurora-17"

        usage = client.get(f"/api/v1/memory/runs/{started.json()['id']}")
        assert usage.json() == [{"memory_id": memory_id, "rank": 1, "score": 1.0, "deleted": False}]
        deleted = client.delete(f"/api/v1/memory/{memory_id}?agent_id={agent_id}")
        assert deleted.status_code == 204
        assert client.get(f"/api/v1/memory?agent_id={agent_id}").json() == []
        historical_usage = client.get(f"/api/v1/memory/runs/{started.json()['id']}").json()
        assert historical_usage[0]["deleted"] is True


def test_memory_api_requires_normal_remote_authorization(database_url: str) -> None:
    upgrade_database(database_url)
    settings = Settings(database_url=database_url)
    with TestClient(create_app(settings, DeterministicGraphRuntime())) as client:
        assert client.get("/api/v1/memory?agent_id=00000000-0000-0000-0000-000000000000").status_code == 403
        assert client.post("/api/v1/lexi/bootstrap").status_code == 403


def test_tool_service_approves_allowlisted_launch_and_rejects_untrusted_requests(database_url: str) -> None:
    class FakeLauncher(DesktopLauncher):
        def __init__(self) -> None:
            self.arguments: list[tuple[str, ...]] = []

        async def launch(self, arguments: tuple[str, ...]) -> None:
            self.arguments.append(arguments)

    async def scenario() -> None:
        engine = create_database_engine(database_url)
        sessions = create_session_factory(engine)
        manager = AgentManager(sessions, DeterministicGraphRuntime(), RunRegistry(), 0, 1)
        agent = await manager.create_agent(
            name="Tool owner", description=None, model_ref="auto://default", graph_definition={}
        )
        run = await manager.start_run(agent_id=agent.id, input_text="tool")
        await asyncio.sleep(0.01)
        events = RuntimeEventBus()
        approvals = ApprovalService(events)
        launcher = FakeLauncher()
        tools = ToolService(
            sessions,
            approvals,
            events,
            Settings(
                database_url=database_url,
                tools_enabled=True,
                tool_application_allowlist_json='{"browser":["safe-browser"]}',
            ),
            launcher,
        )
        pending = asyncio.create_task(
            tools.execute(run_id=run.id, tool_id="desktop.open_application", arguments={"application_id": "browser"})
        )
        for _ in range(100):
            approvals_list = approvals.list_pending()
            if approvals_list:
                break
            await asyncio.sleep(0.01)
        assert approvals_list[0].action == "desktop.open_application"
        await approvals.decide(approvals_list[0].id, True)
        result = await pending
        assert result.status.value == "succeeded"
        assert launcher.arguments == [("safe-browser",)]
        assert RuntimeEventType.TOOL_COMPLETED in [event.type for event in events.history(str(run.id))]

        blocked = await tools.execute(
            run_id=run.id,
            tool_id="desktop.open_application",
            arguments={"application_id": "browser", "flags": "--unsafe"},
        )
        assert blocked.error_code == "tool_invalid_arguments"
        unknown = await tools.execute(run_id=run.id, tool_id="shell.execute", arguments={})
        assert unknown.error_code == "tool_not_found"
        assert launcher.arguments == [("safe-browser",)]
        await manager.shutdown()
        await engine.dispose()

    upgrade_database(database_url)
    asyncio.run(scenario())
