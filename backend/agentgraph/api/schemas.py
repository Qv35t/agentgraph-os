from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agentgraph.domain.entities import Agent, AgentRun, AgentStatus, RunStatus
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
    nodes: list["GraphNode"] = Field(default_factory=list, max_length=100)
    edges: list["GraphEdge"] = Field(default_factory=list, max_length=200)


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100)
    type: str = Field(default="agent", min_length=1, max_length=50)
    label: str = Field(min_length=1, max_length=200)
    position: tuple[float, float]


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
