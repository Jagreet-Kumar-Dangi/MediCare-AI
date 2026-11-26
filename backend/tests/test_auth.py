from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


def test_patient_registration_returns_public_user_only(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register/patient",
        json={
            "email": "Patient@Example.com",
            "password": "a-strong-password-123",
            "first_name": " Avery ",
            "last_name": "Patient",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "patient@example.com"
    assert response.json()["role"] == "PATIENT"
    assert "password_hash" not in response.json()


def test_doctor_registration_is_doctor_role_and_admin_is_not_public(
    client: TestClient,
) -> None:
    doctor_response = client.post(
        "/api/v1/auth/register/doctor",
        json={
            "email": "doctor@example.com",
            "password": "another-strong-password",
            "full_name": "Dr. Devon North",
            "specialization": "Family Medicine",
            "qualification": "MD",
            "medical_registration_number": "DOC-0001",
            "years_of_experience": 5,
        },
    )
    admin_response = client.post(
        "/api/v1/auth/register/admin",
        json={
            "email": "admin@example.com",
            "password": "administrator-password",
        },
    )

    assert doctor_response.status_code == 201
    assert doctor_response.json()["role"] == "DOCTOR"
    assert "password_hash" not in doctor_response.json()
    assert admin_response.status_code == 404


def test_registration_cannot_set_an_admin_role(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register/patient",
        json={
            "email": "patient@example.com",
            "password": "a-strong-password-123",
            "first_name": "Avery",
            "last_name": "Patient",
            "role": "ADMIN",
        },
    )

    assert response.status_code == 422


def test_duplicate_email_is_case_insensitive(client: TestClient) -> None:
    first_response = client.post(
        "/api/v1/auth/register/doctor",
        json={
            "email": "Doctor@Example.com",
            "password": "another-strong-password",
            "full_name": "Dr. Devon North",
            "specialization": "Family Medicine",
            "qualification": "MD",
            "medical_registration_number": "DOC-0002",
            "years_of_experience": 5,
        },
    )
    duplicate_response = client.post(
        "/api/v1/auth/register/patient",
        json={
            "email": "doctor@example.com",
            "password": "a-strong-password-123",
            "first_name": "Avery",
            "last_name": "Patient",
        },
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409


@pytest.mark.parametrize("password", ["short", "            "])
def test_registration_rejects_weak_password(
    client: TestClient,
    password: str,
) -> None:
    response = client.post(
        "/api/v1/auth/register/patient",
        json={
            "email": "patient@example.com",
            "password": password,
            "first_name": "Avery",
            "last_name": "Patient",
        },
    )

    assert response.status_code == 422


def test_login_and_current_user(client: TestClient, patient_account: dict) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "PATIENT@example.com",
            "password": "a-strong-password-123",
        },
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert login.json()["expires_in"] == settings.access_token_expire_minutes * 60

    current_user = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert current_user.status_code == 200
    assert current_user.json()["id"] == patient_account["user"]["id"]
    assert "password_hash" not in current_user.json()


def test_login_rejects_invalid_password(
    client: TestClient,
    patient_account: dict,
) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "patient@example.com",
            "password": "not-the-correct-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_invalid_and_expired_jwts_are_rejected(
    client: TestClient,
    patient_account: dict,
) -> None:
    invalid_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not.a.valid.token"},
    )
    now = datetime.now(timezone.utc)
    expired_token = jwt.encode(
        {
            "sub": str(patient_account["user"]["id"]),
            "jti": str(uuid4()),
            "iat": now - timedelta(minutes=2),
            "exp": now - timedelta(minutes=1),
            "type": "access",
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )
    expired_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert invalid_response.status_code == 401
    assert expired_response.status_code == 401


def test_logout_revokes_the_access_token(
    client: TestClient,
    patient_account: dict,
) -> None:
    authorization = {"Authorization": f"Bearer {patient_account['token']}"}

    logout_response = client.post("/api/v1/auth/logout", headers=authorization)
    current_user_response = client.get("/api/v1/auth/me", headers=authorization)

    assert logout_response.status_code == 204
    assert current_user_response.status_code == 401
