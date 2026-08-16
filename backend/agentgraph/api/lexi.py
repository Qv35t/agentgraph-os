from typing import cast

from fastapi import APIRouter, Header, HTTPException, Request, status

from agentgraph.api.schemas import LexiResponse
from agentgraph.domain.remote import Permission
from agentgraph.services.lexi import LexiTemplateService
from agentgraph.services.remote import AuthorizationError, AuthorizationService

lexi_router = APIRouter(prefix="/api/v1/lexi", tags=["lexi"])


def _service(request: Request) -> LexiTemplateService:
    return cast(LexiTemplateService, request.app.state.lexi_service)


def _authorize(request: Request, identity: str | None, permission: Permission) -> None:
    authorization = cast(AuthorizationService, request.app.state.authorization)
    try:
        principal = authorization.principal(identity)
        authorization.require(principal, permission)
    except AuthorizationError as error:
        raise HTTPException(
            403, detail={"error": {"code": "FORBIDDEN", "message": str(error), "details": {}}}
        ) from error


@lexi_router.get("", response_model=LexiResponse)
async def get_lexi(request: Request, x_agentgraph_identity: str | None = Header(default=None)) -> LexiResponse:
    _authorize(request, x_agentgraph_identity, Permission.READ)
    return LexiResponse.from_agent(await _service(request).get_installed())


@lexi_router.post("/bootstrap", response_model=LexiResponse, status_code=status.HTTP_201_CREATED)
async def bootstrap_lexi(request: Request, x_agentgraph_identity: str | None = Header(default=None)) -> LexiResponse:
    _authorize(request, x_agentgraph_identity, Permission.EXECUTE)
    return LexiResponse.from_agent(await _service(request).ensure_installed())
