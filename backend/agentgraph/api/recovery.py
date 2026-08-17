from typing import cast
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request

from agentgraph.api.remote import _principal
from agentgraph.api.schemas import RecoveryReportResponse
from agentgraph.domain.remote import Permission
from agentgraph.services.errors import RunNotFoundError
from agentgraph.services.manager import AgentManager

recovery_router = APIRouter(prefix="/api/v1/runs", tags=["recovery"])


def _manager(request: Request) -> AgentManager:
    return cast(AgentManager, request.app.state.agent_manager)


@recovery_router.get("/{run_id}/recovery", response_model=RecoveryReportResponse)
async def get_recovery_report(
    request: Request, run_id: UUID, x_agentgraph_identity: str | None = Header(default=None)
) -> RecoveryReportResponse:
    _principal(request, x_agentgraph_identity, Permission.READ)
    try:
        return RecoveryReportResponse.model_validate(await _manager(request).get_recovery_report(run_id))
    except RunNotFoundError as error:
        raise HTTPException(
            404, detail={"error": {"code": "RUN_NOT_FOUND", "message": "Run was not found", "details": {}}}
        ) from error
