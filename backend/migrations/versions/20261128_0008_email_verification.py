"""Add persistent email verification challenges and rate limits.

Revision ID: 20261128_0008
Revises: 20261127_0007
Create Date: 2026-11-28
"""
from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261128_0008"
down_revision: str | None = "20261127_0007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "pending_email_verification",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.create_table(
        "email_verification_challenges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("otp_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_email_verification_challenges_active_user",
        "email_verification_challenges",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text(
            "consumed_at IS NULL AND superseded_at IS NULL"
        ),
        sqlite_where=sa.text("consumed_at IS NULL AND superseded_at IS NULL"),
    )
    op.create_index(
        "ix_email_verification_challenges_expires_at",
        "email_verification_challenges",
        ["expires_at"],
    )
    op.create_table(
        "email_verification_rate_limits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email_hash", sa.String(length=64), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_email_verification_rate_email_time",
        "email_verification_rate_limits",
        ["email_hash", "requested_at"],
    )
    op.create_index(
        "ix_email_verification_rate_ip_time",
        "email_verification_rate_limits",
        ["ip_hash", "requested_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_email_verification_rate_ip_time",
        table_name="email_verification_rate_limits",
    )
    op.drop_index(
        "ix_email_verification_rate_email_time",
        table_name="email_verification_rate_limits",
    )
    op.drop_table("email_verification_rate_limits")
    op.drop_index(
        "ix_email_verification_challenges_expires_at",
        table_name="email_verification_challenges",
    )
    op.drop_index(
        "uq_email_verification_challenges_active_user",
        table_name="email_verification_challenges",
    )
    op.drop_table("email_verification_challenges")
    op.drop_column("users", "pending_email_verification")
    op.drop_column("users", "email_verified_at")
