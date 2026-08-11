from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentgraph.persistence.models import AgentRecord


class AgentRepository:
    async def create(
        self,
        session: AsyncSession,
        *,
        name: str,
        description: str | None,
        model_ref: str,
        graph_definition: dict[str, object],
    ) -> AgentRecord:
        record = AgentRecord(
            name=name,
            description=description,
            model_ref=model_ref,
            graph_definition=graph_definition,
        )
        session.add(record)
        await session.flush()
        return record

    async def get(self, session: AsyncSession, agent_id: UUID) -> AgentRecord | None:
        return await session.get(AgentRecord, str(agent_id))

    async def list(self, session: AsyncSession) -> list[AgentRecord]:
        result = await session.scalars(select(AgentRecord).order_by(AgentRecord.created_at))
        return list(result)

    async def delete(self, session: AsyncSession, record: AgentRecord) -> None:
        await session.delete(record)
