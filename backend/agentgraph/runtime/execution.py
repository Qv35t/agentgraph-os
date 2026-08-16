from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AgentExecutionRequest:
    """The complete, project-owned input accepted by a runtime workflow."""

    agent_id: UUID
    run_id: UUID
    input_text: str
    model_ref: str
    graph_definition: dict[str, object]
