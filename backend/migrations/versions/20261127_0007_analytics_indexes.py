"""Add indexes for admin analytics date-range aggregations.

Revision ID: 20261127_0007
Revises: 20261126_0006
Create Date: 2026-11-27
"""
from typing import Sequence

from alembic import op

revision: str = "20261127_0007"
down_revision: str | None = "20261126_0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


_ANALYTICS_INDEXES = (
    ("ix_users_created_at", "users", ("created_at",)),
    ("ix_doctor_profiles_created_at", "doctor_profiles", ("created_at",)),
    (
        "ix_doctor_verification_events_created_at",
        "doctor_verification_events",
        ("created_at",),
    ),
    ("ix_appointments_created_at", "appointments", ("created_at",)),
    (
        "ix_appointment_audit_events_created_at",
        "appointment_audit_events",
        ("created_at",),
    ),
    (
        "ix_doctor_credentials_submitted_at",
        "doctor_credentials",
        ("submitted_at",),
    ),
    ("ix_notification_jobs_created_at", "notification_jobs", ("created_at",)),
)


def upgrade() -> None:
    for index_name, table_name, columns in _ANALYTICS_INDEXES:
        op.create_index(index_name, table_name, list(columns))


def downgrade() -> None:
    for index_name, table_name, _columns in reversed(_ANALYTICS_INDEXES):
        op.drop_index(index_name, table_name=table_name)
