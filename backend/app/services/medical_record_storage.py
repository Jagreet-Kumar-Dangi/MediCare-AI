import os
import re
import tempfile
import uuid
import zlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from fastapi import UploadFile

from app.core.config import settings

_CHUNK_SIZE = 64 * 1024
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_STORAGE_KEY_PATTERN = re.compile(r"[0-9a-f]{32}\.(?:pdf|jpg|jpeg|png)\Z")
_MIME_TYPES_BY_EXTENSION = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


class InvalidMedicalRecordUpload(ValueError):
    pass


class MedicalRecordUploadTooLarge(ValueError):
    pass


@dataclass(frozen=True)
class StoredMedicalRecordFile:
    storage_key: str
    original_filename: str
    mime_type: str
    file_size: int


InvalidPrivateFileUpload = InvalidMedicalRecordUpload
PrivateFileUploadTooLarge = MedicalRecordUploadTooLarge
StoredPrivateFile = StoredMedicalRecordFile


def get_storage_directory(configured_directory: Path | None = None) -> Path:
    backend_dir = Path(__file__).resolve().parents[2]
    storage_setting = configured_directory or settings.medical_records_storage_dir
    configured_dir = storage_setting.expanduser()
    storage_dir = (
        configured_dir
        if configured_dir.is_absolute()
        else backend_dir / configured_dir
    ).resolve()
    frontend_dir = (backend_dir.parent / "frontend").resolve()
    try:
        storage_dir.relative_to(frontend_dir)
    except ValueError:
        pass
    else:
        raise RuntimeError(
            "Medical-record storage must not be inside the frontend directory."
        )

    storage_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(storage_dir, 0o700)
    return storage_dir


def _safe_original_filename(filename: str | None) -> str:
    if not filename:
        raise InvalidMedicalRecordUpload("A file name is required.")

    normalized_path = filename.replace("\\", "/")
    original_filename = PurePosixPath(normalized_path).name
    if (
        not original_filename
        or original_filename in {".", ".."}
        or len(original_filename) > 255
        or any(ord(character) < 32 or ord(character) == 127 for character in original_filename)
    ):
        raise InvalidMedicalRecordUpload("The supplied file name is invalid.")
    return original_filename


def _max_upload_size_bytes(max_upload_size_mb: int | None = None) -> int:
    limit_megabytes = (
        settings.medical_records_max_upload_size_mb
        if max_upload_size_mb is None
        else max_upload_size_mb
    )
    return limit_megabytes * 1024 * 1024


def _is_valid_pdf(file_obj: BinaryIO, file_size: int) -> bool:
    if file_size < 8:
        return False
    file_obj.seek(0)
    header = file_obj.read(5)
    file_obj.seek(max(0, file_size - 2048))
    trailer = file_obj.read(2048)
    return header == b"%PDF-" and b"%%EOF" in trailer


def _is_valid_jpeg(file_obj: BinaryIO, file_size: int) -> bool:
    if file_size < 4:
        return False
    file_obj.seek(0)
    if file_obj.read(2) != b"\xff\xd8":
        return False

    saw_frame = False
    saw_scan = False
    frame_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }

    while True:
        marker_start = file_obj.tell()
        if file_obj.read(1) != b"\xff":
            return False
        marker_bytes = file_obj.read(1)
        while marker_bytes == b"\xff":
            marker_bytes = file_obj.read(1)
        if not marker_bytes:
            return False
        marker = marker_bytes[0]

        if marker == 0xD9:
            return saw_frame and saw_scan and file_obj.tell() == file_size
        if marker == 0xD8 or marker == 0x00:
            return False
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            continue

        segment_length_bytes = file_obj.read(2)
        if len(segment_length_bytes) != 2:
            return False
        segment_length = int.from_bytes(segment_length_bytes, "big")
        segment_payload_length = segment_length - 2
        if segment_payload_length < 0:
            return False
        if file_obj.tell() + segment_payload_length > file_size:
            return False

        if marker in frame_markers:
            if segment_payload_length < 6:
                return False
            frame_header = file_obj.read(6)
            if len(frame_header) != 6:
                return False
            height = int.from_bytes(frame_header[1:3], "big")
            width = int.from_bytes(frame_header[3:5], "big")
            component_count = frame_header[5]
            if (
                height == 0
                or width == 0
                or component_count == 0
                or segment_payload_length != 6 + 3 * component_count
            ):
                return False
            file_obj.seek(segment_payload_length - 6, os.SEEK_CUR)
            saw_frame = True
        elif marker == 0xDA:
            component_count_bytes = file_obj.read(1)
            if len(component_count_bytes) != 1:
                return False
            component_count = component_count_bytes[0]
            if (
                component_count == 0
                or segment_payload_length != 4 + 2 * component_count
            ):
                return False
            file_obj.seek(segment_payload_length - 1, os.SEEK_CUR)
            saw_scan = True

            scan_data_size = 0
            while True:
                byte_position = file_obj.tell()
                byte = file_obj.read(1)
                if not byte:
                    return False
                if byte != b"\xff":
                    scan_data_size += 1
                    continue
                marker_bytes = file_obj.read(1)
                while marker_bytes == b"\xff":
                    marker_bytes = file_obj.read(1)
                if not marker_bytes:
                    return False
                scan_marker = marker_bytes[0]
                if scan_marker == 0x00 or 0xD0 <= scan_marker <= 0xD7:
                    scan_data_size += 2
                    continue
                if scan_data_size == 0:
                    return False
                file_obj.seek(byte_position)
                break
        else:
            file_obj.seek(segment_payload_length, os.SEEK_CUR)

        if file_obj.tell() <= marker_start:
            return False


def _is_valid_png(file_obj: BinaryIO) -> bool:
    file_obj.seek(0)
    if file_obj.read(len(_PNG_SIGNATURE)) != _PNG_SIGNATURE:
        return False

    saw_header = False
    saw_image_data = False
    while True:
        length_bytes = file_obj.read(4)
        if len(length_bytes) != 4:
            return False
        chunk_length = int.from_bytes(length_bytes, "big")
        chunk_type = file_obj.read(4)
        if len(chunk_type) != 4:
            return False
        if not saw_header and (chunk_type != b"IHDR" or chunk_length != 13):
            return False
        if chunk_type == b"IHDR":
            if saw_header:
                return False
            saw_header = True
        if chunk_type == b"IDAT":
            saw_image_data = True

        checksum = zlib.crc32(chunk_type)
        remaining = chunk_length
        while remaining:
            chunk = file_obj.read(min(remaining, _CHUNK_SIZE))
            if not chunk:
                return False
            checksum = zlib.crc32(chunk, checksum)
            remaining -= len(chunk)

        checksum_bytes = file_obj.read(4)
        if len(checksum_bytes) != 4:
            return False
        if checksum != int.from_bytes(checksum_bytes, "big"):
            return False

        if chunk_type == b"IEND":
            return (
                chunk_length == 0
                and saw_header
                and saw_image_data
                and file_obj.read(1) == b""
            )


def _validate_file_content(path: Path, extension: str, file_size: int) -> bool:
    with path.open("rb") as file_obj:
        if extension == ".pdf":
            return _is_valid_pdf(file_obj, file_size)
        if extension in {".jpg", ".jpeg"}:
            return _is_valid_jpeg(file_obj, file_size)
        if extension == ".png":
            return _is_valid_png(file_obj)
    return False


def store_uploaded_file(
    upload: UploadFile,
    *,
    storage_directory: Path | None = None,
    max_upload_size_mb: int | None = None,
) -> StoredPrivateFile:
    original_filename = _safe_original_filename(upload.filename)
    extension = PurePosixPath(original_filename).suffix.lower()
    expected_mime_type = _MIME_TYPES_BY_EXTENSION.get(extension)
    if expected_mime_type is None:
        raise InvalidMedicalRecordUpload(
            "Only PDF, JPG, JPEG, and PNG files are supported."
        )

    mime_type = (upload.content_type or "").split(";", maxsplit=1)[0].strip().lower()
    if mime_type != expected_mime_type:
        raise InvalidMedicalRecordUpload(
            "The file type does not match its file name."
        )
    max_size_bytes = _max_upload_size_bytes(max_upload_size_mb)
    if upload.size is not None and upload.size > max_size_bytes:
        raise MedicalRecordUploadTooLarge(
            "The uploaded file exceeds the configured size limit."
        )

    storage_dir = get_storage_directory(storage_directory)
    temporary_path: Path | None = None
    file_size = 0
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=".upload-",
            suffix=".tmp",
            dir=storage_dir,
            delete=False,
        ) as destination:
            temporary_path = Path(destination.name)
            if os.name != "nt":
                os.chmod(temporary_path, 0o600)
            while chunk := upload.file.read(_CHUNK_SIZE):
                file_size += len(chunk)
                if file_size > max_size_bytes:
                    raise MedicalRecordUploadTooLarge(
                        "The uploaded file exceeds the configured size limit."
                    )
                destination.write(chunk)
            destination.flush()
            os.fsync(destination.fileno())

        if file_size == 0 or not _validate_file_content(
            temporary_path,
            extension,
            file_size,
        ):
            raise InvalidMedicalRecordUpload(
                "The uploaded file content is invalid or does not match its type."
            )

        storage_key = f"{uuid.uuid4().hex}{extension}"
        final_path = storage_dir / storage_key
        os.replace(temporary_path, final_path)
        temporary_path = None
        return StoredMedicalRecordFile(
            storage_key=storage_key,
            original_filename=original_filename,
            mime_type=expected_mime_type,
            file_size=file_size,
        )
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def get_stored_file_path(
    storage_key: str,
    *,
    must_exist: bool = True,
    storage_directory: Path | None = None,
) -> Path:
    if _STORAGE_KEY_PATTERN.fullmatch(storage_key) is None:
        raise FileNotFoundError

    storage_dir = get_storage_directory(storage_directory)
    file_path = storage_dir / storage_key
    if file_path.is_symlink():
        raise FileNotFoundError
    try:
        resolved_path = file_path.resolve(strict=must_exist)
    except OSError as error:
        raise FileNotFoundError from error
    if resolved_path.parent != storage_dir:
        raise FileNotFoundError
    if must_exist and not resolved_path.is_file():
        raise FileNotFoundError
    return resolved_path


def stage_stored_file_for_deletion(
    storage_key: str,
    *,
    storage_directory: Path | None = None,
) -> tuple[Path, Path] | None:
    file_path = get_stored_file_path(
        storage_key,
        must_exist=False,
        storage_directory=storage_directory,
    )
    if not file_path.exists():
        return None
    if not file_path.is_file():
        raise FileNotFoundError

    staged_path = file_path.parent / f".deleting-{uuid.uuid4().hex}.tmp"
    os.replace(file_path, staged_path)
    return file_path, staged_path
