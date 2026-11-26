import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.doctor_credentials import (
    DoctorCredentialStatus,
    DoctorCredentialType,
)
from app.core.security import create_access_token, hash_password
from app.models import (
    DoctorCredential,
    DoctorCredentialReviewEvent,
    User,
    UserRole,
)

PDF_CONTENT = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
DOCTOR_PASSWORD = "doctor-credential-password-2026!"


@pytest.fixture
def credential_storage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    monkeypatch.setattr(settings, "doctor_credentials_storage_dir", tmp_path)
    monkeypatch.setattr(settings, "doctor_credentials_max_upload_size_mb", 10)
    monkeypatch.setattr(
        settings,
        "required_doctor_credential_types",
        [
            DoctorCredentialType.MEDICAL_REGISTRATION_CERTIFICATE,
            DoctorCredentialType.MEDICAL_DEGREE_CERTIFICATE,
        ],
    )
    return tmp_path


@pytest.fixture
def credential_admin(test_engine: Engine) -> dict[str, object]:
    with Session(test_engine) as db:
        admin = User(
            email="credential-admin@example.com",
            password_hash=hash_password("credential-admin-password-2026!"),
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return {
            "user": admin,
            "token": create_access_token(admin.id),
        }


def register_credential_doctor(
    client: TestClient,
    *,
    email: str = "credential-doctor@example.com",
) -> tuple[dict, str]:
    registration = client.post(
        "/api/v1/auth/register/doctor",
        json={
            "email": email,
            "password": DOCTOR_PASSWORD,
            "full_name": "Dr Credential Example",
            "specialization": "Internal Medicine",
            "qualification": "MD",
            "medical_registration_number": f"REG-{email.split('@')[0]}",
            "years_of_experience": 8,
        },
    )
    assert registration.status_code == 201, registration.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": DOCTOR_PASSWORD},
    )
    assert login.status_code == 200
    profile = client.get(
        "/api/v1/doctors/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert profile.status_code == 200
    return profile.json(), login.json()["access_token"]


def upload_credential(
    client: TestClient,
    token: str,
    *,
    document_type: DoctorCredentialType = (
        DoctorCredentialType.MEDICAL_REGISTRATION_CERTIFICATE
    ),
    filename: str = "registration.pdf",
    content: bytes = PDF_CONTENT,
    content_type: str = "application/pdf",
) -> dict:
    response = client.post(
        "/api/v1/doctor-credentials",
        headers={"Authorization": f"Bearer {token}"},
        data={"document_type": document_type.value},
        files={"file": (filename, content, content_type)},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_doctor_uploads_lists_and_downloads_only_safe_private_metadata(
    client: TestClient,
    credential_storage: Path,
) -> None:
    _, token = register_credential_doctor(client)
    credential = upload_credential(
        client,
        token,
        filename=r"..\..\registration.pdf",
    )
    authorization = {"Authorization": f"Bearer {token}"}
    listed = client.get(
        "/api/v1/doctor-credentials/me",
        headers=authorization,
    )
    detail = client.get(
        f"/api/v1/doctor-credentials/{credential['id']}",
        headers=authorization,
    )
    download = client.get(
        f"/api/v1/doctor-credentials/{credential['id']}/download",
        headers=authorization,
    )

    assert credential["document_type"] == "MEDICAL_REGISTRATION_CERTIFICATE"
    assert credential["verification_status"] == "PENDING"
    assert credential["original_filename"] == "registration.pdf"
    assert "storage_key" not in credential
    assert "file_path" not in credential
    assert listed.status_code == 200
    assert listed.json()["directory_eligible"] is False
    assert listed.json()["required_document_types"] == [
        "MEDICAL_REGISTRATION_CERTIFICATE",
        "MEDICAL_DEGREE_CERTIFICATE",
    ]
    assert [item["id"] for item in listed.json()["credentials"]] == [
        credential["id"]
    ]
    assert detail.json() == credential
    assert download.status_code == 200
    assert download.content == PDF_CONTENT
    assert download.headers["cache-control"] == "no-store"
    assert download.headers["x-content-type-options"] == "nosniff"
    assert len(list(credential_storage.iterdir())) == 1
    assert re.fullmatch(r"[0-9a-f]{32}\.pdf", list(credential_storage.iterdir())[0].name)


def test_patient_and_other_doctor_cannot_access_credentials_or_admin_routes(
    client: TestClient,
    patient_account: dict[str, object],
    credential_admin: dict[str, object],
    credential_storage: Path,
) -> None:
    first_profile, doctor_token = register_credential_doctor(client)
    second_profile, second_token = register_credential_doctor(
        client,
        email="credential-doctor-b@example.com",
    )
    owned_credential = upload_credential(client, second_token)
    patient_headers = {
        "Authorization": f"Bearer {patient_account['token']}",
    }
    doctor_headers = {"Authorization": f"Bearer {doctor_token}"}
    patient_upload = client.post(
        "/api/v1/doctor-credentials",
        headers=patient_headers,
        data={"document_type": "MEDICAL_REGISTRATION_CERTIFICATE"},
        files={"file": ("file.pdf", PDF_CONTENT, "application/pdf")},
    )

    assert patient_upload.status_code == 403
    assert client.get(
        "/api/v1/doctor-credentials/me",
        headers=patient_headers,
    ).status_code == 403
    assert client.get(
        f"/api/v1/doctor-credentials/{owned_credential['id']}",
        headers=patient_headers,
    ).status_code == 403
    assert client.get(
        f"/api/v1/doctor-credentials/{owned_credential['id']}/download",
        headers=patient_headers,
    ).status_code == 403
    assert client.get(
        f"/api/v1/doctor-credentials/{owned_credential['id']}",
        headers=doctor_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/doctor-credentials/{owned_credential['id']}/download",
        headers=doctor_headers,
    ).status_code == 404

    admin_headers = {
        "Authorization": f"Bearer {credential_admin['token']}",
    }
    admin_paths = [
        ("GET", "/api/v1/admin/doctor-credentials", None),
        (
            "GET",
            f"/api/v1/admin/doctor-credentials/{owned_credential['id']}",
            None,
        ),
        (
            "GET",
            f"/api/v1/admin/doctor-credentials/{owned_credential['id']}/download",
            None,
        ),
        (
            "POST",
            f"/api/v1/admin/doctor-credentials/{owned_credential['id']}/approve",
            None,
        ),
        (
            "POST",
            f"/api/v1/admin/doctor-credentials/{owned_credential['id']}/reject",
            {"reason": "Dummy authorization test."},
        ),
    ]
    for method, path, body in admin_paths:
        for headers in (patient_headers, doctor_headers):
            assert (
                client.request(method, path, headers=headers, json=body).status_code
                == 403
            )

    self_status = client.get(
        "/api/v1/doctor-credentials/me",
        headers={"Authorization": f"Bearer {second_token}"},
    )
    assert self_status.status_code == 200
    assert self_status.json()["credentials"][0]["id"] == owned_credential["id"]
    assert second_profile["id"] != first_profile["id"]
    assert len(list(credential_storage.iterdir())) == 1


@pytest.mark.parametrize(
    ("filename", "content", "content_type"),
    [
        ("credential.exe", PDF_CONTENT, "application/pdf"),
        ("credential.pdf", b"not a PDF", "application/pdf"),
        ("credential.pdf", PDF_CONTENT, "image/png"),
    ],
)
def test_upload_rejects_invalid_extension_mime_and_signature(
    client: TestClient,
    credential_storage: Path,
    filename: str,
    content: bytes,
    content_type: str,
) -> None:
    _, token = register_credential_doctor(client)
    response = client.post(
        "/api/v1/doctor-credentials",
        headers={"Authorization": f"Bearer {token}"},
        data={"document_type": "MEDICAL_REGISTRATION_CERTIFICATE"},
        files={"file": (filename, content, content_type)},
    )

    assert response.status_code == 415
    assert response.json()["detail"]
    assert list(credential_storage.iterdir()) == []


def test_upload_rejects_over_limit_and_unknown_document_type(
    client: TestClient,
    credential_storage: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, token = register_credential_doctor(client)
    monkeypatch.setattr(settings, "doctor_credentials_max_upload_size_mb", 1)
    large_pdf = b"%PDF-1.4\n" + b"x" * (1024 * 1024) + b"%%EOF\n"
    oversized = client.post(
        "/api/v1/doctor-credentials",
        headers={"Authorization": f"Bearer {token}"},
        data={"document_type": "MEDICAL_REGISTRATION_CERTIFICATE"},
        files={"file": ("large.pdf", large_pdf, "application/pdf")},
    )
    unknown_type = client.post(
        "/api/v1/doctor-credentials",
        headers={"Authorization": f"Bearer {token}"},
        data={"document_type": "UNSUPPORTED_CERTIFICATE"},
        files={"file": ("other.pdf", PDF_CONTENT, "application/pdf")},
    )

    assert oversized.status_code == 413
    assert unknown_type.status_code == 422
    assert list(credential_storage.iterdir()) == []


def test_admin_review_download_audit_and_resubmission(
    client: TestClient,
    credential_admin: dict[str, object],
    credential_storage: Path,
    test_engine: Engine,
) -> None:
    _, doctor_token = register_credential_doctor(client)
    admin_headers = {
        "Authorization": f"Bearer {credential_admin['token']}",
    }
    doctor_headers = {"Authorization": f"Bearer {doctor_token}"}
    rejected = upload_credential(client, doctor_token)
    missing_reason = client.post(
        f"/api/v1/admin/doctor-credentials/{rejected['id']}/reject",
        headers=admin_headers,
        json={},
    )
    rejected_response = client.post(
        f"/api/v1/admin/doctor-credentials/{rejected['id']}/reject",
        headers=admin_headers,
        json={"reason": "The certificate is out of date."},
    )
    doctor_list = client.get(
        "/api/v1/doctor-credentials/me",
        headers=doctor_headers,
    )
    resubmitted = upload_credential(client, doctor_token)
    approved_response = client.post(
        f"/api/v1/admin/doctor-credentials/{resubmitted['id']}/approve",
        headers=admin_headers,
    )
    duplicate_approved = client.post(
        "/api/v1/doctor-credentials",
        headers=doctor_headers,
        data={"document_type": "MEDICAL_REGISTRATION_CERTIFICATE"},
        files={"file": ("replacement.pdf", PDF_CONTENT, "application/pdf")},
    )
    admin_detail = client.get(
        f"/api/v1/admin/doctor-credentials/{rejected['id']}",
        headers=admin_headers,
    )
    admin_download = client.get(
        f"/api/v1/admin/doctor-credentials/{rejected['id']}/download",
        headers=admin_headers,
    )
    list_pending = client.get(
        "/api/v1/admin/doctor-credentials",
        headers=admin_headers,
        params={"status": "PENDING"},
    )

    assert missing_reason.status_code == 422
    assert rejected_response.status_code == 200
    assert rejected_response.json()["verification_status"] == "REJECTED"
    assert doctor_list.status_code == 200
    assert doctor_list.json()["credentials"][0]["rejection_reason"] == (
        "The certificate is out of date."
    )
    assert approved_response.status_code == 200
    assert approved_response.json()["verification_status"] == "APPROVED"
    assert duplicate_approved.status_code == 409
    assert admin_detail.status_code == 200
    assert admin_detail.json()["reviewed_by"] == credential_admin["user"].id
    assert admin_detail.json()["review_events"][0]["admin_user_id"] == (
        credential_admin["user"].id
    )
    assert admin_detail.json()["review_events"][0]["action"] == "REJECTED"
    assert "storage_key" not in admin_detail.json()
    assert "file_path" not in admin_detail.json()
    assert admin_download.status_code == 200
    assert admin_download.content == PDF_CONTENT
    assert len(list_pending.json()) == 0
    assert len(list(credential_storage.iterdir())) == 2
    with Session(test_engine) as db:
        events = db.scalars(select(DoctorCredentialReviewEvent)).all()
        rejected_model = db.get(DoctorCredential, rejected["id"])
        approved_model = db.get(DoctorCredential, resubmitted["id"])
    assert {event.action for event in events} == {"APPROVED", "REJECTED"}
    assert rejected_model is not None
    assert approved_model is not None
    assert rejected_model.verification_status == DoctorCredentialStatus.REJECTED.value
    assert approved_model.verification_status == DoctorCredentialStatus.APPROVED.value


def test_pending_credential_deletion_removes_private_file_only_for_owner(
    client: TestClient,
    credential_storage: Path,
) -> None:
    _, first_token = register_credential_doctor(client)
    _, second_token = register_credential_doctor(
        client,
        email="credential-owner-b@example.com",
    )
    credential = upload_credential(
        client,
        first_token,
        document_type=DoctorCredentialType.ADDITIONAL_QUALIFICATION_CERTIFICATE,
    )
    stored_file = next(credential_storage.iterdir())
    second_headers = {"Authorization": f"Bearer {second_token}"}
    first_headers = {"Authorization": f"Bearer {first_token}"}

    forbidden_delete = client.delete(
        f"/api/v1/doctor-credentials/{credential['id']}",
        headers=second_headers,
    )
    deleted = client.delete(
        f"/api/v1/doctor-credentials/{credential['id']}",
        headers=first_headers,
    )

    assert forbidden_delete.status_code == 404
    assert deleted.status_code == 204
    assert not stored_file.exists()
    assert client.get(
        "/api/v1/doctor-credentials/me",
        headers=first_headers,
    ).json()["credentials"] == []


def test_directory_requires_all_configured_approved_credentials_and_active_user(
    client: TestClient,
    credential_admin: dict[str, object],
    credential_storage: Path,
    test_engine: Engine,
) -> None:
    profile, doctor_token = register_credential_doctor(client)
    doctor_headers = {"Authorization": f"Bearer {doctor_token}"}
    admin_headers = {
        "Authorization": f"Bearer {credential_admin['token']}",
    }
    client.post(
        f"/api/v1/admin/doctors/{profile['id']}/approve",
        headers=admin_headers,
    )
    assert client.get("/api/v1/doctors").json() == []

    registration = upload_credential(client, doctor_token)
    degree = upload_credential(
        client,
        doctor_token,
        document_type=DoctorCredentialType.MEDICAL_DEGREE_CERTIFICATE,
        filename="degree.pdf",
    )
    client.post(
        f"/api/v1/admin/doctor-credentials/{registration['id']}/reject",
        headers=admin_headers,
        json={"reason": "Please submit a current registration certificate."},
    )
    client.post(
        f"/api/v1/admin/doctor-credentials/{degree['id']}/approve",
        headers=admin_headers,
    )
    assert client.get("/api/v1/doctors").json() == []

    replacement = upload_credential(client, doctor_token)
    client.post(
        f"/api/v1/admin/doctor-credentials/{replacement['id']}/approve",
        headers=admin_headers,
    )
    listed = client.get("/api/v1/doctors")

    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["full_name"] == "Dr Credential Example"
    assert "email" not in listed.json()[0]
    assert "medical_registration_number" not in listed.json()[0]
    assert "verification_status" not in listed.json()[0]
    assert "credentials" not in listed.json()[0]
    doctor_credential_status = client.get(
        "/api/v1/doctor-credentials/me",
        headers=doctor_headers,
    )
    assert doctor_credential_status.json()["directory_eligible"] is True

    with Session(test_engine) as db:
        user = db.scalar(
            select(User).where(User.email == "credential-doctor@example.com")
        )
        assert user is not None
        user.is_active = False
        db.commit()
    assert client.get("/api/v1/doctors").json() == []


def test_unauthenticated_and_public_file_requests_are_rejected(
    client: TestClient,
    credential_storage: Path,
) -> None:
    _, doctor_token = register_credential_doctor(client)
    credential = upload_credential(client, doctor_token)
    unauthorized = client.get("/api/v1/doctor-credentials/me")
    public_file = client.get(f"/doctor-credentials/{credential['id']}/download")
    upload_without_auth = client.post(
        "/api/v1/doctor-credentials",
        data={"document_type": "MEDICAL_REGISTRATION_CERTIFICATE"},
        files={"file": ("file.pdf", PDF_CONTENT, "application/pdf")},
    )
    admin_list_without_auth = client.get("/api/v1/admin/doctor-credentials")

    assert unauthorized.status_code == 401
    assert public_file.status_code == 404
    assert upload_without_auth.status_code == 401
    assert admin_list_without_auth.status_code == 401
    assert len(list(credential_storage.iterdir())) == 1
