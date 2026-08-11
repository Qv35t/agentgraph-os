from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class AgentStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_RUN_STATUSES = frozenset({RunStatus.QUEUED, RunStatus.RUNNING})
TERMINAL_RUN_STATUSES = frozenset({RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED})


@dataclass(frozen=True, slots=True)
class Agent:
    id: UUID
    name: str
    description: str | None
    status: AgentStatus
    model_ref: str
    graph_definition: dict[str, object]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AgentRun:
    id: UUID
    agent_id: UUID
    status: RunStatus
    input_text: str
    output_text: str | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    provider_id: str | None = None
    model_id: str | None = None
    finish_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None
