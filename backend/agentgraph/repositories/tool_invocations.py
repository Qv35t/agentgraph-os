from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentgraph.persistence.models import ToolInvocationRecord


class ToolInvocationRepository:
    async def create(self, session: AsyncSession, record: ToolInvocationRecord) -> ToolInvocationRecord:
        session.add(record)
        await session.flush()
        return record

    async def get(self, session: AsyncSession, invocation_id: str) -> ToolInvocationRecord | None:
        return await session.get(ToolInvocationRecord, invocation_id)

    async def list_for_run(self, session: AsyncSession, run_id: UUID) -> list[ToolInvocationRecord]:
        return list(
            await session.scalars(
                select(ToolInvocationRecord)
                .where(ToolInvocationRecord.run_id == str(run_id))
                .order_by(ToolInvocationRecord.started_at)
            )
        )
