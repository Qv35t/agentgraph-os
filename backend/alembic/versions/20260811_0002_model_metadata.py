"""Add normalized model metadata to runs.

Revision ID: 20260811_0002
Revises: 20260811_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260811_0002"
down_revision: str | None = "20260811_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for name, type_ in (
        ("provider_id", sa.String(length=100)),
        ("model_id", sa.String(length=500)),
        ("finish_reason", sa.String(length=100)),
        ("input_tokens", sa.Integer()),
        ("output_tokens", sa.Integer()),
        ("total_tokens", sa.Integer()),
        ("latency_ms", sa.Integer()),
    ):
        op.add_column("agent_runs", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    for name in (
        "latency_ms",
        "total_tokens",
        "output_tokens",
        "input_tokens",
        "finish_reason",
        "model_id",
        "provider_id",
    ):
        op.drop_column("agent_runs", name)
