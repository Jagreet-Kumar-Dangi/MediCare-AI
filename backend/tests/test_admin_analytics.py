from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.analytics import AnalyticsPeriod, TrendGranularity
from app.core.security import create_access_token, hash_password
from app.models import (
    Appointment,
    AppointmentAuditEvent,
    DoctorProfile,
    DoctorVerificationEvent,
    NotificationJob,
    User,
    UserRole,
)
from app.services.admin_analytics_service import (
    build_period_window,
    get_appointment_analytics,
    get_doctor_analytics,
    get_doctor_performance,
    get_export_rows,
    get_notification_analytics,
    get_overview,
    get_patient_analytics,
)
from app.api.v1.endpoints.admin_analytics import _safe_csv_cell


def _create_user(
    db: Session,
    *,
    email: str,
    role: UserRole,
    created_at: datetime,
) -> User:
    user = User(
        email=email,
        password_hash=hash_password("analytics-test-password"),
        role=role,
        created_at=created_at,
    )
    db.add(user)
    db.flush()
    return user


def test_period_windows_use_kolkata_local_midnight_and_custom_inclusive_dates() -> None:
    now = datetime(2026, 5, 4, 20, 0, tzinfo=timezone.utc)
    today = build_period_window(AnalyticsPeriod.TODAY, now=now)
    custom = build_period_window(
        AnalyticsPeriod.CUSTOM,
        start_date=datetime(2026, 5, 1).date(),
        end_date=datetime(2026, 5, 3).date(),
        now=now,
    )

    assert today.start_date.isoformat() == "2026-05-05"
    assert today.start_utc == datetime(2026, 5, 4, 18, 30, tzinfo=timezone.utc)
    assert today.end_utc == datetime(2026, 5, 5, 18, 30, tzinfo=timezone.utc)
    assert custom.end_date.isoformat() == "2026-05-03"
    assert custom.end_utc == datetime(2026, 5, 3, 18, 30, tzinfo=timezone.utc)
    assert custom.previous_end_utc == custom.start_utc


def test_empty_analytics_returns_zero_counts_and_zero_filled_weekly_trends(
    test_engine: Engine,
) -> None:
    window = build_period_window(
        AnalyticsPeriod.LAST_30_DAYS,
        now=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
    )
    with Session(test_engine) as db:
        patients = get_patient_analytics(db, window, TrendGranularity.WEEKLY)
        notifications = get_notification_analytics(
            db,
            window,
            TrendGranularity.WEEKLY,
        )

    assert patients["total_patients"] == 0
    assert patients["new_registrations"]["comparison_available"] is False
    assert patients["registration_trend"]
    assert all(point["count"] == 0 for point in patients["registration_trend"])
    assert notifications["total_jobs"] == 0
    assert notifications["email_success_rate"] is None
    assert notifications["email_success_rate_available"] is False


def test_admin_analytics_aggregates_and_export_use_database_data(
    test_engine: Engine,
) -> None:
    now = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    window = build_period_window(AnalyticsPeriod.LAST_7_DAYS, now=now)
    with Session(test_engine) as db:
        admin = _create_user(
            db,
            email="analytics-admin@example.com",
            role=UserRole.ADMIN,
            created_at=window.start_utc,
        )
        patient = _create_user(
            db,
            email="analytics-patient@example.com",
            role=UserRole.PATIENT,
            created_at=window.start_utc + timedelta(days=1),
        )
        previous_patient = _create_user(
            db,
            email="previous-patient@example.com",
            role=UserRole.PATIENT,
            created_at=window.previous_start_utc + timedelta(days=1),
        )
        doctor_user = _create_user(
            db,
            email="analytics-doctor@example.com",
            role=UserRole.DOCTOR,
            created_at=window.start_utc,
        )
        doctor = DoctorProfile(
            user_id=doctor_user.id,
            full_name="Dr. Test Analytics",
            specialization="General Medicine",
            qualification="MBBS",
            medical_registration_number="ANALYTICS-1",
            years_of_experience=4,
            verification_status="APPROVED",
            created_at=window.start_utc + timedelta(days=2),
        )
        db.add(doctor)
        db.flush()

        appointment_time = window.start_utc + timedelta(days=2)
        appointment = Appointment(
            patient_id=patient.id,
            doctor_profile_id=doctor.id,
            scheduled_start=appointment_time,
            scheduled_end=appointment_time + timedelta(minutes=30),
            status="COMPLETED",
            reason_for_visit="Dummy test appointment",
            created_at=window.start_utc + timedelta(days=2),
        )
        db.add(appointment)
        db.flush()
        db.add_all(
            [
                AppointmentAuditEvent(
                    appointment_id=appointment.id,
                    actor_user_id=doctor_user.id,
                    action="COMPLETED",
                    created_at=window.start_utc + timedelta(days=3),
                ),
                DoctorVerificationEvent(
                    doctor_profile_id=doctor.id,
                    admin_user_id=admin.id,
                    action="APPROVED",
                    created_at=window.start_utc + timedelta(days=2),
                ),
                NotificationJob(
                    recipient_user_id=patient.id,
                    appointment_id=appointment.id,
                    notification_type="APPOINTMENT_BOOKED",
                    channel="EMAIL",
                    status="SENT",
                    scheduled_at=appointment_time,
                    appointment_start_at=appointment_time,
                    attempt_count=2,
                    idempotency_key="analytics-notification-test",
                    created_at=window.start_utc + timedelta(days=2),
                ),
            ]
        )
        db.commit()

        overview = get_overview(db, window)
        patients = get_patient_analytics(db, window, TrendGranularity.DAILY)
        doctors = get_doctor_analytics(db, window, TrendGranularity.DAILY)
        appointments = get_appointment_analytics(
            db,
            window,
            TrendGranularity.DAILY,
            status_filter=None,
            doctor_id=None,
        )
        notifications = get_notification_analytics(
            db,
            window,
            TrendGranularity.DAILY,
        )
        performance = get_doctor_performance(
            db,
            window,
            limit=20,
            offset=0,
            verification_status=None,
        )
        notification_headers, notification_rows = get_export_rows(
            db,
            dataset="notifications",
            window=window,
            granularity=TrendGranularity.DAILY,
        )
        del previous_patient

    assert overview["total_users"] == 4
    assert overview["total_appointments"] == 1
    assert patients["total_patients"] == 2
    assert patients["new_registrations"]["current"] == 1
    assert patients["new_registrations"]["previous"] == 1
    assert patients["new_registrations"]["percent_change"] == 0
    assert doctors["total_doctors"] == 1
    assert doctors["approval_trend"][2]["count"] == 1
    assert appointments["total_appointments"] == 1
    assert appointments["completion_trend"][3]["count"] == 1
    assert notifications["sent_jobs"] == 1
    assert notifications["retried_jobs"] == 1
    assert notifications["total_retries"] == 1
    assert notifications["email_success_rate"] == 100
    assert performance["items"][0]["completed_appointments"] == 1
    assert performance["items"][0]["upcoming_appointments"] == 0
    assert notification_headers[-2:] == ["jobs", "retries"]
    assert notification_rows[0][-2:] == (1, 1)


def test_admin_analytics_routes_require_admin_and_validate_custom_range(
    client: TestClient,
    patient_account: dict[str, object],
    test_engine: Engine,
) -> None:
    token = str(patient_account["token"])
    denied = client.get(
        "/api/v1/admin/analytics/overview",
        headers={"Authorization": f"Bearer {token}"},
    )

    with Session(test_engine) as db:
        admin = _create_user(
            db,
            email="analytics-route-admin@example.com",
            role=UserRole.ADMIN,
            created_at=datetime.now(timezone.utc),
        )
        doctor = _create_user(
            db,
            email="analytics-route-doctor@example.com",
            role=UserRole.DOCTOR,
            created_at=datetime.now(timezone.utc),
        )
        db.commit()
        admin_token = create_access_token(admin.id)
        doctor_token = create_access_token(doctor.id)

    invalid_range = client.get(
        "/api/v1/admin/analytics/patients",
        params={
            "period": "custom",
            "start_date": "2026-05-04",
            "end_date": "2026-05-03",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    doctor_denied = client.get(
        "/api/v1/admin/analytics/overview",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    csv_response = client.get(
        "/api/v1/admin/analytics/export",
        params={"dataset": "patients", "period": "today"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert denied.status_code == 403
    assert doctor_denied.status_code == 403
    assert invalid_range.status_code == 422
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert csv_response.text.startswith("local_date,registrations\r\n")
    assert "patient_email" not in csv_response.text
    assert "medical_record" not in csv_response.text


def test_csv_cells_escape_spreadsheet_formulas() -> None:
    assert _safe_csv_cell("=SUM(A1:A2)") == "'=SUM(A1:A2)"
    assert _safe_csv_cell("  @cmd") == "'  @cmd"
    assert _safe_csv_cell("ordinary value") == "ordinary value"
