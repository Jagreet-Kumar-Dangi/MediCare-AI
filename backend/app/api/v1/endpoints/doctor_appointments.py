from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_role
from app.core.appointments import AppointmentAuditAction, AppointmentStatus
from app.core.notifications import NotificationType
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
    AppointmentDoctorNotesRequest,
    AppointmentRejectionRequest,
    DoctorAppointmentResponse,
)
from app.services.appointment_service import (
    appointment_payload,
    get_doctor_profile_for_user,
    load_appointment,
    to_utc,
    utc_now,
)
from app.services.notification_service import (
    cancel_reminder_jobs,
    create_appointment_event_notifications,
)

router = APIRouter(prefix="/doctor/appointments", tags=["appointments"])
_require_doctor = require_role(UserRole.DOCTOR)
_ACTIVE_STATUSES = (
    AppointmentStatus.BOOKED.value,
    AppointmentStatus.CONFIRMED.value,
)


def _owned_appointment(
    db: Session,
    *,
    appointment_id: int,
    profile_id: int,
    for_update: bool = False,
) -> Appointment:
    statement = select(Appointment).where(
        Appointment.id == appointment_id,
        Appointment.doctor_profile_id == profile_id,
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
) -> AppointmentAuditEvent:
    event = AppointmentAuditEvent(
        appointment_id=appointment.id,
        actor_user_id=actor.id,
        action=action.value,
        reason=reason,
        created_at=utc_now(),
    )
    db.add(event)
    return event


def _doctor_profile(db: Session, user_id: int) -> DoctorProfile:
    profile = get_doctor_profile_for_user(db, user_id=user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found.",
        )
    return profile


@router.get("", response_model=list[DoctorAppointmentResponse])
def list_doctor_appointments(
    view: Literal["upcoming", "history", "all"] = Query(default="upcoming"),
    current_doctor: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> list[dict]:
    profile = _doctor_profile(db, current_doctor.id)
    now = utc_now()
    statement = (
        select(Appointment)
        .options(
            selectinload(Appointment.doctor_profile),
            selectinload(Appointment.patient).selectinload(User.patient_profile),
            selectinload(Appointment.audit_events),
        )
        .where(Appointment.doctor_profile_id == profile.id)
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
    return [appointment_payload(item, view="doctor") for item in appointments]


@router.get(
    "/{appointment_id}",
    response_model=DoctorAppointmentResponse,
)
def get_doctor_appointment(
    appointment_id: int,
    current_doctor: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> dict:
    profile = _doctor_profile(db, current_doctor.id)
    _owned_appointment(
        db,
        appointment_id=appointment_id,
        profile_id=profile.id,
    )
    appointment = load_appointment(db, appointment_id)
    return appointment_payload(appointment, view="doctor")


def _transition(
    db: Session,
    *,
    appointment: Appointment,
    current_doctor: User,
    allowed_status: AppointmentStatus,
    new_status: AppointmentStatus,
    action: AppointmentAuditAction,
    reason: str | None = None,
) -> dict:
    if appointment.status != allowed_status.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This appointment is not in a state that allows this action.",
        )
    appointment.status = new_status.value
    appointment.updated_at = utc_now()
    if action == AppointmentAuditAction.CANCELLED:
        appointment.cancellation_reason = reason
    elif action == AppointmentAuditAction.REJECTED:
        appointment.rejection_reason = reason
    event = _record_event(
        db,
        appointment=appointment,
        actor=current_doctor,
        action=action,
        reason=reason,
    )
    db.flush()
    notification_types = {
        AppointmentAuditAction.CONFIRMED: NotificationType.APPOINTMENT_CONFIRMED,
        AppointmentAuditAction.CANCELLED: NotificationType.APPOINTMENT_CANCELLED,
        AppointmentAuditAction.COMPLETED: NotificationType.APPOINTMENT_COMPLETED,
    }
    notification_type = notification_types.get(action)
    if notification_type is not None:
        create_appointment_event_notifications(
            db,
            appointment=appointment,
            notification_type=notification_type,
            event_id=event.id,
        )
    elif action in {
        AppointmentAuditAction.REJECTED,
        AppointmentAuditAction.NO_SHOW,
    }:
        cancel_reminder_jobs(
            db,
            appointment_id=appointment.id,
            reason="appointment_inactive",
        )
    db.commit()
    return appointment_payload(load_appointment(db, appointment.id), view="doctor")


@router.post(
    "/{appointment_id}/confirm",
    response_model=DoctorAppointmentResponse,
)
def confirm_appointment(
    appointment_id: int,
    current_doctor: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> dict:
    profile = _doctor_profile(db, current_doctor.id)
    appointment = _owned_appointment(
        db,
        appointment_id=appointment_id,
        profile_id=profile.id,
        for_update=True,
    )
    if to_utc(appointment.scheduled_end) <= utc_now():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Past appointments cannot be confirmed.",
        )
    return _transition(
        db,
        appointment=appointment,
        current_doctor=current_doctor,
        allowed_status=AppointmentStatus.BOOKED,
        new_status=AppointmentStatus.CONFIRMED,
        action=AppointmentAuditAction.CONFIRMED,
    )


@router.post(
    "/{appointment_id}/reject",
    response_model=DoctorAppointmentResponse,
)
def reject_appointment(
    appointment_id: int,
    payload: AppointmentRejectionRequest,
    current_doctor: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> dict:
    profile = _doctor_profile(db, current_doctor.id)
    appointment = _owned_appointment(
        db,
        appointment_id=appointment_id,
        profile_id=profile.id,
        for_update=True,
    )
    return _transition(
        db,
        appointment=appointment,
        current_doctor=current_doctor,
        allowed_status=AppointmentStatus.BOOKED,
        new_status=AppointmentStatus.REJECTED,
        action=AppointmentAuditAction.REJECTED,
        reason=payload.reason,
    )


@router.post(
    "/{appointment_id}/cancel",
    response_model=DoctorAppointmentResponse,
)
def cancel_doctor_appointment(
    appointment_id: int,
    payload: AppointmentCancellationRequest,
    current_doctor: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> dict:
    profile = _doctor_profile(db, current_doctor.id)
    appointment = _owned_appointment(
        db,
        appointment_id=appointment_id,
        profile_id=profile.id,
        for_update=True,
    )
    if appointment.status not in _ACTIVE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only booked or confirmed appointments can be cancelled.",
        )
    return _transition(
        db,
        appointment=appointment,
        current_doctor=current_doctor,
        allowed_status=AppointmentStatus(appointment.status),
        new_status=AppointmentStatus.CANCELLED,
        action=AppointmentAuditAction.CANCELLED,
        reason=payload.reason,
    )


@router.post(
    "/{appointment_id}/complete",
    response_model=DoctorAppointmentResponse,
)
def complete_appointment(
    appointment_id: int,
    current_doctor: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> dict:
    profile = _doctor_profile(db, current_doctor.id)
    appointment = _owned_appointment(
        db,
        appointment_id=appointment_id,
        profile_id=profile.id,
        for_update=True,
    )
    if to_utc(appointment.scheduled_end) > utc_now():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An appointment can only be completed after its scheduled end.",
        )
    return _transition(
        db,
        appointment=appointment,
        current_doctor=current_doctor,
        allowed_status=AppointmentStatus.CONFIRMED,
        new_status=AppointmentStatus.COMPLETED,
        action=AppointmentAuditAction.COMPLETED,
    )


@router.post(
    "/{appointment_id}/no-show",
    response_model=DoctorAppointmentResponse,
)
def mark_appointment_no_show(
    appointment_id: int,
    current_doctor: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> dict:
    profile = _doctor_profile(db, current_doctor.id)
    appointment = _owned_appointment(
        db,
        appointment_id=appointment_id,
        profile_id=profile.id,
        for_update=True,
    )
    if to_utc(appointment.scheduled_end) > utc_now():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An appointment can only be marked no-show after its scheduled end.",
        )
    if appointment.status not in _ACTIVE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This appointment is not in a state that allows this action.",
        )
    return _transition(
        db,
        appointment=appointment,
        current_doctor=current_doctor,
        allowed_status=AppointmentStatus(appointment.status),
        new_status=AppointmentStatus.NO_SHOW,
        action=AppointmentAuditAction.NO_SHOW,
    )


@router.put(
    "/{appointment_id}/notes",
    response_model=DoctorAppointmentResponse,
)
def update_doctor_notes(
    appointment_id: int,
    payload: AppointmentDoctorNotesRequest,
    current_doctor: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> dict:
    profile = _doctor_profile(db, current_doctor.id)
    appointment = _owned_appointment(
        db,
        appointment_id=appointment_id,
        profile_id=profile.id,
        for_update=True,
    )
    appointment.doctor_notes = (
        payload.doctor_notes.strip()
        if payload.doctor_notes is not None and payload.doctor_notes.strip()
        else None
    )
    appointment.updated_at = utc_now()
    db.commit()
    return appointment_payload(load_appointment(db, appointment.id), view="doctor")
