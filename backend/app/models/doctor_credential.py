from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.doctor_credentials import (
    DoctorCredentialReviewAction,
    DoctorCredentialStatus,
    DoctorCredentialType,
)
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.doctor_profile import DoctorProfile
    from app.models.user import User


_CREDENTIAL_TYPE_VALUES = ", ".join(
    f"'{credential_type.value}'" for credential_type in DoctorCredentialType
)
_CREDENTIAL_STATUS_VALUES = ", ".join(
    f"'{credential_status.value}'" for credential_status in DoctorCredentialStatus
)
_REVIEW_ACTION_VALUES = ", ".join(
    f"'{action.value}'" for action in DoctorCredentialReviewAction
)
_SINGLE_ACTIVE_CREDENTIAL_PREDICATE = text(
    "document_type != 'ADDITIONAL_QUALIFICATION_CERTIFICATE' "
    "AND verification_status IN ('PENDING', 'APPROVED')"
)


class DoctorCredential(Base):
    __tablename__ = "doctor_credentials"
    __table_args__ = (
        CheckConstraint(
            f"document_type IN ({_CREDENTIAL_TYPE_VALUES})",
            name="ck_doctor_credentials_document_type",
        ),
        CheckConstraint(
            f"verification_status IN ({_CREDENTIAL_STATUS_VALUES})",
            name="ck_doctor_credentials_verification_status",
        ),
        CheckConstraint(
            "length(trim(original_filename)) > 0",
            name="ck_doctor_credentials_original_filename_nonempty",
        ),
        CheckConstraint(
            "file_size > 0",
            name="ck_doctor_credentials_file_size_positive",
        ),
        Index(
            "ix_doctor_credentials_profile_submitted",
            "doctor_profile_id",
            "submitted_at",
        ),
        Index(
            "ix_doctor_credentials_status_submitted",
            "verification_status",
            "submitted_at",
        ),
        Index(
            "uq_doctor_credentials_one_active_per_type",
            "doctor_profile_id",
            "document_type",
            unique=True,
            postgresql_where=_SINGLE_ACTIVE_CREDENTIAL_PREDICATE,
            sqlite_where=_SINGLE_ACTIVE_CREDENTIAL_PREDICATE,
        ),
        UniqueConstraint("storage_key", name="uq_doctor_credentials_storage_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_profile_id: Mapped[int] = mapped_column(
        ForeignKey("doctor_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_type: Mapped[str] = mapped_column(String(48), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    verification_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=DoctorCredentialStatus.PENDING.value,
        server_default=DoctorCredentialStatus.PENDING.value,
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    doctor_profile: Mapped["DoctorProfile"] = relationship(
        back_populates="credentials"
    )
    reviewer: Mapped["User | None"] = relationship(foreign_keys=[reviewed_by])
    review_events: Mapped[list["DoctorCredentialReviewEvent"]] = relationship(
        back_populates="credential",
        passive_deletes="all",
        order_by="DoctorCredentialReviewEvent.created_at",
    )


class DoctorCredentialReviewEvent(Base):
    __tablename__ = "doctor_credential_review_events"
    __table_args__ = (
        CheckConstraint(
            f"action IN ({_REVIEW_ACTION_VALUES})",
            name="ck_doctor_credential_review_events_action",
        ),
        Index(
            "ix_doctor_credential_review_events_credential_created",
            "credential_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    credential_id: Mapped[int] = mapped_column(
        ForeignKey("doctor_credentials.id", ondelete="RESTRICT"),
        nullable=False,
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

    credential: Mapped[DoctorCredential] = relationship(
        back_populates="review_events"
    )
