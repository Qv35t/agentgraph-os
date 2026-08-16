from typing import cast
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request

from agentgraph.domain.remote import Permission
from agentgraph.services.errors import RunNotFoundError
from agentgraph.services.manager import AgentManager
from agentgraph.services.remote import AuthorizationError, AuthorizationService
from agentgraph.services.tools import ToolService

tool_router = APIRouter(prefix="/api/v1/runs", tags=["tools"])


def _tools(request: Request) -> ToolService:
    return cast(ToolService, request.app.state.tool_service)


def _manager(request: Request) -> AgentManager:
    return cast(AgentManager, request.app.state.agent_manager)


def _authorize(request: Request, identity: str | None) -> None:
    authorization = cast(AuthorizationService, request.app.state.authorization)
    try:
        principal = authorization.principal(identity)
        authorization.require(principal, Permission.READ)
    except AuthorizationError as error:
        raise HTTPException(
            403, detail={"error": {"code": "FORBIDDEN", "message": str(error), "details": {}}}
        ) from error


@tool_router.get("/{run_id}/tools")
async def list_tool_invocations(
    request: Request, run_id: UUID, x_agentgraph_identity: str | None = Header(default=None)
) -> list[dict[str, object]]:
    _authorize(request, x_agentgraph_identity)
    try:
        await _manager(request).get_run(run_id)
    except RunNotFoundError as error:
        raise HTTPException(
            404, detail={"error": {"code": "RUN_NOT_FOUND", "message": "Run was not found", "details": {}}}
        ) from error
    return await _tools(request).list_run_invocations(run_id)
