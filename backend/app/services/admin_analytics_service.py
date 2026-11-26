from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from sqlalchemy import Integer, and_, case, cast, func, select
from sqlalchemy.orm import Session

from app.core.analytics import (
    REPORTING_TIMEZONE,
    AnalyticsPeriod,
    TrendGranularity,
)
from app.core.appointments import AppointmentStatus
from app.core.doctor_credentials import DoctorCredentialStatus
from app.core.notifications import NotificationJobStatus
from app.models import (
    Appointment,
    AppointmentAuditEvent,
    DoctorCredential,
    DoctorProfile,
    DoctorVerificationEvent,
    NotificationJob,
    User,
    UserRole,
)

_REPORTING_ZONE = ZoneInfo(REPORTING_TIMEZONE)
_ACTIVE_APPOINTMENT_STATUSES = (
    AppointmentStatus.BOOKED.value,
    AppointmentStatus.CONFIRMED.value,
)


@dataclass(frozen=True)
class PeriodWindow:
    period: AnalyticsPeriod
    start_date: date
    end_date: date
    start_utc: datetime
    end_utc: datetime
    previous_start_utc: datetime
    previous_end_utc: datetime


def _month_start(day: date, offset: int = 0) -> date:
    month_index = day.year * 12 + day.month - 1 + offset
    year, month_zero_based = divmod(month_index, 12)
    return date(year, month_zero_based + 1, 1)


def _local_midnight(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=_REPORTING_ZONE)


def _utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)


def build_period_window(
    period: AnalyticsPeriod,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    now: datetime | None = None,
) -> PeriodWindow:
    today = (now or datetime.now(timezone.utc)).astimezone(_REPORTING_ZONE).date()
    if period == AnalyticsPeriod.CUSTOM:
        if start_date is None or end_date is None:
            raise ValueError("Custom periods require both start_date and end_date.")
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date.")
        current_start = start_date
        current_end_exclusive = end_date + timedelta(days=1)
        duration_days = (end_date - start_date).days + 1
        previous_start = current_start - timedelta(days=duration_days)
        previous_end = current_start
    elif start_date is not None or end_date is not None:
        raise ValueError("start_date and end_date are only valid for a custom period.")
    elif period == AnalyticsPeriod.TODAY:
        current_start = today
        current_end_exclusive = today + timedelta(days=1)
        previous_start = today - timedelta(days=1)
        previous_end = today
    elif period in {
        AnalyticsPeriod.LAST_7_DAYS,
        AnalyticsPeriod.LAST_30_DAYS,
        AnalyticsPeriod.LAST_90_DAYS,
    }:
        duration_days = {
            AnalyticsPeriod.LAST_7_DAYS: 7,
            AnalyticsPeriod.LAST_30_DAYS: 30,
            AnalyticsPeriod.LAST_90_DAYS: 90,
        }[period]
        current_start = today - timedelta(days=duration_days - 1)
        current_end_exclusive = today + timedelta(days=1)
        previous_start = current_start - timedelta(days=duration_days)
        previous_end = current_start
    elif period == AnalyticsPeriod.THIS_MONTH:
        current_start = _month_start(today)
        current_end_exclusive = _month_start(today, 1)
        previous_start = _month_start(today, -1)
        previous_end = current_start
    else:
        current_start = _month_start(today, -1)
        current_end_exclusive = _month_start(today)
        previous_start = _month_start(today, -2)
        previous_end = current_start

    return PeriodWindow(
        period=period,
        start_date=current_start,
        end_date=current_end_exclusive - timedelta(days=1),
        start_utc=_utc(_local_midnight(current_start)),
        end_utc=_utc(_local_midnight(current_end_exclusive)),
        previous_start_utc=_utc(_local_midnight(previous_start)),
        previous_end_utc=_utc(_local_midnight(previous_end)),
    )


def period_metadata(window: PeriodWindow) -> dict[str, Any]:
    return {
        "period": window.period,
        "date_from": window.start_date,
        "date_to": window.end_date,
        "timezone": REPORTING_TIMEZONE,
    }


def _date_conditions(column: Any, window: PeriodWindow) -> list[Any]:
    return [column >= window.start_utc, column < window.end_utc]


def _count(db: Session, model: Any, *conditions: Any) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(model).where(*conditions)
        )
        or 0
    )


def _comparison(
    db: Session,
    model: Any,
    timestamp_column: Any,
    window: PeriodWindow,
    *conditions: Any,
) -> dict[str, Any]:
    current_period = and_(
        timestamp_column >= window.start_utc,
        timestamp_column < window.end_utc,
    )
    previous_period = and_(
        timestamp_column >= window.previous_start_utc,
        timestamp_column < window.previous_end_utc,
    )
    row = db.execute(
        select(
            func.coalesce(func.sum(case((current_period, 1), else_=0)), 0),
            func.coalesce(func.sum(case((previous_period, 1), else_=0)), 0),
        )
        .select_from(model)
        .where(*conditions)
    ).one()
    current, previous = int(row[0]), int(row[1])
    return {
        "current": current,
        "previous": previous,
        "percent_change": (
            round((current - previous) * 100.0 / previous, 2)
            if previous > 0
            else None
        ),
        "comparison_available": previous > 0,
    }


def _bucket_expression(
    db: Session,
    timestamp_column: Any,
    granularity: TrendGranularity,
) -> Any:
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        local_timestamp = func.timezone(REPORTING_TIMEZONE, timestamp_column)
        return func.date_trunc(granularity.value, local_timestamp)

    local_date = func.date(timestamp_column, "+5 hours", "+30 minutes")
    if granularity == TrendGranularity.WEEKLY:
        weekday = cast(func.strftime("%w", local_date), Integer)
        days_since_monday = (weekday + 6) % 7
        return func.date(local_date, func.printf("-%d days", days_since_monday))
    if granularity == TrendGranularity.MONTHLY:
        return func.strftime("%Y-%m-01", timestamp_column, "+5 hours", "+30 minutes")
    return func.strftime("%Y-%m-%d", timestamp_column, "+5 hours", "+30 minutes")


def _normalise_bucket(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _bucket_start(day: date, granularity: TrendGranularity) -> date:
    if granularity == TrendGranularity.WEEKLY:
        return day - timedelta(days=day.weekday())
    if granularity == TrendGranularity.MONTHLY:
        return day.replace(day=1)
    return day


def _next_bucket(day: date, granularity: TrendGranularity) -> date:
    if granularity == TrendGranularity.WEEKLY:
        return day + timedelta(days=7)
    if granularity == TrendGranularity.MONTHLY:
        return _month_start(day, 1)
    return day + timedelta(days=1)


def grouped_counts(
    db: Session,
    timestamp_column: Any,
    window: PeriodWindow,
    granularity: TrendGranularity,
    *,
    conditions: Sequence[Any] = (),
    dimensions: Sequence[Any] = (),
    from_clause: Any | None = None,
) -> list[tuple[Any, ...]]:
    bucket = _bucket_expression(db, timestamp_column, granularity)
    statement = select(
        bucket.label("bucket"),
        *dimensions,
        func.count().label("count"),
    )
    if from_clause is not None:
        statement = statement.select_from(from_clause)
    statement = (
        statement
        .where(*_date_conditions(timestamp_column, window), *conditions)
        .group_by(bucket, *dimensions)
        .order_by(bucket, *dimensions)
    )
    return [
        (_normalise_bucket(row[0]), *row[1:-1], int(row[-1]))
        for row in db.execute(statement).all()
    ]


def trend_points(
    grouped_rows: Sequence[tuple[Any, ...]],
    window: PeriodWindow,
    granularity: TrendGranularity,
) -> list[dict[str, Any]]:
    counts = {row[0]: int(row[-1]) for row in grouped_rows}
    bucket = _bucket_start(window.start_date, granularity)
    last_bucket = _bucket_start(window.end_date, granularity)
    points: list[dict[str, Any]] = []
    while bucket <= last_bucket:
        points.append({"bucket": bucket, "count": counts.get(bucket, 0)})
        bucket = _next_bucket(bucket, granularity)
    return points


def _status_counts(
    db: Session,
    model: Any,
    column: Any,
    *conditions: Any,
    statuses: Sequence[str],
) -> list[dict[str, Any]]:
    rows = db.execute(
        select(column, func.count())
        .select_from(model)
        .where(*conditions)
        .group_by(column)
    ).all()
    counts = {str(status): int(count) for status, count in rows}
    return [{"status": status, "count": counts.get(status, 0)} for status in statuses]


def _appointment_conditions(
    *,
    status_filter: AppointmentStatus | None,
    doctor_id: int | None,
) -> list[Any]:
    conditions: list[Any] = []
    if status_filter is not None:
        conditions.append(Appointment.status == status_filter.value)
    if doctor_id is not None:
        conditions.append(Appointment.doctor_profile_id == doctor_id)
    return conditions


def get_overview(db: Session, window: PeriodWindow) -> dict[str, Any]:
    user_rows = db.execute(
        select(User.role, User.is_active, func.count())
        .group_by(User.role, User.is_active)
    ).all()
    role_counts: dict[str, int] = {}
    for role, _is_active, count in user_rows:
        role_counts[role.value if isinstance(role, UserRole) else str(role)] = (
            role_counts.get(role.value if isinstance(role, UserRole) else str(role), 0)
            + int(count)
        )

    doctor_rows = db.execute(
        select(DoctorProfile.verification_status, func.count())
        .group_by(DoctorProfile.verification_status)
    ).all()
    doctor_counts = {str(status): int(count) for status, count in doctor_rows}
    appointment_rows = db.execute(
        select(Appointment.status, func.count()).group_by(Appointment.status)
    ).all()
    appointment_counts = {str(status): int(count) for status, count in appointment_rows}
    now = datetime.now(timezone.utc)

    return {
        **period_metadata(window),
        "total_users": sum(role_counts.values()),
        "total_patients": role_counts.get(UserRole.PATIENT.value, 0),
        "total_doctors": _count(db, DoctorProfile),
        "approved_doctors": doctor_counts.get("APPROVED", 0),
        "pending_doctors": doctor_counts.get("PENDING", 0),
        "suspended_doctors": doctor_counts.get("SUSPENDED", 0),
        "total_appointments": sum(appointment_counts.values()),
        "upcoming_appointments": _count(
            db,
            Appointment,
            Appointment.status.in_(_ACTIVE_APPOINTMENT_STATUSES),
            Appointment.scheduled_start >= now,
        ),
        "completed_appointments": appointment_counts.get(
            AppointmentStatus.COMPLETED.value, 0
        ),
        "cancelled_appointments": appointment_counts.get(
            AppointmentStatus.CANCELLED.value, 0
        ),
        "new_users": _comparison(db, User, User.created_at, window),
        "new_patients": _comparison(
            db,
            User,
            User.created_at,
            window,
            User.role == UserRole.PATIENT,
        ),
        "new_doctors": _comparison(
            db,
            DoctorProfile,
            DoctorProfile.created_at,
            window,
        ),
        "appointments_created": _comparison(
            db,
            Appointment,
            Appointment.created_at,
            window,
        ),
    }


def get_patient_analytics(
    db: Session,
    window: PeriodWindow,
    granularity: TrendGranularity,
) -> dict[str, Any]:
    patient_filter = User.role == UserRole.PATIENT
    active_rows = db.execute(
        select(User.is_active, func.count())
        .where(patient_filter)
        .group_by(User.is_active)
    ).all()
    active_counts = {bool(active): int(count) for active, count in active_rows}
    grouped = grouped_counts(
        db,
        User.created_at,
        window,
        granularity,
        conditions=(patient_filter,),
    )
    return {
        **period_metadata(window),
        "total_patients": sum(active_counts.values()),
        "active_patients": active_counts.get(True, 0),
        "inactive_patients": active_counts.get(False, 0),
        "new_registrations": _comparison(
            db,
            User,
            User.created_at,
            window,
            patient_filter,
        ),
        "registration_trend": trend_points(grouped, window, granularity),
    }


def get_doctor_analytics(
    db: Session,
    window: PeriodWindow,
    granularity: TrendGranularity,
    *,
    verification_status: str | None = None,
) -> dict[str, Any]:
    verification_statuses = (
        "PENDING",
        "APPROVED",
        "REJECTED",
        "SUSPENDED",
    )
    credential_statuses = tuple(status.value for status in DoctorCredentialStatus)
    doctor_filters = (
        (DoctorProfile.verification_status == verification_status,)
        if verification_status
        else ()
    )
    account_rows = db.execute(
        select(User.is_active, func.count())
        .select_from(DoctorProfile)
        .join(User, User.id == DoctorProfile.user_id)
        .where(*doctor_filters)
        .group_by(User.is_active)
    ).all()
    account_counts = {bool(active): int(count) for active, count in account_rows}
    registration_rows = grouped_counts(
        db,
        DoctorProfile.created_at,
        window,
        granularity,
        conditions=doctor_filters,
    )
    approval_rows = grouped_counts(
        db,
        DoctorVerificationEvent.created_at,
        window,
        granularity,
        conditions=(
            DoctorVerificationEvent.action == "APPROVED",
            *doctor_filters,
        ),
        from_clause=DoctorVerificationEvent.__table__.join(
            DoctorProfile.__table__,
            DoctorVerificationEvent.doctor_profile_id == DoctorProfile.id,
        ),
    )
    credential_rows = db.execute(
        select(DoctorCredential.verification_status, func.count())
        .select_from(DoctorCredential)
        .join(
            DoctorProfile,
            DoctorCredential.doctor_profile_id == DoctorProfile.id,
        )
        .where(
            *_date_conditions(DoctorCredential.submitted_at, window),
            *doctor_filters,
        )
        .group_by(DoctorCredential.verification_status)
    ).all()
    credential_counts = {
        str(status): int(count) for status, count in credential_rows
    }
    return {
        **period_metadata(window),
        "total_doctors": _count(db, DoctorProfile, *doctor_filters),
        "active_accounts": account_counts.get(True, 0),
        "inactive_accounts": account_counts.get(False, 0),
        "verification_statuses": _status_counts(
            db,
            DoctorProfile,
            DoctorProfile.verification_status,
            *doctor_filters,
            statuses=verification_statuses,
        ),
        "credential_statuses": [
            {"status": status, "count": credential_counts.get(status, 0)}
            for status in credential_statuses
        ],
        "registration_trend": trend_points(
            registration_rows,
            window,
            granularity,
        ),
        "approval_trend": trend_points(approval_rows, window, granularity),
    }


def get_appointment_analytics(
    db: Session,
    window: PeriodWindow,
    granularity: TrendGranularity,
    *,
    status_filter: AppointmentStatus | None,
    doctor_id: int | None,
) -> dict[str, Any]:
    filters = _appointment_conditions(
        status_filter=status_filter,
        doctor_id=doctor_id,
    )
    status_values = tuple(status.value for status in AppointmentStatus)
    status_counts = _status_counts(
        db,
        Appointment,
        Appointment.status,
        *_date_conditions(Appointment.created_at, window),
        *filters,
        statuses=status_values,
    )
    booking_rows = grouped_counts(
        db,
        Appointment.created_at,
        window,
        granularity,
        conditions=filters,
    )
    audit_filters: list[Any] = []
    if status_filter is not None:
        audit_filters.append(Appointment.status == status_filter.value)
    if doctor_id is not None:
        audit_filters.append(Appointment.doctor_profile_id == doctor_id)
    cancellation_rows = grouped_counts(
        db,
        AppointmentAuditEvent.created_at,
        window,
        granularity,
        conditions=(
            AppointmentAuditEvent.action == "CANCELLED",
            *audit_filters,
        ),
        dimensions=(AppointmentAuditEvent.appointment_id,),
        from_clause=AppointmentAuditEvent.__table__.join(
            Appointment.__table__,
            AppointmentAuditEvent.appointment_id == Appointment.id,
        ),
    )
    completion_rows = grouped_counts(
        db,
        AppointmentAuditEvent.created_at,
        window,
        granularity,
        conditions=(
            AppointmentAuditEvent.action == "COMPLETED",
            *audit_filters,
        ),
        dimensions=(AppointmentAuditEvent.appointment_id,),
        from_clause=AppointmentAuditEvent.__table__.join(
            Appointment.__table__,
            AppointmentAuditEvent.appointment_id == Appointment.id,
        ),
    )
    cancellation_totals = _collapse_dimension_counts(cancellation_rows)
    completion_totals = _collapse_dimension_counts(completion_rows)
    now = datetime.now(timezone.utc)
    upcoming_conditions = [
        Appointment.scheduled_start >= max(window.start_utc, now),
        Appointment.scheduled_start < window.end_utc,
        Appointment.status.in_(_ACTIVE_APPOINTMENT_STATUSES),
        *filters,
    ]
    return {
        **period_metadata(window),
        "total_appointments": sum(item["count"] for item in status_counts),
        "upcoming_appointments": _count(db, Appointment, *upcoming_conditions),
        "status_filter": status_filter.value if status_filter else None,
        "doctor_id": doctor_id,
        "status_counts": status_counts,
        "booking_trend": trend_points(booking_rows, window, granularity),
        "cancellation_trend": trend_points(
            cancellation_totals,
            window,
            granularity,
        ),
        "completion_trend": trend_points(
            completion_totals,
            window,
            granularity,
        ),
    }


def _collapse_dimension_counts(
    grouped_rows: Sequence[tuple[Any, ...]],
) -> list[tuple[date, int]]:
    totals: dict[date, int] = {}
    for bucket, _dimension, count in grouped_rows:
        totals[bucket] = totals.get(bucket, 0) + int(count)
    return [(bucket, count) for bucket, count in totals.items()]


def get_notification_analytics(
    db: Session,
    window: PeriodWindow,
    granularity: TrendGranularity,
) -> dict[str, Any]:
    status_rows = db.execute(
        select(NotificationJob.status, func.count())
        .where(*_date_conditions(NotificationJob.created_at, window))
        .group_by(NotificationJob.status)
    ).all()
    status_counts = {str(status): int(count) for status, count in status_rows}
    retry_values = db.execute(
        select(
            func.count(
                case((NotificationJob.attempt_count > 1, NotificationJob.id))
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            NotificationJob.attempt_count > 1,
                            NotificationJob.attempt_count - 1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
        ).where(*_date_conditions(NotificationJob.created_at, window))
    ).one()
    email_delivery = db.execute(
        select(NotificationJob.status, func.count())
        .where(
            *_date_conditions(NotificationJob.created_at, window),
            NotificationJob.channel == "EMAIL",
            NotificationJob.status.in_(
                [NotificationJobStatus.SENT.value, NotificationJobStatus.FAILED.value]
            ),
        )
        .group_by(NotificationJob.status)
    ).all()
    email_counts = {str(status): int(count) for status, count in email_delivery}
    delivered = email_counts.get(NotificationJobStatus.SENT.value, 0)
    delivery_failures = email_counts.get(NotificationJobStatus.FAILED.value, 0)
    denominator = delivered + delivery_failures
    grouped = grouped_counts(
        db,
        NotificationJob.created_at,
        window,
        granularity,
    )
    return {
        **period_metadata(window),
        "total_jobs": sum(status_counts.values()),
        "pending_jobs": status_counts.get(NotificationJobStatus.PENDING.value, 0),
        "processing_jobs": status_counts.get(
            NotificationJobStatus.PROCESSING.value, 0
        ),
        "sent_jobs": status_counts.get(NotificationJobStatus.SENT.value, 0),
        "failed_jobs": status_counts.get(NotificationJobStatus.FAILED.value, 0),
        "cancelled_jobs": status_counts.get(NotificationJobStatus.CANCELLED.value, 0),
        "skipped_jobs": status_counts.get(NotificationJobStatus.SKIPPED.value, 0),
        "retried_jobs": int(retry_values[0] or 0),
        "total_retries": int(retry_values[1] or 0),
        "email_success_rate": (
            round(delivered * 100.0 / denominator, 2) if denominator else None
        ),
        "email_success_rate_available": denominator > 0,
        "job_trend": trend_points(grouped, window, granularity),
    }


def get_doctor_performance(
    db: Session,
    window: PeriodWindow,
    *,
    limit: int,
    offset: int,
    verification_status: str | None,
) -> dict[str, Any]:
    appointment_join_conditions = [
        Appointment.doctor_profile_id == DoctorProfile.id,
        *_date_conditions(Appointment.created_at, window),
    ]
    now = datetime.now(timezone.utc)
    filters: list[Any] = []
    if verification_status is not None:
        filters.append(DoctorProfile.verification_status == verification_status)

    total_appointments = func.count(Appointment.id)
    completed_appointments = func.coalesce(
        func.sum(
            case(
                (Appointment.status == AppointmentStatus.COMPLETED.value, 1),
                else_=0,
            )
        ),
        0,
    )
    cancelled_appointments = func.coalesce(
        func.sum(
            case(
                (Appointment.status == AppointmentStatus.CANCELLED.value, 1),
                else_=0,
            )
        ),
        0,
    )
    upcoming_subquery = (
        select(
            Appointment.doctor_profile_id.label("doctor_profile_id"),
            func.count(Appointment.id).label("upcoming_count"),
        )
        .where(
            Appointment.status.in_(_ACTIVE_APPOINTMENT_STATUSES),
            Appointment.scheduled_start >= now,
        )
        .group_by(Appointment.doctor_profile_id)
        .subquery("upcoming_appointments")
    )
    upcoming_appointments = func.coalesce(
        func.max(upcoming_subquery.c.upcoming_count),
        0,
    )
    statement = (
        select(
            DoctorProfile.id,
            DoctorProfile.full_name,
            DoctorProfile.verification_status,
            User.is_active,
            total_appointments,
            completed_appointments,
            cancelled_appointments,
            upcoming_appointments,
        )
        .join(User, User.id == DoctorProfile.user_id)
        .outerjoin(Appointment, and_(*appointment_join_conditions))
        .outerjoin(
            upcoming_subquery,
            upcoming_subquery.c.doctor_profile_id == DoctorProfile.id,
        )
        .where(*filters)
        .group_by(
            DoctorProfile.id,
            DoctorProfile.full_name,
            DoctorProfile.verification_status,
            User.is_active,
        )
        .order_by(DoctorProfile.full_name, DoctorProfile.id)
        .limit(limit)
        .offset(offset)
    )
    items = [
        {
            "doctor_id": row[0],
            "full_name": row[1],
            "verification_status": row[2],
            "account_active": row[3],
            "total_appointments": int(row[4] or 0),
            "completed_appointments": int(row[5] or 0),
            "cancelled_appointments": int(row[6] or 0),
            "upcoming_appointments": int(row[7] or 0),
        }
        for row in db.execute(statement).all()
    ]
    total = db.scalar(
        select(func.count())
        .select_from(DoctorProfile)
        .where(*filters)
    )
    return {
        **period_metadata(window),
        "items": items,
        "total": int(total or 0),
        "limit": limit,
        "offset": offset,
    }


def get_export_rows(
    db: Session,
    *,
    dataset: str,
    window: PeriodWindow,
    granularity: TrendGranularity,
    status_filter: AppointmentStatus | None = None,
    doctor_id: int | None = None,
    doctor_verification_status: str | None = None,
) -> tuple[list[str], list[tuple[Any, ...]]]:
    if dataset == "patients":
        rows = grouped_counts(
            db,
            User.created_at,
            window,
            granularity,
            conditions=(User.role == UserRole.PATIENT,),
        )
        return ["local_date", "registrations"], rows

    if dataset == "doctors":
        rows = grouped_counts(
            db,
            DoctorProfile.created_at,
            window,
            granularity,
            conditions=(
                (DoctorProfile.verification_status == doctor_verification_status,)
                if doctor_verification_status
                else ()
            ),
            dimensions=(DoctorProfile.verification_status,),
        )
        return ["local_date", "verification_status", "doctor_registrations"], rows

    if dataset == "appointments":
        filters = _appointment_conditions(
            status_filter=status_filter,
            doctor_id=doctor_id,
        )
        rows = grouped_counts(
            db,
            Appointment.created_at,
            window,
            granularity,
            conditions=filters,
            dimensions=(Appointment.status,),
        )
        return ["local_date", "status", "appointments"], rows

    bucket = _bucket_expression(db, NotificationJob.created_at, granularity)
    notification_rows = db.execute(
        select(
            bucket.label("bucket"),
            NotificationJob.channel,
            NotificationJob.status,
            func.count().label("jobs"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            NotificationJob.attempt_count > 1,
                            NotificationJob.attempt_count - 1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("retries"),
        )
        .where(*_date_conditions(NotificationJob.created_at, window))
        .group_by(bucket, NotificationJob.channel, NotificationJob.status)
        .order_by(bucket, NotificationJob.channel, NotificationJob.status)
    ).all()
    expanded_rows = [
        (
            _normalise_bucket(row[0]),
            row[1],
            row[2],
            int(row[3]),
            int(row[4]),
        )
        for row in notification_rows
    ]
    return [
        "local_date",
        "channel",
        "status",
        "jobs",
        "retries",
    ], expanded_rows
