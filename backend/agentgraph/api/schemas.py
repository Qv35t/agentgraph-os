from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agentgraph.domain.entities import Agent, AgentRun, AgentStatus, RunStatus, RunTreeNode
from agentgraph.domain.memory import MemoryKind, MemoryMatch, MemoryRecord
from agentgraph.domain.vision import VisionAnalysisStatus, VisionMode
from agentgraph.models.contracts import (
    ModelErrorCode,
    ModelRef,
    ModelRouterError,
    ProviderStatus,
)


class HealthResponse(BaseModel):
    status: str


class GraphDefinition(BaseModel):
    """Persisted visual graph semantics; runtime behavior remains intentionally fixed."""

    model_config = ConfigDict(extra="forbid")
    version: int | None = Field(default=None, ge=1, le=2)
    runtime: Literal["model-v1", "lexi-v1", "team-v1"] | None = None
    nodes: list["GraphNode"] = Field(default_factory=list, max_length=100)
    edges: list["GraphEdge"] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def validate_team_shape(self) -> "GraphDefinition":
        if self.runtime == "team-v1" and self.version != 2:
            raise ValueError("team-v1 requires graph version 2")
        if self.version == 2 and self.runtime != "team-v1":
            raise ValueError("graph version 2 requires team-v1")
        if self.runtime == "team-v1" and any(node.type != "agent-ref" or node.agent_id is None for node in self.nodes):
            raise ValueError("team-v1 requires agent-ref nodes")
        return self


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100)
    type: str = Field(default="agent", min_length=1, max_length=50)
    label: str = Field(min_length=1, max_length=200)
    position: tuple[float, float]
    agent_id: UUID | None = None
    instructions: str | None = Field(default=None, max_length=4_000)


class GraphEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=100)
    target: str = Field(min_length=1, max_length=100)


class CreateAgentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10_000)
    model_ref: str = Field(default="auto://default", min_length=1, max_length=500)
    graph_definition: GraphDefinition = Field(default_factory=GraphDefinition)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name must contain non-whitespace characters")
        return normalized

    @field_validator("model_ref")
    @classmethod
    def validate_model_ref(cls, value: str) -> str:
        try:
            ModelRef.parse(value)
        except ModelRouterError as error:
            raise ValueError(str(error)) from error
        return value


class UpdateAgentGraphRequest(BaseModel):
    graph_definition: GraphDefinition


class RunAgentRequest(BaseModel):
    agent_id: UUID
    input_text: str = Field(min_length=1, max_length=100_000)


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    status: AgentStatus
    model_ref: str
    graph_definition: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, agent: Agent) -> "AgentResponse":
        return cls(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            status=agent.status,
            model_ref=agent.model_ref,
            graph_definition=agent.graph_definition,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )


class RunResponse(BaseModel):
    id: UUID
    agent_id: UUID
    status: RunStatus
    input_text: str
    output_text: str | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    provider_id: str | None
    model_id: str | None
    finish_reason: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    latency_ms: int | None

    @classmethod
    def from_domain(cls, run: AgentRun) -> "RunResponse":
        return cls(
            id=run.id,
            agent_id=run.agent_id,
            status=run.status,
            input_text=run.input_text,
            output_text=run.output_text,
            error=run.error,
            created_at=run.created_at,
            started_at=run.started_at,
            finished_at=run.finished_at,
            provider_id=run.provider_id,
            model_id=run.model_id,
            finish_reason=run.finish_reason,
            input_tokens=run.input_tokens,
            output_tokens=run.output_tokens,
            total_tokens=run.total_tokens,
            latency_ms=run.latency_ms,
        )


class RecoveryCheckpointResponse(BaseModel):
    checkpoint_id: str
    sequence: int | None
    format_version: int | None
    reason: str
    checksum: str
    created_at: datetime


class RecoveryActionResponse(BaseModel):
    entry_id: str
    action_type: str
    risk: str
    status: str
    rollback_status: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class RecoveryDecisionResponse(BaseModel):
    decision_id: str
    checkpoint_id: str | None
    outcome: str
    details: dict[str, object]
    created_at: datetime


class RecoveryLimitsResponse(BaseModel):
    automatic_resume: bool
    automatic_rollback: bool
    description: str


class RecoveryReportResponse(BaseModel):
    run_id: str
    checkpoints: list[RecoveryCheckpointResponse]
    actions: list[RecoveryActionResponse]
    decisions: list[RecoveryDecisionResponse]
    limits: RecoveryLimitsResponse


class RunTreeNodeResponse(BaseModel):
    node_id: str | None
    depth: int
    run: RunResponse
    children: list["RunTreeNodeResponse"]

    @classmethod
    def from_domain(cls, node: RunTreeNode) -> "RunTreeNodeResponse":
        return cls(
            node_id=node.node_id,
            depth=node.depth,
            run=RunResponse.from_domain(node.run),
            children=[cls.from_domain(child) for child in node.children],
        )


class ProviderStatusResponse(BaseModel):
    provider_id: str
    enabled: bool
    available: bool
    models: list[str]
    capabilities: dict[str, bool]
    error_code: ModelErrorCode | None
    error: str | None

    @classmethod
    def from_domain(cls, provider: ProviderStatus) -> "ProviderStatusResponse":
        return cls(
            provider_id=provider.provider_id,
            enabled=provider.enabled,
            available=provider.available,
            models=list(provider.models),
            capabilities={
                "chat": provider.capabilities.chat,
                "discovery": provider.capabilities.discovery,
                "vision": provider.capabilities.vision,
                "image_captioning": provider.capabilities.image_captioning,
                "ocr": provider.capabilities.ocr,
                "grounding": provider.capabilities.grounding,
                "ui_understanding": provider.capabilities.ui_understanding,
                "multi_image": provider.capabilities.multi_image,
                "function_calling": provider.capabilities.function_calling,
            },
            error_code=provider.error_code,
            error=provider.error,
        )


class VisionAnalysisRequest(BaseModel):
    mode: VisionMode = VisionMode.DESCRIBE
    prompt: str | None = Field(default=None, max_length=10_000)
    model: str | None = Field(default=None, max_length=500)


class VisionFolderRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    root: str = Field(min_length=1, max_length=10_000)


class VisionAssetResponse(BaseModel):
    id: str
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    source_type: str
    created_at: datetime


class VisionAnalysisResponse(BaseModel):
    id: str
    asset_id: str
    provider_id: str
    model_id: str
    mode: VisionMode
    prompt: str | None
    status: VisionAnalysisStatus
    raw_text: str | None
    description: str | None
    ocr_text: str | None
    structured_result: dict[str, Any] | None
    latency_ms: int | None
    error_code: str | None
    created_at: datetime
    completed_at: datetime | None


class VisionFolderResponse(BaseModel):
    id: str
    display_name: str
    enabled: bool
    created_at: datetime


class CreateMemoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: UUID
    kind: MemoryKind
    content: str = Field(min_length=1, max_length=100_000)
    tags: list[str] = Field(default_factory=list, max_length=100)


class MemorySearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: UUID
    query: str = Field(default="", max_length=100_000)


class MemoryResponse(BaseModel):
    id: UUID
    project_id: str
    agent_id: UUID
    kind: MemoryKind
    content: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, record: MemoryRecord) -> "MemoryResponse":
        return cls(
            id=record.id,
            project_id=record.project_id,
            agent_id=record.agent_id,
            kind=record.kind,
            content=record.content,
            tags=list(record.tags),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class MemorySearchResponse(MemoryResponse):
    rank: int
    score: float | None

    @classmethod
    def from_match(cls, match: MemoryMatch) -> "MemorySearchResponse":
        return cls(**MemoryResponse.from_domain(match.record).model_dump(), rank=match.rank, score=match.score)


class LexiResponse(BaseModel):
    installed: bool
    agent: AgentResponse | None

    @classmethod
    def from_agent(cls, agent: Agent | None) -> "LexiResponse":
        return cls(installed=agent is not None, agent=AgentResponse.from_domain(agent) if agent else None)


class BootstrapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9_.-]+$")
    bootstrap_secret: str = Field(min_length=32, max_length=512)
    device_name: str = Field(min_length=1, max_length=200)


class PasskeyRegistrationOptionsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_name: str = Field(min_length=1, max_length=200)


class PasskeyAuthenticationOptionsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9_.-]+$")


class PasskeyVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_id: str = Field(min_length=1, max_length=36)
    credential: dict[str, Any]


class WebAuthnOptionsResponse(BaseModel):
    challenge_id: str
    options: dict[str, Any]


class AuthPrincipalResponse(BaseModel):
    user_id: str
    username: str
    role: str
    session_id: str
    device_id: str
    device_trust: str
    authentication_strength: str
    csrf_token: str


class TotpEnrollmentResponse(BaseModel):
    secret: str
    otpauth_uri: str


class TotpConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    secret: str = Field(min_length=16, max_length=128)
    code: str = Field(pattern=r"^\d{6,8}$")


class TotpVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(pattern=r"^\d{6,8}$")


class DeviceResponse(BaseModel):
    id: str
    display_name: str
    trust: str
    revoked_at: datetime | None
    last_authenticated_at: datetime | None
    created_at: datetime


class RenameDeviceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=200)


class CreateSecurityApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=10_000)
    scope: dict[str, Any] = Field(default_factory=dict)
    expires_in_seconds: int = Field(default=300, gt=0, le=86_400)
    target: str | None = Field(default=None, max_length=500)
    run_id: str | None = Field(default=None, max_length=36)
    task_ref: str | None = Field(default=None, max_length=100)
    risk: str | None = Field(default=None, max_length=30)


class DecideSecurityApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["allow_once", "allow_for_task", "reject"]


class SecurityApprovalResponse(BaseModel):
    id: str
    project_id: str
    requested_by: str
    action: str
    target: str | None
    run_id: str | None
    task_ref: str | None
    risk: str | None
    reason: str
    scope: dict[str, Any]
    status: str
    decision: str | None
    expires_at: datetime
    decided_at: datetime | None
    created_at: datetime


class GrantResponse(BaseModel):
    id: str
    subject: str
    action: str
    target: str | None
    run_id: str | None
    task_ref: str | None
    status: str
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime


class LockdownResponse(BaseModel):
    active: bool
    updated_at: datetime


class SecurityAuditResponse(BaseModel):
    id: str
    event_type: str
    actor_user_id: str | None
    session_id: str | None
    device_id: str | None
    target: str | None
    result: str
    metadata: dict[str, Any]
    created_at: datetime


class CreateVaultCredentialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    credential_type: str = Field(min_length=1, max_length=100)
    secret: str = Field(min_length=1, max_length=100_000)


class ReplaceVaultCredentialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    secret: str = Field(min_length=1, max_length=100_000)


class VaultCredentialResponse(BaseModel):
    id: str
    name: str
    credential_type: str
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime
