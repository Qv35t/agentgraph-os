from collections.abc import Mapping
from typing import cast
from uuid import UUID

from sqlalchemy import Integer, func, select, text
from sqlalchemy import cast as sql_cast
from sqlalchemy.ext.asyncio import AsyncSession

from agentgraph.domain.recovery import ActionLedgerStatus, CheckpointReason, RecoveryOutcome, checkpoint_checksum
from agentgraph.persistence.models import RunActionLedgerEntryRecord, RunCheckpointRecord, RunRecoveryDecisionRecord


class RecoveryRepository:
    async def create_checkpoint(
        self, session: AsyncSession, *, run_id: UUID, reason: CheckpointReason, state: dict[str, object]
    ) -> RunCheckpointRecord:
        previous = await session.scalar(
            select(func.max(sql_cast(RunCheckpointRecord.sequence, Integer))).where(
                RunCheckpointRecord.run_id == str(run_id)
            )
        )
        checkpoint = RunCheckpointRecord(
            run_id=str(run_id),
            sequence=(previous or 0) + 1,
            reason=reason,
            state=state,
            checksum=checkpoint_checksum(state),
        )
        session.add(checkpoint)
        await session.flush()
        return checkpoint

    async def latest_checkpoint(self, session: AsyncSession, run_id: UUID) -> RunCheckpointRecord | None:
        return cast(
            RunCheckpointRecord | None,
            await session.scalar(
                select(RunCheckpointRecord)
                .where(RunCheckpointRecord.run_id == str(run_id))
                .order_by(RunCheckpointRecord.sequence.desc())
                .limit(1)
            ),
        )

    async def list_checkpoint_metadata(self, session: AsyncSession, run_id: UUID) -> list[dict[str, object]]:
        result = await session.execute(
            text(
                "SELECT id, sequence, format_version, reason, checksum, created_at "
                "FROM run_checkpoints WHERE run_id = :run_id "
                "ORDER BY CASE WHEN typeof(sequence) = 'integer' THEN sequence ELSE -1 END DESC"
            ),
            {"run_id": str(run_id)},
        )
        return [_checkpoint_metadata(dict(row._mapping)) for row in result]

    async def create_action(
        self,
        session: AsyncSession,
        *,
        run_id: UUID,
        tool_invocation_id: str | None,
        action_type: str,
        risk: str,
        metadata: dict[str, object],
    ) -> RunActionLedgerEntryRecord:
        entry = RunActionLedgerEntryRecord(
            run_id=str(run_id),
            tool_invocation_id=tool_invocation_id,
            action_type=action_type,
            risk=risk,
            status=ActionLedgerStatus.INTENT_RECORDED,
            action_details=metadata,
            rollback_status="not_supported",
        )
        session.add(entry)
        await session.flush()
        return entry

    async def get_action(self, session: AsyncSession, entry_id: str) -> RunActionLedgerEntryRecord | None:
        return await session.get(RunActionLedgerEntryRecord, entry_id)

    async def list_actions(self, session: AsyncSession, run_id: UUID) -> list[RunActionLedgerEntryRecord]:
        return list(
            await session.scalars(
                select(RunActionLedgerEntryRecord)
                .where(RunActionLedgerEntryRecord.run_id == str(run_id))
                .order_by(RunActionLedgerEntryRecord.created_at)
            )
        )

    async def create_decision(
        self,
        session: AsyncSession,
        *,
        run_id: UUID,
        checkpoint_id: str | None,
        outcome: RecoveryOutcome,
        details: dict[str, object],
    ) -> RunRecoveryDecisionRecord:
        decision = RunRecoveryDecisionRecord(
            run_id=str(run_id), checkpoint_id=checkpoint_id, outcome=outcome, details=details
        )
        session.add(decision)
        await session.flush()
        return decision

    async def list_decisions(self, session: AsyncSession, run_id: UUID) -> list[RunRecoveryDecisionRecord]:
        return list(
            await session.scalars(
                select(RunRecoveryDecisionRecord)
                .where(RunRecoveryDecisionRecord.run_id == str(run_id))
                .order_by(RunRecoveryDecisionRecord.created_at.desc())
            )
        )


def _checkpoint_metadata(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "id": str(row["id"]),
        "sequence": _safe_int(row["sequence"]),
        "format_version": _safe_int(row["format_version"]),
        "reason": str(row["reason"]),
        "checksum": str(row["checksum"]),
        "created_at": row["created_at"],
    }


def _safe_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
