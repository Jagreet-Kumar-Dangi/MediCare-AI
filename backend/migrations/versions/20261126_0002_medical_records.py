"""Create patient medical records metadata.

Revision ID: 20261126_0002
Revises: 20261125_0001
Create Date: 2026-11-26
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261126_0002"
down_revision: str | None = "20261125_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "medical_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=32), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=True),
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
            "length(trim(title)) > 0",
            name="ck_medical_records_title_nonempty",
        ),
        sa.CheckConstraint(
            "category IN "
            "('Blood Test', 'Prescription', 'Radiology', 'MRI / CT Scan', "
            "'X-Ray', 'Discharge Summary', 'Laboratory Report', 'Other')",
            name="ck_medical_records_category",
        ),
        sa.CheckConstraint(
            "file_size > 0",
            name="ck_medical_records_file_size_positive",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patient_profiles.user_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_medical_records_storage_key"),
    )
    op.create_index(
        "ix_medical_records_patient_created_at",
        "medical_records",
        ["patient_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_medical_records_patient_created_at",
        table_name="medical_records",
    )
    op.drop_table("medical_records")
