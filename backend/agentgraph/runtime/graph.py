from typing import TypedDict, cast
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from agentgraph.models.contracts import ModelMessage, ModelResponse
from agentgraph.models.router import ModelRouter
from agentgraph.runtime.execution import AgentExecutionRequest


class RuntimeState(TypedDict):
    agent_id: str
    run_id: str
    input_text: str
    output_text: str
    model_ref: str
    model_response: ModelResponse | None


class DeterministicGraphRuntime:
    """A real LangGraph workflow used before provider-backed execution exists."""

    def __init__(self) -> None:
        builder = StateGraph(RuntimeState)
        builder.add_node("execute", self._execute)
        builder.add_edge(START, "execute")
        builder.add_edge("execute", END)
        self._graph = builder.compile()

    async def invoke(
        self,
        execution: AgentExecutionRequest | None = None,
        *,
        agent_id: UUID | None = None,
        run_id: UUID | None = None,
        input_text: str | None = None,
        model_ref: str = "auto://default",
    ) -> ModelResponse:
        execution = _execution(execution, agent_id, run_id, input_text, model_ref)
        result = self._graph.invoke(
            {
                "agent_id": str(execution.agent_id),
                "run_id": str(execution.run_id),
                "input_text": execution.input_text,
                "output_text": "",
                "model_ref": execution.model_ref,
                "model_response": None,
            }
        )
        return ModelResponse(content=cast(str, result["output_text"]), provider_id="deterministic", model_id="phase2")

    @staticmethod
    def _execute(state: RuntimeState) -> dict[str, str]:
        return {"output_text": f"Processed: {state['input_text']}"}


class ModelGraphRuntime:
    def __init__(self, router: ModelRouter) -> None:
        self._router = router
        builder = StateGraph(RuntimeState)
        builder.add_node("generate", self._generate)
        builder.add_edge(START, "generate")
        builder.add_edge("generate", END)
        self._graph = builder.compile()

    async def invoke(
        self,
        execution: AgentExecutionRequest | None = None,
        *,
        agent_id: UUID | None = None,
        run_id: UUID | None = None,
        input_text: str | None = None,
        model_ref: str = "auto://default",
    ) -> ModelResponse:
        execution = _execution(execution, agent_id, run_id, input_text, model_ref)
        result = await self._graph.ainvoke(
            {
                "agent_id": str(execution.agent_id),
                "run_id": str(execution.run_id),
                "input_text": execution.input_text,
                "output_text": "",
                "model_ref": execution.model_ref,
                "model_response": None,
            }
        )
        response = result["model_response"]
        if response is None:
            raise RuntimeError("Model graph returned no response")
        return cast(ModelResponse, response)

    async def _generate(self, state: RuntimeState) -> dict[str, object]:
        response = await self._router.complete(
            state["model_ref"], [ModelMessage(role="user", content=state["input_text"])]
        )
        return {"output_text": response.content, "model_response": response}


def _execution(
    execution: AgentExecutionRequest | None,
    agent_id: UUID | None,
    run_id: UUID | None,
    input_text: str | None,
    model_ref: str,
) -> AgentExecutionRequest:
    if execution is not None:
        return execution
    if agent_id is None or run_id is None or input_text is None:
        raise TypeError("execution or agent_id, run_id, and input_text are required")
    return AgentExecutionRequest(agent_id, run_id, input_text, model_ref, {})
