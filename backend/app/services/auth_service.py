from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import DoctorProfile, PatientProfile, User, UserRole


class EmailAlreadyRegisteredError(Exception):
    pass


class DoctorRegistrationNumberAlreadyUsedError(Exception):
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


def register_doctor(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    specialization: str,
    qualification: str,
    medical_registration_number: str,
    years_of_experience: int,
    phone_number: str | None = None,
    clinic_or_hospital: str | None = None,
    consultation_fee: Decimal | None = None,
    biography: str | None = None,
) -> User:
    return _register_user(
        db,
        email=email,
        password=password,
        role=UserRole.DOCTOR,
        doctor_profile=DoctorProfile(
            full_name=full_name,
            specialization=specialization,
            qualification=qualification,
            medical_registration_number=medical_registration_number,
            years_of_experience=years_of_experience,
            phone_number=phone_number,
            clinic_or_hospital=clinic_or_hospital,
            consultation_fee=consultation_fee,
            biography=biography,
        ),
    )


def _register_user(
    db: Session,
    *,
    email: str,
    password: str,
    role: UserRole,
    first_name: str | None = None,
    last_name: str | None = None,
    doctor_profile: DoctorProfile | None = None,
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
    elif role == UserRole.DOCTOR:
        if doctor_profile is None:
            raise ValueError("Doctor registrations require a profile.")
        user.doctor_profile = doctor_profile

    try:
        db.add(user)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if db.scalar(select(User.id).where(User.email == normalized_email)) is not None:
            raise EmailAlreadyRegisteredError from error
        if (
            doctor_profile is not None
            and db.scalar(
                select(DoctorProfile.id).where(
                    DoctorProfile.medical_registration_number
                    == doctor_profile.medical_registration_number
                )
            )
            is not None
        ):
            raise DoctorRegistrationNumberAlreadyUsedError from error
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
