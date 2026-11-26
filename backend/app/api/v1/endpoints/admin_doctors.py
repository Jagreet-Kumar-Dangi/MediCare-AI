import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_role
from app.db.session import get_db
from app.models import (
    DoctorProfile,
    DoctorVerificationAction,
    DoctorVerificationEvent,
    DoctorVerificationStatus,
    User,
    UserRole,
)
from app.schemas.doctor import (
    DoctorRejectionRequest,
    DoctorSelfProfile,
    DoctorSuspensionRequest,
    DoctorVerificationDetail,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/doctors", tags=["admin"])
_require_admin = require_role(UserRole.ADMIN)


def _load_profile(
    db: Session,
    doctor_id: int,
    *,
    for_update: bool = False,
) -> DoctorProfile:
    statement = (
        select(DoctorProfile)
        .options(
            selectinload(DoctorProfile.user),
            selectinload(DoctorProfile.verification_events),
        )
        .where(DoctorProfile.id == doctor_id)
    )
    if for_update:
        statement = statement.with_for_update()
    profile = db.scalar(statement)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor application not found.",
        )
    return profile


def _transition(
    db: Session,
    *,
    admin: User,
    doctor_id: int,
    allowed_status: DoctorVerificationStatus,
    new_status: DoctorVerificationStatus,
    action: DoctorVerificationAction,
    reason: str | None,
) -> DoctorProfile:
    profile = _load_profile(db, doctor_id, for_update=True)
    if profile.verification_status != allowed_status.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This doctor application is not in a state that allows this action.",
        )

    now = datetime.now(timezone.utc)
    profile.verification_status = new_status.value
    profile.verified_at = now
    profile.verified_by = admin.id
    profile.rejection_reason = (
        reason if action == DoctorVerificationAction.REJECTED else None
    )
    profile.updated_at = now
    db.add(
        DoctorVerificationEvent(
            doctor_profile_id=profile.id,
            admin_user_id=admin.id,
            action=action.value,
            reason=reason,
            created_at=now,
        )
    )
    db.commit()
    db.refresh(profile)
    logger.info(
        "Doctor verification decision: doctor_profile_id=%s admin_user_id=%s action=%s",
        profile.id,
        admin.id,
        action.value,
    )
    return profile


@router.get("/pending", response_model=list[DoctorVerificationDetail])
def list_pending_doctors(
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> list[DoctorProfile]:
    del current_admin
    profiles = db.scalars(
        select(DoctorProfile)
        .options(
            selectinload(DoctorProfile.user),
            selectinload(DoctorProfile.verification_events),
        )
        .where(
            DoctorProfile.verification_status
            == DoctorVerificationStatus.PENDING.value
        )
        .order_by(DoctorProfile.verification_submitted_at, DoctorProfile.id)
    )
    return list(profiles)


@router.get("/suspended", response_model=list[DoctorVerificationDetail])
def list_suspended_doctors(
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> list[DoctorProfile]:
    del current_admin
    profiles = db.scalars(
        select(DoctorProfile)
        .options(
            selectinload(DoctorProfile.user),
            selectinload(DoctorProfile.verification_events),
        )
        .where(
            DoctorProfile.verification_status
            == DoctorVerificationStatus.SUSPENDED.value
        )
        .order_by(DoctorProfile.updated_at.desc(), DoctorProfile.id)
    )
    return list(profiles)


@router.get("/approved", response_model=list[DoctorVerificationDetail])
def list_approved_doctors_for_admin(
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> list[DoctorProfile]:
    del current_admin
    profiles = db.scalars(
        select(DoctorProfile)
        .options(selectinload(DoctorProfile.user))
        .where(
            DoctorProfile.verification_status
            == DoctorVerificationStatus.APPROVED.value
        )
        .order_by(DoctorProfile.updated_at.desc(), DoctorProfile.id)
    )
    return list(profiles)


@router.get("/{doctor_id}", response_model=DoctorVerificationDetail)
def get_doctor_application(
    doctor_id: int,
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> DoctorProfile:
    del current_admin
    return _load_profile(db, doctor_id)


@router.post("/{doctor_id}/approve", response_model=DoctorSelfProfile)
def approve_doctor_application(
    doctor_id: int,
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> DoctorProfile:
    return _transition(
        db,
        admin=current_admin,
        doctor_id=doctor_id,
        allowed_status=DoctorVerificationStatus.PENDING,
        new_status=DoctorVerificationStatus.APPROVED,
        action=DoctorVerificationAction.APPROVED,
        reason=None,
    )


@router.post("/{doctor_id}/reject", response_model=DoctorSelfProfile)
def reject_doctor_application(
    doctor_id: int,
    request: DoctorRejectionRequest,
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> DoctorProfile:
    return _transition(
        db,
        admin=current_admin,
        doctor_id=doctor_id,
        allowed_status=DoctorVerificationStatus.PENDING,
        new_status=DoctorVerificationStatus.REJECTED,
        action=DoctorVerificationAction.REJECTED,
        reason=request.reason,
    )


@router.post("/{doctor_id}/suspend", response_model=DoctorSelfProfile)
def suspend_doctor(
    doctor_id: int,
    request: DoctorSuspensionRequest,
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> DoctorProfile:
    return _transition(
        db,
        admin=current_admin,
        doctor_id=doctor_id,
        allowed_status=DoctorVerificationStatus.APPROVED,
        new_status=DoctorVerificationStatus.SUSPENDED,
        action=DoctorVerificationAction.SUSPENDED,
        reason=request.reason,
    )
