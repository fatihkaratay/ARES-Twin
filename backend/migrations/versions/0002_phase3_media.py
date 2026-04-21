"""phase 3 media tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mission_video",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "mission_log_id",
            sa.Integer,
            sa.ForeignKey("mission_log.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("video_path", sa.String(512), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "terrain_snapshot",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("quadrant_x", sa.Integer, nullable=False),
        sa.Column("quadrant_y", sa.Integer, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("image_path", sa.String(512), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("quadrant_x", "quadrant_y"),
    )


def downgrade() -> None:
    op.drop_table("terrain_snapshot")
    op.drop_table("mission_video")
