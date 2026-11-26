from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from pydantic import BaseModel

from app.core.config import settings

_password_hasher = PasswordHasher()
_JWT_ALGORITHM = "HS256"


class AccessTokenClaims(BaseModel):
    user_id: int
    token_id: UUID
    expires_at: datetime


def hash_password(password: str) -> str:
    """Return an Argon2id password hash."""
    if not password:
        raise ValueError("Password must not be empty.")
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Compare a password with a hash produced by ``hash_password``."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, TypeError):
        return False


def create_access_token(user_id: int) -> str:
    if user_id < 1:
        raise ValueError("User ID must be positive.")

    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "jti": str(uuid4()),
        "iat": issued_at,
        "exp": expires_at,
        "type": "access",
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=_JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> AccessTokenClaims | None:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[_JWT_ALGORITHM],
            options={"require": ["exp", "iat", "jti", "sub", "type"]},
        )
        if payload.get("type") != "access":
            return None

        subject = payload.get("sub")
        if not isinstance(subject, str):
            return None

        user_id = int(subject)
        if user_id < 1:
            return None

        return AccessTokenClaims(
            user_id=user_id,
            token_id=UUID(payload["jti"]),
            expires_at=datetime.fromtimestamp(payload["exp"], timezone.utc),
        )
    except (
        jwt.PyJWTError,
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
    ):
        return None
