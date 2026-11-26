import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_role
from app.core.doctor_credentials import (
    DoctorCredentialReviewAction,
    DoctorCredentialStatus,
)
from app.db.session import get_db
from app.models import (
    DoctorCredential,
    DoctorCredentialReviewEvent,
    DoctorProfile,
    User,
    UserRole,
)
from app.schemas.doctor_credential import (
    AdminDoctorCredentialDetail,
    DoctorCredentialRejectionRequest,
)
from app.services.doctor_credential_storage import get_doctor_credential_file_path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/doctor-credentials", tags=["admin"])
_require_admin = require_role(UserRole.ADMIN)


def _credential_detail_statement():
    return select(DoctorCredential).options(
        selectinload(DoctorCredential.doctor_profile).selectinload(
            DoctorProfile.user
        ),
        selectinload(DoctorCredential.review_events),
    )


def _load_credential(db: Session, credential_id: int) -> DoctorCredential:
    credential = db.scalar(
        _credential_detail_statement().where(
            DoctorCredential.id == credential_id
        )
    )
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor credential not found.",
        )
    return credential


def _transition_credential(
    db: Session,
    *,
    admin: User,
    credential_id: int,
    action: DoctorCredentialReviewAction,
    reason: str | None,
) -> DoctorCredential:
    credential = db.scalar(
        select(DoctorCredential)
        .where(DoctorCredential.id == credential_id)
        .with_for_update()
    )
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor credential not found.",
        )
    if credential.verification_status != DoctorCredentialStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending credentials can be reviewed.",
        )

    now = datetime.now(timezone.utc)
    credential.verification_status = action.value
    credential.reviewed_by = admin.id
    credential.reviewed_at = now
    credential.rejection_reason = (
        reason if action == DoctorCredentialReviewAction.REJECTED else None
    )
    db.add(
        DoctorCredentialReviewEvent(
            credential_id=credential.id,
            admin_user_id=admin.id,
            action=action.value,
            reason=reason,
            created_at=now,
        )
    )
    db.commit()
    logger.info(
        "Doctor credential decision: credential_id=%s admin_user_id=%s action=%s",
        credential.id,
        admin.id,
        action.value,
    )
    return _load_credential(db, credential.id)


@router.get("", response_model=list[AdminDoctorCredentialDetail])
def list_doctor_credentials(
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
    verification_status: DoctorCredentialStatus | None = Query(
        default=DoctorCredentialStatus.PENDING,
        alias="status",
    ),
    doctor_profile_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[DoctorCredential]:
    del current_admin
    statement = _credential_detail_statement()
    if verification_status is not None:
        statement = statement.where(
            DoctorCredential.verification_status == verification_status.value
        )
    if doctor_profile_id is not None:
        statement = statement.where(
            DoctorCredential.doctor_profile_id == doctor_profile_id
        )
    credentials = db.scalars(
        statement.order_by(
            DoctorCredential.submitted_at,
            DoctorCredential.id,
        )
        .limit(limit)
        .offset(offset)
    )
    return list(credentials)


@router.get(
    "/{credential_id}/download",
    response_class=FileResponse,
)
def download_doctor_credential_for_admin(
    credential_id: int,
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> FileResponse:
    del current_admin
    credential = _load_credential(db, credential_id)
    try:
        file_path = get_doctor_credential_file_path(credential.storage_key)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor credential file not found.",
        ) from None

    return FileResponse(
        path=file_path,
        media_type=credential.mime_type,
        filename=credential.original_filename,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/{credential_id}",
    response_model=AdminDoctorCredentialDetail,
)
def get_doctor_credential_for_admin(
    credential_id: int,
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> DoctorCredential:
    del current_admin
    return _load_credential(db, credential_id)


@router.post(
    "/{credential_id}/approve",
    response_model=AdminDoctorCredentialDetail,
)
def approve_doctor_credential(
    credential_id: int,
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> DoctorCredential:
    return _transition_credential(
        db,
        admin=current_admin,
        credential_id=credential_id,
        action=DoctorCredentialReviewAction.APPROVED,
        reason=None,
    )


@router.post(
    "/{credential_id}/reject",
    response_model=AdminDoctorCredentialDetail,
)
def reject_doctor_credential(
    credential_id: int,
    request: DoctorCredentialRejectionRequest,
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> DoctorCredential:
    return _transition_credential(
        db,
        admin=current_admin,
        credential_id=credential_id,
        action=DoctorCredentialReviewAction.REJECTED,
        reason=request.reason,
    )
