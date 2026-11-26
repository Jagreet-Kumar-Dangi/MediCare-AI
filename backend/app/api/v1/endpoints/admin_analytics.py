import csv
from datetime import date
from io import StringIO
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.analytics import AnalyticsPeriod, TrendGranularity
from app.core.appointments import AppointmentStatus
from app.db.session import get_db
from app.models import User, UserRole
from app.models.doctor_profile import DoctorVerificationStatus
from app.schemas.admin_analytics import (
    AppointmentAnalyticsResponse,
    DoctorAnalyticsResponse,
    DoctorPerformanceResponse,
    NotificationAnalyticsResponse,
    OverviewResponse,
    PatientAnalyticsResponse,
)
from app.services.admin_analytics_service import (
    PeriodWindow,
    build_period_window,
    get_appointment_analytics,
    get_doctor_analytics,
    get_doctor_performance,
    get_export_rows,
    get_notification_analytics,
    get_overview,
    get_patient_analytics,
)

router = APIRouter(prefix="/admin/analytics", tags=["admin analytics"])
_require_admin = require_role(UserRole.ADMIN)
_CSV_DATASETS = ("patients", "doctors", "appointments", "notifications")
_MAX_PERFORMANCE_PAGE_SIZE = 100


def _period_window(
    period: AnalyticsPeriod,
    start_date: date | None,
    end_date: date | None,
) -> PeriodWindow:
    try:
        return build_period_window(
            period,
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _safe_csv_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


def _csv_stream(
    headers: list[str],
    rows: list[tuple[Any, ...]],
):
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(headers)
    yield buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)

    for row in rows:
        writer.writerow([_safe_csv_cell(value) for value in row])
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)


@router.get("/overview", response_model=OverviewResponse)
def overview(
    period: AnalyticsPeriod = AnalyticsPeriod.LAST_30_DAYS,
    start_date: date | None = None,
    end_date: date | None = None,
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> OverviewResponse:
    del current_admin
    window = _period_window(period, start_date, end_date)
    return OverviewResponse(**get_overview(db, window))


@router.get("/patients", response_model=PatientAnalyticsResponse)
def patient_analytics(
    period: AnalyticsPeriod = AnalyticsPeriod.LAST_30_DAYS,
    start_date: date | None = None,
    end_date: date | None = None,
    granularity: TrendGranularity = TrendGranularity.DAILY,
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> PatientAnalyticsResponse:
    del current_admin
    window = _period_window(period, start_date, end_date)
    return PatientAnalyticsResponse(
        **get_patient_analytics(db, window, granularity)
    )


@router.get("/doctors", response_model=DoctorAnalyticsResponse)
def doctor_analytics(
    period: AnalyticsPeriod = AnalyticsPeriod.LAST_30_DAYS,
    start_date: date | None = None,
    end_date: date | None = None,
    granularity: TrendGranularity = TrendGranularity.DAILY,
    verification_status: DoctorVerificationStatus | None = None,
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> DoctorAnalyticsResponse:
    del current_admin
    window = _period_window(period, start_date, end_date)
    return DoctorAnalyticsResponse(
        **get_doctor_analytics(
            db,
            window,
            granularity,
            verification_status=(
                verification_status.value if verification_status else None
            ),
        )
    )


@router.get("/appointments", response_model=AppointmentAnalyticsResponse)
def appointment_analytics(
    period: AnalyticsPeriod = AnalyticsPeriod.LAST_30_DAYS,
    start_date: date | None = None,
    end_date: date | None = None,
    granularity: TrendGranularity = TrendGranularity.DAILY,
    status: AppointmentStatus | None = None,
    doctor_id: Annotated[int | None, Query(ge=1)] = None,
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> AppointmentAnalyticsResponse:
    del current_admin
    window = _period_window(period, start_date, end_date)
    return AppointmentAnalyticsResponse(
        **get_appointment_analytics(
            db,
            window,
            granularity,
            status_filter=status,
            doctor_id=doctor_id,
        )
    )


@router.get("/notifications", response_model=NotificationAnalyticsResponse)
def notification_analytics(
    period: AnalyticsPeriod = AnalyticsPeriod.LAST_30_DAYS,
    start_date: date | None = None,
    end_date: date | None = None,
    granularity: TrendGranularity = TrendGranularity.DAILY,
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> NotificationAnalyticsResponse:
    del current_admin
    window = _period_window(period, start_date, end_date)
    return NotificationAnalyticsResponse(
        **get_notification_analytics(db, window, granularity)
    )


@router.get(
    "/doctor-performance",
    response_model=DoctorPerformanceResponse,
)
def doctor_performance(
    period: AnalyticsPeriod = AnalyticsPeriod.LAST_30_DAYS,
    start_date: date | None = None,
    end_date: date | None = None,
    verification_status: DoctorVerificationStatus | None = None,
    limit: Annotated[
        int, Query(ge=1, le=_MAX_PERFORMANCE_PAGE_SIZE)
    ] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> DoctorPerformanceResponse:
    del current_admin
    window = _period_window(period, start_date, end_date)
    return DoctorPerformanceResponse(
        **get_doctor_performance(
            db,
            window,
            limit=limit,
            offset=offset,
            verification_status=(
                verification_status.value if verification_status else None
            ),
        )
    )


@router.get("/export")
def export_analytics(
    dataset: Annotated[str, Query()],
    period: AnalyticsPeriod = AnalyticsPeriod.LAST_30_DAYS,
    start_date: date | None = None,
    end_date: date | None = None,
    granularity: TrendGranularity = TrendGranularity.DAILY,
    status: AppointmentStatus | None = None,
    doctor_id: Annotated[int | None, Query(ge=1)] = None,
    verification_status: DoctorVerificationStatus | None = None,
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    del current_admin
    if dataset not in _CSV_DATASETS:
        raise HTTPException(
            status_code=422,
            detail=f"dataset must be one of: {', '.join(_CSV_DATASETS)}.",
        )
    if dataset != "appointments" and (status is not None or doctor_id is not None):
        raise HTTPException(
            status_code=422,
            detail="status and doctor_id filters are only valid for appointments.",
        )
    if dataset != "doctors" and verification_status is not None:
        raise HTTPException(
            status_code=422,
            detail="verification_status is only valid for the doctors dataset.",
        )
    window = _period_window(period, start_date, end_date)
    headers, rows = get_export_rows(
        db,
        dataset=dataset,
        window=window,
        granularity=granularity,
        status_filter=status,
        doctor_id=doctor_id,
        doctor_verification_status=(
            verification_status.value if verification_status else None
        ),
    )
    filename = f"medicare-{dataset}-{window.start_date}-{window.end_date}.csv"
    return StreamingResponse(
        _csv_stream(headers, rows),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
