from datetime import UTC, datetime
from enum import Enum as PythonEnum
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from agentgraph.domain.distributed import NodeRole, NodeStatus
from agentgraph.domain.entities import AgentStatus, RunStatus
from agentgraph.domain.recovery import ActionLedgerStatus, CheckpointReason, RecoveryOutcome
from agentgraph.domain.vision import VisionAnalysisStatus, VisionMode


def utc_now() -> datetime:
    return datetime.now(UTC)


def enum_values(enum_type: type[PythonEnum]) -> list[str]:
    return [str(member.value) for member in enum_type]


class Base(DeclarativeBase):
    pass


class AgentRecord(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AgentStatus] = mapped_column(
        SQLAlchemyEnum(AgentStatus, native_enum=False, values_callable=enum_values),
        nullable=False,
        default=AgentStatus.IDLE,
    )
    model_ref: Mapped[str] = mapped_column(String(500), nullable=False, default="auto://default")
    graph_definition: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class AgentRunRecord(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[RunStatus] = mapped_column(
        SQLAlchemyEnum(RunStatus, native_enum=False, values_callable=enum_values),
        nullable=False,
        default=RunStatus.QUEUED,
        index=True,
    )
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    output_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    finish_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_spec: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)


class RunDelegationRecord(Base):
    __tablename__ = "run_delegations"
    __table_args__ = (UniqueConstraint("parent_run_id", "node_id", name="uq_run_delegations_parent_node"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    parent_run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    child_run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class NodeRecord(Base):
    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[NodeRole] = mapped_column(
        SQLAlchemyEnum(NodeRole, native_enum=False, values_callable=enum_values), nullable=False
    )
    status: Mapped[NodeStatus] = mapped_column(
        SQLAlchemyEnum(NodeStatus, native_enum=False, values_callable=enum_values), nullable=False, index=True
    )
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    enrollment_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    capabilities: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RunCheckpointRecord(Base):
    __tablename__ = "run_checkpoints"
    __table_args__ = (UniqueConstraint("run_id", "sequence", name="uq_run_checkpoints_run_sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    format_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reason: Mapped[CheckpointReason] = mapped_column(
        SQLAlchemyEnum(CheckpointReason, native_enum=False, values_callable=enum_values), nullable=False
    )
    state: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class RunActionLedgerEntryRecord(Base):
    __tablename__ = "run_action_ledger_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_invocation_id: Mapped[str | None] = mapped_column(
        ForeignKey("tool_invocations.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    risk: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[ActionLedgerStatus] = mapped_column(
        SQLAlchemyEnum(ActionLedgerStatus, native_enum=False, values_callable=enum_values), nullable=False
    )
    action_details: Mapped[dict[str, object]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    rollback_status: Mapped[str] = mapped_column(String(30), nullable=False, default="not_supported")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RunRecoveryDecisionRecord(Base):
    __tablename__ = "run_recovery_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    checkpoint_id: Mapped[str | None] = mapped_column(
        ForeignKey("run_checkpoints.id", ondelete="SET NULL"), nullable=True
    )
    outcome: Mapped[RecoveryOutcome] = mapped_column(
        SQLAlchemyEnum(RecoveryOutcome, native_enum=False, values_callable=enum_values), nullable=False
    )
    details: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class VisionAssetRecord(Base):
    __tablename__ = "vision_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    storage_locator: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class VisionAnalysisRecord(Base):
    __tablename__ = "vision_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("vision_assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model_id: Mapped[str] = mapped_column(String(500), nullable=False)
    mode: Mapped[VisionMode] = mapped_column(
        SQLAlchemyEnum(VisionMode, native_enum=False, values_callable=enum_values), nullable=False
    )
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[VisionAnalysisStatus] = mapped_column(
        SQLAlchemyEnum(VisionAnalysisStatus, native_enum=False, values_callable=enum_values), nullable=False
    )
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_result: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VisionFolderRecord(Base):
    __tablename__ = "vision_folders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    root: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class MemoryRecordRecord(Base):
    __tablename__ = "memory_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RunMemoryRecord(Base):
    __tablename__ = "run_memory_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    memory_id: Mapped[str | None] = mapped_column(
        ForeignKey("memory_records.id", ondelete="SET NULL"), nullable=True, index=True
    )
    memory_id_snapshot: Mapped[str] = mapped_column(String(36), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)


class ToolInvocationRecord(Base):
    __tablename__ = "tool_invocations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_id: Mapped[str] = mapped_column(String(100), nullable=False)
    risk: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    approval_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    output_metadata: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
