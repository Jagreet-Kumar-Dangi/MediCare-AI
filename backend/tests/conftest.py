from collections.abc import Generator
import re
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (
    Appointment,
    AppointmentAuditEvent,
    DoctorCredential,
    DoctorCredentialReviewEvent,
    DoctorAvailability,
    DoctorAvailabilityException,
    DoctorProfile,
    DoctorVerificationEvent,
    EmailVerificationChallenge,
    EmailVerificationRateLimit,
    MedicalRecord,
    Notification,
    NotificationJob,
    NotificationPreference,
    PatientProfile,
    RevokedToken,
    User,
)


@pytest.fixture
def test_engine(tmp_path: Path) -> Generator[Engine, None, None]:
    database_path = tmp_path.parent / f"{tmp_path.name}-{uuid4().hex}.sqlite"
    engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(database_path)),
        connect_args={"check_same_thread": False},
    )
    expected_tables = {
        model.__tablename__
        for model in (
            User,
            Appointment,
            AppointmentAuditEvent,
            PatientProfile,
            DoctorProfile,
            DoctorAvailability,
            DoctorAvailabilityException,
            DoctorCredential,
            DoctorCredentialReviewEvent,
            DoctorVerificationEvent,
            RevokedToken,
            MedicalRecord,
            Notification,
            NotificationJob,
            NotificationPreference,
        )
    }
    Base.metadata.create_all(engine)
    assert expected_tables <= Base.metadata.tables.keys()
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()
    database_path.unlink(missing_ok=True)


@pytest.fixture
def verification_mailbox(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    from app.core.config import settings

    monkeypatch.setattr(settings, "smtp_host", "smtp.gmail.com")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_username", "test-sender@example.com")
    monkeypatch.setattr(settings, "smtp_password", "test-app-password")
    monkeypatch.setattr(settings, "smtp_from_email", "test-sender@example.com")
    monkeypatch.setattr(settings, "smtp_use_tls", True)
    monkeypatch.setattr(settings, "smtp_use_ssl", False)
    codes: dict[str, str] = {}

    def capture_email(recipient: str, rendered: object) -> None:
        message = getattr(rendered, "text")
        match = re.search(r"(?<!\d)\d{6}(?!\d)", message)
        assert match is not None
        codes[recipient] = match.group()

    monkeypatch.setattr(
        "app.services.email_verification.send_email",
        capture_email,
    )
    return codes


@pytest.fixture
def client(
    test_engine: Engine,
    verification_mailbox: dict[str, str],
) -> Generator[TestClient, None, None]:
    test_session_factory = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    def override_get_db() -> Generator:
        with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.test_verification_codes = verification_mailbox
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        del app.state.test_verification_codes


def verify_test_email(client: TestClient, email: str) -> None:
    code = client.app.state.test_verification_codes[email]
    response = client.post(
        "/api/v1/auth/verify-email/confirm",
        json={"email": email, "code": code},
    )
    assert response.status_code == 200


@pytest.fixture
def patient_account(client: TestClient) -> dict[str, object]:
    registration = client.post(
        "/api/v1/auth/register/patient",
        json={
            "email": "patient@example.com",
            "password": "a-strong-password-123",
            "first_name": "Avery",
            "last_name": "Patient",
        },
    )
    assert registration.status_code == 201
    verify_test_email(client, "patient@example.com")
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "patient@example.com",
            "password": "a-strong-password-123",
        },
    )
    assert login.status_code == 200
    current_user = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert current_user.status_code == 200
    return {"user": current_user.json(), "token": login.json()["access_token"]}
