from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class RuntimeEventType(StrEnum):
    PROJECT_CREATED = "project.created"
    RUN_CREATED = "run.created"
    RUN_STARTED = "run.started"
    RUN_PAUSED = "run.paused"
    RUN_RESUMED = "run.resumed"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    RUN_CANCELLED = "run.cancelled"
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    AGENT_STARTED = "agent.started"
    AGENT_WAITING = "agent.waiting"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    PROVIDER_SELECTED = "provider.selected"
    PROVIDER_CHANGED = "provider.changed"
    PROVIDER_ERROR = "provider.error"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    APPROVAL_REQUIRED = "approval.required"
    APPROVAL_APPROVED = "approval.approved"
    APPROVAL_REJECTED = "approval.rejected"
    APPROVAL_EXPIRED = "approval.expired"
    LOG_CREATED = "log.created"
    VISION_ASSET_CREATED = "vision.asset.created"
    VISION_ANALYSIS_QUEUED = "vision.analysis.queued"
    VISION_ANALYSIS_STARTED = "vision.analysis.started"
    VISION_ANALYSIS_COMPLETED = "vision.analysis.completed"
    VISION_ANALYSIS_FAILED = "vision.analysis.failed"
    VISION_FOLDER_SCAN_STARTED = "vision.folder.scan.started"
    VISION_FOLDER_SCAN_COMPLETED = "vision.folder.scan.completed"


class Permission(StrEnum):
    READ = "read"
    EXECUTE = "execute"
    CONTROL = "control"
    APPROVE = "approve"
    ADMIN = "admin"


class RuntimeCommandType(StrEnum):
    CREATE_AGENT = "create_agent"
    UPDATE_AGENT_GRAPH = "update_agent_graph"
    START_RUN = "start_run"
    PAUSE_RUN = "pause_run"
    RESUME_RUN = "resume_run"
    STOP_RUN = "stop_run"
    RETRY_RUN = "retry_run"
    SUBMIT_APPROVAL = "submit_approval"
    REJECT_APPROVAL = "reject_approval"
    GET_STATUS = "get_status"
    GET_AGENT = "get_agent"
    GET_RUN = "get_run"
    LIST_RUNS = "list_runs"
    GET_LOGS = "get_logs"
    LIST_PROVIDERS = "list_providers"
    LIST_AGENTS = "list_agents"
    LIST_PROJECTS = "list_projects"
    GET_RUN_TREE = "get_run_tree"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    id: str
    type: RuntimeEventType
    timestamp: datetime
    project_id: str
    run_id: str | None = None
    task_id: str | None = None
    agent_id: str | None = None
    provider_id: str | None = None
    severity: str = "info"
    payload: dict[str, object] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        type: RuntimeEventType,
        project_id: str,
        *,
        run_id: str | None = None,
        task_id: str | None = None,
        agent_id: str | None = None,
        provider_id: str | None = None,
        severity: str = "info",
        payload: dict[str, object] | None = None,
    ) -> "RuntimeEvent":
        return cls(
            id=f"evt_{uuid4().hex}",
            type=type,
            timestamp=utc_now(),
            project_id=project_id,
            run_id=run_id,
            task_id=task_id,
            agent_id=agent_id,
            provider_id=provider_id,
            severity=severity,
            payload=payload or {},
        )


@dataclass(frozen=True, slots=True)
class Principal:
    identity: str
    permissions: frozenset[Permission]


@dataclass(frozen=True, slots=True)
class RuntimeCommand:
    id: str
    type: RuntimeCommandType
    principal: Principal
    target_id: str | None = None
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ApprovalRequest:
    id: str
    project_id: str
    action: str
    description: str
    requested_by: str
    risk: str | None = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    run_id: str | None = None
    task_id: str | None = None
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, object] = field(default_factory=dict)
