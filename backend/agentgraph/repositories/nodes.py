from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentgraph.persistence.models import NodeRecord


class NodeRepository:
    async def get(self, session: AsyncSession, node_id: str) -> NodeRecord | None:
        return await session.get(NodeRecord, node_id)

    async def list(self, session: AsyncSession) -> list[NodeRecord]:
        result = await session.scalars(select(NodeRecord).order_by(NodeRecord.created_at))
        return list(result)

    async def create(self, session: AsyncSession, record: NodeRecord) -> NodeRecord:
        session.add(record)
        await session.flush()
        return record

    async def touch(self, session: AsyncSession, record: NodeRecord, seen_at: datetime) -> None:
        record.last_seen_at = seen_at
        await session.flush()
