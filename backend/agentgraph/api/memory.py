from typing import cast
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status

from agentgraph.api.schemas import (
    CreateMemoryRequest,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResponse,
)
from agentgraph.domain.remote import Permission
from agentgraph.services.errors import AgentNotFoundError, RunNotFoundError
from agentgraph.services.manager import AgentManager
from agentgraph.services.memory import MemoryError, MemoryService
from agentgraph.services.remote import AuthorizationError, AuthorizationService

memory_router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


def _service(request: Request) -> MemoryService:
    return cast(MemoryService, request.app.state.memory_service)


def _manager(request: Request) -> AgentManager:
    return cast(AgentManager, request.app.state.agent_manager)


def _authorize(request: Request, identity: str | None, permission: Permission) -> None:
    authorization = cast(AuthorizationService, request.app.state.authorization)
    try:
        principal = authorization.principal(identity)
        authorization.require(principal, permission)
    except AuthorizationError as error:
        raise HTTPException(
            403, detail={"error": {"code": "FORBIDDEN", "message": str(error), "details": {}}}
        ) from error


@memory_router.get("", response_model=list[MemoryResponse])
async def list_memory(
    request: Request, agent_id: UUID, x_agentgraph_identity: str | None = Header(default=None)
) -> list[MemoryResponse]:
    _authorize(request, x_agentgraph_identity, Permission.READ)
    try:
        return [
            MemoryResponse.from_domain(record)
            for record in await _service(request).list_records(
                project_id=request.app.state.settings.project_id, agent_id=agent_id
            )
        ]
    except MemoryError as error:
        raise _memory_error(error) from error


@memory_router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    request: Request, payload: CreateMemoryRequest, x_agentgraph_identity: str | None = Header(default=None)
) -> MemoryResponse:
    _authorize(request, x_agentgraph_identity, Permission.EXECUTE)
    try:
        await _manager(request).get_agent(payload.agent_id)
        record = await _service(request).create(
            project_id=request.app.state.settings.project_id,
            agent_id=payload.agent_id,
            kind=payload.kind,
            content=payload.content,
            tags=payload.tags,
        )
    except (MemoryError, AgentNotFoundError) as error:
        if isinstance(error, AgentNotFoundError):
            raise HTTPException(
                404, detail={"error": {"code": "AGENT_NOT_FOUND", "message": "Agent was not found", "details": {}}}
            ) from error
        raise _memory_error(error) from error
    return MemoryResponse.from_domain(record)


@memory_router.post("/search", response_model=list[MemorySearchResponse])
async def search_memory(
    request: Request, payload: MemorySearchRequest, x_agentgraph_identity: str | None = Header(default=None)
) -> list[MemorySearchResponse]:
    _authorize(request, x_agentgraph_identity, Permission.READ)
    try:
        matches = await _service(request).search(
            project_id=request.app.state.settings.project_id, agent_id=payload.agent_id, query=payload.query
        )
    except MemoryError as error:
        raise _memory_error(error) from error
    return [MemorySearchResponse.from_match(match) for match in matches]


@memory_router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    request: Request,
    memory_id: UUID,
    agent_id: UUID,
    x_agentgraph_identity: str | None = Header(default=None),
) -> None:
    _authorize(request, x_agentgraph_identity, Permission.CONTROL)
    try:
        await _service(request).delete(
            project_id=request.app.state.settings.project_id, agent_id=agent_id, memory_id=memory_id
        )
    except MemoryError as error:
        raise _memory_error(error) from error


@memory_router.get("/runs/{run_id}")
async def run_memory_usage(
    request: Request, run_id: UUID, x_agentgraph_identity: str | None = Header(default=None)
) -> list[dict[str, object]]:
    _authorize(request, x_agentgraph_identity, Permission.READ)
    try:
        await _manager(request).get_run(run_id)
        return await _service(request).list_run_usage(run_id)
    except RunNotFoundError as error:
        raise HTTPException(
            404, detail={"error": {"code": "RUN_NOT_FOUND", "message": "Run was not found", "details": {}}}
        ) from error
    except MemoryError as error:
        raise _memory_error(error) from error


def _memory_error(error: MemoryError) -> HTTPException:
    status_code = 404 if error.code == "memory_not_found" else 400
    return HTTPException(status_code, detail={"error": {"code": error.code, "message": str(error), "details": {}}})
