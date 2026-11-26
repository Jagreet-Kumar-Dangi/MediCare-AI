from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class DoctorVerificationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class DoctorVerificationAction(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


_VERIFICATION_STATUS_VALUES = ", ".join(
    f"'{status.value}'" for status in DoctorVerificationStatus
)
_VERIFICATION_ACTION_VALUES = ", ".join(
    f"'{action.value}'" for action in DoctorVerificationAction
)


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"
    __table_args__ = (
        CheckConstraint(
            "length(trim(full_name)) > 0",
            name="ck_doctor_profiles_full_name_nonempty",
        ),
        CheckConstraint(
            "length(trim(specialization)) > 0",
            name="ck_doctor_profiles_specialization_nonempty",
        ),
        CheckConstraint(
            "length(trim(qualification)) > 0",
            name="ck_doctor_profiles_qualification_nonempty",
        ),
        CheckConstraint(
            "medical_registration_number = "
            "upper(trim(medical_registration_number)) "
            "AND length(trim(medical_registration_number)) > 0",
            name="ck_doctor_profiles_registration_number_normalized",
        ),
        CheckConstraint(
            "years_of_experience BETWEEN 0 AND 80",
            name="ck_doctor_profiles_experience_range",
        ),
        CheckConstraint(
            "consultation_fee IS NULL OR consultation_fee >= 0",
            name="ck_doctor_profiles_consultation_fee_nonnegative",
        ),
        CheckConstraint(
            f"verification_status IN ({_VERIFICATION_STATUS_VALUES})",
            name="ck_doctor_profiles_verification_status",
        ),
        Index(
            "ix_doctor_profiles_status_created_at",
            "verification_status",
            "created_at",
        ),
        UniqueConstraint("user_id", name="uq_doctor_profiles_user_id"),
        UniqueConstraint(
            "medical_registration_number",
            name="uq_doctor_profiles_registration_number",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    specialization: Mapped[str] = mapped_column(String(120), nullable=False)
    qualification: Mapped[str] = mapped_column(String(160), nullable=False)
    medical_registration_number: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    years_of_experience: Mapped[int] = mapped_column(nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    clinic_or_hospital: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    consultation_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    biography: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=DoctorVerificationStatus.PENDING.value,
        server_default=DoctorVerificationStatus.PENDING.value,
    )
    verification_submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    user: Mapped["User"] = relationship(
        back_populates="doctor_profile",
        foreign_keys=[user_id],
    )
    verifier: Mapped["User | None"] = relationship(foreign_keys=[verified_by])
    verification_events: Mapped[list["DoctorVerificationEvent"]] = relationship(
        back_populates="doctor_profile",
        passive_deletes="all",
        order_by="DoctorVerificationEvent.created_at",
    )

    @property
    def email(self) -> str:
        return self.user.email


class DoctorVerificationEvent(Base):
    __tablename__ = "doctor_verification_events"
    __table_args__ = (
        CheckConstraint(
            f"action IN ({_VERIFICATION_ACTION_VALUES})",
            name="ck_doctor_verification_events_action",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_profile_id: Mapped[int] = mapped_column(
        ForeignKey("doctor_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    admin_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    doctor_profile: Mapped[DoctorProfile] = relationship(
        back_populates="verification_events"
    )

