from dataclasses import dataclass
from enum import StrEnum


class ToolRisk(StrEnum):
    READ = "read"
    CONTROL = "control"


class ToolStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    SUCCEEDED = "succeeded"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    id: str
    description: str
    risk: ToolRisk
    requires_approval: bool


@dataclass(frozen=True, slots=True)
class ToolResult:
    tool_id: str
    status: ToolStatus
    output: str | None = None
    error_code: str | None = None
    duration_ms: int | None = None
    approval_id: str | None = None
