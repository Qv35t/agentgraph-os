import asyncio
from typing import cast

import anyio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError

from agentgraph.domain.distributed import (
    MAX_MESSAGE_BYTES,
    TaskError,
    TaskRequest,
    TaskResult,
    WorkerCapabilitiesUpdate,
    WorkerHeartbeat,
    WorkerHello,
    WorkerRegistered,
    client_message_adapter,
)
from agentgraph.services.nodes import NodeDisabledError, NodeError, NodeService

worker_router = APIRouter()


@worker_router.websocket("/ws/internal/workers")
async def worker_socket(websocket: WebSocket) -> None:
    try:
        await _serve_worker_socket(websocket)
    except asyncio.CancelledError:
        # ASGI servers may cancel a disconnected socket after its cleanup finishes.
        return


async def _serve_worker_socket(websocket: WebSocket) -> None:
    if websocket.app.state.settings.node_role != "core":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websocket.accept()
    service = cast(NodeService, websocket.app.state.node_service)
    node_id: str | None = None
    try:
        first = await _receive(websocket)
        if not isinstance(first, WorkerHello):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        with anyio.CancelScope(shield=True):
            node = await service.enroll(first, websocket.headers.get("x-agentgraph-worker-proof"))
        node_id = node.node_id
        queue = await service.connect(node_id)
        await websocket.send_json(WorkerRegistered(node_id=node_id, status=node.status).model_dump(mode="json"))
        while True:
            receive = asyncio.create_task(websocket.receive_text())
            send = asyncio.create_task(queue.get())
            done, pending = await asyncio.wait({receive, send}, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                value = task.result()
                if isinstance(value, str):
                    with anyio.CancelScope(shield=True):
                        await _handle(service, node_id, value)
                elif isinstance(value, (WorkerRegistered, TaskRequest)):
                    await websocket.send_json(value.model_dump(mode="json"))
    except (NodeDisabledError, NodeError, ValidationError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except WebSocketDisconnect:
        return
    finally:
        if node_id is not None:
            # Finish the database-backed disconnect when ASGI cancels the socket task.
            with anyio.CancelScope(shield=True):
                await service.disconnect(node_id)


async def _receive(websocket: WebSocket) -> object:
    raw = await websocket.receive_text()
    if len(raw.encode()) > MAX_MESSAGE_BYTES:
        raise ValueError("Worker message exceeds limit")
    return client_message_adapter.validate_json(raw)


async def _handle(service: NodeService, node_id: str, raw: str) -> None:
    if len(raw.encode()) > MAX_MESSAGE_BYTES:
        raise ValueError("Worker message exceeds limit")
    message = client_message_adapter.validate_json(raw)
    if isinstance(message, WorkerHeartbeat):
        await service.heartbeat(node_id)
    elif isinstance(message, WorkerCapabilitiesUpdate):
        await service.heartbeat(node_id, message.capabilities)
    elif isinstance(message, (TaskResult, TaskError)):
        await service.receive_result(node_id, message)
