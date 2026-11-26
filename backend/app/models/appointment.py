from datetime import date, datetime, time, timezone
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
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.appointments import AppointmentAuditAction, AppointmentStatus
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.doctor_profile import DoctorProfile
    from app.models.user import User


_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in AppointmentStatus)
_AUDIT_ACTION_VALUES = ", ".join(
    f"'{action.value}'" for action in AppointmentAuditAction
)


class DoctorAvailability(Base):
    __tablename__ = "doctor_availabilities"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_doctor_availabilities_weekday"),
        CheckConstraint(
            "start_time < end_time",
            name="ck_doctor_availabilities_time_range",
        ),
        CheckConstraint(
            "(break_start IS NULL AND break_end IS NULL) OR "
            "(break_start IS NOT NULL AND break_end IS NOT NULL AND "
            "start_time <= break_start AND break_start < break_end AND "
            "break_end <= end_time)",
            name="ck_doctor_availabilities_break_range",
        ),
        CheckConstraint(
            "appointment_duration_minutes BETWEEN 5 AND 240",
            name="ck_doctor_availabilities_duration",
        ),
        Index(
            "ix_doctor_availabilities_profile_weekday",
            "doctor_profile_id",
            "weekday",
        ),
        UniqueConstraint(
            "doctor_profile_id",
            "weekday",
            "start_time",
            "end_time",
            name="uq_doctor_availabilities_window",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_profile_id: Mapped[int] = mapped_column(
        ForeignKey("doctor_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time(), nullable=False)
    end_time: Mapped[time] = mapped_column(Time(), nullable=False)
    break_start: Mapped[time | None] = mapped_column(Time(), nullable=True)
    break_end: Mapped[time | None] = mapped_column(Time(), nullable=True)
    appointment_duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
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

    doctor_profile: Mapped["DoctorProfile"] = relationship(
        back_populates="availability_rules"
    )


class DoctorAvailabilityException(Base):
    __tablename__ = "doctor_availability_exceptions"
    __table_args__ = (
        CheckConstraint(
            "(start_time IS NULL AND end_time IS NULL) OR "
            "(start_time IS NOT NULL AND end_time IS NOT NULL AND "
            "start_time < end_time)",
            name="ck_doctor_availability_exceptions_time_range",
        ),
        Index(
            "ix_doctor_availability_exceptions_profile_date",
            "doctor_profile_id",
            "exception_date",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_profile_id: Mapped[int] = mapped_column(
        ForeignKey("doctor_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    exception_date: Mapped[date] = mapped_column(Date(), nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time(), nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time(), nullable=True)
    reason: Mapped[str] = mapped_column(String(250), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    doctor_profile: Mapped["DoctorProfile"] = relationship(
        back_populates="availability_exceptions"
    )


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint(
            "scheduled_start < scheduled_end",
            name="ck_appointments_time_range",
        ),
        CheckConstraint(
            f"status IN ({_STATUS_VALUES})",
            name="ck_appointments_status",
        ),
        Index(
            "ix_appointments_patient_status_start",
            "patient_id",
            "status",
            "scheduled_start",
        ),
        Index(
            "ix_appointments_doctor_status_start",
            "doctor_profile_id",
            "status",
            "scheduled_start",
        ),
        ExcludeConstraint(
            ("doctor_profile_id", "="),
            (
                text("tstzrange(scheduled_start, scheduled_end, '[)')"),
                "&&",
            ),
            where=text("status IN ('BOOKED', 'CONFIRMED')"),
            using="gist",
            name="ex_appointments_doctor_time_overlap",
        ).ddl_if(dialect="postgresql"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    doctor_profile_id: Mapped[int] = mapped_column(
        ForeignKey("doctor_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    scheduled_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    scheduled_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=AppointmentStatus.BOOKED.value,
        server_default=AppointmentStatus.BOOKED.value,
    )
    reason_for_visit: Mapped[str] = mapped_column(String(1000), nullable=False)
    patient_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    doctor_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
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

    patient: Mapped["User"] = relationship(
        back_populates="patient_appointments",
        foreign_keys=[patient_id],
    )
    doctor_profile: Mapped["DoctorProfile"] = relationship(
        back_populates="appointments"
    )
    audit_events: Mapped[list["AppointmentAuditEvent"]] = relationship(
        back_populates="appointment",
        passive_deletes="all",
        order_by="AppointmentAuditEvent.created_at",
    )


class AppointmentAuditEvent(Base):
    __tablename__ = "appointment_audit_events"
    __table_args__ = (
        CheckConstraint(
            f"action IN ({_AUDIT_ACTION_VALUES})",
            name="ck_appointment_audit_events_action",
        ),
        Index(
            "ix_appointment_audit_events_appointment_created",
            "appointment_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    previous_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    previous_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    new_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    new_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    appointment: Mapped[Appointment] = relationship(back_populates="audit_events")
    actor: Mapped["User"] = relationship(
        back_populates="appointment_audit_events",
        foreign_keys=[actor_user_id],
    )
