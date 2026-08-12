import asyncio
import json
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from agentgraph.app import create_app
from agentgraph.models.contracts import (
    ModelErrorCode,
    ModelMessage,
    ModelRef,
    ModelRequest,
    ModelResponse,
    ModelRouterError,
    ModelUsage,
    ProviderStatus,
)
from agentgraph.models.router import ModelProvider, ModelRouter
from agentgraph.persistence.database import create_database_engine, create_session_factory
from agentgraph.providers.ollama import OllamaProvider
from agentgraph.providers.openai_compatible import OpenAICompatibleProvider
from agentgraph.providers.opencode import OpenCodeBridgeProvider
from agentgraph.runtime.graph import ModelGraphRuntime
from agentgraph.runtime.registry import RunRegistry
from agentgraph.services.manager import AgentManager
from agentgraph.settings import Settings

from .conftest import upgrade_database


def model_request(reference: str, content: str = "hello") -> ModelRequest:
    return ModelRequest(
        model_ref=ModelRef.parse(reference),
        messages=(ModelMessage(role="user", content=content),),
    )


def test_model_ref_and_local_default_routing() -> None:
    class StubProvider(ModelProvider):
        provider_id = "ollama"

        async def complete(self, request: ModelRequest) -> ModelResponse:
            return ModelResponse(request.messages[0].content, self.provider_id, request.model_ref.model_id)

        async def status(self) -> ProviderStatus:
            return ProviderStatus(self.provider_id, True, True, ("qwen3-4b-nothink:latest",))

    async def scenario() -> None:
        router = ModelRouter({"ollama": StubProvider()}, "ollama://qwen3-4b-nothink:latest")
        response = await router.complete("auto://default", [ModelMessage(role="user", content="hello")])
        assert response.model_id == "qwen3-4b-nothink:latest"
        runtime = ModelGraphRuntime(router)
        graph_response = await runtime.invoke(
            agent_id=uuid4(),
            run_id=uuid4(),
            input_text="graph",
            model_ref="auto://default",
        )
        assert graph_response.content == "graph"

    asyncio.run(scenario())
    assert ModelRef.parse("opencode://openai/gpt-5").model_id == "openai/gpt-5"
    with pytest.raises(ModelRouterError):
        ModelRef.parse("ollama://bad model")
    with pytest.raises(ModelRouterError):
        ModelRef.parse("invalid")


def test_ollama_adapter_completion_and_discovery() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen3:4B"}]})
        body = json.loads(request.content)
        assert body["stream"] is False
        return httpx.Response(
            200,
            json={
                "message": {"content": "local answer"},
                "done_reason": "stop",
                "prompt_eval_count": 3,
                "eval_count": 4,
            },
        )

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OllamaProvider(client)
            response = await provider.complete(model_request("ollama://qwen3:4B"))
            assert response.content == "local answer"
            assert response.usage.total_tokens == 7
            status = await provider.status()
            assert status.available
            assert status.models == ("qwen3:4B",)

    asyncio.run(scenario())


def test_ollama_timeout_and_invalid_response_are_normalized() -> None:
    async def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    async def invalid_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True})

    async def scenario() -> None:
        for handler, expected in (
            (timeout_handler, ModelErrorCode.TIMEOUT),
            (invalid_handler, ModelErrorCode.INVALID_RESPONSE),
        ):
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                provider = OllamaProvider(client)
                with pytest.raises(ModelRouterError) as caught:
                    await provider.complete(model_request("ollama://qwen3:4B"))
                assert caught.value.code == expected

    asyncio.run(scenario())


def test_router_never_falls_back_to_cloud() -> None:
    async def scenario() -> None:
        router = ModelRouter({}, "ollama://qwen3-4b-nothink:latest")
        with pytest.raises(ModelRouterError) as caught:
            await router.complete("auto://default", [ModelMessage(role="user", content="hello")])
        assert caught.value.code == ModelErrorCode.PROVIDER_UNAVAILABLE

    asyncio.run(scenario())


def test_legacy_model_reference_maps_to_local_default() -> None:
    class StubProvider(ModelProvider):
        provider_id = "ollama"

        async def complete(self, request: ModelRequest) -> ModelResponse:
            return ModelResponse(request.messages[0].content, self.provider_id, request.model_ref.model_id)

        async def status(self) -> ProviderStatus:
            return ProviderStatus(self.provider_id, True, True)

    async def scenario() -> None:
        router = ModelRouter({"ollama": StubProvider()}, "ollama://qwen3-4b-nothink:latest")
        response = await router.complete("local/default", [ModelMessage(role="user", content="legacy")])
        assert response.model_id == "qwen3-4b-nothink:latest"

    asyncio.run(scenario())


def test_opencode_bridge_disables_tools_and_normalizes_response() -> None:
    requests: list[tuple[str, dict[str, object]]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else {}
        requests.append((request.url.path, body))
        if request.url.path == "/global/health":
            return httpx.Response(200, json={"healthy": True, "version": "1.18.16"})
        if request.url.path == "/config/providers":
            return httpx.Response(200, json={"providers": [{"id": "openai", "models": {"gpt-5": {}}}]})
        if request.method == "POST" and request.url.path == "/session":
            return httpx.Response(200, json={"id": "ses_test"})
        if request.method == "POST" and request.url.path.endswith("/message"):
            return httpx.Response(
                200,
                json={
                    "info": {
                        "finish": "stop",
                        "tokens": {"input": 5, "output": 6, "total": 11},
                    },
                    "parts": [{"type": "text", "text": "subscription answer"}],
                },
            )
        return httpx.Response(200, json=True)

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenCodeBridgeProvider(client, "http://127.0.0.1:4096")
            status = await provider.status()
            assert status.models == ("openai/gpt-5",)
            response = await provider.complete(model_request("opencode://openai/gpt-5"))
            assert response.content == "subscription answer"
            assert response.usage.total_tokens == 11

    asyncio.run(scenario())
    session_payload = next(body for path, body in requests if path == "/session")
    assert session_payload["permission"] == [{"permission": "*", "pattern": "*", "action": "deny"}]
    assert any(path == "/session/ses_test" for path, _ in requests)
    message_payload = next(body for path, body in requests if path.endswith("/message"))
    assert message_payload["tools"] == {"*": False}


def test_opencode_cancellation_aborts_and_deletes_session(database_url: str) -> None:
    paths: list[str] = []
    message_started = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/session":
            return httpx.Response(200, json={"id": "ses_cancel"})
        if request.url.path.endswith("/message"):
            message_started.set()
            await asyncio.Event().wait()
        return httpx.Response(200, json=True)

    upgrade_database(database_url)

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenCodeBridgeProvider(client, "http://127.0.0.1:4096")
            router = ModelRouter({"opencode": provider}, "ollama://qwen3-4b-nothink:latest")
            engine = create_database_engine(database_url)
            manager = AgentManager(
                create_session_factory(engine),
                ModelGraphRuntime(router),
                RunRegistry(),
                runtime_delay_seconds=0,
                cancellation_timeout_seconds=1,
            )
            agent = await manager.create_agent(
                name="Cancel OpenCode",
                description=None,
                model_ref="opencode://openai/gpt-5",
                graph_definition={},
            )
            run = await manager.start_run(agent_id=agent.id, input_text="cancel")
            await message_started.wait()
            stopped = await manager.stop_run(run.id)
            assert stopped.status.value == "cancelled"
            assert await manager.shutdown()
            await engine.dispose()

    asyncio.run(scenario())
    assert "/session/ses_cancel/abort" in paths
    assert "/session/ses_cancel" in paths


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        ({"name": "ProviderError", "data": {"statusCode": 401}}, ModelErrorCode.AUTHENTICATION_FAILED),
        ({"name": "ProviderError", "data": {"statusCode": 429}}, ModelErrorCode.RATE_LIMITED),
        ({"name": "ModelNotFoundError", "statusCode": 404}, ModelErrorCode.MODEL_NOT_FOUND),
        ({"name": "TimeoutError"}, ModelErrorCode.TIMEOUT),
        ({"name": "AbortedError"}, ModelErrorCode.CANCELLED),
    ],
)
def test_opencode_structured_errors_are_normalized(error: dict[str, object], expected: ModelErrorCode) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/session":
            return httpx.Response(200, json={"id": "ses_error"})
        if request.url.path.endswith("/message"):
            return httpx.Response(200, json={"info": {"error": error}, "parts": []})
        return httpx.Response(200, json=True)

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenCodeBridgeProvider(client, "http://127.0.0.1:4096")
            with pytest.raises(ModelRouterError) as caught:
                await provider.complete(model_request("opencode://openai/gpt-5"))
            assert caught.value.code == expected

    asyncio.run(scenario())


def test_opencode_timeout_still_aborts_and_deletes() -> None:
    paths: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/session":
            return httpx.Response(200, json={"id": "ses_timeout"})
        if request.url.path.endswith("/message"):
            raise httpx.ReadTimeout("timeout", request=request)
        if request.url.path.endswith("/abort"):
            return httpx.Response(500)
        return httpx.Response(200, json=True)

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenCodeBridgeProvider(client, "http://127.0.0.1:4096")
            with pytest.raises(ModelRouterError) as caught:
                await provider.complete(model_request("opencode://openai/gpt-5"))
            assert caught.value.code == ModelErrorCode.TIMEOUT

    asyncio.run(scenario())
    assert "/session/ses_timeout/abort" in paths
    assert "/session/ses_timeout" in paths


def test_opencode_malformed_envelope_is_normalized() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/session":
            return httpx.Response(200, json={"id": "ses_malformed"})
        if request.url.path.endswith("/message"):
            return httpx.Response(
                200,
                json={
                    "info": {"tokens": {}},
                    "parts": [{"type": "text", "text": "partial"}, "not-an-object"],
                },
            )
        return httpx.Response(200, json=True)

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenCodeBridgeProvider(client, "http://127.0.0.1:4096")
            with pytest.raises(ModelRouterError) as caught:
                await provider.complete(model_request("opencode://openai/gpt-5"))
            assert caught.value.code == ModelErrorCode.INVALID_RESPONSE

    asyncio.run(scenario())


def test_model_graph_persists_normalized_metadata(database_url: str) -> None:
    class StubProvider(ModelProvider):
        provider_id = "ollama"

        async def complete(self, request: ModelRequest) -> ModelResponse:
            return ModelResponse(
                content=f"llm:{request.messages[0].content}",
                provider_id=self.provider_id,
                model_id=request.model_ref.model_id,
                finish_reason="stop",
                usage=ModelUsage(2, 3, 5),
                latency_ms=7,
            )

        async def status(self) -> ProviderStatus:
            return ProviderStatus(self.provider_id, True, True)

    upgrade_database(database_url)
    router = ModelRouter({"ollama": StubProvider()}, "ollama://qwen3-4b-nothink:latest")
    with TestClient(
        create_app(Settings(database_url=database_url, legacy_api_enabled=True), ModelGraphRuntime(router))
    ) as client:
        agent = client.post("/api/agents/create", json={"name": "LLM"}).json()
        run = client.post("/api/agents/run", json={"agent_id": agent["id"], "input_text": "hello"}).json()
        for _ in range(100):
            result = client.get(f"/api/runs/{run['id']}").json()
            if result["status"] == "succeeded":
                break
        assert result["output_text"] == "llm:hello"
        assert result["provider_id"] == "ollama"
        assert result["total_tokens"] == 5


def test_model_graph_shutdown_keeps_resources_open_until_stubborn_provider_finishes(
    database_url: str,
) -> None:
    upgrade_database(database_url)

    class StubbornProvider(ModelProvider):
        provider_id = "ollama"

        def __init__(self) -> None:
            self.entered = asyncio.Event()
            self.release = asyncio.Event()

        async def complete(self, request: ModelRequest) -> ModelResponse:
            self.entered.set()
            while not self.release.is_set():
                try:
                    await self.release.wait()
                except asyncio.CancelledError:
                    continue
            return ModelResponse("late", self.provider_id, request.model_ref.model_id)

        async def status(self) -> ProviderStatus:
            return ProviderStatus(self.provider_id, True, True)

    async def scenario() -> None:
        engine = create_database_engine(database_url)
        provider = StubbornProvider()
        router = ModelRouter({"ollama": provider}, "ollama://qwen3-4b-nothink:latest")
        manager = AgentManager(
            create_session_factory(engine),
            ModelGraphRuntime(router),
            RunRegistry(),
            runtime_delay_seconds=0,
            cancellation_timeout_seconds=0.01,
        )
        agent = await manager.create_agent(
            name="Stubborn",
            description=None,
            model_ref="auto://default",
            graph_definition={},
        )
        await manager.start_run(agent_id=agent.id, input_text="wait")
        await provider.entered.wait()
        assert await manager.shutdown() is False
        provider.release.set()
        await asyncio.sleep(0.02)
        await engine.dispose()

    asyncio.run(scenario())


def test_openai_compatible_errors_are_normalized() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-secret"
        return httpx.Response(401, json={"error": {"message": "raw secret response"}})

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider("openrouter", client, "https://example.test/v1", "test-secret")
            with pytest.raises(ModelRouterError) as caught:
                await provider.complete(model_request("openrouter://model"))
            assert caught.value.code == ModelErrorCode.AUTHENTICATION_FAILED
            assert "raw secret response" not in str(caught.value)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [(401, ModelErrorCode.AUTHENTICATION_FAILED), (429, ModelErrorCode.RATE_LIMITED)],
)
def test_openai_discovery_errors_are_normalized(status_code: int, expected: ModelErrorCode) -> None:
    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(status_code))) as client:
            provider = OpenAICompatibleProvider("openrouter", client, "https://example.test/v1", "secret")
            status = await provider.status()
            assert status.error_code == expected

    asyncio.run(scenario())


def test_openai_discovery_timeout_is_normalized() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider("openrouter", client, "https://example.test/v1", "secret")
            status = await provider.status()
            assert status.error_code == ModelErrorCode.TIMEOUT

    asyncio.run(scenario())


def test_credentialed_and_opencode_urls_are_restricted() -> None:
    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200))) as client:
            with pytest.raises(ModelRouterError):
                OpenCodeBridgeProvider(client, "http://remote.example:4096")
            with pytest.raises(ModelRouterError):
                OpenAICompatibleProvider("openrouter", client, "http://remote.example/v1", "secret")

    asyncio.run(scenario())
