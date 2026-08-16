from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from agentgraph.domain.entities import AgentRun


@dataclass(frozen=True, slots=True)
class DelegationContext:
    parent_run_id: UUID | None = None
    root_run_id: UUID | None = None
    depth: int = 0
    ancestry: tuple[UUID, ...] = ()


class DelegationPort(Protocol):
    async def run_child(
        self,
        *,
        parent_run_id: UUID,
        node_id: str,
        agent_id: UUID,
        input_text: str,
        context: DelegationContext,
    ) -> AgentRun: ...


@dataclass(frozen=True, slots=True)
class AgentExecutionRequest:
    """The complete, project-owned input accepted by a runtime workflow."""

    agent_id: UUID
    run_id: UUID
    input_text: str
    model_ref: str
    graph_definition: dict[str, object]
    delegation_context: DelegationContext | None = None
