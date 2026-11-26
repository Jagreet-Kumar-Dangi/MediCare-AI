from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.services.medical_record_storage import (
    InvalidPrivateFileUpload,
    PrivateFileUploadTooLarge,
    StoredPrivateFile,
    get_stored_file_path,
    stage_stored_file_for_deletion,
    store_uploaded_file,
)


def store_doctor_credential_file(upload: UploadFile) -> StoredPrivateFile:
    return store_uploaded_file(
        upload,
        storage_directory=settings.doctor_credentials_storage_dir,
        max_upload_size_mb=settings.doctor_credentials_max_upload_size_mb,
    )


def get_doctor_credential_file_path(
    storage_key: str,
    *,
    must_exist: bool = True,
) -> Path:
    return get_stored_file_path(
        storage_key,
        must_exist=must_exist,
        storage_directory=settings.doctor_credentials_storage_dir,
    )


def stage_doctor_credential_file_for_deletion(
    storage_key: str,
) -> tuple[Path, Path] | None:
    return stage_stored_file_for_deletion(
        storage_key,
        storage_directory=settings.doctor_credentials_storage_dir,
    )


__all__ = [
    "InvalidPrivateFileUpload",
    "PrivateFileUploadTooLarge",
    "get_doctor_credential_file_path",
    "stage_doctor_credential_file_for_deletion",
    "store_doctor_credential_file",
]
