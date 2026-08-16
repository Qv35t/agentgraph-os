"""Add Lexi memory, run usage links, and controlled tool history.

Revision ID: 20260815_0004
Revises: 20260812_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260815_0004"
down_revision: str | None = "20260812_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memory_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=100), nullable=False),
        sa.Column("agent_id", sa.String(length=36), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_memory_records_project_id", "memory_records", ["project_id"])
    op.create_index("ix_memory_records_agent_id", "memory_records", ["agent_id"])
    op.create_table(
        "run_memory_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "memory_id",
            sa.String(length=36),
            sa.ForeignKey("memory_records.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("memory_id_snapshot", sa.String(length=36), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
    )
    op.create_index("ix_run_memory_records_run_id", "run_memory_records", ["run_id"])
    op.create_index("ix_run_memory_records_memory_id", "run_memory_records", ["memory_id"])
    op.create_table(
        "tool_invocations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_id", sa.String(length=100), nullable=False),
        sa.Column("risk", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("approval_id", sa.String(length=100), nullable=True),
        sa.Column("input_metadata", sa.JSON(), nullable=False),
        sa.Column("output_metadata", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )
    op.create_index("ix_tool_invocations_run_id", "tool_invocations", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_tool_invocations_run_id", table_name="tool_invocations")
    op.drop_table("tool_invocations")
    op.drop_index("ix_run_memory_records_memory_id", table_name="run_memory_records")
    op.drop_index("ix_run_memory_records_run_id", table_name="run_memory_records")
    op.drop_table("run_memory_records")
    op.drop_index("ix_memory_records_agent_id", table_name="memory_records")
    op.drop_index("ix_memory_records_project_id", table_name="memory_records")
    op.drop_table("memory_records")
