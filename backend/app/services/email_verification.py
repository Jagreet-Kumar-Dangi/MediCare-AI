import hashlib
import hmac
import logging
import secrets
import smtplib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    EmailVerificationChallenge,
    EmailVerificationRateLimit,
    User,
    UserRole,
)
from app.services.email_notifications import RenderedEmail, send_email

logger = logging.getLogger(__name__)

OTP_LIFETIME = timedelta(minutes=5)
RESEND_COOLDOWN = timedelta(seconds=60)
MAX_ATTEMPTS = 5
EMAIL_REQUESTS_PER_HOUR = 5
IP_REQUESTS_PER_HOUR = 20
RATE_LIMIT_WINDOW = timedelta(hours=1)
RATE_LIMIT_RETENTION = timedelta(days=1)


class VerificationRequestOutcome(str, Enum):
    SENT = "sent"
    SUPPRESSED = "suppressed"
    COOLDOWN = "cooldown"
    THROTTLED = "throttled"


class EmailDeliveryError(Exception):
    pass


class InvalidVerificationCodeError(Exception):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _identifier_hash(kind: str, value: str) -> str:
    key = settings.jwt_secret_key.get_secret_value().encode("utf-8")
    payload = f"email-verification:{kind}:{value}".encode("utf-8")
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def _otp_hash(challenge_id: int, email: str, code: str) -> str:
    key = settings.jwt_secret_key.get_secret_value().encode("utf-8")
    payload = f"email-otp:{challenge_id}:{email}:{code}".encode("utf-8")
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def _smtp_is_ready() -> bool:
    return bool(
        settings.smtp_host
        and settings.smtp_host.strip().lower() == "smtp.gmail.com"
        and settings.smtp_port == 587
        and settings.smtp_use_tls
        and not settings.smtp_use_ssl
        and settings.smtp_username
        and settings.smtp_password
        and settings.smtp_from_email
    )


def _verification_email(code: str) -> RenderedEmail:
    return RenderedEmail(
        subject="Verify your MediCare AI email address",
        text=(
            "MediCare AI email verification\n\n"
            f"Your six-digit verification code is {code}.\n"
            "This code expires in five minutes. Do not share it with anyone.\n"
            "If you did not request this registration, you can ignore this message."
        ),
        html=(
            "<!doctype html><html><body>"
            '<main style="font-family:Arial,sans-serif;max-width:560px;margin:24px auto;'
            'padding:24px;color:#17233b;border:1px solid #dce5ef;border-radius:12px">'
            '<p style="color:#176b82;font-weight:bold">MediCare AI</p>'
            "<h1 style=\"font-size:22px\">Verify your email address</h1>"
            "<p>Use this six-digit code to verify your email address:</p>"
            '<p style="font-size:30px;font-weight:bold;letter-spacing:8px">'
            f"{code}</p>"
            "<p>This code expires in five minutes. Do not share it with anyone.</p>"
            "<p>If you did not request this registration, you can ignore this message.</p>"
            "</main></body></html>"
        ),
    )


@dataclass(frozen=True)
class _RateLimitDecision:
    email_hash: str
    ip_hash: str
    allowed: bool


def _check_rate_limit(
    db: Session,
    *,
    email: str,
    ip_address: str,
    now: datetime,
) -> _RateLimitDecision:
    email_hash = _identifier_hash("email", email)
    ip_hash = _identifier_hash("ip", ip_address)
    window_start = now - RATE_LIMIT_WINDOW
    db.execute(
        delete(EmailVerificationRateLimit).where(
            EmailVerificationRateLimit.requested_at < now - RATE_LIMIT_RETENTION
        )
    )
    email_count = db.scalar(
        select(func.count())
        .select_from(EmailVerificationRateLimit)
        .where(
            EmailVerificationRateLimit.email_hash == email_hash,
            EmailVerificationRateLimit.requested_at >= window_start,
        )
    ) or 0
    ip_count = db.scalar(
        select(func.count())
        .select_from(EmailVerificationRateLimit)
        .where(
            EmailVerificationRateLimit.ip_hash == ip_hash,
            EmailVerificationRateLimit.requested_at >= window_start,
        )
    ) or 0
    return _RateLimitDecision(
        email_hash=email_hash,
        ip_hash=ip_hash,
        allowed=(
            email_count < EMAIL_REQUESTS_PER_HOUR
            and ip_count < IP_REQUESTS_PER_HOUR
        ),
    )


def _lock_rate_identifiers(
    db: Session,
    *,
    email_hash: str,
    ip_hash: str,
) -> None:
    if db.get_bind().dialect.name != "postgresql":
        return
    lock_keys = sorted(
        int.from_bytes(bytes.fromhex(value[:16]), "big", signed=True)
        for value in (email_hash, ip_hash)
    )
    for lock_key in lock_keys:
        db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": lock_key},
        )


def request_email_verification(
    db: Session,
    *,
    email: str,
    ip_address: str,
) -> VerificationRequestOutcome:
    normalized_email = email.strip().lower()
    now = _utcnow()
    user = db.scalar(
        select(User)
        .where(User.email == normalized_email)
        .with_for_update()
    )
    email_hash = _identifier_hash("email", normalized_email)
    ip_hash = _identifier_hash("ip", ip_address)
    _lock_rate_identifiers(
        db,
        email_hash=email_hash,
        ip_hash=ip_hash,
    )
    rate = _check_rate_limit(
        db,
        email=normalized_email,
        ip_address=ip_address,
        now=now,
    )
    if not rate.allowed:
        db.rollback()
        return VerificationRequestOutcome.THROTTLED

    if (
        user is None
        or user.role == UserRole.ADMIN
        or user.email_verified_at is not None
    ):
        db.add(
            EmailVerificationRateLimit(
                email_hash=rate.email_hash,
                ip_hash=rate.ip_hash,
                requested_at=now,
            )
        )
        db.commit()
        return VerificationRequestOutcome.SUPPRESSED

    challenge = db.scalar(
        select(EmailVerificationChallenge)
        .where(
            EmailVerificationChallenge.user_id == user.id,
            EmailVerificationChallenge.consumed_at.is_(None),
            EmailVerificationChallenge.superseded_at.is_(None),
        )
        .with_for_update()
    )
    if (
        challenge is not None
        and now - _as_utc(challenge.last_sent_at) < RESEND_COOLDOWN
    ):
        db.rollback()
        return VerificationRequestOutcome.COOLDOWN
    if not _smtp_is_ready():
        db.rollback()
        raise EmailDeliveryError("Verification email delivery is unavailable.")

    if challenge is not None:
        challenge.superseded_at = now

    code = f"{secrets.randbelow(1_000_000):06d}"
    new_challenge = EmailVerificationChallenge(
        user_id=user.id,
        otp_hash="",
        created_at=now,
        expires_at=now + OTP_LIFETIME,
        attempt_count=0,
        last_sent_at=now,
    )
    db.add(new_challenge)
    db.flush()
    new_challenge.otp_hash = _otp_hash(new_challenge.id, normalized_email, code)
    db.add(
        EmailVerificationRateLimit(
            email_hash=rate.email_hash,
            ip_hash=rate.ip_hash,
            requested_at=now,
        )
    )
    db.commit()

    try:
        send_email(user.email, _verification_email(code))
    except (OSError, smtplib.SMTPException, RuntimeError) as error:
        logger.error(
            "Verification email delivery failed (%s).",
            type(error).__name__,
        )
        raise EmailDeliveryError(
            "Verification email delivery is unavailable."
        ) from None
    return VerificationRequestOutcome.SENT


def verify_email_address(db: Session, *, email: str, code: str) -> None:
    normalized_email = email.strip().lower()
    now = _utcnow()
    user = db.scalar(
        select(User)
        .where(User.email == normalized_email)
        .with_for_update()
    )
    if (
        user is None
        or user.role == UserRole.ADMIN
        or user.email_verified_at is not None
    ):
        raise InvalidVerificationCodeError

    challenge = db.scalar(
        select(EmailVerificationChallenge)
        .where(
            EmailVerificationChallenge.user_id == user.id,
            EmailVerificationChallenge.consumed_at.is_(None),
            EmailVerificationChallenge.superseded_at.is_(None),
        )
        .with_for_update()
    )
    if (
        challenge is None
        or challenge.attempt_count >= MAX_ATTEMPTS
        or _as_utc(challenge.expires_at) <= now
    ):
        raise InvalidVerificationCodeError

    expected_hash = _otp_hash(challenge.id, normalized_email, code)
    if not hmac.compare_digest(challenge.otp_hash, expected_hash):
        updated = db.execute(
            update(EmailVerificationChallenge)
            .where(
                EmailVerificationChallenge.id == challenge.id,
                EmailVerificationChallenge.consumed_at.is_(None),
                EmailVerificationChallenge.superseded_at.is_(None),
                EmailVerificationChallenge.attempt_count < MAX_ATTEMPTS,
                EmailVerificationChallenge.expires_at > now,
            )
            .values(
                attempt_count=EmailVerificationChallenge.attempt_count + 1
            )
            .execution_options(synchronize_session=False)
        )
        db.commit()
        if updated.rowcount != 1:
            raise InvalidVerificationCodeError
        raise InvalidVerificationCodeError

    consumed = db.execute(
        update(EmailVerificationChallenge)
        .where(
            EmailVerificationChallenge.id == challenge.id,
            EmailVerificationChallenge.consumed_at.is_(None),
            EmailVerificationChallenge.superseded_at.is_(None),
            EmailVerificationChallenge.attempt_count < MAX_ATTEMPTS,
            EmailVerificationChallenge.expires_at > now,
        )
        .values(consumed_at=now)
        .execution_options(synchronize_session=False)
    )
    if consumed.rowcount != 1:
        db.rollback()
        raise InvalidVerificationCodeError

    user.email_verified_at = now
    if user.pending_email_verification:
        user.pending_email_verification = False
        user.is_active = True
    db.commit()
