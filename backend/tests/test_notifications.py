from datetime import timedelta
import smtplib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.notifications import NotificationJobChannel
from app.core.security import create_access_token, hash_password
from app.core.notifications import NotificationJobStatus
from app.models import Notification, NotificationJob, User, UserRole
from app.services.appointment_service import local_now
from app.services import notification_worker
from app.services.email_notifications import render_appointment_email

PDF_CONTENT = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_admin(engine: Engine) -> dict[str, object]:
    with Session(engine) as db:
        admin = User(
            email="notification-admin@example.com",
            password_hash=hash_password("notification-admin-password-2026!"),
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return {"id": admin.id, "token": create_access_token(admin.id)}


def _register_verified_doctor(
    client: TestClient,
    *,
    admin: dict[str, object],
    storage_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    monkeypatch.setattr(settings, "doctor_credentials_storage_dir", storage_dir)
    email = "notification-doctor@example.com"
    password = "notification-doctor-password-2026!"
    registration = client.post(
        "/api/v1/auth/register/doctor",
        json={
            "email": email,
            "password": password,
            "full_name": "Dr Notification Example",
            "specialization": "Family Medicine",
            "qualification": "MD",
            "medical_registration_number": "NOTIFICATION-REG-1",
            "years_of_experience": 8,
        },
    )
    assert registration.status_code == 201, registration.text
    code = client.app.state.test_verification_codes[email]
    verified = client.post(
        "/api/v1/auth/verify-email/confirm",
        json={"email": email, "code": code},
    )
    assert verified.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    doctor_headers = _headers(token)
    profile = client.get("/api/v1/doctors/me", headers=doctor_headers)
    assert profile.status_code == 200
    admin_headers = _headers(str(admin["token"]))
    approved = client.post(
        f"/api/v1/admin/doctors/{profile.json()['id']}/approve",
        headers=admin_headers,
    )
    assert approved.status_code == 200, approved.text

    for index, document_type in enumerate(settings.required_doctor_credential_types):
        uploaded = client.post(
            "/api/v1/doctor-credentials",
            headers=doctor_headers,
            data={"document_type": document_type.value},
            files={
                "file": (
                    f"required-{index}.pdf",
                    PDF_CONTENT,
                    "application/pdf",
                )
            },
        )
        assert uploaded.status_code == 201, uploaded.text
        review = client.post(
            f"/api/v1/admin/doctor-credentials/{uploaded.json()['id']}/approve",
            headers=admin_headers,
        )
        assert review.status_code == 200, review.text

    return {
        "profile_id": profile.json()["id"],
        "headers": doctor_headers,
    }


def _book_appointment(
    client: TestClient,
    *,
    patient_token: str,
    doctor: dict[str, object],
) -> dict[str, object]:
    target_date = local_now().date() + timedelta(days=7)
    availability = client.post(
        "/api/v1/doctor/availability",
        headers=doctor["headers"],
        json={
            "weekday": target_date.weekday(),
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "appointment_duration_minutes": 30,
        },
    )
    assert availability.status_code == 201, availability.text
    slots_response = client.get(
        "/api/v1/appointments/available-slots",
        params={"doctor_id": doctor["profile_id"], "date": target_date.isoformat()},
    )
    assert slots_response.status_code == 200, slots_response.text
    slot = slots_response.json()["slots"][0]
    booking = client.post(
        "/api/v1/appointments",
        headers=_headers(patient_token),
        json={
            "doctor_id": doctor["profile_id"],
            "scheduled_start": slot["scheduled_start"],
            "reason_for_visit": "Routine consultation",
            "patient_notes": "Private patient notes must not be emailed.",
        },
    )
    assert booking.status_code == 201, booking.text
    return booking.json()


def test_appointment_events_preferences_and_admin_monitoring(
    client: TestClient,
    test_engine: Engine,
    patient_account: dict[str, object],
    tmp_path: Path,
    monkeypatch,
) -> None:
    from app.services import email_verification

    monkeypatch.setattr(settings, "smtp_host", None)
    monkeypatch.setattr(settings, "smtp_from_email", None)
    monkeypatch.setattr(email_verification, "_smtp_is_ready", lambda: True)
    admin = _create_admin(test_engine)
    doctor = _register_verified_doctor(
        client,
        admin=admin,
        storage_dir=tmp_path,
        monkeypatch=monkeypatch,
    )
    appointment = _book_appointment(
        client,
        patient_token=str(patient_account["token"]),
        doctor=doctor,
    )

    patient_headers = _headers(str(patient_account["token"]))
    patient_notifications = client.get(
        "/api/v1/notifications",
        headers=patient_headers,
    )
    doctor_notifications = client.get(
        "/api/v1/notifications",
        headers=doctor["headers"],
    )
    assert patient_notifications.status_code == 200
    assert doctor_notifications.status_code == 200
    assert len(patient_notifications.json()) == 1
    assert len(doctor_notifications.json()) == 1
    assert patient_notifications.json()[0]["notification_type"] == "APPOINTMENT_BOOKED"

    confirmed = client.post(
        f"/api/v1/doctor/appointments/{appointment['id']}/confirm",
        headers=doctor["headers"],
    )
    assert confirmed.status_code == 200, confirmed.text
    patient_notifications = client.get(
        "/api/v1/notifications",
        headers=patient_headers,
    )
    doctor_notifications = client.get(
        "/api/v1/notifications",
        headers=doctor["headers"],
    )
    assert {
        item["notification_type"] for item in patient_notifications.json()
    } == {"APPOINTMENT_BOOKED", "APPOINTMENT_CONFIRMED"}
    assert {
        item["notification_type"] for item in doctor_notifications.json()
    } == {"APPOINTMENT_BOOKED", "APPOINTMENT_CONFIRMED"}

    doctor_notification_id = next(
        item["id"]
        for item in doctor_notifications.json()
        if item["notification_type"] == "APPOINTMENT_CONFIRMED"
    )
    denied_read = client.patch(
        f"/api/v1/notifications/{doctor_notification_id}/read",
        headers=patient_headers,
    )
    assert denied_read.status_code == 404
    own_notification_id = next(
        item["id"]
        for item in patient_notifications.json()
        if item["notification_type"] == "APPOINTMENT_BOOKED"
    )
    own_read = client.patch(
        f"/api/v1/notifications/{own_notification_id}/read",
        headers=patient_headers,
    )
    assert own_read.status_code == 200
    assert own_read.json()["read_at"] is not None

    patient_jobs = client.get(
        "/api/v1/admin/notifications/jobs",
        headers=patient_headers,
    )
    assert patient_jobs.status_code == 403
    admin_jobs = client.get(
        "/api/v1/admin/notifications/jobs",
        headers=_headers(str(admin["token"])),
    )
    assert admin_jobs.status_code == 200
    assert admin_jobs.json()["total"] == 8
    assert all(
        "@" not in job["recipient_masked"]
        or "***@" in job["recipient_masked"]
        for job in admin_jobs.json()["jobs"]
    )

    test_session_factory = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )
    with Session(test_engine) as db:
        patient_id = int(patient_account["user"]["id"])
        email_job = db.scalar(
            select(NotificationJob).where(
                NotificationJob.appointment_id == appointment["id"],
                NotificationJob.recipient_user_id == patient_id,
                NotificationJob.channel == NotificationJobChannel.EMAIL.value,
                NotificationJob.notification_type == "APPOINTMENT_BOOKED",
            )
        )
        patient = db.get(User, patient_id)
        assert email_job is not None
        assert patient is not None
        rendered = render_appointment_email(
            db,
            job=email_job,
            recipient=patient,
        )
        assert "Private patient notes" not in rendered.text
        assert "Routine consultation" not in rendered.text

        email_job.status = "PROCESSING"
        email_job.attempt_count = 1
        email_job.lease_token = "test-lease-token"
        email_job.locked_until = local_now() + timedelta(minutes=5)
        db.commit()
        email_job_id = email_job.id

    def fail_smtp(*args: object, **kwargs: object) -> None:
        raise smtplib.SMTPServerDisconnected("mock transport failure")

    monkeypatch.setattr(notification_worker, "SessionLocal", test_session_factory)
    monkeypatch.setattr(notification_worker, "smtp_is_configured", lambda: True)
    monkeypatch.setattr(notification_worker, "send_email", fail_smtp)
    assert notification_worker.process_claimed_job(
        email_job_id,
        "test-lease-token",
    )
    with Session(test_engine) as db:
        retried_job = db.get(NotificationJob, email_job_id)
        assert retried_job is not None
        assert retried_job.status == "PENDING"
        assert retried_job.next_attempt_at is not None
        assert retried_job.last_error == "smtp_delivery_failed"

    cancelled = client.post(
        f"/api/v1/appointments/{appointment['id']}/cancel",
        headers=patient_headers,
        json={"reason": "Dummy browser notification test cancellation"},
    )
    assert cancelled.status_code == 200, cancelled.text
    patient_notifications = client.get(
        "/api/v1/notifications",
        headers=patient_headers,
    )
    assert any(
        item["notification_type"] == "APPOINTMENT_CANCELLED"
        for item in patient_notifications.json()
    )

    preferences = client.put(
        "/api/v1/notifications/preferences",
        headers=patient_headers,
        json={
            "email_enabled": False,
            "in_app_enabled": False,
            "reminder_24h_enabled": False,
            "reminder_1h_enabled": False,
        },
    )
    assert preferences.status_code == 200
    assert preferences.json()["email_enabled"] is False
    assert preferences.json()["in_app_enabled"] is False

    with Session(test_engine) as db:
        reminder_jobs = db.scalars(
            select(NotificationJob).where(
                NotificationJob.appointment_id == appointment["id"],
                NotificationJob.channel == "REMINDER",
                NotificationJob.recipient_user_id == patient_account["user"]["id"],
            )
        ).all()
        assert len(reminder_jobs) == 2
        assert all(
            job.status == NotificationJobStatus.CANCELLED.value
            for job in reminder_jobs
        )
        assert db.scalar(
            select(Notification.id).where(
                Notification.recipient_user_id == patient_account["user"]["id"],
            )
        ) is not None
