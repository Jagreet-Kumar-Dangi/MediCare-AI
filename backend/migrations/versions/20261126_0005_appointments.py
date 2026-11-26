"""Add doctor availability and appointment management.

Revision ID: 20261126_0005
Revises: 20261126_0004
Create Date: 2026-11-26
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261126_0005"
down_revision: str | None = "20261126_0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


_ACTIVE_APPOINTMENT_EXCLUSION = postgresql.ExcludeConstraint(
    ("doctor_profile_id", "="),
    (sa.text("tstzrange(scheduled_start, scheduled_end, '[)')"), "&&"),
    where=sa.text("status IN ('BOOKED', 'CONFIRMED')"),
    using="gist",
    name="ex_appointments_doctor_time_overlap",
).ddl_if(dialect="postgresql")


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.create_table(
        "doctor_availabilities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doctor_profile_id", sa.Integer(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("break_start", sa.Time(), nullable=True),
        sa.Column("break_end", sa.Time(), nullable=True),
        sa.Column("appointment_duration_minutes", sa.Integer(), nullable=False),
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
        sa.CheckConstraint(
            "weekday BETWEEN 0 AND 6",
            name="ck_doctor_availabilities_weekday",
        ),
        sa.CheckConstraint(
            "start_time < end_time",
            name="ck_doctor_availabilities_time_range",
        ),
        sa.CheckConstraint(
            "(break_start IS NULL AND break_end IS NULL) OR "
            "(break_start IS NOT NULL AND break_end IS NOT NULL AND "
            "start_time <= break_start AND break_start < break_end AND "
            "break_end <= end_time)",
            name="ck_doctor_availabilities_break_range",
        ),
        sa.CheckConstraint(
            "appointment_duration_minutes BETWEEN 5 AND 240",
            name="ck_doctor_availabilities_duration",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_profile_id"],
            ["doctor_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "doctor_profile_id",
            "weekday",
            "start_time",
            "end_time",
            name="uq_doctor_availabilities_window",
        ),
    )
    op.create_index(
        "ix_doctor_availabilities_profile_weekday",
        "doctor_availabilities",
        ["doctor_profile_id", "weekday"],
    )
    op.create_table(
        "doctor_availability_exceptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doctor_profile_id", sa.Integer(), nullable=False),
        sa.Column("exception_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("reason", sa.String(length=250), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(start_time IS NULL AND end_time IS NULL) OR "
            "(start_time IS NOT NULL AND end_time IS NOT NULL AND "
            "start_time < end_time)",
            name="ck_doctor_availability_exceptions_time_range",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_profile_id"],
            ["doctor_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_doctor_availability_exceptions_profile_date",
        "doctor_availability_exceptions",
        ["doctor_profile_id", "exception_date"],
    )
    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("doctor_profile_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="BOOKED",
            nullable=False,
        ),
        sa.Column("reason_for_visit", sa.String(length=1000), nullable=False),
        sa.Column("patient_notes", sa.Text(), nullable=True),
        sa.Column("doctor_notes", sa.Text(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "scheduled_start < scheduled_end",
            name="ck_appointments_time_range",
        ),
        sa.CheckConstraint(
            "status IN ('BOOKED', 'CONFIRMED', 'REJECTED', 'COMPLETED', "
            "'CANCELLED', 'NO_SHOW')",
            name="ck_appointments_status",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_profile_id"],
            ["doctor_profiles.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        _ACTIVE_APPOINTMENT_EXCLUSION,
    )
    op.create_index(
        "ix_appointments_patient_status_start",
        "appointments",
        ["patient_id", "status", "scheduled_start"],
    )
    op.create_index(
        "ix_appointments_doctor_status_start",
        "appointments",
        ["doctor_profile_id", "status", "scheduled_start"],
    )
    op.create_table(
        "appointment_audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("previous_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("previous_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("new_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("new_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('BOOKED', 'CONFIRMED', 'REJECTED', 'COMPLETED', "
            "'CANCELLED', 'RESCHEDULED', 'NO_SHOW')",
            name="ck_appointment_audit_events_action",
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_appointment_audit_events_appointment_created",
        "appointment_audit_events",
        ["appointment_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_appointment_audit_events_appointment_created",
        table_name="appointment_audit_events",
    )
    op.drop_table("appointment_audit_events")
    op.drop_index(
        "ix_appointments_doctor_status_start",
        table_name="appointments",
    )
    op.drop_index(
        "ix_appointments_patient_status_start",
        table_name="appointments",
    )
    op.drop_table("appointments")
    op.drop_index(
        "ix_doctor_availability_exceptions_profile_date",
        table_name="doctor_availability_exceptions",
    )
    op.drop_table("doctor_availability_exceptions")
    op.drop_index(
        "ix_doctor_availabilities_profile_weekday",
        table_name="doctor_availabilities",
    )
    op.drop_table("doctor_availabilities")
