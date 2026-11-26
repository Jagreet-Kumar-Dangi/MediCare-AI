from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.core.config import settings
from app.models import DoctorProfile, DoctorVerificationEvent, User, UserRole

DOCTOR_REGISTRATION = {
    "email": "doctor@example.com",
    "password": "a-strong-password-123",
    "full_name": "Dr. Casey Hart",
    "specialization": "Cardiology",
    "qualification": "MD, FACC",
    "medical_registration_number": "med-12345",
    "years_of_experience": 12,
    "phone_number": "+1-555-0100",
    "clinic_or_hospital": "North Clinic",
    "consultation_fee": "125.00",
    "biography": "Board-certified cardiologist.",
}


@pytest.fixture
def admin_account(test_engine: Engine) -> dict[str, object]:
    with Session(test_engine) as db:
        admin = User(
            email="admin@example.com",
            password_hash=hash_password("admin-strong-password-123"),
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return {
            "user": admin,
            "token": create_access_token(admin.id),
        }


def register_doctor(
    client: TestClient,
    *,
    email: str = "doctor@example.com",
    registration_number: str = "med-12345",
) -> tuple[dict, str]:
    payload = {
        **DOCTOR_REGISTRATION,
        "email": email,
        "medical_registration_number": registration_number,
    }
    response = client.post("/api/v1/auth/register/doctor", json=payload)
    if response.status_code != 201:
        raise AssertionError(response.text)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": DOCTOR_REGISTRATION["password"]},
    )
    assert login.status_code == 200
    return response.json(), login.json()["access_token"]


def test_doctor_registration_creates_pending_profile(
    client: TestClient,
) -> None:
    user, token = register_doctor(client)
    response = client.get(
        "/api/v1/doctors/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert user["role"] == "DOCTOR"
    assert "password_hash" not in user
    assert response.status_code == 200
    assert response.json()["verification_status"] == "PENDING"
    assert response.json()["medical_registration_number"] == "MED-12345"


def test_doctor_cannot_approve_self_or_read_pending_public_profile(
    client: TestClient,
) -> None:
    _, token = register_doctor(client)
    authorization = {"Authorization": f"Bearer {token}"}

    self_approval = client.post(
        "/api/v1/admin/doctors/1/approve",
        headers=authorization,
    )
    public_profile = client.get("/api/v1/doctors/1")

    assert self_approval.status_code == 403
    assert public_profile.status_code == 404


def test_registration_number_is_unique_case_insensitively(
    client: TestClient,
) -> None:
    _, _ = register_doctor(client)
    duplicate = client.post(
        "/api/v1/auth/register/doctor",
        json={
            **DOCTOR_REGISTRATION,
            "email": "different@example.com",
            "medical_registration_number": "MED-12345",
        },
    )

    assert duplicate.status_code == 409
    assert "registration number" in duplicate.json()["detail"].lower()


def test_doctor_registration_rejects_client_supplied_privileges_and_status(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/auth/register/doctor",
        json={
            **DOCTOR_REGISTRATION,
            "verification_status": "APPROVED",
            "role": "ADMIN",
        },
    )

    assert response.status_code == 422


def test_admin_can_review_and_approve_application_with_audit_record(
    client: TestClient,
    admin_account: dict[str, object],
    test_engine: Engine,
) -> None:
    register_doctor(client)
    authorization = {
        "Authorization": f"Bearer {admin_account['token']}",
    }
    pending = client.get(
        "/api/v1/admin/doctors/pending",
        headers=authorization,
    )
    doctor_id = pending.json()[0]["id"]
    detail = client.get(
        f"/api/v1/admin/doctors/{doctor_id}",
        headers=authorization,
    )
    approved = client.post(
        f"/api/v1/admin/doctors/{doctor_id}/approve",
        headers=authorization,
    )
    reviewed_after = client.get(
        f"/api/v1/admin/doctors/{doctor_id}",
        headers=authorization,
    )

    assert pending.status_code == 200
    assert pending.json()[0]["email"] == DOCTOR_REGISTRATION["email"]
    assert detail.status_code == 200
    assert detail.json()["medical_registration_number"] == "MED-12345"
    assert approved.status_code == 200
    assert approved.json()["verification_status"] == "APPROVED"
    assert reviewed_after.status_code == 200
    assert reviewed_after.json()["verification_events"][0]["action"] == "APPROVED"
    assert (
        reviewed_after.json()["verification_events"][0]["admin_user_id"]
        == admin_account["user"].id
    )
    with Session(test_engine) as db:
        event = db.scalar(select(DoctorVerificationEvent))
        profile = db.scalar(select(DoctorProfile))
    assert event is not None
    assert event.admin_user_id == admin_account["user"].id
    assert event.action == "APPROVED"
    assert profile is not None
    assert profile.verified_by == admin_account["user"].id


def test_patient_and_doctor_cannot_review_applications(
    client: TestClient,
    patient_account: dict[str, object],
) -> None:
    _, doctor_token = register_doctor(client)
    endpoint = "/api/v1/admin/doctors/1/approve"
    patient_response = client.post(
        endpoint,
        headers={"Authorization": f"Bearer {patient_account['token']}"},
    )
    doctor_response = client.post(
        endpoint,
        headers={"Authorization": f"Bearer {doctor_token}"},
    )

    assert patient_response.status_code == 403
    assert doctor_response.status_code == 403


def test_rejection_requires_reason_and_invalid_repeat_is_conflict(
    client: TestClient,
    admin_account: dict[str, object],
) -> None:
    register_doctor(client)
    authorization = {"Authorization": f"Bearer {admin_account['token']}"}

    missing_reason = client.post(
        "/api/v1/admin/doctors/1/reject",
        headers=authorization,
        json={},
    )
    rejected = client.post(
        "/api/v1/admin/doctors/1/reject",
        headers=authorization,
        json={"reason": "Please provide a current license document."},
    )
    repeated = client.post(
        "/api/v1/admin/doctors/1/approve",
        headers=authorization,
    )

    assert missing_reason.status_code == 422
    assert rejected.status_code == 200
    assert rejected.json()["verification_status"] == "REJECTED"
    assert rejected.json()["rejection_reason"]
    assert repeated.status_code == 409


def test_suspended_doctor_is_removed_from_public_discovery(
    client: TestClient,
    admin_account: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "doctor_credentials_storage_dir", tmp_path)
    _, doctor_token = register_doctor(client)
    authorization = {"Authorization": f"Bearer {admin_account['token']}"}
    doctor_authorization = {"Authorization": f"Bearer {doctor_token}"}
    profile = client.get(
        "/api/v1/doctors/me",
        headers=doctor_authorization,
    ).json()
    approved = client.post(
        f"/api/v1/admin/doctors/{profile['id']}/approve",
        headers=authorization,
    )
    for index, document_type in enumerate(settings.required_doctor_credential_types):
        uploaded = client.post(
            "/api/v1/doctor-credentials",
            headers=doctor_authorization,
            data={"document_type": document_type.value},
            files={
                "file": (
                    f"required-{index}.pdf",
                    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n",
                    "application/pdf",
                )
            },
        )
        assert uploaded.status_code == 201
        credential_review = client.post(
            f"/api/v1/admin/doctor-credentials/{uploaded.json()['id']}/approve",
            headers=authorization,
        )
        assert credential_review.status_code == 200
    active_directory = client.get(
        "/api/v1/admin/doctors/approved",
        headers=authorization,
    )
    publicly_discoverable = client.get("/api/v1/doctors")
    suspended = client.post(
        f"/api/v1/admin/doctors/{profile['id']}/suspend",
        headers=authorization,
        json={"reason": "Credential verification expired."},
    )
    discovery = client.get(
        "/api/v1/doctors",
        params={"specialization": "cardio", "min_experience": 5},
    )
    self_profile = client.get(
        "/api/v1/doctors/me",
        headers=doctor_authorization,
    )

    assert approved.status_code == 200
    assert suspended.status_code == 200
    assert active_directory.status_code == 200
    assert len(active_directory.json()) == 1
    assert len(publicly_discoverable.json()) == 1
    assert suspended.json()["verification_status"] == "SUSPENDED"
    assert discovery.status_code == 200
    assert discovery.json() == []
    assert self_profile.status_code == 200
    assert "verified_by" not in self_profile.json()


def test_directory_filters_approved_profiles_and_omits_private_fields(
    client: TestClient,
    admin_account: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "doctor_credentials_storage_dir", tmp_path)
    _, doctor_token = register_doctor(client)
    authorization = {"Authorization": f"Bearer {admin_account['token']}"}
    profile = client.get(
        "/api/v1/doctors/me",
        headers={"Authorization": f"Bearer {doctor_token}"},
    ).json()
    client.post(
        f"/api/v1/admin/doctors/{profile['id']}/approve",
        headers=authorization,
    )
    for index, document_type in enumerate(settings.required_doctor_credential_types):
        uploaded = client.post(
            "/api/v1/doctor-credentials",
            headers={"Authorization": f"Bearer {doctor_token}"},
            data={"document_type": document_type.value},
            files={
                "file": (
                    f"required-{index}.pdf",
                    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n",
                    "application/pdf",
                )
            },
        )
        assert uploaded.status_code == 201
        review = client.post(
            f"/api/v1/admin/doctor-credentials/{uploaded.json()['id']}/approve",
            headers=authorization,
        )
        assert review.status_code == 200

    response = client.get(
        "/api/v1/doctors",
        params={
            "specialization": "cardio",
            "min_experience": 10,
            "max_consultation_fee": "150.00",
            "search": "Casey",
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    doctor = response.json()[0]
    assert doctor["full_name"] == "Dr. Casey Hart"
    assert "email" not in doctor
    assert "phone_number" not in doctor
    assert "medical_registration_number" not in doctor
    assert "verification_status" not in doctor
