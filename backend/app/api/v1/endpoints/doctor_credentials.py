import logging
import os
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.config import settings
from app.core.doctor_credentials import (
    DoctorCredentialStatus,
    DoctorCredentialType,
)
from app.db.session import get_db
from app.models import DoctorCredential, DoctorProfile, User, UserRole
from app.schemas.doctor_credential import (
    DoctorCredentialListResponse,
    DoctorCredentialResponse,
)
from app.services.doctor_credential_service import (
    get_doctor_profile_for_user,
    is_directory_eligible,
)
from app.services.doctor_credential_storage import (
    InvalidPrivateFileUpload,
    PrivateFileUploadTooLarge,
    get_doctor_credential_file_path,
    stage_doctor_credential_file_for_deletion,
    store_doctor_credential_file,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/doctor-credentials", tags=["doctor credentials"])
_require_doctor = require_role(UserRole.DOCTOR)


def _get_owned_credential(
    db: Session,
    *,
    doctor_profile_id: int,
    credential_id: int,
) -> DoctorCredential:
    credential = db.scalar(
        select(DoctorCredential).where(
            DoctorCredential.id == credential_id,
            DoctorCredential.doctor_profile_id == doctor_profile_id,
        )
    )
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor credential not found.",
        )
    return credential


def _current_doctor_profile(db: Session, user_id: int) -> DoctorProfile:
    try:
        return get_doctor_profile_for_user(db, user_id)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found.",
        ) from None


def _cleanup_uploaded_file(storage_key: str) -> None:
    try:
        get_doctor_credential_file_path(storage_key).unlink()
    except FileNotFoundError:
        pass
    except OSError:
        logger.exception("Could not remove an uncommitted doctor credential file.")


@router.post(
    "",
    response_model=DoctorCredentialResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_doctor_credential(
    document_type: Annotated[DoctorCredentialType, Form()],
    file: Annotated[UploadFile, File()],
    current_user: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> DoctorCredential:
    doctor_profile = _current_doctor_profile(db, current_user.id)

    if document_type != DoctorCredentialType.ADDITIONAL_QUALIFICATION_CERTIFICATE:
        active_credential = db.scalar(
            select(DoctorCredential.id).where(
                DoctorCredential.doctor_profile_id == doctor_profile.id,
                DoctorCredential.document_type == document_type.value,
                DoctorCredential.verification_status.in_(
                    [
                        DoctorCredentialStatus.PENDING.value,
                        DoctorCredentialStatus.APPROVED.value,
                    ]
                ),
            )
        )
        if active_credential is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A pending or approved credential of this type already exists. "
                    "Rejected credentials may be resubmitted."
                ),
            )

    try:
        stored_file = store_doctor_credential_file(file)
    except PrivateFileUploadTooLarge as error:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(error),
        ) from None
    except InvalidPrivateFileUpload as error:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(error),
        ) from None

    credential = DoctorCredential(
        doctor_profile_id=doctor_profile.id,
        document_type=document_type.value,
        original_filename=stored_file.original_filename,
        storage_key=stored_file.storage_key,
        mime_type=stored_file.mime_type,
        file_size=stored_file.file_size,
        verification_status=DoctorCredentialStatus.PENDING.value,
    )
    db.add(credential)
    try:
        db.flush()
        db.commit()
        db.refresh(credential)
    except IntegrityError:
        db.rollback()
        _cleanup_uploaded_file(stored_file.storage_key)
        active_credential = db.scalar(
            select(DoctorCredential.id).where(
                DoctorCredential.doctor_profile_id == doctor_profile.id,
                DoctorCredential.document_type == document_type.value,
                DoctorCredential.verification_status.in_(
                    [
                        DoctorCredentialStatus.PENDING.value,
                        DoctorCredentialStatus.APPROVED.value,
                    ]
                ),
            )
        )
        if active_credential is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A pending or approved credential of this type already exists. "
                    "Rejected credentials may be resubmitted."
                ),
            ) from None
        logger.exception("Could not save doctor credential metadata.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Doctor credential could not be saved.",
        ) from None
    except SQLAlchemyError:
        db.rollback()
        _cleanup_uploaded_file(stored_file.storage_key)
        logger.exception("Could not save doctor credential metadata.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Doctor credential could not be saved.",
        ) from None
    return credential


@router.get("/me", response_model=DoctorCredentialListResponse)
def list_my_doctor_credentials(
    current_user: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> DoctorCredentialListResponse:
    doctor_profile = _current_doctor_profile(db, current_user.id)

    credentials = db.scalars(
        select(DoctorCredential)
        .where(DoctorCredential.doctor_profile_id == doctor_profile.id)
        .order_by(DoctorCredential.submitted_at.desc(), DoctorCredential.id.desc())
    )
    return DoctorCredentialListResponse(
        credentials=list(credentials),
        required_document_types=settings.required_doctor_credential_types,
        directory_eligible=is_directory_eligible(
            db,
            user=current_user,
            doctor_profile=doctor_profile,
        ),
    )


@router.get("/{credential_id}/download")
def download_my_doctor_credential(
    credential_id: int,
    current_user: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> FileResponse:
    doctor_profile = _current_doctor_profile(db, current_user.id)
    credential = _get_owned_credential(
        db,
        doctor_profile_id=doctor_profile.id,
        credential_id=credential_id,
    )
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


@router.get("/{credential_id}", response_model=DoctorCredentialResponse)
def get_my_doctor_credential(
    credential_id: int,
    current_user: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> DoctorCredential:
    doctor_profile = _current_doctor_profile(db, current_user.id)
    return _get_owned_credential(
        db,
        doctor_profile_id=doctor_profile.id,
        credential_id=credential_id,
    )


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pending_doctor_credential(
    credential_id: int,
    current_user: User = Depends(_require_doctor),
    db: Session = Depends(get_db),
) -> Response:
    doctor_profile = _current_doctor_profile(db, current_user.id)
    credential = _get_owned_credential(
        db,
        doctor_profile_id=doctor_profile.id,
        credential_id=credential_id,
    )
    if credential.verification_status != DoctorCredentialStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending credentials can be deleted.",
        )

    try:
        staged_file = stage_doctor_credential_file_for_deletion(
            credential.storage_key
        )
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Doctor credential could not be deleted safely.",
        ) from None

    db.delete(credential)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        if staged_file is not None:
            original_path, staged_path = staged_file
            try:
                os.replace(staged_path, original_path)
            except OSError:
                logger.exception(
                    "Could not restore a doctor credential after failed deletion."
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Doctor credential could not be deleted safely.",
                ) from None
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Doctor credential could not be deleted.",
        ) from None

    if staged_file is not None:
        _, staged_path = staged_file
        try:
            staged_path.unlink()
        except OSError:
            logger.exception("Could not remove deleted doctor credential file.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Credential metadata was removed, but its stored file "
                    "could not be deleted."
                ),
            ) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
