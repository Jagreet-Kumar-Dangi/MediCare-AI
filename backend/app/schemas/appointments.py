from datetime import date, datetime, time
from typing import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)
from typing_extensions import Self

from app.core.appointments import AppointmentAuditAction, AppointmentStatus

NonEmptyReason = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=5, max_length=1000),
]


class DoctorAvailabilityPayload(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    break_start: time | None = None
    break_end: time | None = None
    appointment_duration_minutes: int = Field(ge=5, le=240)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_availability_window(self) -> Self:
        if self.start_time >= self.end_time:
            raise ValueError("Availability end time must be after its start time.")
        if (self.break_start is None) != (self.break_end is None):
            raise ValueError("Both break start and end times must be provided.")
        if self.break_start is not None and self.break_end is not None:
            if not (
                self.start_time <= self.break_start
                < self.break_end
                <= self.end_time
            ):
                raise ValueError("Break times must fall within working hours.")
        return self


class DoctorAvailabilityResponse(DoctorAvailabilityPayload):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AvailabilityExceptionPayload(BaseModel):
    exception_date: date
    start_time: time | None = None
    end_time: time | None = None
    reason: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=3, max_length=250),
    ]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_exception_window(self) -> Self:
        if (self.start_time is None) != (self.end_time is None):
            raise ValueError("Both exception start and end times must be provided.")
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time >= self.end_time
        ):
            raise ValueError("Exception end time must be after its start time.")
        return self


class AvailabilityExceptionResponse(AvailabilityExceptionPayload):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AvailableSlot(BaseModel):
    scheduled_start: datetime
    scheduled_end: datetime


class AvailableSlotsResponse(BaseModel):
    doctor_id: int
    date: date
    timezone: str
    slots: list[AvailableSlot]


class AppointmentCreate(BaseModel):
    doctor_id: int = Field(gt=0)
    scheduled_start: AwareDatetime
    reason_for_visit: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
    ]
    patient_notes: Annotated[str, Field(max_length=4000)] | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def normalize_optional_notes(self) -> Self:
        if self.patient_notes is not None:
            self.patient_notes = self.patient_notes.strip() or None
        return self


class AppointmentRescheduleRequest(BaseModel):
    scheduled_start: AwareDatetime
    reason: NonEmptyReason

    model_config = ConfigDict(extra="forbid")


class AppointmentCancellationRequest(BaseModel):
    reason: NonEmptyReason

    model_config = ConfigDict(extra="forbid")


class AppointmentRejectionRequest(BaseModel):
    reason: NonEmptyReason

    model_config = ConfigDict(extra="forbid")


class AppointmentDoctorView(BaseModel):
    id: int
    full_name: str


class AppointmentAuditResponse(BaseModel):
    id: int
    action: AppointmentAuditAction
    reason: str | None
    previous_start: datetime | None
    previous_end: datetime | None
    new_start: datetime | None
    new_end: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientAppointmentResponse(BaseModel):
    id: int
    doctor: AppointmentDoctorView
    scheduled_start: datetime
    scheduled_end: datetime
    status: AppointmentStatus
    reason_for_visit: str
    patient_notes: str | None
    cancellation_reason: str | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime
    audit_events: list[AppointmentAuditResponse]


class DoctorAppointmentResponse(PatientAppointmentResponse):
    patient_name: str
    doctor_notes: str | None


class AdminAppointmentResponse(DoctorAppointmentResponse):
    patient_id: int
    patient_email: str


class AppointmentDoctorNotesRequest(BaseModel):
    doctor_notes: Annotated[str, Field(max_length=4000)] | None = None

    model_config = ConfigDict(extra="forbid")
