from collections.abc import Awaitable
from typing import TypeVar, cast

from fastapi import APIRouter, Header, HTTPException, Request, status

from agentgraph.api.remote import _principal
from agentgraph.domain.distributed import NodeInfo, ProbeResult
from agentgraph.domain.remote import Permission
from agentgraph.services.nodes import NodeError, NodeService

node_router = APIRouter()
T = TypeVar("T")


def _nodes(request: Request) -> NodeService:
    return cast(NodeService, request.app.state.node_service)


@node_router.get("/api/v1/nodes", response_model=list[NodeInfo])
async def list_nodes(request: Request, x_agentgraph_identity: str | None = Header(default=None)) -> list[NodeInfo]:
    _principal(request, x_agentgraph_identity, Permission.READ)
    return await _nodes(request).list()


@node_router.get("/api/v1/nodes/{node_id}", response_model=NodeInfo)
async def get_node(
    request: Request, node_id: str, x_agentgraph_identity: str | None = Header(default=None)
) -> NodeInfo:
    _principal(request, x_agentgraph_identity, Permission.READ)
    return await _node_response(_nodes(request).get(node_id))


@node_router.post("/api/v1/nodes/{node_id}/enable", response_model=NodeInfo)
async def enable_node(
    request: Request, node_id: str, x_agentgraph_identity: str | None = Header(default=None)
) -> NodeInfo:
    _principal(request, x_agentgraph_identity, Permission.CONTROL)
    return await _node_response(_nodes(request).set_enabled(node_id, True))


@node_router.post("/api/v1/nodes/{node_id}/disable", response_model=NodeInfo)
async def disable_node(
    request: Request, node_id: str, x_agentgraph_identity: str | None = Header(default=None)
) -> NodeInfo:
    _principal(request, x_agentgraph_identity, Permission.CONTROL)
    return await _node_response(_nodes(request).set_enabled(node_id, False))


@node_router.post("/api/v1/nodes/{node_id}/probe", response_model=ProbeResult)
async def probe_node(
    request: Request, node_id: str, x_agentgraph_identity: str | None = Header(default=None)
) -> ProbeResult:
    _principal(request, x_agentgraph_identity, Permission.EXECUTE)
    return await _node_response(_nodes(request).probe(node_id))


async def _node_response[T](awaitable: Awaitable[T]) -> T:
    try:
        return await awaitable
    except NodeError as error:
        error_status = status.HTTP_404_NOT_FOUND if error.code == "NODE_NOT_FOUND" else status.HTTP_409_CONFLICT
        raise HTTPException(
            status_code=error_status,
            detail={"error": {"code": error.code, "message": str(error), "details": {}}},
        ) from error
