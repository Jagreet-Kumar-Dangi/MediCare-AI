from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.appointments import AppointmentStatus
from app.core.config import settings
from app.core.notifications import (
    NotificationJobChannel,
    NotificationJobStatus,
    NotificationType,
)
from app.models import (
    Appointment,
    DoctorProfile,
    Notification,
    NotificationJob,
    NotificationPreference,
    User,
)
from app.services.appointment_service import to_utc

_ACTIVE_STATUSES = {
    AppointmentStatus.BOOKED.value,
    AppointmentStatus.CONFIRMED.value,
}

_EVENT_TEXT = {
    NotificationType.APPOINTMENT_BOOKED: (
        "Appointment requested",
        "A new appointment request has been booked.",
        "Your appointment request has been received.",
    ),
    NotificationType.APPOINTMENT_CONFIRMED: (
        "Appointment confirmed",
        "An appointment has been confirmed.",
        "Your appointment has been confirmed.",
    ),
    NotificationType.APPOINTMENT_CANCELLED: (
        "Appointment cancelled",
        "An appointment has been cancelled.",
        "Your appointment has been cancelled.",
    ),
    NotificationType.APPOINTMENT_RESCHEDULED: (
        "Appointment rescheduled",
        "An appointment has been rescheduled.",
        "Your appointment has been rescheduled.",
    ),
    NotificationType.APPOINTMENT_COMPLETED: (
        "Appointment completed",
        "An appointment has been marked completed.",
        "Your appointment has been marked completed.",
    ),
    NotificationType.APPOINTMENT_REMINDER_24H: (
        "Appointment reminder",
        "An appointment is scheduled in about 24 hours.",
        "You have an appointment scheduled in about 24 hours.",
    ),
    NotificationType.APPOINTMENT_REMINDER_1H: (
        "Appointment reminder",
        "An appointment is scheduled in about 1 hour.",
        "You have an appointment scheduled in about 1 hour.",
    ),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _preference(db: Session, user_id: int) -> NotificationPreference | None:
    return db.get(NotificationPreference, user_id)


def clinic_time_label(value: datetime) -> str:
    local_time = to_utc(value).astimezone(ZoneInfo(settings.appointment_timezone))
    return f"{local_time.strftime('%a, %d %b %Y at %I:%M %p')} {local_time.tzname() or settings.appointment_timezone}"


def cancel_reminder_jobs(
    db: Session,
    *,
    appointment_id: int,
    reason: str = "appointment_inactive",
) -> None:
    now = _now()
    db.execute(
        update(NotificationJob)
        .where(
            NotificationJob.appointment_id == appointment_id,
            NotificationJob.channel == NotificationJobChannel.REMINDER.value,
            NotificationJob.status.in_(
                [
                    NotificationJobStatus.PENDING.value,
                    NotificationJobStatus.PROCESSING.value,
                ]
            ),
        )
        .values(
            status=NotificationJobStatus.CANCELLED.value,
            last_error=reason,
            completed_at=now,
            locked_until=None,
            lease_token=None,
            updated_at=now,
        )
    )


def _schedule_reminders(
    db: Session,
    *,
    appointment: Appointment,
    recipient_id: int,
    preference: NotificationPreference | None,
) -> None:
    if appointment.status not in _ACTIVE_STATUSES:
        return
    enablement = (
        (
            NotificationType.APPOINTMENT_REMINDER_24H,
            settings.appointment_reminder_24h_minutes,
            preference.reminder_24h_enabled if preference is not None else True,
        ),
        (
            NotificationType.APPOINTMENT_REMINDER_1H,
            settings.appointment_reminder_1h_minutes,
            preference.reminder_1h_enabled if preference is not None else True,
        ),
    )
    now = _now()
    appointment_start = to_utc(appointment.scheduled_start)
    for reminder_type, minutes_before, enabled in enablement:
        if not enabled or not (
            (preference.in_app_enabled if preference is not None else True)
            or (preference.email_enabled if preference is not None else True)
        ):
            continue
        scheduled_at = appointment_start - timedelta(minutes=minutes_before)
        if scheduled_at <= now:
            continue

        idempotency_key = (
            f"reminder:{appointment.id}:{reminder_type.value}:"
            f"{recipient_id}:{appointment_start.isoformat()}"
        )
        existing = db.scalar(
            select(NotificationJob).where(
                NotificationJob.idempotency_key == idempotency_key
            )
        )
        if existing is not None:
            if existing.status == NotificationJobStatus.CANCELLED.value:
                existing.status = NotificationJobStatus.PENDING.value
                existing.scheduled_at = scheduled_at
                existing.appointment_start_at = appointment_start
                existing.last_error = None
                existing.completed_at = None
                existing.next_attempt_at = None
                existing.locked_until = None
                existing.lease_token = None
                existing.updated_at = now
            continue

        db.add(
            NotificationJob(
                recipient_user_id=recipient_id,
                appointment_id=appointment.id,
                notification_type=reminder_type.value,
                channel=NotificationJobChannel.REMINDER.value,
                status=NotificationJobStatus.PENDING.value,
                scheduled_at=scheduled_at,
                appointment_start_at=appointment_start,
                attempt_count=0,
                idempotency_key=idempotency_key,
                created_at=now,
                updated_at=now,
            )
        )


def create_reminder_notification(
    db: Session,
    *,
    job: NotificationJob,
    recipient: User,
) -> None:
    if db.scalar(
        select(Notification.id).where(
            Notification.idempotency_key == job.idempotency_key
        )
    ) is not None:
        return
    title, doctor_message, patient_message = _EVENT_TEXT[
        NotificationType(job.notification_type)
    ]
    db.add(
        Notification(
            recipient_user_id=recipient.id,
            notification_type=job.notification_type,
            title=title,
            message=(
                patient_message
                if recipient.role.value == "PATIENT"
                else doctor_message
            ),
            related_appointment_id=job.appointment_id,
            idempotency_key=job.idempotency_key,
            created_at=_now(),
        )
    )


def create_appointment_event_notifications(
    db: Session,
    *,
    appointment: Appointment,
    notification_type: NotificationType,
    event_id: int,
) -> None:
    doctor_user_id = db.scalar(
        select(DoctorProfile.user_id).where(
            DoctorProfile.id == appointment.doctor_profile_id
        )
    )
    if doctor_user_id is None:
        raise LookupError("Appointment doctor account was not found.")
    if notification_type in {
        NotificationType.APPOINTMENT_RESCHEDULED,
        NotificationType.APPOINTMENT_CANCELLED,
        NotificationType.APPOINTMENT_COMPLETED,
    }:
        cancel_reminder_jobs(
            db,
            appointment_id=appointment.id,
            reason="appointment_changed",
        )

    recipients = (appointment.patient_id, doctor_user_id)
    title, doctor_message, patient_message = _EVENT_TEXT[notification_type]
    now = _now()
    appointment_start = to_utc(appointment.scheduled_start)

    for recipient_id in recipients:
        preference = _preference(db, recipient_id)
        is_patient = recipient_id == appointment.patient_id
        if preference is None or preference.in_app_enabled:
            db.add(
                Notification(
                    recipient_user_id=recipient_id,
                    notification_type=notification_type.value,
                    title=title,
                    message=patient_message if is_patient else doctor_message,
                    related_appointment_id=appointment.id,
                    idempotency_key=f"appointment-event:{event_id}:{recipient_id}",
                    created_at=now,
                )
            )

        email_enabled = preference is None or preference.email_enabled
        smtp_configured = bool(settings.smtp_host and settings.smtp_from_email)
        job_status = (
            NotificationJobStatus.PENDING.value
            if email_enabled and smtp_configured
            else NotificationJobStatus.SKIPPED.value
        )
        skip_reason = (
            None
            if job_status == NotificationJobStatus.PENDING.value
            else "email_disabled"
            if not email_enabled
            else "smtp_not_configured"
        )
        db.add(
            NotificationJob(
                recipient_user_id=recipient_id,
                appointment_id=appointment.id,
                notification_type=notification_type.value,
                channel=NotificationJobChannel.EMAIL.value,
                status=job_status,
                scheduled_at=now,
                appointment_start_at=appointment_start,
                attempt_count=0,
                last_error=skip_reason,
                idempotency_key=f"appointment-email:{event_id}:{recipient_id}",
                created_at=now,
                updated_at=now,
                completed_at=now if skip_reason else None,
            )
        )
        if notification_type in {
            NotificationType.APPOINTMENT_BOOKED,
            NotificationType.APPOINTMENT_RESCHEDULED,
        }:
            _schedule_reminders(
                db,
                appointment=appointment,
                recipient_id=recipient_id,
                preference=preference,
            )


def refresh_reminder_jobs_for_user(
    db: Session,
    *,
    user: User,
    preference: NotificationPreference,
) -> None:
    now = _now()
    if not preference.reminder_24h_enabled:
        db.execute(
            update(NotificationJob)
            .where(
                NotificationJob.recipient_user_id == user.id,
                NotificationJob.notification_type
                == NotificationType.APPOINTMENT_REMINDER_24H.value,
                NotificationJob.status == NotificationJobStatus.PENDING.value,
            )
            .values(
                status=NotificationJobStatus.CANCELLED.value,
                last_error="reminder_disabled",
                completed_at=now,
                updated_at=now,
            )
        )
    if not preference.reminder_1h_enabled:
        db.execute(
            update(NotificationJob)
            .where(
                NotificationJob.recipient_user_id == user.id,
                NotificationJob.notification_type
                == NotificationType.APPOINTMENT_REMINDER_1H.value,
                NotificationJob.status == NotificationJobStatus.PENDING.value,
            )
            .values(
                status=NotificationJobStatus.CANCELLED.value,
                last_error="reminder_disabled",
                completed_at=now,
                updated_at=now,
            )
        )

    if not preference.in_app_enabled and not preference.email_enabled:
        db.execute(
            update(NotificationJob)
            .where(
                NotificationJob.recipient_user_id == user.id,
                NotificationJob.channel == NotificationJobChannel.REMINDER.value,
                NotificationJob.status == NotificationJobStatus.PENDING.value,
            )
            .values(
                status=NotificationJobStatus.CANCELLED.value,
                last_error="delivery_disabled",
                completed_at=now,
                updated_at=now,
            )
        )
        return

    appointments = db.scalars(
        select(Appointment).where(
            Appointment.status.in_(_ACTIVE_STATUSES),
            (Appointment.patient_id == user.id)
            | (
                Appointment.doctor_profile_id
                == select(DoctorProfile.id)
                .where(DoctorProfile.user_id == user.id)
                .scalar_subquery()
            ),
        )
    ).all()
    for appointment in appointments:
        _schedule_reminders(
            db,
            appointment=appointment,
            recipient_id=user.id,
            preference=preference,
        )
