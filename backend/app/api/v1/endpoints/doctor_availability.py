from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.appointments import AppointmentStatus
from app.db.session import get_db
from app.models import (
    Appointment,
    DoctorAvailability,
    DoctorAvailabilityException,
    DoctorProfile,
    User,
    UserRole,
)
from app.schemas.appointments import (
    AvailabilityExceptionPayload,
    AvailabilityExceptionResponse,
    DoctorAvailabilityPayload,
    DoctorAvailabilityResponse,
)
from app.services.appointment_service import (
    appointment_zone,
    aware_utc,
    doctor_is_eligible,
    get_doctor_profile_for_user,
    local_now,
    utc_now,
)

router = APIRouter(prefix="/doctor/availability", tags=["appointments"])
_require_doctor = require_role(UserRole.DOCTOR)
_ACTIVE_STATUSES = (
    AppointmentStatus.BOOKED.value,
    AppointmentStatus.CONFIRMED.value,
)


def _profile_for_update(db: Session, user_id: int) -> DoctorProfile:
    profile = get_doctor_profile_for_user(db, user_id=user_id, for_update=True)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found.",
        )
    if not doctor_is_eligible(db, profile):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only eligible doctors can publish availability.",
        )
    return profile


def _ensure_no_window_overlap(
    db: Session,
    *,
    profile_id: int,
    payload: DoctorAvailabilityPayload,
    exclude_id: int | None = None,
) -> None:
    rules = db.scalars(
        select(DoctorAvailability).where(
            DoctorAvailability.doctor_profile_id == profile_id,
            DoctorAvailability.weekday == payload.weekday,
        )
    ).all()
    if any(
        rule.id != exclude_id
        and payload.start_time < rule.end_time
        and payload.end_time > rule.start_time
        for rule in rules
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Availability windows for the same day cannot overlap.",
        )


def _ensure_rule_has_no_upcoming_bookings(
    db: Session,
    *,
    profile_id: int,
    rule: DoctorAvailability,
) -> None:
    now = utc_now()
    appointments = db.scalars(
        select(Appointment).where(
            Appointment.doctor_profile_id == profile_id,
            Appointment.status.in_(_ACTIVE_STATUSES),
            Appointment.scheduled_start > now,
        )
    ).all()
    zone = appointment_zone()
    if any(
        (local_start := aware_utc(appointment.scheduled_start).astimezone(zone)).weekday()
        == rule.weekday
        and rule.start_time <= local_start.time().replace(tzinfo=None) < rule.end_time
        for appointment in appointments
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Availability cannot be changed while it contains upcoming appointments.",
        )


@router.get("", response_model=list[DoctorAvailabilityResponse])
def list_my_availability(
    current_doctor: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> list[DoctorAvailability]:
    profile = get_doctor_profile_for_user(db, user_id=current_doctor.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found.",
        )
    return list(
        db.scalars(
            select(DoctorAvailability)
            .where(DoctorAvailability.doctor_profile_id == profile.id)
            .order_by(
                DoctorAvailability.weekday,
                DoctorAvailability.start_time,
                DoctorAvailability.id,
            )
        )
    )


@router.post(
    "",
    response_model=DoctorAvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_availability(
    payload: DoctorAvailabilityPayload,
    current_doctor: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> DoctorAvailability:
    profile = _profile_for_update(db, current_doctor.id)
    _ensure_no_window_overlap(db, profile_id=profile.id, payload=payload)
    availability = DoctorAvailability(
        doctor_profile_id=profile.id,
        **payload.model_dump(),
    )
    db.add(availability)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if "uq_doctor_availabilities_window" in str(error.orig):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This availability window already exists.",
            ) from error
        raise
    db.refresh(availability)
    return availability


@router.put(
    "/{availability_id}",
    response_model=DoctorAvailabilityResponse,
)
def update_availability(
    availability_id: int,
    payload: DoctorAvailabilityPayload,
    current_doctor: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> DoctorAvailability:
    profile = _profile_for_update(db, current_doctor.id)
    availability = db.scalar(
        select(DoctorAvailability)
        .where(
            DoctorAvailability.id == availability_id,
            DoctorAvailability.doctor_profile_id == profile.id,
        )
        .with_for_update()
    )
    if availability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability window not found.",
        )
    _ensure_rule_has_no_upcoming_bookings(
        db,
        profile_id=profile.id,
        rule=availability,
    )
    _ensure_no_window_overlap(
        db,
        profile_id=profile.id,
        payload=payload,
        exclude_id=availability.id,
    )
    for field, value in payload.model_dump().items():
        setattr(availability, field, value)
    availability.updated_at = utc_now()
    db.commit()
    db.refresh(availability)
    return availability


@router.delete("/{availability_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_availability(
    availability_id: int,
    current_doctor: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> Response:
    profile = _profile_for_update(db, current_doctor.id)
    availability = db.scalar(
        select(DoctorAvailability)
        .where(
            DoctorAvailability.id == availability_id,
            DoctorAvailability.doctor_profile_id == profile.id,
        )
        .with_for_update()
    )
    if availability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability window not found.",
        )
    _ensure_rule_has_no_upcoming_bookings(
        db,
        profile_id=profile.id,
        rule=availability,
    )
    db.delete(availability)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/exceptions",
    response_model=list[AvailabilityExceptionResponse],
)
def list_my_exceptions(
    exception_date: date | None = Query(default=None),
    current_doctor: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> list[DoctorAvailabilityException]:
    profile = get_doctor_profile_for_user(db, user_id=current_doctor.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found.",
        )
    statement = select(DoctorAvailabilityException).where(
        DoctorAvailabilityException.doctor_profile_id == profile.id
    )
    if exception_date is not None:
        statement = statement.where(
            DoctorAvailabilityException.exception_date == exception_date
        )
    return list(
        db.scalars(
            statement.order_by(
                DoctorAvailabilityException.exception_date,
                DoctorAvailabilityException.id,
            )
        )
    )


@router.post(
    "/exceptions",
    response_model=AvailabilityExceptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_availability_exception(
    payload: AvailabilityExceptionPayload,
    current_doctor: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> DoctorAvailabilityException:
    profile = _profile_for_update(db, current_doctor.id)
    if payload.exception_date < local_now().date():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unavailable dates must be today or in the future.",
        )
    exception = DoctorAvailabilityException(
        doctor_profile_id=profile.id,
        **payload.model_dump(),
    )
    db.add(exception)
    db.commit()
    db.refresh(exception)
    return exception


@router.delete(
    "/exceptions/{exception_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_availability_exception(
    exception_id: int,
    current_doctor: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> Response:
    profile = _profile_for_update(db, current_doctor.id)
    exception = db.scalar(
        select(DoctorAvailabilityException)
        .where(
            DoctorAvailabilityException.id == exception_id,
            DoctorAvailabilityException.doctor_profile_id == profile.id,
        )
        .with_for_update()
    )
    if exception is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability exception not found.",
        )
    db.delete(exception)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
