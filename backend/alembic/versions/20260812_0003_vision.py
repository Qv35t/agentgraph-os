"""Add persisted vision assets, analyses, and registered folders.

Revision ID: 20260812_0003
Revises: 20260811_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260812_0003"
down_revision: str | None = "20260811_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vision_assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False, unique=True),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("storage_locator", sa.String(length=255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vision_assets_sha256", "vision_assets", ["sha256"])
    op.create_table(
        "vision_analyses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "asset_id", sa.String(length=36), sa.ForeignKey("vision_assets.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("provider_id", sa.String(length=100), nullable=False),
        sa.Column("model_id", sa.String(length=500), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("structured_result", sa.JSON(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_vision_analyses_asset_id", "vision_analyses", ["asset_id"])
    op.create_table(
        "vision_folders",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("root", sa.Text(), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("vision_folders")
    op.drop_index("ix_vision_analyses_asset_id", table_name="vision_analyses")
    op.drop_table("vision_analyses")
    op.drop_index("ix_vision_assets_sha256", table_name="vision_assets")
    op.drop_table("vision_assets")
