from sqlalchemy import exists, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.config import settings
from app.core.doctor_credentials import DoctorCredentialStatus
from app.models import DoctorCredential, DoctorProfile, DoctorVerificationStatus, User


def get_doctor_profile_for_user(db: Session, user_id: int) -> DoctorProfile:
    profile = db.scalar(
        select(DoctorProfile).where(DoctorProfile.user_id == user_id)
    )
    if profile is None:
        raise LookupError("Doctor profile not found.")
    return profile


def required_credential_eligibility_conditions() -> list[ColumnElement[bool]]:
    return [
        exists(
            select(DoctorCredential.id).where(
                DoctorCredential.doctor_profile_id == DoctorProfile.id,
                DoctorCredential.document_type == credential_type.value,
                DoctorCredential.verification_status
                == DoctorCredentialStatus.APPROVED.value,
            )
        )
        for credential_type in settings.required_doctor_credential_types
    ]


def is_directory_eligible(
    db: Session,
    *,
    user: User,
    doctor_profile: DoctorProfile,
) -> bool:
    if (
        not user.is_active
        or doctor_profile.verification_status
        != DoctorVerificationStatus.APPROVED.value
    ):
        return False

    return all(
        db.scalar(
            select(
                exists(
                    select(DoctorCredential.id).where(
                        DoctorCredential.doctor_profile_id == doctor_profile.id,
                        DoctorCredential.document_type == credential_type.value,
                        DoctorCredential.verification_status
                        == DoctorCredentialStatus.APPROVED.value,
                    )
                )
            )
        )
        for credential_type in settings.required_doctor_credential_types
    )
