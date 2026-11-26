from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models import DoctorProfile, DoctorVerificationStatus, User, UserRole
from app.services.appointment_service import local_now

PDF_CONTENT = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
DOCTOR_PASSWORD = "appointment-doctor-password-2026!"


@pytest.fixture
def appointment_admin(test_engine: Engine) -> dict[str, object]:
    with Session(test_engine) as db:
        admin = User(
            email="appointment-admin@example.com",
            password_hash=hash_password("appointment-admin-password-2026!"),
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return {
            "user": admin,
            "token": create_access_token(admin.id),
        }


@pytest.fixture
def approved_appointment_doctor(
    client: TestClient,
    appointment_admin: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    monkeypatch.setattr(settings, "doctor_credentials_storage_dir", tmp_path)
    email = "appointment-doctor@example.com"
    registration = client.post(
        "/api/v1/auth/register/doctor",
        json={
            "email": email,
            "password": DOCTOR_PASSWORD,
            "full_name": "Dr Appointment Example",
            "specialization": "Family Medicine",
            "qualification": "MD",
            "medical_registration_number": "APPOINTMENT-REG-1",
            "years_of_experience": 10,
        },
    )
    assert registration.status_code == 201, registration.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": DOCTOR_PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    doctor_headers = {"Authorization": f"Bearer {token}"}
    profile = client.get("/api/v1/doctors/me", headers=doctor_headers)
    assert profile.status_code == 200
    admin_headers = {
        "Authorization": f"Bearer {appointment_admin['token']}",
    }
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
        "profile": profile.json(),
        "token": token,
        "headers": doctor_headers,
    }


def create_weekly_availability(
    client: TestClient,
    doctor: dict[str, object],
) -> str:
    target_date = local_now().date() + timedelta(days=7)
    response = client.post(
        "/api/v1/doctor/availability",
        headers=doctor["headers"],
        json={
            "weekday": target_date.weekday(),
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "break_start": "10:30:00",
            "break_end": "11:00:00",
            "appointment_duration_minutes": 30,
        },
    )
    assert response.status_code == 201, response.text
    return target_date.isoformat()


def get_slots(
    client: TestClient,
    *,
    doctor_id: int,
    requested_date: str,
) -> list[dict[str, str]]:
    response = client.get(
        "/api/v1/appointments/available-slots",
        params={"doctor_id": doctor_id, "date": requested_date},
    )
    assert response.status_code == 200, response.text
    return response.json()["slots"]


def book_slot(
    client: TestClient,
    *,
    patient_token: str,
    doctor_id: int,
    scheduled_start: str,
) -> dict:
    return client.post(
        "/api/v1/appointments",
        headers={"Authorization": f"Bearer {patient_token}"},
        json={
            "doctor_id": doctor_id,
            "scheduled_start": scheduled_start,
            "reason_for_visit": "Routine consultation",
            "patient_notes": "Please review my recent symptoms.",
        },
    ).json()


def test_patient_books_eligible_doctor_and_doctor_confirms(
    client: TestClient,
    patient_account: dict[str, object],
    approved_appointment_doctor: dict[str, object],
) -> None:
    doctor = approved_appointment_doctor
    requested_date = create_weekly_availability(client, doctor)
    slots = get_slots(
        client,
        doctor_id=doctor["profile"]["id"],
        requested_date=requested_date,
    )
    assert len(slots) == 3

    created = client.post(
        "/api/v1/appointments",
        headers={"Authorization": f"Bearer {patient_account['token']}"},
        json={
            "doctor_id": doctor["profile"]["id"],
            "scheduled_start": slots[0]["scheduled_start"],
            "reason_for_visit": "Routine consultation",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "BOOKED"
    assert created.json()["scheduled_start"].endswith(("Z", "+00:00"))
    assert created.json()["doctor"]["id"] == doctor["profile"]["id"]

    confirmed = client.post(
        f"/api/v1/doctor/appointments/{created.json()['id']}/confirm",
        headers=doctor["headers"],
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "CONFIRMED"
    assert confirmed.json()["audit_events"][-1]["action"] == "CONFIRMED"
    assert confirmed.json()["patient_name"] == "Avery Patient"


def test_booking_rejects_pending_doctors_and_taken_slots(
    client: TestClient,
    patient_account: dict[str, object],
    approved_appointment_doctor: dict[str, object],
) -> None:
    pending = client.post(
        "/api/v1/auth/register/doctor",
        json={
            "email": "appointment-pending@example.com",
            "password": DOCTOR_PASSWORD,
            "full_name": "Dr Pending Example",
            "specialization": "Pediatrics",
            "qualification": "MD",
            "medical_registration_number": "APPOINTMENT-PENDING-1",
            "years_of_experience": 5,
        },
    )
    assert pending.status_code == 201
    pending_slots = client.get(
        "/api/v1/appointments/available-slots",
        params={"doctor_id": pending.json()["id"], "date": local_now().date().isoformat()},
    )
    assert pending_slots.status_code == 404

    doctor = approved_appointment_doctor
    requested_date = create_weekly_availability(client, doctor)
    slots = get_slots(
        client,
        doctor_id=doctor["profile"]["id"],
        requested_date=requested_date,
    )
    headers = {"Authorization": f"Bearer {patient_account['token']}"}
    first = client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "doctor_id": doctor["profile"]["id"],
            "scheduled_start": slots[0]["scheduled_start"],
            "reason_for_visit": "Routine consultation",
        },
    )
    duplicate = client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "doctor_id": doctor["profile"]["id"],
            "scheduled_start": slots[0]["scheduled_start"],
            "reason_for_visit": "Another consultation",
        },
    )
    assert first.status_code == 201, first.text
    assert duplicate.status_code == 409
    remaining = get_slots(
        client,
        doctor_id=doctor["profile"]["id"],
        requested_date=requested_date,
    )
    assert slots[0]["scheduled_start"] not in {
        slot["scheduled_start"] for slot in remaining
    }


def test_patient_ownership_and_reschedule_cancel_lifecycle(
    client: TestClient,
    patient_account: dict[str, object],
    approved_appointment_doctor: dict[str, object],
    test_engine: Engine,
) -> None:
    doctor = approved_appointment_doctor
    requested_date = create_weekly_availability(client, doctor)
    slots = get_slots(
        client,
        doctor_id=doctor["profile"]["id"],
        requested_date=requested_date,
    )
    headers = {"Authorization": f"Bearer {patient_account['token']}"}
    appointment = client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "doctor_id": doctor["profile"]["id"],
            "scheduled_start": slots[0]["scheduled_start"],
            "reason_for_visit": "Routine consultation",
        },
    )
    assert appointment.status_code == 201, appointment.text
    appointment_id = appointment.json()["id"]
    original_start = appointment.json()["scheduled_start"]

    with Session(test_engine) as db:
        other_doctor = User(
            email="appointment-other-doctor@example.com",
            password_hash=hash_password("other-doctor-password-2026!"),
            role=UserRole.DOCTOR,
        )
        db.add(other_doctor)
        db.flush()
        other_profile = DoctorProfile(
            user_id=other_doctor.id,
            full_name="Dr Other Appointment",
            specialization="Dermatology",
            qualification="MD",
            medical_registration_number="OTHER-APPOINTMENT-REG-1",
            years_of_experience=4,
            verification_status=DoctorVerificationStatus.APPROVED.value,
        )
        db.add(other_profile)
        db.commit()
        other_doctor_token = create_access_token(other_doctor.id)
    other_doctor_headers = {
        "Authorization": f"Bearer {other_doctor_token}",
    }
    assert client.get(
        f"/api/v1/doctor/appointments/{appointment_id}",
        headers=other_doctor_headers,
    ).status_code == 404
    assert client.post(
        f"/api/v1/doctor/appointments/{appointment_id}/confirm",
        headers=other_doctor_headers,
    ).status_code == 404

    second_patient = client.post(
        "/api/v1/auth/register/patient",
        json={
            "email": "appointment-other-patient@example.com",
            "password": "another-strong-password-2026!",
            "first_name": "Jordan",
            "last_name": "Other",
        },
    )
    assert second_patient.status_code == 201
    second_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "appointment-other-patient@example.com",
            "password": "another-strong-password-2026!",
        },
    )
    other_headers = {
        "Authorization": f"Bearer {second_login.json()['access_token']}",
    }
    assert client.get(
        f"/api/v1/appointments/{appointment_id}",
        headers=other_headers,
    ).status_code == 404
    assert client.post(
        f"/api/v1/doctor/appointments/{appointment_id}/confirm",
        headers=headers,
    ).status_code == 403
    assert client.put(
        f"/api/v1/appointments/{appointment_id}",
        headers=headers,
        json={"status": "COMPLETED"},
    ).status_code == 405
    assert "doctor_notes" not in appointment.json()

    invalid_reschedule = client.put(
        f"/api/v1/appointments/{appointment_id}/reschedule",
        headers=headers,
        json={
            "scheduled_start": "2035-01-01T10:00:00Z",
            "reason": "Trying a time outside the schedule.",
        },
    )
    still_unchanged = client.get(
        f"/api/v1/appointments/{appointment_id}",
        headers=headers,
    )
    assert invalid_reschedule.status_code == 422
    assert still_unchanged.json()["scheduled_start"] == original_start

    rescheduled = client.put(
        f"/api/v1/appointments/{appointment_id}/reschedule",
        headers=headers,
        json={
            "scheduled_start": slots[1]["scheduled_start"],
            "reason": "Schedule changed for work.",
        },
    )
    assert rescheduled.status_code == 200, rescheduled.text
    assert rescheduled.json()["scheduled_start"] == slots[1]["scheduled_start"]
    assert rescheduled.json()["audit_events"][-1]["action"] == "RESCHEDULED"

    cancelled = client.post(
        f"/api/v1/appointments/{appointment_id}/cancel",
        headers=headers,
        json={"reason": "I no longer need this appointment."},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "CANCELLED"
    assert cancelled.json()["cancellation_reason"] == (
        "I no longer need this appointment."
    )
    assert slots[1]["scheduled_start"] in {
        slot["scheduled_start"]
        for slot in get_slots(
            client,
            doctor_id=doctor["profile"]["id"],
            requested_date=requested_date,
        )
    }


def test_availability_overlap_and_exception_handling(
    client: TestClient,
    patient_account: dict[str, object],
    approved_appointment_doctor: dict[str, object],
) -> None:
    doctor = approved_appointment_doctor
    requested_date = create_weekly_availability(client, doctor)
    overlap = client.post(
        "/api/v1/doctor/availability",
        headers=doctor["headers"],
        json={
            "weekday": local_now().date().weekday(),
            "start_time": "11:00:00",
            "end_time": "13:00:00",
            "appointment_duration_minutes": 30,
        },
    )
    blocked = client.post(
        "/api/v1/doctor/availability/exceptions",
        headers=doctor["headers"],
        json={
            "exception_date": requested_date,
            "reason": "Clinic closed.",
        },
    )
    patient_write = client.post(
        "/api/v1/doctor/availability",
        headers={"Authorization": f"Bearer {patient_account['token']}"},
        json={
            "weekday": 0,
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "appointment_duration_minutes": 30,
        },
    )
    slots = get_slots(
        client,
        doctor_id=doctor["profile"]["id"],
        requested_date=requested_date,
    )

    assert overlap.status_code == 409
    assert blocked.status_code == 201, blocked.text
    assert patient_write.status_code == 403
    assert slots == []


def test_admin_appointment_inspection_is_role_protected(
    client: TestClient,
    patient_account: dict[str, object],
    approved_appointment_doctor: dict[str, object],
    appointment_admin: dict[str, object],
) -> None:
    patient_headers = {"Authorization": f"Bearer {patient_account['token']}"}
    doctor_headers = approved_appointment_doctor["headers"]
    admin_headers = {"Authorization": f"Bearer {appointment_admin['token']}"}
    for headers in (patient_headers, doctor_headers):
        assert client.get("/api/v1/admin/appointments", headers=headers).status_code == 403
    assert client.get(
        "/api/v1/admin/appointments",
        headers=admin_headers,
    ).status_code == 200
