from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import PatientProfile, User, UserRole


class EmailAlreadyRegisteredError(Exception):
    pass


def register_patient(
    db: Session,
    *,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
) -> User:
    return _register_user(
        db,
        email=email,
        password=password,
        role=UserRole.PATIENT,
        first_name=first_name,
        last_name=last_name,
    )


def register_doctor(db: Session, *, email: str, password: str) -> User:
    return _register_user(
        db,
        email=email,
        password=password,
        role=UserRole.DOCTOR,
    )


def _register_user(
    db: Session,
    *,
    email: str,
    password: str,
    role: UserRole,
    first_name: str | None = None,
    last_name: str | None = None,
) -> User:
    normalized_email = email.strip().lower()
    existing_user_id = db.scalar(
        select(User.id).where(User.email == normalized_email)
    )
    if existing_user_id is not None:
        raise EmailAlreadyRegisteredError

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        role=role,
    )
    if role == UserRole.PATIENT:
        if first_name is None or last_name is None:
            raise ValueError("Patient registrations require a profile name.")
        user.patient_profile = PatientProfile(
            first_name=first_name,
            last_name=last_name,
        )

    try:
        db.add(user)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if db.scalar(select(User.id).where(User.email == normalized_email)) is not None:
            raise EmailAlreadyRegisteredError from error
        raise

    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User | None:
    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if (
        user is None
        or not user.is_active
        or not verify_password(password, user.password_hash)
    ):
        return None
    return user
