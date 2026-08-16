import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from agentgraph.api.lexi import lexi_router
from agentgraph.api.memory import memory_router
from agentgraph.api.remote import remote_router
from agentgraph.api.routes import router
from agentgraph.api.tools import tool_router
from agentgraph.api.vision import vision_router
from agentgraph.models.router import DisabledProvider, ModelProvider, ModelRouter
from agentgraph.persistence.database import create_database_engine, create_session_factory
from agentgraph.providers.ollama import OllamaProvider
from agentgraph.providers.openai_compatible import OpenAICompatibleProvider
from agentgraph.providers.opencode import OpenCodeBridgeProvider
from agentgraph.runtime.events import RuntimeEventBus
from agentgraph.runtime.graph import ModelGraphRuntime
from agentgraph.runtime.lexi import LexiGraphRuntime
from agentgraph.runtime.registry import RunRegistry
from agentgraph.runtime.selector import WorkflowRuntime
from agentgraph.runtime.team import TeamGraphRuntime
from agentgraph.services.lexi import LexiTemplateService
from agentgraph.services.manager import AgentManager, AgentRuntime
from agentgraph.services.memory import MemoryService
from agentgraph.services.remote import ApprovalService, AuthorizationService, RemoteCommandService
from agentgraph.services.tools import ToolService
from agentgraph.services.vision import VisionService
from agentgraph.settings import Settings


def create_app(
    settings: Settings | None = None,
    runtime: AgentRuntime | None = None,
    configured_router: ModelRouter | None = None,
) -> FastAPI:
    runtime_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_database_engine(runtime_settings.database_url)
        http_client = httpx.AsyncClient(timeout=httpx.Timeout(60, connect=5), trust_env=False)
        registry = RunRegistry()
        event_bus = RuntimeEventBus()
        manager: AgentManager | None = None

        async def close_resources() -> None:
            try:
                await http_client.aclose()
            finally:
                await engine.dispose()

        try:
            if configured_router is None:
                providers: dict[str, ModelProvider] = {
                    "ollama": OllamaProvider(http_client, runtime_settings.ollama_base_url)
                }
                if runtime_settings.opencode_base_url:
                    providers["opencode"] = OpenCodeBridgeProvider(
                        http_client,
                        runtime_settings.opencode_base_url,
                        runtime_settings.opencode_basic_auth_username,
                        runtime_settings.opencode_basic_auth_password,
                    )
                else:
                    providers["opencode"] = DisabledProvider("opencode")
                if runtime_settings.openai_compatible_base_url:
                    providers["openrouter"] = OpenAICompatibleProvider(
                        "openrouter",
                        http_client,
                        runtime_settings.openai_compatible_base_url,
                        runtime_settings.openai_compatible_api_key,
                    )
                else:
                    providers["openrouter"] = DisabledProvider("openrouter")
                model_router = ModelRouter(providers, "ollama://qwen3-4b-nothink:latest")
            else:
                model_router = configured_router
            approvals = ApprovalService(event_bus)
            memory_service = MemoryService(create_session_factory(engine), runtime_settings)
            tool_service = ToolService(create_session_factory(engine), approvals, event_bus, runtime_settings)
            selected_runtime = runtime or WorkflowRuntime(
                ModelGraphRuntime(model_router),
                LexiGraphRuntime(model_router, memory_service, tool_service, runtime_settings),
            )
            manager = AgentManager(
                create_session_factory(engine),
                selected_runtime,
                registry,
                runtime_settings.runtime_delay_seconds,
                runtime_settings.cancellation_timeout_seconds,
                event_bus,
                runtime_settings.project_id,
                runtime_settings,
            )
            if isinstance(selected_runtime, WorkflowRuntime):
                selected_runtime.bind_team(TeamGraphRuntime(model_router, manager, runtime_settings))
            await manager.recover_stale_runs()
            app.state.agent_manager = manager
            app.state.model_router = model_router
            app.state.event_bus = event_bus
            authorization = AuthorizationService(
                runtime_settings.remote_control_enabled, runtime_settings.remote_control_policies
            )
            app.state.authorization = authorization
            app.state.remote_commands = RemoteCommandService(manager, model_router, authorization)
            app.state.approvals = approvals
            app.state.memory_service = memory_service
            app.state.tool_service = tool_service
            app.state.lexi_service = LexiTemplateService(manager)
            app.state.vision_service = VisionService(
                create_session_factory(engine), model_router, event_bus, runtime_settings
            )
            await app.state.vision_service.recover_stale_analyses()
            app.state.settings = runtime_settings
            yield
        finally:
            if manager is None:
                await close_resources()
            else:
                safe_to_close = False
                try:
                    await app.state.vision_service.shutdown()
                    safe_to_close = await manager.shutdown()
                finally:
                    if safe_to_close:
                        await close_resources()
                    else:

                        async def close_after_runs() -> None:
                            try:
                                await registry.wait_all()
                            finally:
                                await close_resources()

                        app.state.deferred_cleanup = asyncio.create_task(close_after_runs())

    app = FastAPI(title="AgentGraph OS", lifespan=lifespan)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, error: HTTPException) -> JSONResponse:
        if isinstance(error.detail, dict) and "error" in error.detail:
            return JSONResponse(status_code=error.status_code, content=error.detail, headers=error.headers)
        return JSONResponse(status_code=error.status_code, content={"detail": error.detail}, headers=error.headers)

    if runtime_settings.legacy_api_enabled:
        app.include_router(router)
    app.include_router(remote_router)
    app.include_router(memory_router)
    app.include_router(lexi_router)
    app.include_router(tool_router)
    app.include_router(vision_router)
    return app


app = create_app()
