from agentgraph.models.contracts import ModelErrorCode, ModelResponse, ModelRouterError
from agentgraph.runtime.execution import AgentExecutionRequest
from agentgraph.runtime.graph import ModelGraphRuntime
from agentgraph.runtime.lexi import LexiGraphRuntime
from agentgraph.runtime.team import TeamGraphRuntime


class WorkflowRuntime:
    """Allowlisted runtime dispatch stored as data in a normal agent graph."""

    def __init__(self, model: ModelGraphRuntime, lexi: LexiGraphRuntime, team: TeamGraphRuntime | None = None) -> None:
        self._model = model
        self._lexi = lexi
        self._team = team

    def bind_team(self, team: TeamGraphRuntime) -> None:
        self._team = team

    async def invoke(self, execution: AgentExecutionRequest) -> ModelResponse:
        runtime = execution.graph_definition.get("runtime", "model-v1")
        if runtime == "model-v1":
            return await self._model.invoke(execution)
        if runtime == "lexi-v1":
            return await self._lexi.invoke(execution)
        if runtime == "team-v1" and self._team is not None:
            return await self._team.invoke(execution)
        raise ModelRouterError(ModelErrorCode.CONFIGURATION_ERROR, "Unsupported workflow runtime")
