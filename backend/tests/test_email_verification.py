from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import smtplib
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    DoctorProfile,
    EmailVerificationChallenge,
    EmailVerificationRateLimit,
    User,
    UserRole,
)

PATIENT_REGISTRATION = {
    "email": "verified-patient@example.com",
    "password": "a-strong-password-123",
    "first_name": "Avery",
    "last_name": "Patient",
}

DOCTOR_REGISTRATION = {
    "email": "verified-doctor@example.com",
    "password": "another-strong-password",
    "full_name": "Dr. Devon North",
    "specialization": "Family Medicine",
    "qualification": "MD",
    "medical_registration_number": "DOC-OTP-0001",
    "years_of_experience": 5,
}


def register_patient(client: TestClient, email: str = "verified-patient@example.com"):
    response = client.post(
        "/api/v1/auth/register/patient",
        json={**PATIENT_REGISTRATION, "email": email},
    )
    return response


def code_for(client: TestClient, email: str) -> str:
    return client.app.state.test_verification_codes[email]


def verify(client: TestClient, email: str, code: str):
    return client.post(
        "/api/v1/auth/verify-email/confirm",
        json={"email": email, "code": code},
    )


def test_patient_registration_is_pending_until_correct_code_then_can_login(
    client: TestClient,
    test_engine: Engine,
) -> None:
    email = "verified-patient@example.com"
    response = register_patient(client, email)
    code = code_for(client, email)

    assert response.status_code == 201
    assert response.json()["is_active"] is False
    assert code not in response.text

    with Session(test_engine) as db:
        user = db.scalar(select(User).where(User.email == email))
        challenge = db.scalar(select(EmailVerificationChallenge))
        assert user is not None
        assert user.email_verified_at is None
        assert user.pending_email_verification is True
        assert challenge is not None
        assert challenge.otp_hash != code
        assert code not in challenge.otp_hash

    rejected_login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PATIENT_REGISTRATION["password"]},
    )
    confirmed = verify(client, email, code)
    accepted_login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PATIENT_REGISTRATION["password"]},
    )

    assert rejected_login.status_code == 403
    assert rejected_login.json()["detail"] == "Email verification required."
    assert confirmed.status_code == 200
    assert accepted_login.status_code == 200


def test_wrong_code_attempts_are_bounded_and_correct_code_is_one_time(
    client: TestClient,
    test_engine: Engine,
) -> None:
    email = "attempts@example.com"
    assert register_patient(client, email).status_code == 201
    code = code_for(client, email)

    for _ in range(5):
        response = verify(client, email, "000000" if code != "000000" else "000001")
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid or expired verification code."

    assert verify(client, email, code).status_code == 400
    with Session(test_engine) as db:
        challenge = db.scalar(select(EmailVerificationChallenge))
        assert challenge is not None
        assert challenge.attempt_count == 5


def test_expired_code_and_replay_are_rejected(
    client: TestClient,
    test_engine: Engine,
) -> None:
    email = "expired@example.com"
    assert register_patient(client, email).status_code == 201
    code = code_for(client, email)
    with Session(test_engine) as db:
        challenge = db.scalar(select(EmailVerificationChallenge))
        assert challenge is not None
        challenge.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        challenge.last_sent_at = datetime.now(timezone.utc) - timedelta(seconds=61)
        db.commit()

    assert verify(client, email, code).status_code == 400

    resend = client.post(
        "/api/v1/auth/verify-email/resend",
        json={"email": email},
    )
    assert resend.status_code == 202
    refreshed_code = code_for(client, email)
    assert verify(client, email, refreshed_code).status_code == 200
    assert verify(client, email, refreshed_code).status_code == 400


def test_resend_invalidates_previous_code_and_obeys_cooldown(
    client: TestClient,
    test_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import email_verification

    email = "resend@example.com"
    current_time = datetime(2026, 11, 28, tzinfo=timezone.utc)
    codes = iter((123456, 654321))
    monkeypatch.setattr(email_verification, "_utcnow", lambda: current_time)
    monkeypatch.setattr(email_verification.secrets, "randbelow", lambda _: next(codes))
    assert register_patient(client, email).status_code == 201
    old_code = code_for(client, email)

    cooldown_response = client.post(
        "/api/v1/auth/verify-email/resend",
        json={"email": email},
    )
    assert cooldown_response.status_code == 202
    assert code_for(client, email) == old_code

    current_time += timedelta(seconds=61)
    resent = client.post(
        "/api/v1/auth/verify-email/resend",
        json={"email": email},
    )
    new_code = code_for(client, email)
    assert resent.status_code == 202
    assert new_code != old_code
    assert verify(client, email, old_code).status_code == 400
    assert verify(client, email, new_code).status_code == 200

    with Session(test_engine) as db:
        challenges = list(
            db.scalars(
                select(EmailVerificationChallenge).order_by(
                    EmailVerificationChallenge.id
                )
            )
        )
        assert len(challenges) == 2
        assert challenges[0].superseded_at is not None
        assert challenges[1].consumed_at is not None


def test_doctor_email_verification_does_not_approve_doctor(
    client: TestClient,
    test_engine: Engine,
) -> None:
    registration = client.post(
        "/api/v1/auth/register/doctor",
        json=DOCTOR_REGISTRATION,
    )
    email = DOCTOR_REGISTRATION["email"]
    code = code_for(client, email)
    assert registration.status_code == 201
    assert verify(client, email, code).status_code == 200

    with Session(test_engine) as db:
        profile = db.scalar(select(DoctorProfile))
        user = db.scalar(select(User).where(User.email == email))
        assert profile is not None
        assert profile.verification_status == "PENDING"
        assert user is not None and user.is_active


def test_legacy_patient_must_verify_but_admin_cli_accounts_remain_usable(
    client: TestClient,
    test_engine: Engine,
) -> None:
    with Session(test_engine) as db:
        legacy = User(
            email="legacy@example.com",
            password_hash=hash_password("legacy-password-123"),
            role=UserRole.PATIENT,
            is_active=True,
        )
        admin = User(
            email="trusted-admin@example.com",
            password_hash=hash_password("admin-password-123"),
            role=UserRole.ADMIN,
        )
        db.add_all([legacy, admin])
        db.commit()

    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": "legacy@example.com", "password": "legacy-password-123"},
    )
    assert blocked.status_code == 403

    sent = client.post(
        "/api/v1/auth/verify-email/send",
        json={"email": "legacy@example.com"},
    )
    assert sent.status_code == 202
    code = code_for(client, "legacy@example.com")
    assert verify(client, "legacy@example.com", code).status_code == 200
    legacy_login = client.post(
        "/api/v1/auth/login",
        json={"email": "legacy@example.com", "password": "legacy-password-123"},
    )
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "trusted-admin@example.com", "password": "admin-password-123"},
    )
    assert legacy_login.status_code == 200
    assert admin_login.status_code == 200


def test_unknown_email_response_is_generic_and_rate_limited_by_email_and_ip(
    client: TestClient,
    test_engine: Engine,
) -> None:
    response = None
    for _ in range(6):
        response = client.post(
            "/api/v1/auth/verify-email/send",
            json={"email": "not-registered@example.com"},
        )
        assert response.status_code == 202
        assert "not-registered" not in response.text
    with Session(test_engine) as db:
        events = list(db.scalars(select(EmailVerificationRateLimit)))
        assert len(events) == 5

    for index in range(20):
        client.post(
            "/api/v1/auth/verify-email/send",
            json={"email": f"unique-{index}@example.com"},
        )
    with Session(test_engine) as db:
        events = list(db.scalars(select(EmailVerificationRateLimit)))
        assert len(events) == 20


def test_smtp_failure_leaves_new_account_inactive_and_logs_no_code(
    client: TestClient,
    test_engine: Engine,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import email_verification

    monkeypatch.setattr(email_verification.secrets, "randbelow", lambda _: 123456)

    def fail_smtp(*_args: object) -> None:
        raise smtplib.SMTPAuthenticationError(535, b"Authentication failed")

    monkeypatch.setattr(email_verification, "send_email", fail_smtp)
    response = register_patient(client, "smtp-failed@example.com")

    assert response.status_code == 503
    assert "123456" not in caplog.text
    assert "test-app-password" not in caplog.text
    with Session(test_engine) as db:
        user = db.scalar(
            select(User).where(User.email == "smtp-failed@example.com")
        )
        assert user is not None
        assert user.is_active is False
        assert user.email_verified_at is None
        assert user.pending_email_verification is True


def test_concurrent_verification_allows_only_one_success(
    client: TestClient,
) -> None:
    email = "concurrent-confirm@example.com"
    assert register_patient(client, email).status_code == 201
    code = code_for(client, email)
    barrier = Barrier(2)

    def submit() -> int:
        barrier.wait()
        return verify(client, email, code).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _: submit(), range(2)))

    assert sorted(statuses) == [200, 400]


def test_concurrent_resend_creates_only_one_active_code(
    client: TestClient,
    test_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import email_verification

    email = "concurrent-resend@example.com"
    assert register_patient(client, email).status_code == 201
    initial_time = datetime.now(timezone.utc)
    with Session(test_engine) as db:
        challenge = db.scalar(select(EmailVerificationChallenge))
        assert challenge is not None
        challenge.last_sent_at = initial_time - timedelta(seconds=61)
        db.commit()
    monkeypatch.setattr(
        email_verification,
        "_utcnow",
        lambda: initial_time,
    )
    barrier = Barrier(2)

    def resend() -> int:
        barrier.wait()
        return client.post(
            "/api/v1/auth/verify-email/resend",
            json={"email": email},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _: resend(), range(2)))

    assert statuses == [202, 202]
    with Session(test_engine) as db:
        challenges = list(
            db.scalars(
                select(EmailVerificationChallenge).where(
                    EmailVerificationChallenge.user_id
                    == db.scalar(select(User.id).where(User.email == email))
                )
            )
        )
        active = [
            item
            for item in challenges
            if item.consumed_at is None and item.superseded_at is None
        ]
        assert len(active) == 1


def test_registration_rejects_duplicate_and_unverified_token_is_not_usable(
    client: TestClient,
) -> None:
    email = "duplicate@example.com"
    assert register_patient(client, email).status_code == 201
    duplicate = register_patient(client, email)
    assert duplicate.status_code == 409


def test_confirmation_rejects_non_six_digit_codes(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/verify-email/confirm",
        json={"email": "someone@example.com", "code": "12345"},
    )
    assert response.status_code == 422
