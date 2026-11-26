import logging
import os
from datetime import date
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
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models import MedicalRecord, MedicalRecordCategory, User, UserRole
from app.schemas.medical_record import MedicalRecordResponse
from app.services.medical_record_storage import (
    InvalidMedicalRecordUpload,
    MedicalRecordUploadTooLarge,
    get_stored_file_path,
    stage_stored_file_for_deletion,
    store_uploaded_file,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/medical-records", tags=["medical records"])
_require_patient = require_role(UserRole.PATIENT)


def _get_owned_record(db: Session, user_id: int, record_id: int) -> MedicalRecord:
    record = db.scalar(
        select(MedicalRecord).where(
            MedicalRecord.id == record_id,
            MedicalRecord.patient_id == user_id,
        )
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found.",
        )
    return record


@router.post(
    "/upload",
    response_model=MedicalRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_medical_record(
    title: Annotated[str, Form(min_length=1, max_length=200)],
    category: Annotated[MedicalRecordCategory, Form()],
    file: Annotated[UploadFile, File()],
    current_user: User = Depends(_require_patient),
    db: Session = Depends(get_db),
    description: Annotated[str | None, Form(max_length=2000)] = None,
    report_date: Annotated[date | None, Form()] = None,
) -> MedicalRecord:
    normalized_title = title.strip()
    if not normalized_title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Title must not be blank.",
        )

    try:
        stored_file = store_uploaded_file(file)
    except MedicalRecordUploadTooLarge as error:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(error),
        ) from None
    except InvalidMedicalRecordUpload as error:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(error),
        ) from None

    record = MedicalRecord(
        patient_id=current_user.id,
        title=normalized_title,
        category=category.value,
        description=(description or "").strip() or None,
        original_filename=stored_file.original_filename,
        storage_key=stored_file.storage_key,
        mime_type=stored_file.mime_type,
        file_size=stored_file.file_size,
        report_date=report_date,
    )
    db.add(record)
    try:
        db.flush()
        db.refresh(record)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        try:
            get_stored_file_path(stored_file.storage_key).unlink()
        except FileNotFoundError:
            pass
        except OSError:
            logger.exception(
                "Could not remove a stored file after a failed record save."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Medical record could not be saved.",
        ) from None
    return record


@router.get("", response_model=list[MedicalRecordResponse])
def list_medical_records(
    current_user: User = Depends(_require_patient),
    db: Session = Depends(get_db),
) -> list[MedicalRecord]:
    records = db.scalars(
        select(MedicalRecord)
        .where(MedicalRecord.patient_id == current_user.id)
        .order_by(MedicalRecord.created_at.desc(), MedicalRecord.id.desc())
    )
    return list(records)


@router.get("/{record_id}/download")
def download_medical_record(
    record_id: int,
    current_user: User = Depends(_require_patient),
    db: Session = Depends(get_db),
) -> FileResponse:
    record = _get_owned_record(db, current_user.id, record_id)
    try:
        file_path = get_stored_file_path(record.storage_key)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record file not found.",
        ) from None

    return FileResponse(
        path=file_path,
        media_type=record.mime_type,
        filename=record.original_filename,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{record_id}", response_model=MedicalRecordResponse)
def get_medical_record(
    record_id: int,
    current_user: User = Depends(_require_patient),
    db: Session = Depends(get_db),
) -> MedicalRecord:
    return _get_owned_record(db, current_user.id, record_id)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_medical_record(
    record_id: int,
    current_user: User = Depends(_require_patient),
    db: Session = Depends(get_db),
) -> Response:
    record = _get_owned_record(db, current_user.id, record_id)
    try:
        staged_file = stage_stored_file_for_deletion(record.storage_key)
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Medical record could not be deleted safely.",
        ) from None

    db.delete(record)
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
                    "Could not restore a stored file after a failed record deletion."
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Medical record could not be deleted safely.",
                ) from None
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Medical record could not be deleted.",
        ) from None

    if staged_file is not None:
        _, staged_path = staged_file
        try:
            staged_path.unlink()
        except OSError:
            logger.exception("Could not remove a deleted medical record file.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Record was removed, but its stored file could not be deleted.",
            ) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
