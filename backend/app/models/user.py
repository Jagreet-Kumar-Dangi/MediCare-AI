from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SqlEnum, Index
from sqlalchemy import String, UniqueConstraint, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.appointment import Appointment, AppointmentAuditEvent
    from app.models.doctor_profile import DoctorProfile
    from app.models.patient_profile import PatientProfile


class UserRole(str, Enum):
    PATIENT = "PATIENT"
    DOCTOR = "DOCTOR"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
        Index("ix_users_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(
            UserRole,
            name="user_role",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_type: [role.value for role in enum_type],
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    patient_profile: Mapped["PatientProfile | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    doctor_profile: Mapped["DoctorProfile | None"] = relationship(
        back_populates="user",
        foreign_keys="DoctorProfile.user_id",
        cascade="all, delete-orphan",
        uselist=False,
    )
    patient_appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="patient",
        foreign_keys="Appointment.patient_id",
        passive_deletes="all",
        order_by="Appointment.scheduled_start",
    )
    appointment_audit_events: Mapped[list["AppointmentAuditEvent"]] = relationship(
        back_populates="actor",
        foreign_keys="AppointmentAuditEvent.actor_user_id",
        passive_deletes="all",
        order_by="AppointmentAuditEvent.created_at",
    )
