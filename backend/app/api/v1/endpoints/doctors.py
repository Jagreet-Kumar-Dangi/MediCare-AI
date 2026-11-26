from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models import (
    DoctorProfile,
    DoctorVerificationStatus,
    User,
    UserRole,
)
from app.schemas.doctor import DoctorSelfProfile, PublicDoctorProfile
from app.services.doctor_credential_service import (
    required_credential_eligibility_conditions,
)

router = APIRouter(prefix="/doctors", tags=["doctors"])
_require_doctor = require_role(UserRole.DOCTOR)


@router.get("", response_model=list[PublicDoctorProfile])
def list_approved_doctors(
    specialization: str | None = Query(default=None, max_length=120),
    min_experience: int | None = Query(default=None, ge=0, le=80),
    max_experience: int | None = Query(default=None, ge=0, le=80),
    max_consultation_fee: Decimal | None = Query(default=None, ge=0),
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[DoctorProfile]:
    if (
        min_experience is not None
        and max_experience is not None
        and min_experience > max_experience
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Minimum experience cannot exceed maximum experience.",
        )

    statement = (
        select(DoctorProfile)
        .join(DoctorProfile.user)
        .where(
            DoctorProfile.verification_status
            == DoctorVerificationStatus.APPROVED.value,
            User.is_active.is_(True),
            *required_credential_eligibility_conditions(),
        )
    )
    if specialization and specialization.strip():
        statement = statement.where(
            DoctorProfile.specialization.ilike(f"%{specialization.strip()}%")
        )
    if min_experience is not None:
        statement = statement.where(
            DoctorProfile.years_of_experience >= min_experience
        )
    if max_experience is not None:
        statement = statement.where(
            DoctorProfile.years_of_experience <= max_experience
        )
    if max_consultation_fee is not None:
        statement = statement.where(
            DoctorProfile.consultation_fee <= max_consultation_fee
        )
    if search and search.strip():
        statement = statement.where(
            or_(
                DoctorProfile.full_name.ilike(f"%{search.strip()}%"),
                DoctorProfile.specialization.ilike(f"%{search.strip()}%"),
            )
        )
    statement = (
        statement.order_by(DoctorProfile.full_name, DoctorProfile.id)
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement))


@router.get("/me", response_model=DoctorSelfProfile)
def get_my_doctor_profile(
    current_user: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> DoctorProfile:
    profile = db.scalar(
        select(DoctorProfile).where(DoctorProfile.user_id == current_user.id)
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found.",
        )
    return profile


@router.get("/{doctor_id}", response_model=PublicDoctorProfile)
def get_approved_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
) -> DoctorProfile:
    profile = db.scalar(
        select(DoctorProfile)
        .join(DoctorProfile.user)
        .where(
            DoctorProfile.id == doctor_id,
            DoctorProfile.verification_status
            == DoctorVerificationStatus.APPROVED.value,
            User.is_active.is_(True),
            *required_credential_eligibility_conditions(),
        )
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found.",
        )
    return profile
