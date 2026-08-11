from typing import TypedDict, cast
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from agentgraph.models.contracts import ModelMessage, ModelResponse
from agentgraph.models.router import ModelRouter


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
        self, *, agent_id: UUID, run_id: UUID, input_text: str, model_ref: str = "auto://default"
    ) -> ModelResponse:
        result = self._graph.invoke(
            {
                "agent_id": str(agent_id),
                "run_id": str(run_id),
                "input_text": input_text,
                "output_text": "",
                "model_ref": model_ref,
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

    async def invoke(self, *, agent_id: UUID, run_id: UUID, input_text: str, model_ref: str) -> ModelResponse:
        result = await self._graph.ainvoke(
            {
                "agent_id": str(agent_id),
                "run_id": str(run_id),
                "input_text": input_text,
                "output_text": "",
                "model_ref": model_ref,
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
