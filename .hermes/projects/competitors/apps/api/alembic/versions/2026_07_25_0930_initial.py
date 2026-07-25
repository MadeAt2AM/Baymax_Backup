"""Initial schema: users, competitors, pipeline_runs, reels, reel_analyses.

Revision ID: 2026_07_25_0930_initial
Revises:
Create Date: 2026-07-25 09:30:00

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "2026_07_25_0930_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "competitors",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column("reels_collected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reels_published", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "reels",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("shortcode", sa.String(length=32), nullable=False, unique=True),
        sa.Column("competitor_username", sa.String(length=64), nullable=False),
        sa.Column("url", sa.String(length=512), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=True),
        sa.Column("like_count", sa.Integer(), nullable=True),
        sa.Column("comment_count", sa.Integer(), nullable=True),
        sa.Column("audio_path", sa.String(length=512), nullable=True),
        sa.Column("pipeline_run_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_reels_competitor_username", "reels", ["competitor_username"])
    op.create_index("ix_reels_published_at", "reels", ["published_at"])

    op.create_table(
        "reel_analyses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("reel_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("hook", sa.Text(), nullable=True),
        sa.Column("emotion", sa.String(length=64), nullable=True),
        sa.Column("pacing", sa.String(length=64), nullable=True),
        sa.Column("notable_phrases", sa.JSON(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(length=512), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["reel_id"], ["reels.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("reel_analyses")
    op.drop_index("ix_reels_published_at", table_name="reels")
    op.drop_index("ix_reels_competitor_username", table_name="reels")
    op.drop_table("reels")
    op.drop_table("pipeline_runs")
    op.drop_table("competitors")
    op.drop_table("users")
