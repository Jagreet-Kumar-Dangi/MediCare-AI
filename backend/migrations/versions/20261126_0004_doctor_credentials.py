"""Add private doctor credential documents and review history.

Revision ID: 20261126_0004
Revises: 20261126_0003
Create Date: 2026-11-26
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261126_0004"
down_revision: str | None = "20261126_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


_SINGLE_ACTIVE_CREDENTIAL_PREDICATE = sa.text(
    "document_type != 'ADDITIONAL_QUALIFICATION_CERTIFICATE' "
    "AND verification_status IN ('PENDING', 'APPROVED')"
)


def upgrade() -> None:
    op.create_table(
        "doctor_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doctor_profile_id", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(length=48), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=32), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "verification_status",
            sa.String(length=16),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "document_type IN "
            "('MEDICAL_REGISTRATION_CERTIFICATE', "
            "'MEDICAL_DEGREE_CERTIFICATE', "
            "'ADDITIONAL_QUALIFICATION_CERTIFICATE')",
            name="ck_doctor_credentials_document_type",
        ),
        sa.CheckConstraint(
            "verification_status IN ('PENDING', 'APPROVED', 'REJECTED')",
            name="ck_doctor_credentials_verification_status",
        ),
        sa.CheckConstraint(
            "length(trim(original_filename)) > 0",
            name="ck_doctor_credentials_original_filename_nonempty",
        ),
        sa.CheckConstraint(
            "file_size > 0",
            name="ck_doctor_credentials_file_size_positive",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_profile_id"],
            ["doctor_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "storage_key",
            name="uq_doctor_credentials_storage_key",
        ),
    )
    op.create_index(
        "ix_doctor_credentials_profile_submitted",
        "doctor_credentials",
        ["doctor_profile_id", "submitted_at"],
        unique=False,
    )
    op.create_index(
        "ix_doctor_credentials_status_submitted",
        "doctor_credentials",
        ["verification_status", "submitted_at"],
        unique=False,
    )
    op.create_index(
        "uq_doctor_credentials_one_active_per_type",
        "doctor_credentials",
        ["doctor_profile_id", "document_type"],
        unique=True,
        postgresql_where=_SINGLE_ACTIVE_CREDENTIAL_PREDICATE,
        sqlite_where=_SINGLE_ACTIVE_CREDENTIAL_PREDICATE,
    )
    op.create_table(
        "doctor_credential_review_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=False),
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
            "action IN ('APPROVED', 'REJECTED')",
            name="ck_doctor_credential_review_events_action",
        ),
        sa.ForeignKeyConstraint(
            ["credential_id"],
            ["doctor_credentials.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["admin_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_doctor_credential_review_events_credential_created",
        "doctor_credential_review_events",
        ["credential_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_doctor_credential_review_events_credential_created",
        table_name="doctor_credential_review_events",
    )
    op.drop_table("doctor_credential_review_events")
    op.drop_index(
        "uq_doctor_credentials_one_active_per_type",
        table_name="doctor_credentials",
    )
    op.drop_index(
        "ix_doctor_credentials_status_submitted",
        table_name="doctor_credentials",
    )
    op.drop_index(
        "ix_doctor_credentials_profile_submitted",
        table_name="doctor_credentials",
    )
    op.drop_table("doctor_credentials")
