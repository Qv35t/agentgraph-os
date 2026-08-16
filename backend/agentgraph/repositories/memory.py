from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentgraph.persistence.models import MemoryRecordRecord, RunMemoryRecord


class MemoryRepository:
    async def create(self, session: AsyncSession, record: MemoryRecordRecord) -> MemoryRecordRecord:
        session.add(record)
        await session.flush()
        return record

    async def list_for_scope(
        self, session: AsyncSession, *, project_id: str, agent_id: UUID, limit: int | None = None
    ) -> list[MemoryRecordRecord]:
        statement = (
            select(MemoryRecordRecord)
            .where(MemoryRecordRecord.project_id == project_id)
            .where(MemoryRecordRecord.agent_id == str(agent_id))
            .where(MemoryRecordRecord.deleted_at.is_(None))
            .order_by(MemoryRecordRecord.updated_at.desc(), MemoryRecordRecord.id.desc())
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list(await session.scalars(statement))

    async def get_for_scope(
        self, session: AsyncSession, *, memory_id: UUID, project_id: str, agent_id: UUID
    ) -> MemoryRecordRecord | None:
        return cast(
            MemoryRecordRecord | None,
            await session.scalar(
                select(MemoryRecordRecord)
                .where(MemoryRecordRecord.id == str(memory_id))
                .where(MemoryRecordRecord.project_id == project_id)
                .where(MemoryRecordRecord.agent_id == str(agent_id))
                .where(MemoryRecordRecord.deleted_at.is_(None))
            ),
        )

    async def add_run_links(
        self, session: AsyncSession, *, run_id: UUID, matches: list[tuple[MemoryRecordRecord, float | None]]
    ) -> None:
        session.add_all(
            [
                RunMemoryRecord(
                    run_id=str(run_id),
                    memory_id=match.id,
                    memory_id_snapshot=match.id,
                    rank=rank,
                    score=score,
                )
                for rank, (match, score) in enumerate(matches, start=1)
            ]
        )
        await session.flush()

    async def list_run_links(self, session: AsyncSession, run_id: UUID) -> list[RunMemoryRecord]:
        return list(
            await session.scalars(
                select(RunMemoryRecord).where(RunMemoryRecord.run_id == str(run_id)).order_by(RunMemoryRecord.rank)
            )
        )
