from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentgraph.persistence.models import RunDelegationRecord


class RunDelegationRepository:
    async def create(
        self,
        session: AsyncSession,
        *,
        parent_run_id: UUID,
        child_run_id: UUID,
        node_id: str,
        depth: int,
    ) -> RunDelegationRecord:
        record = RunDelegationRecord(
            parent_run_id=str(parent_run_id), child_run_id=str(child_run_id), node_id=node_id, depth=depth
        )
        session.add(record)
        await session.flush()
        return record

    async def list_for_parents(self, session: AsyncSession, run_ids: Iterable[UUID]) -> list[RunDelegationRecord]:
        ids = [str(run_id) for run_id in run_ids]
        if not ids:
            return []
        result = await session.scalars(
            select(RunDelegationRecord)
            .where(RunDelegationRecord.parent_run_id.in_(ids))
            .order_by(RunDelegationRecord.created_at)
        )
        return list(result)

    async def list_for_child(self, session: AsyncSession, child_run_id: UUID) -> list[RunDelegationRecord]:
        result = await session.scalars(
            select(RunDelegationRecord).where(RunDelegationRecord.child_run_id == str(child_run_id))
        )
        return list(result)
