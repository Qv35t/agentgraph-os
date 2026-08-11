from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agentgraph.domain.entities import Agent, AgentRun, AgentStatus, RunStatus
from agentgraph.models.contracts import (
    ModelErrorCode,
    ModelRef,
    ModelRouterError,
    ProviderStatus,
)


class HealthResponse(BaseModel):
    status: str


class GraphDefinition(BaseModel):
    """Phase 2 supports no configurable graph behavior or provider metadata."""

    model_config = ConfigDict(extra="forbid")


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
            },
            error_code=provider.error_code,
            error=provider.error,
        )
