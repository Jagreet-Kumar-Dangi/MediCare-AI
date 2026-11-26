from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import AwareDatetime
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_role
from app.core.appointments import AppointmentStatus
from app.db.session import get_db
from app.models import Appointment, User, UserRole
from app.schemas.appointments import AdminAppointmentResponse
from app.services.appointment_service import appointment_payload, load_appointment

router = APIRouter(prefix="/admin/appointments", tags=["admin"])
_require_admin = require_role(UserRole.ADMIN)


@router.get("", response_model=list[AdminAppointmentResponse])
def list_appointments(
    appointment_status: AppointmentStatus | None = Query(
        default=None,
        alias="status",
    ),
    patient_id: int | None = Query(default=None, gt=0),
    doctor_id: int | None = Query(default=None, gt=0),
    scheduled_from: AwareDatetime | None = None,
    scheduled_before: AwareDatetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    del current_admin
    if (
        scheduled_from is not None
        and scheduled_before is not None
        and scheduled_from >= scheduled_before
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="scheduled_from must be earlier than scheduled_before.",
        )
    statement = (
        select(Appointment)
        .options(
            selectinload(Appointment.doctor_profile),
            selectinload(Appointment.patient).selectinload(User.patient_profile),
            selectinload(Appointment.audit_events),
        )
    )
    if appointment_status is not None:
        statement = statement.where(
            Appointment.status == appointment_status.value
        )
    if patient_id is not None:
        statement = statement.where(Appointment.patient_id == patient_id)
    if doctor_id is not None:
        statement = statement.where(Appointment.doctor_profile_id == doctor_id)
    if scheduled_from is not None:
        statement = statement.where(
            Appointment.scheduled_start >= scheduled_from
        )
    if scheduled_before is not None:
        statement = statement.where(
            Appointment.scheduled_start < scheduled_before
        )
    appointments = db.scalars(
        statement.order_by(Appointment.scheduled_start.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [appointment_payload(item, view="admin") for item in appointments]


@router.get(
    "/{appointment_id}",
    response_model=AdminAppointmentResponse,
)
def get_appointment(
    appointment_id: int,
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> dict:
    del current_admin
    appointment = load_appointment(db, appointment_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found.",
        )
    return appointment_payload(appointment, view="admin")
