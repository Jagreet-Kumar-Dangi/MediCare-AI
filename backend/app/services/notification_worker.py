import argparse
import logging
import smtplib
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.appointments import AppointmentStatus
from app.core.config import settings
from app.core.notifications import NotificationJobChannel, NotificationJobStatus
from app.db.session import SessionLocal
from app.models import (
    Appointment,
    NotificationJob,
    NotificationPreference,
    User,
)
from app.services.email_notifications import (
    render_appointment_email,
    send_email,
    smtp_is_configured,
)
from app.services.notification_service import create_reminder_notification
from app.services.appointment_service import to_utc

logger = logging.getLogger(__name__)
_ACTIVE_STATUSES = {
    AppointmentStatus.BOOKED.value,
    AppointmentStatus.CONFIRMED.value,
}
_LEASE_SECONDS = 300
_BATCH_SIZE = 10


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def claim_ready_jobs(
    db: Session,
    *,
    limit: int = _BATCH_SIZE,
) -> list[tuple[int, str]]:
    now = _utc_now()
    due_pending = and_(
        NotificationJob.status == NotificationJobStatus.PENDING.value,
        NotificationJob.scheduled_at <= now,
        or_(
            NotificationJob.next_attempt_at.is_(None),
            NotificationJob.next_attempt_at <= now,
        ),
    )
    expired_processing = and_(
        NotificationJob.status == NotificationJobStatus.PROCESSING.value,
        NotificationJob.locked_until <= now,
    )
    jobs = db.scalars(
        select(NotificationJob)
        .where(or_(due_pending, expired_processing))
        .order_by(NotificationJob.scheduled_at, NotificationJob.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    ).all()
    claims: list[tuple[int, str]] = []
    for job in jobs:
        lease_token = str(uuid4())
        job.status = NotificationJobStatus.PROCESSING.value
        job.attempt_count += 1
        job.locked_until = now + timedelta(seconds=_LEASE_SECONDS)
        job.lease_token = lease_token
        job.updated_at = now
        claims.append((job.id, lease_token))
    db.commit()
    return claims


def _finish_job(
    job: NotificationJob,
    *,
    status: NotificationJobStatus,
    now: datetime,
    reason: str | None = None,
) -> None:
    job.status = status.value
    job.last_error = reason
    job.completed_at = now
    job.next_attempt_at = None
    job.locked_until = None
    job.lease_token = None
    job.updated_at = now


def _record_failure(
    job: NotificationJob,
    *,
    now: datetime,
    error_code: str,
) -> None:
    job.last_error = error_code
    job.locked_until = None
    job.lease_token = None
    job.updated_at = now
    if job.attempt_count >= settings.notification_max_attempts:
        job.status = NotificationJobStatus.FAILED.value
        job.completed_at = now
        job.next_attempt_at = None
        return

    retry_seconds = min(
        settings.notification_retry_base_seconds
        * (2 ** (job.attempt_count - 1)),
        settings.notification_retry_max_seconds,
    )
    job.status = NotificationJobStatus.PENDING.value
    job.completed_at = None
    job.next_attempt_at = now + timedelta(seconds=retry_seconds)


def process_claimed_job(job_id: int, lease_token: str) -> bool:
    with SessionLocal() as db:
        candidate = db.get(NotificationJob, job_id)
        if (
            candidate is None
            or candidate.status != NotificationJobStatus.PROCESSING.value
            or candidate.lease_token != lease_token
        ):
            return False

        appointment = db.scalar(
            select(Appointment)
            .options(
                selectinload(Appointment.patient).selectinload(
                    User.patient_profile
                ),
                selectinload(Appointment.doctor_profile),
            )
            .where(Appointment.id == candidate.appointment_id)
            .with_for_update()
        )
        job = db.scalar(
            select(NotificationJob)
            .where(
                NotificationJob.id == job_id,
                NotificationJob.status == NotificationJobStatus.PROCESSING.value,
                NotificationJob.lease_token == lease_token,
            )
            .with_for_update()
        )
        if job is None:
            return False

        now = _utc_now()
        if appointment is None:
            _finish_job(
                job,
                status=NotificationJobStatus.CANCELLED,
                now=now,
                reason="appointment_missing",
            )
            db.commit()
            return True

        recipient = db.get(User, job.recipient_user_id)
        if recipient is None or not recipient.is_active:
            _finish_job(
                job,
                status=NotificationJobStatus.CANCELLED,
                now=now,
                reason="recipient_inactive",
            )
            db.commit()
            return True

        preference = db.get(NotificationPreference, recipient.id)
        if job.channel == NotificationJobChannel.REMINDER.value:
            reminder_enabled = (
                preference is None
                or (
                    preference.reminder_24h_enabled
                    if job.notification_type.endswith("24H")
                    else preference.reminder_1h_enabled
                )
            )
            if (
                appointment.status not in _ACTIVE_STATUSES
                or to_utc(appointment.scheduled_start)
                != to_utc(job.appointment_start_at)
                or to_utc(appointment.scheduled_start) <= now
            ):
                _finish_job(
                    job,
                    status=NotificationJobStatus.CANCELLED,
                    now=now,
                    reason="appointment_inactive_or_rescheduled",
                )
                db.commit()
                return True
            if not reminder_enabled:
                _finish_job(
                    job,
                    status=NotificationJobStatus.CANCELLED,
                    now=now,
                    reason="reminder_disabled",
                )
                db.commit()
                return True
            if preference is None or preference.in_app_enabled:
                create_reminder_notification(
                    db,
                    job=job,
                    recipient=recipient,
                )

        email_enabled = preference is None or preference.email_enabled
        if not email_enabled:
            _finish_job(
                job,
                status=NotificationJobStatus.SKIPPED,
                now=now,
                reason="email_disabled",
            )
            db.commit()
            return True
        if not smtp_is_configured():
            _finish_job(
                job,
                status=NotificationJobStatus.SKIPPED,
                now=now,
                reason="smtp_not_configured",
            )
            db.commit()
            return True

        rendered = render_appointment_email(
            db,
            job=job,
            recipient=recipient,
        )
        try:
            send_email(recipient.email, rendered)
        except (OSError, smtplib.SMTPException) as error:
            _record_failure(
                job,
                now=now,
                error_code="smtp_delivery_failed",
            )
            logger.warning(
                "Notification delivery failed: job_id=%s error_type=%s",
                job.id,
                type(error).__name__,
            )
            db.commit()
            return True

        _finish_job(job, status=NotificationJobStatus.SENT, now=_utc_now())
        db.commit()
        return True


def _record_unexpected_failure(job_id: int, lease_token: str) -> None:
    with SessionLocal() as db:
        job = db.scalar(
            select(NotificationJob)
            .where(
                NotificationJob.id == job_id,
                NotificationJob.status == NotificationJobStatus.PROCESSING.value,
                NotificationJob.lease_token == lease_token,
            )
            .with_for_update()
        )
        if job is None:
            return
        _record_failure(
            job,
            now=_utc_now(),
            error_code="worker_processing_failed",
        )
        db.commit()


def process_due_jobs(*, limit: int = _BATCH_SIZE) -> int:
    with SessionLocal() as db:
        claims = claim_ready_jobs(db, limit=limit)
    processed = 0
    for job_id, lease_token in claims:
        try:
            processed += int(process_claimed_job(job_id, lease_token))
        except Exception as error:
            logger.error(
                "Notification worker could not process a job: job_id=%s error_type=%s",
                job_id,
                type(error).__name__,
            )
            _record_unexpected_failure(job_id, lease_token)
    return processed


def run_worker(
    *,
    poll_seconds: int | None = None,
    once: bool = False,
) -> None:
    interval = (
        settings.notification_worker_poll_seconds
        if poll_seconds is None
        else poll_seconds
    )
    if not 1 <= interval <= 300:
        raise ValueError("Worker polling interval must be between 1 and 300 seconds.")
    logger.info("Notification worker started.")
    while True:
        processed = process_due_jobs()
        if once:
            return
        if processed == 0:
            time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the MediCare AI notification worker.")
    parser.add_argument("--once", action="store_true", help="Process one due-job batch.")
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=None,
        help="Override the configured worker polling interval.",
    )
    arguments = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_worker(poll_seconds=arguments.poll_seconds, once=arguments.once)


if __name__ == "__main__":
    main()
