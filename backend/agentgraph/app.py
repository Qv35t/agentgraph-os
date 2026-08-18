import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from agentgraph.api.auth import auth_router
from agentgraph.api.lexi import lexi_router
from agentgraph.api.memory import memory_router
from agentgraph.api.nodes import node_router
from agentgraph.api.recovery import recovery_router
from agentgraph.api.remote import remote_router
from agentgraph.api.security import security_router
from agentgraph.api.tools import tool_router
from agentgraph.api.vision import vision_router
from agentgraph.api.workers import worker_router
from agentgraph.domain.remote import Principal
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
from agentgraph.services.auth import AuthenticationError, AuthService
from agentgraph.services.lexi import LexiTemplateService
from agentgraph.services.manager import AgentManager, AgentRuntime
from agentgraph.services.memory import MemoryService
from agentgraph.services.nodes import NodeService
from agentgraph.services.recovery import RecoveryService
from agentgraph.services.remote import (
    ApprovalService,
    AuthorizationService,
    RemoteCommandService,
    set_request_principal,
)
from agentgraph.services.security import SecurityService
from agentgraph.services.tools import ToolService
from agentgraph.services.vault import MasterKeyStore, VaultService
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
        liveness_task: asyncio.Task[None] | None = None

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
            session_factory = create_session_factory(engine)
            key_store = MasterKeyStore(runtime_settings.security_master_key_path)
            auth_service = AuthService(session_factory, runtime_settings, key_store)
            security_service = SecurityService(session_factory)
            vault_service = VaultService(session_factory, runtime_settings, key_store)
            approvals = ApprovalService(event_bus)
            recovery_service = RecoveryService(session_factory, event_bus, runtime_settings)
            memory_service = MemoryService(session_factory, runtime_settings)
            tool_service = ToolService(
                session_factory, approvals, event_bus, runtime_settings, recovery=recovery_service
            )
            selected_runtime = runtime or WorkflowRuntime(
                ModelGraphRuntime(model_router),
                LexiGraphRuntime(model_router, memory_service, tool_service, runtime_settings),
            )
            manager = AgentManager(
                session_factory,
                selected_runtime,
                registry,
                runtime_settings.runtime_delay_seconds,
                runtime_settings.cancellation_timeout_seconds,
                event_bus,
                runtime_settings.project_id,
                runtime_settings,
                recovery_service,
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
            app.state.auth_service = auth_service
            app.state.security_service = security_service
            app.state.vault_service = vault_service
            app.state.node_service = NodeService(session_factory, event_bus, runtime_settings)
            if runtime_settings.node_role.value == "core":
                core_name = runtime_settings.node_name
                if core_name == "AgentGraph Worker":
                    core_name = "AgentGraph Core"
                await app.state.node_service.ensure_core(core_name)
            app.state.remote_commands = RemoteCommandService(manager, model_router, authorization)
            app.state.approvals = approvals
            app.state.memory_service = memory_service
            app.state.tool_service = tool_service
            app.state.recovery_service = recovery_service
            app.state.lexi_service = LexiTemplateService(manager)
            app.state.vision_service = VisionService(
                create_session_factory(engine), model_router, event_bus, runtime_settings
            )
            await app.state.vision_service.recover_stale_analyses()
            app.state.settings = runtime_settings
            if runtime_settings.node_role.value == "core":
                liveness_task = asyncio.create_task(_node_liveness_loop(app.state.node_service, runtime_settings))
            yield
        finally:
            for task in (liveness_task,):
                if task is not None:
                    task.cancel()
            for task in (liveness_task,):
                if task is not None:
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
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

    @app.middleware("http")
    async def authenticate_request(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        auth_service = getattr(request.app.state, "auth_service", None)
        principal = None
        if isinstance(auth_service, AuthService):
            try:
                session_principal = await auth_service.principal_from_session_token(
                    request.cookies.get(runtime_settings.session_cookie_name)
                )
                principal = session_principal
            except AuthenticationError:
                pass
        token = set_request_principal(
            None if principal is None else Principal(identity=principal.user_id, permissions=principal.permissions)
        )
        try:
            if (
                principal is not None
                and isinstance(auth_service, AuthService)
                and request.method not in {"GET", "HEAD", "OPTIONS"}
                and request.url.path
                not in {
                    "/api/v1/auth/bootstrap",
                    "/api/v1/auth/passkeys/authentication/options",
                    "/api/v1/auth/passkeys/authentication/verify",
                    "/api/v1/auth/passkeys/registration/verify",
                }
            ):
                try:
                    await auth_service.require_csrf(
                        principal,
                        request.headers.get("x-agentgraph-csrf"),
                        request.headers.get("origin"),
                    )
                except AuthenticationError as error:
                    return JSONResponse(
                        status_code=403,
                        content={"error": {"code": "CSRF_DENIED", "message": str(error), "details": {}}},
                    )
            return await call_next(request)
        finally:
            token.var.reset(token)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, error: HTTPException) -> JSONResponse:
        if isinstance(error.detail, dict) and "error" in error.detail:
            return JSONResponse(status_code=error.status_code, content=error.detail, headers=error.headers)
        return JSONResponse(status_code=error.status_code, content={"detail": error.detail}, headers=error.headers)

    app.include_router(auth_router)
    app.include_router(security_router)
    app.include_router(remote_router)
    app.include_router(node_router)
    app.include_router(recovery_router)
    app.include_router(worker_router)
    app.include_router(memory_router)
    app.include_router(lexi_router)
    app.include_router(tool_router)
    app.include_router(vision_router)
    return app


app = create_app()


async def _node_liveness_loop(service: NodeService, settings: Settings) -> None:
    while True:
        await asyncio.sleep(min(settings.worker_heartbeat_timeout_seconds / 2, 10))
        await service.mark_stale_offline()
