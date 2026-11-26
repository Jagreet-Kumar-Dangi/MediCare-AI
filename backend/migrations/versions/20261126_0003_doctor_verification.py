"""Add doctor profiles and verification audit events.

Revision ID: 20261126_0003
Revises: 20261126_0002
Create Date: 2026-11-26
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261126_0003"
down_revision: str | None = "20261126_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "doctor_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("specialization", sa.String(length=120), nullable=False),
        sa.Column("qualification", sa.String(length=160), nullable=False),
        sa.Column("medical_registration_number", sa.String(length=64), nullable=False),
        sa.Column("years_of_experience", sa.Integer(), nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=True),
        sa.Column("clinic_or_hospital", sa.String(length=200), nullable=True),
        sa.Column("consultation_fee", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("biography", sa.Text(), nullable=True),
        sa.Column(
            "verification_status",
            sa.String(length=16),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column(
            "verification_submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.Integer(), nullable=True),
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
            "length(trim(full_name)) > 0",
            name="ck_doctor_profiles_full_name_nonempty",
        ),
        sa.CheckConstraint(
            "length(trim(specialization)) > 0",
            name="ck_doctor_profiles_specialization_nonempty",
        ),
        sa.CheckConstraint(
            "length(trim(qualification)) > 0",
            name="ck_doctor_profiles_qualification_nonempty",
        ),
        sa.CheckConstraint(
            "medical_registration_number = "
            "upper(trim(medical_registration_number)) "
            "AND length(trim(medical_registration_number)) > 0",
            name="ck_doctor_profiles_registration_number_normalized",
        ),
        sa.CheckConstraint(
            "years_of_experience BETWEEN 0 AND 80",
            name="ck_doctor_profiles_experience_range",
        ),
        sa.CheckConstraint(
            "consultation_fee IS NULL OR consultation_fee >= 0",
            name="ck_doctor_profiles_consultation_fee_nonnegative",
        ),
        sa.CheckConstraint(
            "verification_status IN ('PENDING', 'APPROVED', 'REJECTED', 'SUSPENDED')",
            name="ck_doctor_profiles_verification_status",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["verified_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_doctor_profiles_user_id"),
        sa.UniqueConstraint(
            "medical_registration_number",
            name="uq_doctor_profiles_registration_number",
        ),
    )
    op.create_index(
        "ix_doctor_profiles_status_created_at",
        "doctor_profiles",
        ["verification_status", "created_at"],
        unique=False,
    )
    op.create_table(
        "doctor_verification_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doctor_profile_id", sa.Integer(), nullable=False),
        sa.Column("admin_user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('APPROVED', 'REJECTED', 'SUSPENDED')",
            name="ck_doctor_verification_events_action",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_profile_id"], ["doctor_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["admin_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_doctor_verification_events_doctor_profile_id",
        "doctor_verification_events",
        ["doctor_profile_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_doctor_verification_events_doctor_profile_id",
        table_name="doctor_verification_events",
    )
    op.drop_table("doctor_verification_events")
    op.drop_index(
        "ix_doctor_profiles_status_created_at",
        table_name="doctor_profiles",
    )
    op.drop_table("doctor_profiles")
