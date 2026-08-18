# ruff: noqa: E501

from typing import cast
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from agentgraph.api.schemas import (
    AgentResponse,
    CreateAgentRequest,
    HealthResponse,
    ProviderStatusResponse,
    RunResponse,
    RunTreeNodeResponse,
    UpdateAgentGraphRequest,
)
from agentgraph.domain.entities import Agent, AgentRun, RunTreeNode
from agentgraph.domain.remote import ApprovalRequest, Permission, Principal, RuntimeCommand, RuntimeCommandType
from agentgraph.models.contracts import ProviderStatus
from agentgraph.runtime.events import RuntimeEventBus, event_json
from agentgraph.services.auth import AuthenticationError, AuthService
from agentgraph.services.errors import AgentNotFoundError, LifecycleConflictError, OrchestrationError, RunNotFoundError
from agentgraph.services.remote import (
    ApprovalService,
    AuthorizationError,
    AuthorizationService,
    RemoteCommandService,
    set_request_principal,
)

remote_router = APIRouter()


class StartRunPayload(BaseModel):
    input_text: str = Field(min_length=1, max_length=100_000)


class ApprovalPayload(BaseModel):
    action: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10_000)
    run_id: str | None = None
    task_id: str | None = None


def _authorization(request: Request) -> AuthorizationService:
    return cast(AuthorizationService, request.app.state.authorization)


def _commands(request: Request) -> RemoteCommandService:
    return cast(RemoteCommandService, request.app.state.remote_commands)


def _events(request: Request) -> RuntimeEventBus:
    return cast(RuntimeEventBus, request.app.state.event_bus)


def _approvals(request: Request) -> ApprovalService:
    return cast(ApprovalService, request.app.state.approvals)


def _principal(request: Request, identity: str | None, permission: Permission) -> Principal:
    try:
        principal = _authorization(request).principal(identity)
        _authorization(request).require(principal, permission)
        return principal
    except AuthorizationError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": str(error), "details": {}}},
        ) from error


def _command(
    type: RuntimeCommandType,
    principal: Principal,
    target_id: str | None = None,
    **payload: object,
) -> RuntimeCommand:
    return RuntimeCommand(f"cmd_{uuid4().hex}", type, principal, target_id, payload)


@remote_router.get("/api/v1/system")
async def system(request: Request, x_agentgraph_identity: str | None = Header(default=None)) -> dict[str, object]:
    _principal(request, x_agentgraph_identity, Permission.READ)
    return {"project_id": request.app.state.settings.project_id, "remote_control": True}


@remote_router.get("/api/v1/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@remote_router.get("/api/v1/projects")
async def list_projects(
    request: Request, x_agentgraph_identity: str | None = Header(default=None)
) -> list[dict[str, str]]:
    _principal(request, x_agentgraph_identity, Permission.READ)
    return [{"project_id": request.app.state.settings.project_id, "name": "Local project"}]


@remote_router.get("/api/v1/projects/{project_id}")
async def get_project(
    request: Request, project_id: str, x_agentgraph_identity: str | None = Header(default=None)
) -> dict[str, str]:
    _principal(request, x_agentgraph_identity, Permission.READ)
    if project_id != request.app.state.settings.project_id:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "PROJECT_NOT_FOUND", "message": "Project was not found", "details": {}}},
        )
    return {"project_id": project_id, "name": "Local project"}


@remote_router.get("/api/v1/agents", response_model=list[AgentResponse])
async def agents(request: Request, x_agentgraph_identity: str | None = Header(default=None)) -> list[AgentResponse]:
    principal = _principal(request, x_agentgraph_identity, Permission.READ)
    agent_list = cast(
        list[Agent],
        await _commands(request).dispatch(_command(RuntimeCommandType.LIST_AGENTS, principal)),
    )
    return [AgentResponse.from_domain(agent) for agent in agent_list]


@remote_router.post("/api/v1/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: Request, payload: CreateAgentRequest, x_agentgraph_identity: str | None = Header(default=None)
) -> AgentResponse:
    principal = _principal(request, x_agentgraph_identity, Permission.EXECUTE)
    try:
        agent = cast(
            Agent,
            await _commands(request).dispatch(
                _command(
                    RuntimeCommandType.CREATE_AGENT,
                    principal,
                    name=payload.name,
                    description=payload.description,
                    model_ref=payload.model_ref,
                    graph_definition=payload.graph_definition.model_dump(mode="json", exclude_none=True),
                )
            ),
        )
    except OrchestrationError as error:
        raise _orchestration_http(error) from error
    return AgentResponse.from_domain(agent)


@remote_router.get("/api/v1/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    request: Request, agent_id: str, x_agentgraph_identity: str | None = Header(default=None)
) -> AgentResponse:
    principal = _principal(request, x_agentgraph_identity, Permission.READ)
    try:
        agent = cast(
            Agent,
            await _commands(request).dispatch(_command(RuntimeCommandType.GET_AGENT, principal, agent_id)),
        )
    except (AgentNotFoundError, ValueError) as error:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "AGENT_NOT_FOUND", "message": "Agent was not found", "details": {}}},
        ) from error
    except OrchestrationError as error:
        raise _orchestration_http(error) from error
    return AgentResponse.from_domain(agent)


@remote_router.patch("/api/v1/agents/{agent_id}/graph", response_model=AgentResponse)
async def update_agent_graph(
    request: Request,
    agent_id: str,
    payload: UpdateAgentGraphRequest,
    x_agentgraph_identity: str | None = Header(default=None),
) -> AgentResponse:
    principal = _principal(request, x_agentgraph_identity, Permission.EXECUTE)
    try:
        agent = cast(
            Agent,
            await _commands(request).dispatch(
                _command(
                    RuntimeCommandType.UPDATE_AGENT_GRAPH,
                    principal,
                    agent_id,
                    graph_definition=payload.graph_definition.model_dump(mode="json", exclude_none=True),
                )
            ),
        )
    except (AgentNotFoundError, ValueError) as error:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "AGENT_NOT_FOUND", "message": "Agent was not found", "details": {}}},
        ) from error
    except OrchestrationError as error:
        raise _orchestration_http(error) from error
    return AgentResponse.from_domain(agent)


@remote_router.get("/api/v1/agents/{agent_id}/runs", response_model=list[RunResponse])
async def list_agent_runs(
    request: Request, agent_id: str, x_agentgraph_identity: str | None = Header(default=None)
) -> list[RunResponse]:
    principal = _principal(request, x_agentgraph_identity, Permission.READ)
    try:
        runs = cast(
            list[AgentRun],
            await _commands(request).dispatch(_command(RuntimeCommandType.LIST_RUNS, principal, agent_id)),
        )
    except (AgentNotFoundError, ValueError) as error:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "AGENT_NOT_FOUND", "message": "Agent was not found", "details": {}}},
        ) from error
    return [RunResponse.from_domain(run) for run in runs]


@remote_router.get("/api/v1/runs/{run_id}", response_model=RunResponse)
async def get_run(
    request: Request, run_id: str, x_agentgraph_identity: str | None = Header(default=None)
) -> RunResponse:
    principal = _principal(request, x_agentgraph_identity, Permission.READ)
    try:
        run = cast(
            AgentRun,
            await _commands(request).dispatch(_command(RuntimeCommandType.GET_RUN, principal, run_id)),
        )
    except (RunNotFoundError, ValueError) as error:
        raise HTTPException(
            status_code=404, detail={"error": {"code": "RUN_NOT_FOUND", "message": "Run was not found", "details": {}}}
        ) from error
    return RunResponse.from_domain(run)


@remote_router.post("/api/v1/agents/{agent_id}/runs", response_model=RunResponse, status_code=202)
async def start_run(
    request: Request, agent_id: str, payload: StartRunPayload, x_agentgraph_identity: str | None = Header(default=None)
) -> RunResponse:
    principal = _principal(request, x_agentgraph_identity, Permission.EXECUTE)
    try:
        run = cast(
            AgentRun,
            await _commands(request).dispatch(
                _command(RuntimeCommandType.START_RUN, principal, agent_id, input_text=payload.input_text)
            ),
        )
    except (AgentNotFoundError, ValueError) as error:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "AGENT_NOT_FOUND", "message": "Agent was not found", "details": {}}},
        ) from error
    except LifecycleConflictError as error:
        raise HTTPException(
            status_code=409, detail={"error": {"code": "RUN_CONFLICT", "message": str(error), "details": {}}}
        ) from error
    except OrchestrationError as error:
        raise _orchestration_http(error) from error
    return RunResponse.from_domain(run)


@remote_router.get("/api/v1/runs/{run_id}/tree", response_model=RunTreeNodeResponse)
async def get_run_tree(
    request: Request, run_id: str, x_agentgraph_identity: str | None = Header(default=None)
) -> RunTreeNodeResponse:
    principal = _principal(request, x_agentgraph_identity, Permission.READ)
    try:
        tree = cast(
            RunTreeNode,
            await _commands(request).dispatch(_command(RuntimeCommandType.GET_RUN_TREE, principal, run_id)),
        )
    except (RunNotFoundError, ValueError) as error:
        raise HTTPException(
            status_code=404, detail={"error": {"code": "RUN_NOT_FOUND", "message": "Run was not found", "details": {}}}
        ) from error
    return RunTreeNodeResponse.from_domain(tree)


@remote_router.post("/api/v1/runs/{run_id}/stop", response_model=RunResponse)
async def stop_run(
    request: Request, run_id: str, x_agentgraph_identity: str | None = Header(default=None)
) -> RunResponse:
    principal = _principal(request, x_agentgraph_identity, Permission.CONTROL)
    try:
        run = cast(
            AgentRun,
            await _commands(request).dispatch(_command(RuntimeCommandType.STOP_RUN, principal, run_id)),
        )
    except (RunNotFoundError, ValueError) as error:
        raise HTTPException(
            status_code=404, detail={"error": {"code": "RUN_NOT_FOUND", "message": "Run was not found", "details": {}}}
        ) from error
    except LifecycleConflictError as error:
        raise HTTPException(
            status_code=409, detail={"error": {"code": "RUN_CONFLICT", "message": str(error), "details": {}}}
        ) from error
    return RunResponse.from_domain(run)


@remote_router.get("/api/v1/providers", response_model=list[ProviderStatusResponse])
async def providers(
    request: Request, x_agentgraph_identity: str | None = Header(default=None)
) -> list[ProviderStatusResponse]:
    principal = _principal(request, x_agentgraph_identity, Permission.READ)
    statuses = cast(
        list[ProviderStatus],
        await _commands(request).dispatch(_command(RuntimeCommandType.LIST_PROVIDERS, principal)),
    )
    return [ProviderStatusResponse.from_domain(item) for item in statuses]


@remote_router.get("/api/v1/events")
async def events(
    request: Request, run_id: str | None = None, x_agentgraph_identity: str | None = Header(default=None)
) -> list[dict[str, object]]:
    _principal(request, x_agentgraph_identity, Permission.READ)
    return [event_json(event) for event in _events(request).history(run_id)]


@remote_router.post("/api/v1/approvals")
async def create_approval(
    request: Request, payload: ApprovalPayload, x_agentgraph_identity: str | None = Header(default=None)
) -> dict[str, object]:
    principal = _principal(request, x_agentgraph_identity, Permission.APPROVE)
    approval = await _approvals(request).create(
        project_id=request.app.state.settings.project_id,
        action=payload.action,
        description=payload.description,
        requested_by=principal.identity,
        run_id=payload.run_id,
        task_id=payload.task_id,
    )
    return _approval_json(approval)


@remote_router.get("/api/v1/approvals")
async def approvals(
    request: Request, x_agentgraph_identity: str | None = Header(default=None)
) -> list[dict[str, object]]:
    _principal(request, x_agentgraph_identity, Permission.READ)
    project_id = request.app.state.settings.project_id
    return [_approval_json(approval) for approval in _approvals(request).list_pending(project_id)]


@remote_router.post("/api/v1/approvals/{approval_id}/approve")
async def approve(
    request: Request, approval_id: str, x_agentgraph_identity: str | None = Header(default=None)
) -> dict[str, object]:
    _principal(request, x_agentgraph_identity, Permission.APPROVE)
    return await _approval_decision(request, approval_id, True)


@remote_router.post("/api/v1/approvals/{approval_id}/reject")
async def reject(
    request: Request, approval_id: str, x_agentgraph_identity: str | None = Header(default=None)
) -> dict[str, object]:
    _principal(request, x_agentgraph_identity, Permission.APPROVE)
    return await _approval_decision(request, approval_id, False)


@remote_router.websocket("/ws/events")
async def event_socket(websocket: WebSocket, run_id: str | None = None) -> None:
    authorization = cast(AuthorizationService, websocket.app.state.authorization)
    try:
        auth_service = cast(AuthService, websocket.app.state.auth_service)
        session_principal = await auth_service.principal_from_session_token(
            websocket.cookies.get(websocket.app.state.settings.session_cookie_name)
        )
        token = set_request_principal(Principal(session_principal.user_id, session_principal.permissions))
        principal = authorization.principal(None)
        authorization.require(principal, Permission.READ)
    except (AuthenticationError, AuthorizationError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        await websocket.accept()
        bus = cast(RuntimeEventBus, websocket.app.state.event_bus)
        try:
            async for event in bus.subscribe(run_id):
                await websocket.send_json(event_json(event))
        except WebSocketDisconnect:
            return
    finally:
        token.var.reset(token)


async def _approval_decision(request: Request, approval_id: str, approved: bool) -> dict[str, object]:
    try:
        return _approval_json(await _approvals(request).decide(approval_id, approved))
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "APPROVAL_NOT_FOUND", "message": "Approval was not found", "details": {}}},
        ) from error
    except LifecycleConflictError as error:
        raise HTTPException(
            status_code=409, detail={"error": {"code": "APPROVAL_CONFLICT", "message": str(error), "details": {}}}
        ) from error


def _approval_json(approval: ApprovalRequest) -> dict[str, object]:
    return {
        "approval_id": approval.id,
        "project_id": approval.project_id,
        "run_id": approval.run_id,
        "task_id": approval.task_id,
        "action": approval.action,
        "description": approval.description,
        "risk": approval.risk,
        "status": approval.status,
        "created_at": approval.created_at.isoformat(),
    }


def _orchestration_http(error: OrchestrationError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={"error": {"code": error.code, "message": str(error), "details": {}}},
    )
