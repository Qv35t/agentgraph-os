"""Add persistent parent-child run delegations.

Revision ID: 20260816_0005
Revises: 20260815_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260816_0005"
down_revision: str | None = "20260815_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "run_delegations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "parent_run_id", sa.String(length=36), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "child_run_id", sa.String(length=36), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("node_id", sa.String(length=100), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("parent_run_id", "node_id", name="uq_run_delegations_parent_node"),
        sa.UniqueConstraint("child_run_id"),
    )
    op.create_index("ix_run_delegations_parent_run_id", "run_delegations", ["parent_run_id"])
    op.create_index("ix_run_delegations_child_run_id", "run_delegations", ["child_run_id"])


def downgrade() -> None:
    op.drop_index("ix_run_delegations_child_run_id", table_name="run_delegations")
    op.drop_index("ix_run_delegations_parent_run_id", table_name="run_delegations")
    op.drop_table("run_delegations")
