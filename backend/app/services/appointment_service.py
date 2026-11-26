from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.appointments import AppointmentStatus
from app.core.config import settings
from app.models import (
    Appointment,
    DoctorAvailability,
    DoctorAvailabilityException,
    DoctorProfile,
    User,
)
from app.services.doctor_credential_service import is_directory_eligible

ACTIVE_APPOINTMENT_STATUSES = (
    AppointmentStatus.BOOKED.value,
    AppointmentStatus.CONFIRMED.value,
)
MAX_AVAILABILITY_DAYS = 90


@dataclass(frozen=True)
class Slot:
    scheduled_start: datetime
    scheduled_end: datetime


def appointment_zone() -> ZoneInfo:
    return ZoneInfo(settings.appointment_timezone)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def local_now() -> datetime:
    return utc_now().astimezone(appointment_zone())


def to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _local_instants(value: datetime, zone: ZoneInfo) -> list[datetime]:
    instants: dict[datetime, datetime] = {}
    for fold in (0, 1):
        candidate = value.replace(tzinfo=zone, fold=fold)
        instant = candidate.astimezone(timezone.utc)
        if instant.astimezone(zone).replace(tzinfo=None) == value:
            instants[instant] = candidate
    return [instants[key] for key in sorted(instants)]


def _day_utc_bounds(day: date, zone: ZoneInfo) -> tuple[datetime, datetime]:
    start_candidates = _local_instants(datetime.combine(day, time.min), zone)
    end_candidates = _local_instants(
        datetime.combine(day + timedelta(days=1), time.min),
        zone,
    )
    if not start_candidates or not end_candidates:
        raise ValueError("The selected date has no valid local-time boundary.")
    return to_utc(start_candidates[0]), to_utc(end_candidates[0])


def get_doctor_profile(
    db: Session,
    *,
    doctor_profile_id: int,
    for_update: bool = False,
) -> DoctorProfile | None:
    statement = select(DoctorProfile).where(DoctorProfile.id == doctor_profile_id)
    if for_update:
        statement = statement.with_for_update()
    return db.scalar(statement)


def get_doctor_profile_for_user(
    db: Session,
    *,
    user_id: int,
    for_update: bool = False,
) -> DoctorProfile | None:
    statement = select(DoctorProfile).where(DoctorProfile.user_id == user_id)
    if for_update:
        statement = statement.with_for_update()
    return db.scalar(statement)


def doctor_is_eligible(db: Session, profile: DoctorProfile) -> bool:
    user = db.get(User, profile.user_id)
    return user is not None and is_directory_eligible(
        db,
        user=user,
        doctor_profile=profile,
    )


def _candidate_slots_for_date(
    db: Session,
    *,
    doctor_profile_id: int,
    requested_date: date,
    include_booked: bool = False,
) -> list[Slot]:
    zone = appointment_zone()
    weekday = requested_date.weekday()
    rules = db.scalars(
        select(DoctorAvailability)
        .where(
            DoctorAvailability.doctor_profile_id == doctor_profile_id,
            DoctorAvailability.weekday == weekday,
        )
        .order_by(DoctorAvailability.start_time, DoctorAvailability.id)
    ).all()
    exceptions = db.scalars(
        select(DoctorAvailabilityException).where(
            DoctorAvailabilityException.doctor_profile_id == doctor_profile_id,
            DoctorAvailabilityException.exception_date == requested_date,
        )
    ).all()
    day_start, day_end = _day_utc_bounds(requested_date, zone)
    appointments = db.scalars(
        select(Appointment).where(
            Appointment.doctor_profile_id == doctor_profile_id,
            Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
            Appointment.scheduled_start < day_end,
            Appointment.scheduled_end > day_start,
        )
    ).all()
    now_utc = utc_now()
    slots: dict[datetime, Slot] = {}

    for rule in rules:
        start_naive = datetime.combine(requested_date, rule.start_time)
        end_naive = datetime.combine(requested_date, rule.end_time)
        break_start = (
            datetime.combine(requested_date, rule.break_start)
            if rule.break_start is not None
            else None
        )
        break_end = (
            datetime.combine(requested_date, rule.break_end)
            if rule.break_end is not None
            else None
        )
        duration = timedelta(minutes=rule.appointment_duration_minutes)
        candidate = start_naive

        while candidate + duration <= end_naive:
            candidate_end = candidate + duration
            intersects_break = (
                break_start is not None
                and break_end is not None
                and candidate < break_end
                and candidate_end > break_start
            )
            blocked_by_exception = any(
                exception.start_time is None
                or exception.end_time is None
                or (
                    candidate
                    < datetime.combine(requested_date, exception.end_time)
                    and candidate_end
                    > datetime.combine(requested_date, exception.start_time)
                )
                for exception in exceptions
            )

            if not intersects_break and not blocked_by_exception:
                for local_start in _local_instants(candidate, zone):
                    start_utc = to_utc(local_start)
                    end_utc = start_utc + duration
                    local_end = end_utc.astimezone(zone).replace(tzinfo=None)
                    if local_end > end_naive or start_utc <= now_utc:
                        continue
                    if not include_booked and any(
                        start_utc < aware_utc(appointment.scheduled_end)
                        and end_utc > aware_utc(appointment.scheduled_start)
                        for appointment in appointments
                    ):
                        continue
                    slots[start_utc] = Slot(
                        scheduled_start=start_utc,
                        scheduled_end=end_utc,
                    )
            candidate += duration

    return [slots[start] for start in sorted(slots)]


def get_available_slots(
    db: Session,
    *,
    doctor_profile_id: int,
    requested_date: date,
) -> list[Slot]:
    today = local_now().date()
    if requested_date < today:
        raise ValueError("Appointments cannot be offered for past dates.")
    if requested_date > today + timedelta(days=MAX_AVAILABILITY_DAYS):
        raise ValueError(
            f"Availability can only be viewed up to {MAX_AVAILABILITY_DAYS} days ahead."
        )
    return _candidate_slots_for_date(
        db,
        doctor_profile_id=doctor_profile_id,
        requested_date=requested_date,
    )


def resolve_available_slot(
    db: Session,
    *,
    doctor_profile_id: int,
    scheduled_start: datetime,
) -> Slot | None:
    start_utc = to_utc(scheduled_start)
    requested_date = start_utc.astimezone(appointment_zone()).date()
    today = local_now().date()
    if (
        requested_date < today
        or requested_date > today + timedelta(days=MAX_AVAILABILITY_DAYS)
    ):
        return None
    try:
        slots = _candidate_slots_for_date(
            db,
            doctor_profile_id=doctor_profile_id,
            requested_date=requested_date,
            include_booked=True,
        )
    except ValueError:
        return None
    return next(
        (slot for slot in slots if slot.scheduled_start == start_utc),
        None,
    )


def slot_is_conflicted(
    db: Session,
    *,
    doctor_profile_id: int,
    slot: Slot,
    exclude_appointment_id: int | None = None,
) -> bool:
    statement = select(Appointment.id).where(
        Appointment.doctor_profile_id == doctor_profile_id,
        Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
        Appointment.scheduled_start < slot.scheduled_end,
        Appointment.scheduled_end > slot.scheduled_start,
    )
    if exclude_appointment_id is not None:
        statement = statement.where(Appointment.id != exclude_appointment_id)
    return db.scalar(statement.limit(1)) is not None


def aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def load_appointment(db: Session, appointment_id: int) -> Appointment | None:
    return db.scalar(
        select(Appointment)
        .options(
            selectinload(Appointment.doctor_profile).selectinload(
                DoctorProfile.user
            ),
            selectinload(Appointment.patient).selectinload(User.patient_profile),
            selectinload(Appointment.audit_events),
        )
        .where(Appointment.id == appointment_id)
    )


def appointment_payload(appointment: Appointment, *, view: str) -> dict:
    events = sorted(
        appointment.audit_events,
        key=lambda event: (to_utc(event.created_at), event.id),
    )
    payload = {
        "id": appointment.id,
        "doctor": {
            "id": appointment.doctor_profile.id,
            "full_name": appointment.doctor_profile.full_name,
        },
        "scheduled_start": aware_utc(appointment.scheduled_start),
        "scheduled_end": aware_utc(appointment.scheduled_end),
        "status": appointment.status,
        "reason_for_visit": appointment.reason_for_visit,
        "patient_notes": appointment.patient_notes,
        "cancellation_reason": appointment.cancellation_reason,
        "rejection_reason": appointment.rejection_reason,
        "created_at": aware_utc(appointment.created_at),
        "updated_at": aware_utc(appointment.updated_at),
        "audit_events": [
            {
                "id": event.id,
                "action": event.action,
                "reason": event.reason,
                "previous_start": (
                    aware_utc(event.previous_start)
                    if event.previous_start is not None
                    else None
                ),
                "previous_end": (
                    aware_utc(event.previous_end)
                    if event.previous_end is not None
                    else None
                ),
                "new_start": (
                    aware_utc(event.new_start) if event.new_start is not None else None
                ),
                "new_end": (
                    aware_utc(event.new_end) if event.new_end is not None else None
                ),
                "created_at": aware_utc(event.created_at),
            }
            for event in events
        ],
    }
    if view in {"doctor", "admin"}:
        patient_profile = appointment.patient.patient_profile
        payload["patient_name"] = (
            f"{patient_profile.first_name} {patient_profile.last_name}"
            if patient_profile is not None
            else None
        )
        payload["doctor_notes"] = appointment.doctor_notes
    if view == "admin":
        payload["patient_id"] = appointment.patient_id
        payload["patient_email"] = appointment.patient.email
    return payload
