"""Add durable local recovery records.

Revision ID: 20260817_0007
Revises: 20260817_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260817_0007"
down_revision: str | None = "20260817_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("execution_spec", sa.JSON(), nullable=True))
    op.create_table(
        "run_checkpoints",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("format_version", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=20), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "sequence", name="uq_run_checkpoints_run_sequence"),
    )
    op.create_index("ix_run_checkpoints_run_id", "run_checkpoints", ["run_id"])
    op.create_table(
        "run_action_ledger_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "tool_invocation_id",
            sa.String(length=36),
            sa.ForeignKey("tool_invocations.id", ondelete="SET NULL"),
            nullable=True,
            unique=True,
        ),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("risk", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("rollback_status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_run_action_ledger_entries_run_id", "run_action_ledger_entries", ["run_id"])
    op.create_table(
        "run_recovery_decisions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "checkpoint_id",
            sa.String(length=36),
            sa.ForeignKey("run_checkpoints.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_run_recovery_decisions_run_id", "run_recovery_decisions", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_run_recovery_decisions_run_id", table_name="run_recovery_decisions")
    op.drop_table("run_recovery_decisions")
    op.drop_index("ix_run_action_ledger_entries_run_id", table_name="run_action_ledger_entries")
    op.drop_table("run_action_ledger_entries")
    op.drop_index("ix_run_checkpoints_run_id", table_name="run_checkpoints")
    op.drop_table("run_checkpoints")
    op.drop_column("agent_runs", "execution_spec")
