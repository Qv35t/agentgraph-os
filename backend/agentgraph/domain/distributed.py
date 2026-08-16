from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 64_000


class NodeRole(StrEnum):
    CORE = "core"
    WORKER = "worker"


class NodeStatus(StrEnum):
    REGISTERED = "registered"
    ONLINE = "online"
    OFFLINE = "offline"
    DISABLED = "disabled"


class ResourceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cpu_count: int = Field(ge=0, le=1024)
    load_average: float | None = Field(default=None, ge=0, le=10_000)
    memory_total_bytes: int | None = Field(default=None, ge=0)
    memory_available_bytes: int | None = Field(default=None, ge=0)


class WorkerCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: str = Field(min_length=1, max_length=120)
    architecture: str = Field(min_length=1, max_length=120)
    agentgraph_version: str = Field(min_length=1, max_length=40)
    features: list[str] = Field(default_factory=lambda: ["system.probe"], max_length=20)
    resources: ResourceSnapshot


class ProtocolMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    protocol_version: Literal[1] = 1


class WorkerHello(ProtocolMessage):
    type: Literal["worker.hello"] = "worker.hello"
    node_id: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    node_name: str = Field(min_length=1, max_length=200)
    capabilities: WorkerCapabilities


class WorkerHeartbeat(ProtocolMessage):
    type: Literal["worker.heartbeat"] = "worker.heartbeat"
    resources: ResourceSnapshot


class WorkerCapabilitiesUpdate(ProtocolMessage):
    type: Literal["worker.capabilities"] = "worker.capabilities"
    capabilities: WorkerCapabilities


class TaskRequest(ProtocolMessage):
    type: Literal["task.request"] = "task.request"
    task_id: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    operation: Literal["system.probe"] = "system.probe"
    timeout_seconds: float = Field(gt=0, le=60)


class TaskResult(ProtocolMessage):
    type: Literal["task.result"] = "task.result"
    task_id: str = Field(min_length=8, max_length=100)
    result: dict[str, object] = Field(default_factory=dict)


class TaskError(ProtocolMessage):
    type: Literal["task.error"] = "task.error"
    task_id: str = Field(min_length=8, max_length=100)
    code: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=300)


class TaskCancel(ProtocolMessage):
    type: Literal["task.cancel"] = "task.cancel"
    task_id: str = Field(min_length=8, max_length=100)


class WorkerRegistered(ProtocolMessage):
    type: Literal["worker.registered"] = "worker.registered"
    node_id: str
    status: NodeStatus


ClientMessage = Annotated[
    WorkerHello | WorkerHeartbeat | WorkerCapabilitiesUpdate | TaskResult | TaskError | TaskCancel,
    Field(discriminator="type"),
]
ServerMessage = WorkerRegistered | TaskRequest | TaskCancel
client_message_adapter: TypeAdapter[ClientMessage] = TypeAdapter(ClientMessage)
server_message_adapter: TypeAdapter[ServerMessage] = TypeAdapter(ServerMessage)


class NodeInfo(BaseModel):
    node_id: str
    name: str
    role: NodeRole
    status: NodeStatus
    enabled: bool
    capabilities: WorkerCapabilities
    created_at: str
    updated_at: str
    last_seen_at: str | None


class ProbeResult(BaseModel):
    task_id: str
    node_id: str
    status: Literal["succeeded"]
    result: dict[str, object]
