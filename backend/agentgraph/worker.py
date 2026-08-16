import asyncio
import os
import platform
from collections import OrderedDict
from pathlib import Path
from uuid import uuid4

from websockets.asyncio.client import connect

from agentgraph.domain.distributed import (
    MAX_MESSAGE_BYTES,
    PROTOCOL_VERSION,
    ResourceSnapshot,
    TaskCancel,
    TaskError,
    TaskRequest,
    TaskResult,
    WorkerCapabilities,
    WorkerHeartbeat,
    WorkerHello,
    server_message_adapter,
)
from agentgraph.services.nodes import NodeService
from agentgraph.settings import Settings


def load_node_id(path: str) -> str:
    """Create one opaque local identity, never deriving it from host details."""
    destination = Path(path)
    try:
        existing = destination.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        destination.parent.mkdir(parents=True, exist_ok=True)
        node_id = f"node_{uuid4().hex}"
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(node_id, encoding="utf-8")
        os.chmod(temporary, 0o600)
        temporary.replace(destination)
        return node_id
    if len(existing) < 8 or len(existing) > 100:
        raise ValueError("Worker node id file is invalid")
    return existing


def safe_capabilities() -> WorkerCapabilities:
    memory_total: int | None = None
    memory_available: int | None = None
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        memory_total = page_size * os.sysconf("SC_PHYS_PAGES")
        memory_available = page_size * os.sysconf("SC_AVPHYS_PAGES")
    except (AttributeError, OSError, ValueError):
        pass
    try:
        load_average: float | None = os.getloadavg()[0]
    except OSError:
        load_average = None
    return WorkerCapabilities(
        platform=platform.system() or "unknown",
        architecture=platform.machine() or "unknown",
        agentgraph_version="0.1.0",
        resources=ResourceSnapshot(
            cpu_count=os.cpu_count() or 0,
            load_average=load_average,
            memory_total_bytes=memory_total,
            memory_available_bytes=memory_available,
        ),
    )


class WorkerClient:
    """Outbound-only worker transport for the intentionally small v1 operation set."""

    def __init__(self, settings: Settings) -> None:
        if settings.node_role.value != "worker":
            raise ValueError("Worker requires AGENTGRAPH_NODE_ROLE=worker")
        if not settings.worker_enabled:
            raise ValueError("Worker requires AGENTGRAPH_WORKER_ENABLED=true")
        if not settings.core_url or not settings.worker_enrollment_secret:
            raise ValueError("Worker requires AGENTGRAPH_CORE_URL and AGENTGRAPH_WORKER_ENROLLMENT_SECRET")
        self._settings = settings
        self.node_id = load_node_id(settings.node_id_path)
        self._stopped = asyncio.Event()
        self._completed: OrderedDict[str, TaskResult] = OrderedDict()

    def stop(self) -> None:
        self._stopped.set()

    async def run(self) -> None:
        delay = 1.0
        while not self._stopped.is_set():
            try:
                await self._connect_once()
                delay = 1.0
            except asyncio.CancelledError:
                raise
            except Exception:
                try:
                    await asyncio.wait_for(self._stopped.wait(), timeout=delay)
                except TimeoutError:
                    pass
            delay = min(delay * 2, self._settings.worker_reconnect_max_seconds)

    async def _connect_once(self) -> None:
        url = (self._settings.core_url or "").rstrip("/")
        url = url.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
        proof = NodeService.enrollment_proof(self._settings.worker_enrollment_secret or "", self.node_id)
        async with connect(
            f"{url}/ws/internal/workers",
            additional_headers={"x-agentgraph-worker-proof": proof},
            max_size=MAX_MESSAGE_BYTES,
            proxy=None,
        ) as websocket:
            capabilities = safe_capabilities()
            hello = WorkerHello(node_id=self.node_id, node_name=self._settings.node_name, capabilities=capabilities)
            await websocket.send(hello.model_dump_json())
            await websocket.recv()  # worker.registered acknowledgement
            while not self._stopped.is_set():
                try:
                    raw = await asyncio.wait_for(websocket.recv(), self._settings.worker_heartbeat_interval_seconds)
                except TimeoutError:
                    await websocket.send(WorkerHeartbeat(resources=safe_capabilities().resources).model_dump_json())
                    continue
                if not isinstance(raw, str) or len(raw.encode()) > MAX_MESSAGE_BYTES:
                    return
                message = server_message_adapter.validate_json(raw)
                if isinstance(message, TaskRequest):
                    await websocket.send((await self._execute(message)).model_dump_json())
                elif isinstance(message, TaskCancel):
                    # system.probe is immediate; cancellation is acknowledged by not starting queued work.
                    continue

    async def _execute(self, request: TaskRequest) -> TaskResult | TaskError:
        cached = self._completed.get(request.task_id)
        if cached is not None:
            return cached
        if request.operation != "system.probe":
            return TaskError(
                task_id=request.task_id, code="UNSUPPORTED_OPERATION", message="Operation is not permitted"
            )
        result = TaskResult(
            task_id=request.task_id,
            result={
                "node_id": self.node_id,
                "protocol_version": PROTOCOL_VERSION,
                "resources": safe_capabilities().resources.model_dump(),
            },
        )
        self._completed[request.task_id] = result
        self._completed.move_to_end(request.task_id)
        while len(self._completed) > self._settings.worker_max_tasks:
            self._completed.popitem(last=False)
        return result


def main() -> None:
    asyncio.run(WorkerClient(Settings()).run())


if __name__ == "__main__":
    main()
