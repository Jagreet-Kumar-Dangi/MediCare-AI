"""Add persistent notification and outbox tables.

Revision ID: 20261126_0006
Revises: 20261126_0005
Create Date: 2026-11-26
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261126_0006"
down_revision: str | None = "20261126_0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_NOTIFICATION_TYPES = (
    "'APPOINTMENT_BOOKED', 'APPOINTMENT_CONFIRMED', "
    "'APPOINTMENT_CANCELLED', 'APPOINTMENT_RESCHEDULED', "
    "'APPOINTMENT_COMPLETED', 'APPOINTMENT_REMINDER_24H', "
    "'APPOINTMENT_REMINDER_1H'"
)


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recipient_user_id", sa.Integer(), nullable=False),
        sa.Column("notification_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("related_appointment_id", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            f"notification_type IN ({_NOTIFICATION_TYPES})",
            name="ck_notifications_type",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["related_appointment_id"],
            ["appointments.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_notifications_idempotency_key",
        ),
    )
    op.create_index(
        "ix_notifications_recipient_created",
        "notifications",
        ["recipient_user_id", "created_at"],
    )
    op.create_index(
        "ix_notifications_recipient_read_created",
        "notifications",
        ["recipient_user_id", "read_at", "created_at"],
    )

    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "email_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "in_app_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "reminder_24h_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "reminder_1h_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "notification_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recipient_user_id", sa.Integer(), nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=False),
        sa.Column("notification_type", sa.String(length=40), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("appointment_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_token", sa.String(length=36), nullable=True),
        sa.Column("last_error", sa.String(length=80), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            f"notification_type IN ({_NOTIFICATION_TYPES})",
            name="ck_notification_jobs_type",
        ),
        sa.CheckConstraint(
            "channel IN ('EMAIL', 'REMINDER')",
            name="ck_notification_jobs_channel",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'SENT', 'FAILED', "
            "'CANCELLED', 'SKIPPED')",
            name="ck_notification_jobs_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_notification_jobs_attempt_count",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_notification_jobs_idempotency_key",
        ),
    )
    op.create_index(
        "ix_notification_jobs_status_schedule",
        "notification_jobs",
        ["status", "scheduled_at", "next_attempt_at"],
    )
    op.create_index(
        "ix_notification_jobs_recipient_created",
        "notification_jobs",
        ["recipient_user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_jobs_recipient_created",
        table_name="notification_jobs",
    )
    op.drop_index(
        "ix_notification_jobs_status_schedule",
        table_name="notification_jobs",
    )
    op.drop_table("notification_jobs")
    op.drop_table("notification_preferences")
    op.drop_index(
        "ix_notifications_recipient_read_created",
        table_name="notifications",
    )
    op.drop_index(
        "ix_notifications_recipient_created",
        table_name="notifications",
    )
    op.drop_table("notifications")
