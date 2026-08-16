import asyncio

from agentgraph.domain.entities import Agent
from agentgraph.services.manager import AgentManager

LEXI_RUNTIME = "lexi-v1"


class LexiTemplateService:
    """Idempotently installs Lexi as a normal AgentGraph agent."""

    def __init__(self, manager: AgentManager) -> None:
        self._manager = manager
        self._lock = asyncio.Lock()

    async def get_installed(self) -> Agent | None:
        for agent in await self._manager.list_agents():
            if agent.graph_definition.get("runtime") == LEXI_RUNTIME:
                return agent
        return None

    async def ensure_installed(self) -> Agent:
        async with self._lock:
            existing = await self.get_installed()
            if existing is not None:
                return existing
            return await self._manager.create_agent(
                name="Lexi",
                description="Local-first assistant workflow with scoped memory and controlled tools.",
                model_ref="auto://default",
                graph_definition={"version": 1, "runtime": LEXI_RUNTIME, "nodes": [], "edges": []},
            )
