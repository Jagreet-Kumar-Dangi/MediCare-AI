from datetime import date, datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.patient_profile import PatientProfile


class MedicalRecordCategory(str, Enum):
    BLOOD_TEST = "Blood Test"
    PRESCRIPTION = "Prescription"
    RADIOLOGY = "Radiology"
    MRI_CT_SCAN = "MRI / CT Scan"
    X_RAY = "X-Ray"
    DISCHARGE_SUMMARY = "Discharge Summary"
    LABORATORY_REPORT = "Laboratory Report"
    OTHER = "Other"


_CATEGORY_SQL_VALUES = ", ".join(
    f"'{category.value}'" for category in MedicalRecordCategory
)


class MedicalRecord(Base):
    __tablename__ = "medical_records"
    __table_args__ = (
        CheckConstraint(
            "length(trim(title)) > 0",
            name="ck_medical_records_title_nonempty",
        ),
        CheckConstraint(
            f"category IN ({_CATEGORY_SQL_VALUES})",
            name="ck_medical_records_category",
        ),
        CheckConstraint(
            "file_size > 0",
            name="ck_medical_records_file_size_positive",
        ),
        Index(
            "ix_medical_records_patient_created_at",
            "patient_id",
            "created_at",
        ),
        UniqueConstraint("storage_key", name="uq_medical_records_storage_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    report_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    patient: Mapped["PatientProfile"] = relationship(
        back_populates="medical_records"
    )
