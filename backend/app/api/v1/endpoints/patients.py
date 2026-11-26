from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models import PatientProfile, User, UserRole
from app.schemas.patient import PatientProfileResponse, PatientProfileUpdate

router = APIRouter(prefix="/patients", tags=["patients"])
_require_patient = require_role(UserRole.PATIENT)


def _get_profile(db: Session, user_id: int) -> PatientProfile:
    profile = db.scalar(
        select(PatientProfile).where(PatientProfile.user_id == user_id)
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found.",
        )
    return profile


@router.get("/me", response_model=PatientProfileResponse)
def get_my_profile(
    current_user: User = Depends(_require_patient),
    db: Session = Depends(get_db),
) -> PatientProfile:
    return _get_profile(db, current_user.id)


@router.put("/me", response_model=PatientProfileResponse)
def update_my_profile(
    profile_update: PatientProfileUpdate,
    current_user: User = Depends(_require_patient),
    db: Session = Depends(get_db),
) -> PatientProfile:
    profile = _get_profile(db, current_user.id)
    profile.first_name = profile_update.first_name
    profile.last_name = profile_update.last_name
    profile.date_of_birth = profile_update.date_of_birth
    profile.phone_number = profile_update.phone_number
    db.commit()
    db.refresh(profile)
    return profile
