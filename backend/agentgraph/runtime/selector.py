from agentgraph.models.contracts import ModelErrorCode, ModelResponse, ModelRouterError
from agentgraph.runtime.execution import AgentExecutionRequest
from agentgraph.runtime.graph import ModelGraphRuntime
from agentgraph.runtime.lexi import LexiGraphRuntime


class WorkflowRuntime:
    """Allowlisted runtime dispatch stored as data in a normal agent graph."""

    def __init__(self, model: ModelGraphRuntime, lexi: LexiGraphRuntime) -> None:
        self._model = model
        self._lexi = lexi

    async def invoke(self, execution: AgentExecutionRequest) -> ModelResponse:
        runtime = execution.graph_definition.get("runtime", "model-v1")
        if runtime == "model-v1":
            return await self._model.invoke(execution)
        if runtime == "lexi-v1":
            return await self._lexi.invoke(execution)
        raise ModelRouterError(ModelErrorCode.CONFIGURATION_ERROR, "Unsupported workflow runtime")
