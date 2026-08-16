from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentgraph.domain.entities import ACTIVE_RUN_STATUSES
from agentgraph.persistence.models import AgentRunRecord


class RunRepository:
    async def create(self, session: AsyncSession, *, agent_id: UUID, input_text: str) -> AgentRunRecord:
        record = AgentRunRecord(agent_id=str(agent_id), input_text=input_text)
        session.add(record)
        await session.flush()
        return record

    async def get(self, session: AsyncSession, run_id: UUID) -> AgentRunRecord | None:
        return await session.get(AgentRunRecord, str(run_id))

    async def list_for_agent(self, session: AsyncSession, agent_id: UUID) -> list[AgentRunRecord]:
        result = await session.scalars(
            select(AgentRunRecord)
            .where(AgentRunRecord.agent_id == str(agent_id))
            .order_by(AgentRunRecord.created_at.desc())
        )
        return list(result)

    async def has_active_for_agent(self, session: AsyncSession, agent_id: UUID) -> bool:
        result = await session.scalar(
            select(AgentRunRecord.id)
            .where(AgentRunRecord.agent_id == str(agent_id))
            .where(AgentRunRecord.status.in_(ACTIVE_RUN_STATUSES))
            .limit(1)
        )
        return result is not None

    async def list_stale(self, session: AsyncSession) -> list[AgentRunRecord]:
        result = await session.scalars(select(AgentRunRecord).where(AgentRunRecord.status.in_(ACTIVE_RUN_STATUSES)))
        return list(result)

    async def list_by_ids(self, session: AsyncSession, run_ids: list[UUID]) -> list[AgentRunRecord]:
        if not run_ids:
            return []
        statement = select(AgentRunRecord).where(AgentRunRecord.id.in_([str(run_id) for run_id in run_ids]))
        result = await session.scalars(statement)
        return list(result)
