from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_role
from app.core.appointments import AppointmentAuditAction, AppointmentStatus
from app.core.config import settings
from app.db.session import get_db
from app.models import (
    Appointment,
    AppointmentAuditEvent,
    DoctorProfile,
    User,
    UserRole,
)
from app.schemas.appointments import (
    AppointmentCancellationRequest,
    AppointmentCreate,
    AppointmentRescheduleRequest,
    AvailableSlotsResponse,
    PatientAppointmentResponse,
)
from app.services.appointment_service import (
    appointment_payload,
    doctor_is_eligible,
    get_available_slots,
    get_doctor_profile,
    load_appointment,
    resolve_available_slot,
    slot_is_conflicted,
    to_utc,
    utc_now,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])
_require_patient = require_role(UserRole.PATIENT)
_ACTIVE_STATUSES = (
    AppointmentStatus.BOOKED.value,
    AppointmentStatus.CONFIRMED.value,
)


def _overlap_constraint_failed(error: IntegrityError) -> bool:
    constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    return (
        constraint_name == "ex_appointments_doctor_time_overlap"
        or "ex_appointments_doctor_time_overlap" in str(error.orig)
    )


def _get_eligible_doctor(
    db: Session,
    doctor_profile_id: int,
    *,
    for_update: bool = False,
) -> DoctorProfile:
    profile = get_doctor_profile(
        db,
        doctor_profile_id=doctor_profile_id,
        for_update=for_update,
    )
    if profile is None or not doctor_is_eligible(db, profile):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found.",
        )
    return profile


def _get_patient_appointment(
    db: Session,
    *,
    appointment_id: int,
    patient_id: int,
    for_update: bool = False,
) -> Appointment:
    statement = select(Appointment).where(
        Appointment.id == appointment_id,
        Appointment.patient_id == patient_id,
    )
    if for_update:
        statement = statement.with_for_update()
    appointment = db.scalar(statement)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found.",
        )
    return appointment


def _record_event(
    db: Session,
    *,
    appointment: Appointment,
    actor: User,
    action: AppointmentAuditAction,
    reason: str | None = None,
    previous_start: datetime | None = None,
    previous_end: datetime | None = None,
    new_start: datetime | None = None,
    new_end: datetime | None = None,
) -> None:
    db.add(
        AppointmentAuditEvent(
            appointment=appointment,
            actor_user_id=actor.id,
            action=action.value,
            reason=reason,
            previous_start=previous_start,
            previous_end=previous_end,
            new_start=new_start,
            new_end=new_end,
            created_at=utc_now(),
        )
    )


def _commit_booking(db: Session) -> None:
    try:
        db.flush()
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if _overlap_constraint_failed(error):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The selected appointment slot is no longer available.",
            ) from error
        raise


@router.get("/available-slots", response_model=AvailableSlotsResponse)
def list_available_slots(
    doctor_id: int = Query(gt=0),
    requested_date: date = Query(alias="date"),
    db: Session = Depends(get_db),
) -> dict:
    profile = _get_eligible_doctor(db, doctor_id)
    try:
        slots = get_available_slots(
            db,
            doctor_profile_id=profile.id,
            requested_date=requested_date,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    return {
        "doctor_id": profile.id,
        "date": requested_date,
        "timezone": settings.appointment_timezone,
        "slots": slots,
    }


@router.post(
    "",
    response_model=PatientAppointmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_appointment(
    payload: AppointmentCreate,
    current_patient: User = Depends(_require_patient),
    db: Session = Depends(get_db),
) -> dict:
    profile = _get_eligible_doctor(db, payload.doctor_id, for_update=True)
    slot = resolve_available_slot(
        db,
        doctor_profile_id=profile.id,
        scheduled_start=payload.scheduled_start,
    )
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The selected start time is not a valid appointment slot.",
        )
    if slot_is_conflicted(db, doctor_profile_id=profile.id, slot=slot):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The selected appointment slot is no longer available.",
        )

    appointment = Appointment(
        patient_id=current_patient.id,
        doctor_profile_id=profile.id,
        scheduled_start=slot.scheduled_start,
        scheduled_end=slot.scheduled_end,
        status=AppointmentStatus.BOOKED.value,
        reason_for_visit=payload.reason_for_visit,
        patient_notes=payload.patient_notes,
    )
    db.add(appointment)
    _record_event(
        db,
        appointment=appointment,
        actor=current_patient,
        action=AppointmentAuditAction.BOOKED,
        new_start=slot.scheduled_start,
        new_end=slot.scheduled_end,
    )
    _commit_booking(db)
    return appointment_payload(load_appointment(db, appointment.id), view="patient")


@router.get("/me", response_model=list[PatientAppointmentResponse])
def list_my_appointments(
    view: Literal["upcoming", "history", "all"] = Query(default="upcoming"),
    current_patient: User = Depends(_require_patient),
    db: Session = Depends(get_db),
) -> list[dict]:
    now = utc_now()
    statement = (
        select(Appointment)
        .options(
            selectinload(Appointment.doctor_profile),
            selectinload(Appointment.audit_events),
        )
        .where(Appointment.patient_id == current_patient.id)
    )
    if view == "upcoming":
        statement = statement.where(
            Appointment.status.in_(_ACTIVE_STATUSES),
            Appointment.scheduled_end >= now,
        )
    elif view == "history":
        statement = statement.where(
            (Appointment.status.not_in(_ACTIVE_STATUSES))
            | (Appointment.scheduled_end < now)
        )
    appointments = db.scalars(
        statement.order_by(Appointment.scheduled_start.desc())
    ).all()
    return [appointment_payload(item, view="patient") for item in appointments]


@router.get("/{appointment_id}", response_model=PatientAppointmentResponse)
def get_my_appointment(
    appointment_id: int,
    current_patient: User = Depends(_require_patient),
    db: Session = Depends(get_db),
) -> dict:
    _get_patient_appointment(
        db,
        appointment_id=appointment_id,
        patient_id=current_patient.id,
    )
    appointment = load_appointment(db, appointment_id)
    return appointment_payload(appointment, view="patient")


@router.put(
    "/{appointment_id}/reschedule",
    response_model=PatientAppointmentResponse,
)
def reschedule_appointment(
    appointment_id: int,
    payload: AppointmentRescheduleRequest,
    current_patient: User = Depends(_require_patient),
    db: Session = Depends(get_db),
) -> dict:
    appointment = _get_patient_appointment(
        db,
        appointment_id=appointment_id,
        patient_id=current_patient.id,
        for_update=True,
    )
    if appointment.status not in _ACTIVE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only booked or confirmed appointments can be rescheduled.",
        )
    old_start = to_utc(appointment.scheduled_start)
    old_end = to_utc(appointment.scheduled_end)
    now = utc_now()
    cutoff = timedelta(
        hours=settings.patient_appointment_rescheduling_cutoff_hours
    )
    if now > old_start - cutoff:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointments cannot be rescheduled within the configured cutoff.",
        )
    if to_utc(payload.scheduled_start) == old_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Choose a different appointment time.",
        )
    profile = _get_eligible_doctor(
        db,
        appointment.doctor_profile_id,
        for_update=True,
    )
    slot = resolve_available_slot(
        db,
        doctor_profile_id=profile.id,
        scheduled_start=payload.scheduled_start,
    )
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The selected start time is not a valid appointment slot.",
        )
    if slot_is_conflicted(
        db,
        doctor_profile_id=profile.id,
        slot=slot,
        exclude_appointment_id=appointment.id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The selected appointment slot is no longer available.",
        )
    appointment.scheduled_start = slot.scheduled_start
    appointment.scheduled_end = slot.scheduled_end
    if appointment.status == AppointmentStatus.CONFIRMED.value:
        appointment.status = AppointmentStatus.BOOKED.value
    appointment.updated_at = now
    _record_event(
        db,
        appointment=appointment,
        actor=current_patient,
        action=AppointmentAuditAction.RESCHEDULED,
        reason=payload.reason,
        previous_start=old_start,
        previous_end=old_end,
        new_start=slot.scheduled_start,
        new_end=slot.scheduled_end,
    )
    _commit_booking(db)
    return appointment_payload(load_appointment(db, appointment.id), view="patient")


@router.post(
    "/{appointment_id}/cancel",
    response_model=PatientAppointmentResponse,
)
def cancel_appointment(
    appointment_id: int,
    payload: AppointmentCancellationRequest,
    current_patient: User = Depends(_require_patient),
    db: Session = Depends(get_db),
) -> dict:
    appointment = _get_patient_appointment(
        db,
        appointment_id=appointment_id,
        patient_id=current_patient.id,
        for_update=True,
    )
    if appointment.status not in _ACTIVE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only booked or confirmed appointments can be cancelled.",
        )
    now = utc_now()
    cutoff = timedelta(hours=settings.patient_appointment_cancellation_cutoff_hours)
    if now > to_utc(appointment.scheduled_start) - cutoff:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointments cannot be cancelled within the configured cutoff.",
        )
    appointment.status = AppointmentStatus.CANCELLED.value
    appointment.cancellation_reason = payload.reason
    appointment.updated_at = now
    _record_event(
        db,
        appointment=appointment,
        actor=current_patient,
        action=AppointmentAuditAction.CANCELLED,
        reason=payload.reason,
    )
    db.commit()
    return appointment_payload(load_appointment(db, appointment.id), view="patient")
