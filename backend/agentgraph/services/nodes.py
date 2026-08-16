import asyncio
import hashlib
import hmac
import os
import platform
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from agentgraph.domain.distributed import (
    NodeInfo,
    NodeRole,
    NodeStatus,
    ProbeResult,
    ResourceSnapshot,
    ServerMessage,
    TaskCancel,
    TaskError,
    TaskRequest,
    TaskResult,
    WorkerCapabilities,
    WorkerHello,
)
from agentgraph.domain.remote import RuntimeEvent, RuntimeEventType
from agentgraph.persistence.database import SessionFactory
from agentgraph.persistence.models import NodeRecord
from agentgraph.repositories.nodes import NodeRepository
from agentgraph.runtime.events import RuntimeEventBus
from agentgraph.settings import Settings


class NodeError(Exception):
    code = "NODE_ERROR"


class NodeNotFoundError(NodeError):
    code = "NODE_NOT_FOUND"


class NodeDisabledError(NodeError):
    code = "NODE_DISABLED"


class NodeUnavailableError(NodeError):
    code = "NODE_UNAVAILABLE"


class NodeControlError(NodeError):
    code = "NODE_CONTROL_FORBIDDEN"


class NodeTaskTimeoutError(NodeError):
    code = "WORKER_TIMEOUT"


class NodeTaskDisconnectedError(NodeError):
    code = "WORKER_DISCONNECTED"


class NodeTaskDuplicateError(NodeError):
    code = "TASK_DUPLICATE"


@dataclass(slots=True)
class _Session:
    queue: asyncio.Queue[ServerMessage]
    pending: dict[str, asyncio.Future[TaskResult]]


class NodeService:
    """Core-owned node registry and bounded in-memory worker sessions."""

    def __init__(self, sessions: SessionFactory, events: RuntimeEventBus, settings: Settings) -> None:
        self._sessions = sessions
        self._events = events
        self._settings = settings
        self._repository = NodeRepository()
        self._connections: dict[str, _Session] = {}
        self._recent_tasks: OrderedDict[str, None] = OrderedDict()
        self._lock = asyncio.Lock()
        self._database_lock = asyncio.Lock()

    @staticmethod
    def enrollment_proof(secret: str, node_id: str) -> str:
        return hmac.new(secret.encode(), node_id.encode(), hashlib.sha256).hexdigest()

    def verify_enrollment(self, node_id: str, proof: str | None) -> bool:
        if not self._settings.worker_enrollment_secret or not proof:
            return False
        return hmac.compare_digest(self.enrollment_proof(self._settings.worker_enrollment_secret, node_id), proof)

    async def enroll(self, hello: WorkerHello, proof: str | None) -> NodeInfo:
        async with self._database_lock:
            return await self._enroll(hello, proof)

    async def _enroll(self, hello: WorkerHello, proof: str | None) -> NodeInfo:
        if not self.verify_enrollment(hello.node_id, proof):
            raise NodeError("Worker enrollment was denied")
        now = _now()
        async with self._sessions() as session:
            record = await self._repository.get(session, hello.node_id)
            if record is not None and not record.enabled:
                raise NodeDisabledError("Worker is disabled")
            if record is None:
                record = NodeRecord(
                    id=hello.node_id,
                    name=hello.node_name,
                    role=NodeRole.WORKER,
                    status=NodeStatus.REGISTERED,
                    enabled=True,
                    enrollment_hash=self.enrollment_proof(self._settings.worker_enrollment_secret or "", hello.node_id),
                    capabilities=hello.capabilities.model_dump(mode="json"),
                    last_seen_at=now,
                )
                await self._repository.create(session, record)
                event_type = RuntimeEventType.NODE_REGISTERED
            else:
                if not hmac.compare_digest(record.enrollment_hash, proof or ""):
                    raise NodeError("Worker enrollment was denied")
                record.name = hello.node_name
                record.capabilities = hello.capabilities.model_dump(mode="json")
                record.last_seen_at = now
                event_type = RuntimeEventType.NODE_CONNECTED
            record.status = NodeStatus.ONLINE
            await session.commit()
            await session.refresh(record)
        await self._publish(event_type, record.id, {"status": record.status})
        return _node_info(record)

    async def connect(self, node_id: str) -> asyncio.Queue[ServerMessage]:
        async with self._lock:
            if node_id not in self._connections and len(self._connections) >= self._settings.worker_max_connections:
                raise NodeUnavailableError("Worker connection limit reached")
            previous = self._connections.pop(node_id, None)
            if previous is not None:
                self._fail_pending(previous, NodeTaskDisconnectedError("Worker session was replaced"))
            queue: asyncio.Queue[ServerMessage] = asyncio.Queue(maxsize=self._settings.worker_max_messages)
            self._connections[node_id] = _Session(queue, {})
        return queue

    async def ensure_core(self, name: str) -> NodeInfo:
        """Keep the single authoritative Core visible without treating it as a worker."""
        async with self._sessions() as session:
            record = await self._repository.get(session, "core_local")
            if record is None:
                record = NodeRecord(
                    id="core_local",
                    name=name,
                    role=NodeRole.CORE,
                    status=NodeStatus.ONLINE,
                    enabled=True,
                    enrollment_hash="",
                    capabilities=_local_capabilities().model_dump(mode="json"),
                    last_seen_at=_now(),
                )
                await self._repository.create(session, record)
            else:
                record.name = name
                record.status = NodeStatus.ONLINE
                record.last_seen_at = _now()
            await session.commit()
            await session.refresh(record)
            return _node_info(record)

    async def disconnect(self, node_id: str) -> None:
        async with self._lock:
            connected = self._connections.pop(node_id, None)
        if connected is not None:
            self._fail_pending(connected, NodeTaskDisconnectedError("Worker disconnected"))
        async with self._database_lock:
            await self._set_status_if_enabled(node_id, NodeStatus.OFFLINE)

    async def heartbeat(self, node_id: str, capabilities: WorkerCapabilities | None = None) -> None:
        now = _now()
        async with self._database_lock:
            async with self._sessions() as session:
                record = await self._repository.get(session, node_id)
                if record is None:
                    raise NodeNotFoundError("Worker was not registered")
                if not record.enabled:
                    raise NodeDisabledError("Worker is disabled")
                record.status = NodeStatus.ONLINE
                record.last_seen_at = now
                if capabilities is not None:
                    record.capabilities = capabilities.model_dump(mode="json")
                await session.commit()

    async def list(self) -> list[NodeInfo]:
        await self.mark_stale_offline()
        async with self._sessions() as session:
            records = await self._repository.list(session)
            return [_node_info(record) for record in records]

    async def get(self, node_id: str) -> NodeInfo:
        await self.mark_stale_offline()
        async with self._sessions() as session:
            record = await self._repository.get(session, node_id)
            if record is None:
                raise NodeNotFoundError("Node was not found")
            return _node_info(record)

    async def set_enabled(self, node_id: str, enabled: bool) -> NodeInfo:
        async with self._database_lock:
            async with self._sessions() as session:
                record = await self._repository.get(session, node_id)
                if record is None:
                    raise NodeNotFoundError("Node was not found")
                if record.role is not NodeRole.WORKER:
                    raise NodeControlError("Core node cannot be enabled or disabled")
                record.enabled = enabled
                record.status = NodeStatus.REGISTERED if enabled else NodeStatus.DISABLED
                await session.commit()
                await session.refresh(record)
        if not enabled:
            await self.disconnect(node_id)
            await self._publish(RuntimeEventType.NODE_DISABLED, node_id, {"status": "disabled"})
        return _node_info(record)

    async def probe(
        self, node_id: str, timeout_seconds: float | None = None, task_id: str | None = None
    ) -> ProbeResult:
        info = await self.get(node_id)
        if not info.enabled or info.status is NodeStatus.DISABLED:
            raise NodeDisabledError("Worker is disabled")
        if info.status is not NodeStatus.ONLINE:
            raise NodeUnavailableError("Worker is offline")
        identifier = task_id or f"tsk_{uuid4().hex}"
        async with self._lock:
            if identifier in self._recent_tasks:
                raise NodeTaskDuplicateError("Task id has already been dispatched")
            connected = self._connections.get(node_id)
            if connected is None:
                raise NodeUnavailableError("Worker is unavailable")
            if len(connected.pending) >= self._settings.worker_max_tasks:
                raise NodeUnavailableError("Worker task limit reached")
            future: asyncio.Future[TaskResult] = asyncio.get_running_loop().create_future()
            connected.pending[identifier] = future
            try:
                connected.queue.put_nowait(TaskRequest(
                    task_id=identifier,
                    operation="system.probe",
                    timeout_seconds=timeout_seconds or self._settings.worker_task_timeout_seconds,
                ))
            except asyncio.QueueFull as error:
                connected.pending.pop(identifier, None)
                raise NodeUnavailableError("Worker command queue is full") from error
            self._recent_tasks[identifier] = None
            self._recent_tasks.move_to_end(identifier)
            while len(self._recent_tasks) > self._settings.worker_max_tasks * self._settings.worker_max_connections:
                self._recent_tasks.popitem(last=False)
        await self._publish(
            RuntimeEventType.WORKER_TASK_REQUESTED,
            node_id,
            {"task_id": identifier, "operation": "system.probe"},
        )
        try:
            result = await asyncio.wait_for(future, timeout_seconds or self._settings.worker_task_timeout_seconds)
        except TimeoutError as error:
            async with self._lock:
                connected.pending.pop(identifier, None)
                try:
                    connected.queue.put_nowait(TaskCancel(task_id=identifier))
                except asyncio.QueueFull:
                    pass
            await self._publish(RuntimeEventType.WORKER_TASK_TIMED_OUT, node_id, {"task_id": identifier})
            raise NodeTaskTimeoutError("Worker did not return a result before timeout") from error
        await self._publish(RuntimeEventType.WORKER_TASK_COMPLETED, node_id, {"task_id": identifier})
        return ProbeResult(task_id=identifier, node_id=node_id, status="succeeded", result=result.result)

    async def receive_result(self, node_id: str, result: TaskResult | TaskError) -> None:
        async with self._lock:
            connected = self._connections.get(node_id)
            future = connected.pending.pop(result.task_id, None) if connected else None
        if future is None or future.done():
            return
        if isinstance(result, TaskError):
            future.set_exception(NodeError(result.message))
            await self._publish(
                RuntimeEventType.WORKER_TASK_FAILED,
                node_id,
                {"task_id": result.task_id, "code": result.code},
            )
        else:
            future.set_result(result)

    async def mark_stale_offline(self) -> None:
        cutoff = _now() - timedelta(seconds=self._settings.worker_heartbeat_timeout_seconds)
        async with self._sessions() as session:
            records = await self._repository.list(session)
            stale = [
                record
                for record in records
                if record.role is NodeRole.WORKER
                and record.enabled
                and record.last_seen_at
                and _as_utc(record.last_seen_at) < cutoff
            ]
            for record in stale:
                record.status = NodeStatus.OFFLINE
            await session.commit()
        for record in stale:
            await self.disconnect(record.id)
            await self._publish(RuntimeEventType.NODE_OFFLINE, record.id, {"status": "offline"})

    async def _set_status_if_enabled(self, node_id: str, status: NodeStatus) -> None:
        async with self._sessions() as session:
            record = await self._repository.get(session, node_id)
            if record is None or not record.enabled:
                return
            record.status = status
            await session.commit()
        await self._publish(RuntimeEventType.NODE_OFFLINE, node_id, {"status": status})

    @staticmethod
    def _fail_pending(session: _Session, error: NodeError) -> None:
        for future in session.pending.values():
            if not future.done():
                future.set_exception(error)
        session.pending.clear()

    async def _publish(self, event_type: RuntimeEventType, node_id: str, payload: dict[str, object]) -> None:
        await self._events.publish(
            RuntimeEvent.create(event_type, self._settings.project_id, payload={"node_id": node_id, **payload})
        )


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _local_capabilities() -> WorkerCapabilities:
    memory_total: int | None = None
    memory_available: int | None = None
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        memory_total = page_size * os.sysconf("SC_PHYS_PAGES")
        memory_available = page_size * os.sysconf("SC_AVPHYS_PAGES")
    except (AttributeError, OSError, ValueError):
        pass
    return WorkerCapabilities(
        platform=platform.system() or "unknown",
        architecture=platform.machine() or "unknown",
        agentgraph_version="0.1.0",
        resources=ResourceSnapshot(
            cpu_count=os.cpu_count() or 0,
            memory_total_bytes=memory_total,
            memory_available_bytes=memory_available,
        ),
    )


def _node_info(record: NodeRecord) -> NodeInfo:
    return NodeInfo(
        node_id=record.id,
        name=record.name,
        role=NodeRole(record.role),
        status=NodeStatus(record.status),
        enabled=record.enabled,
        capabilities=WorkerCapabilities.model_validate(record.capabilities),
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
        last_seen_at=record.last_seen_at.isoformat() if record.last_seen_at else None,
    )
