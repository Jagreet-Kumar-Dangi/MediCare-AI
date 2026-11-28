import re
import struct
import zlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

PDF_CONTENT = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


def _png_chunk(chunk_type: bytes, content: bytes) -> bytes:
    payload = chunk_type + content
    return (
        len(content).to_bytes(4, "big")
        + payload
        + (zlib.crc32(payload) & 0xFFFFFFFF).to_bytes(4, "big")
    )


PNG_CONTENT = (
    b"\x89PNG\r\n\x1a\n"
    + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0))
    + _png_chunk(b"IDAT", zlib.compress(b"\x00\x00"))
    + _png_chunk(b"IEND", b"")
)


def _jpeg_segment(marker: int, content: bytes) -> bytes:
    return (
        b"\xff"
        + bytes([marker])
        + (len(content) + 2).to_bytes(2, "big")
        + content
    )


JPEG_HUFFMAN_COUNTS = bytes([1, *([0] * 15)])
JPEG_CONTENT = (
    b"\xff\xd8"
    + _jpeg_segment(0xDB, b"\x00" + bytes([1] * 64))
    + _jpeg_segment(
        0xC0,
        bytes([8])
        + (1).to_bytes(2, "big")
        + (1).to_bytes(2, "big")
        + bytes([1, 1, 0x11, 0]),
    )
    + _jpeg_segment(
        0xC4,
        b"\x00"
        + JPEG_HUFFMAN_COUNTS
        + b"\x00"
        + b"\x10"
        + JPEG_HUFFMAN_COUNTS
        + b"\x00",
    )
    + _jpeg_segment(0xDA, b"\x01\x01\x00\x00\x3f\x00")
    + b"\x3f\xff\xd9"
)


@pytest.fixture
def medical_record_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "medical_records_storage_dir", tmp_path)
    return tmp_path


def _upload_pdf(
    client: TestClient,
    token: str,
    *,
    filename: str = "lab-report.pdf",
    content: bytes = PDF_CONTENT,
    content_type: str = "application/pdf",
) -> dict:
    response = client.post(
        "/api/v1/medical-records/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "title": "Annual blood work",
            "category": "Laboratory Report",
            "description": "Routine laboratory report",
            "report_date": "2026-03-15",
        },
        files={"file": (filename, content, content_type)},
    )
    assert response.status_code == 201
    return response.json()


def _register_patient(client: TestClient, email: str) -> str:
    registration = client.post(
        "/api/v1/auth/register/patient",
        json={
            "email": email,
            "password": "a-strong-password-123",
            "first_name": "Other",
            "last_name": "Patient",
        },
    )
    assert registration.status_code == 201
    code = client.app.state.test_verification_codes[email]
    verification = client.post(
        "/api/v1/auth/verify-email/confirm",
        json={"email": email, "code": code},
    )
    assert verification.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "a-strong-password-123",
        },
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def test_authenticated_patient_can_upload_list_and_download_own_record(
    client: TestClient,
    patient_account: dict,
    medical_record_storage: Path,
) -> None:
    record = _upload_pdf(
        client,
        patient_account["token"],
        filename=r"..\..\lab-report.pdf",
    )
    authorization = {"Authorization": f"Bearer {patient_account['token']}"}

    assert record["title"] == "Annual blood work"
    assert record["category"] == "Laboratory Report"
    assert record["original_filename"] == "lab-report.pdf"
    assert record["file_size"] == len(PDF_CONTENT)
    assert record["mime_type"] == "application/pdf"
    assert record["report_date"] == "2026-03-15"
    assert not {
        "patient_id",
        "storage_key",
        "stored_filename",
        "file_path",
    }.intersection(record)

    stored_files = list(medical_record_storage.iterdir())
    assert len(stored_files) == 1
    assert re.fullmatch(r"[0-9a-f]{32}\.pdf", stored_files[0].name)
    assert stored_files[0].read_bytes() == PDF_CONTENT

    listed = client.get("/api/v1/medical-records", headers=authorization)
    details = client.get(
        f"/api/v1/medical-records/{record['id']}",
        headers=authorization,
    )
    download = client.get(
        f"/api/v1/medical-records/{record['id']}/download",
        headers=authorization,
    )

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [record["id"]]
    assert details.status_code == 200
    assert details.json() == record
    assert download.status_code == 200
    assert download.content == PDF_CONTENT
    assert "attachment" in download.headers["content-disposition"]
    assert "Cache-Control" in download.headers
    assert str(medical_record_storage) not in download.headers["content-disposition"]


@pytest.mark.parametrize(
    ("filename", "content", "content_type"),
    [
        ("report.jpg", JPEG_CONTENT, "image/jpeg"),
        ("report.jpeg", JPEG_CONTENT, "image/jpeg"),
        ("report.png", PNG_CONTENT, "image/png"),
    ],
)
def test_upload_accepts_supported_image_content(
    client: TestClient,
    patient_account: dict,
    medical_record_storage: Path,
    filename: str,
    content: bytes,
    content_type: str,
) -> None:
    response = client.post(
        "/api/v1/medical-records/upload",
        headers={"Authorization": f"Bearer {patient_account['token']}"},
        data={"title": "Image report", "category": "Radiology"},
        files={"file": (filename, content, content_type)},
    )

    assert response.status_code == 201
    assert response.json()["mime_type"] == content_type
    assert response.json()["file_size"] == len(content)
    assert list(medical_record_storage.iterdir())[0].read_bytes() == content


def test_medical_record_endpoints_require_authentication(
    client: TestClient,
    patient_account: dict,
    medical_record_storage: Path,
) -> None:
    record = _upload_pdf(client, patient_account["token"])
    paths = [
        "/api/v1/medical-records",
        f"/api/v1/medical-records/{record['id']}",
        f"/api/v1/medical-records/{record['id']}/download",
    ]

    for path in paths:
        assert client.get(path).status_code == 401
    assert client.delete(f"/api/v1/medical-records/{record['id']}").status_code == 401
    assert (
        client.post(
            "/api/v1/medical-records/upload",
            data={"title": "Report", "category": "Other"},
            files={"file": ("report.pdf", PDF_CONTENT, "application/pdf")},
        ).status_code
        == 401
    )


def test_non_patient_role_cannot_use_medical_record_endpoints(
    client: TestClient,
    medical_record_storage: Path,
) -> None:
    registration = client.post(
        "/api/v1/auth/register/doctor",
        json={
            "email": "doctor@example.com",
            "password": "another-strong-password",
            "full_name": "Dr. Devon North",
            "specialization": "Family Medicine",
            "qualification": "MD",
            "medical_registration_number": "DOC-0004",
            "years_of_experience": 5,
        },
    )
    assert registration.status_code == 201
    code = client.app.state.test_verification_codes["doctor@example.com"]
    assert client.post(
        "/api/v1/auth/verify-email/confirm",
        json={"email": "doctor@example.com", "code": code},
    ).status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "doctor@example.com",
            "password": "another-strong-password",
        },
    )
    authorization = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert client.get("/api/v1/medical-records", headers=authorization).status_code == 403
    response = client.post(
        "/api/v1/medical-records/upload",
        headers=authorization,
        data={"title": "Report", "category": "Other"},
        files={"file": ("report.pdf", PDF_CONTENT, "application/pdf")},
    )

    assert response.status_code == 403
    assert list(medical_record_storage.iterdir()) == []


@pytest.mark.parametrize(
    ("filename", "content", "content_type"),
    [
        ("report.exe", PDF_CONTENT, "application/pdf"),
        ("report.pdf", b"not a PDF file", "application/pdf"),
        ("report.pdf", PDF_CONTENT, "image/png"),
    ],
)
def test_upload_rejects_unsupported_or_mismatched_files(
    client: TestClient,
    patient_account: dict,
    medical_record_storage: Path,
    filename: str,
    content: bytes,
    content_type: str,
) -> None:
    response = client.post(
        "/api/v1/medical-records/upload",
        headers={"Authorization": f"Bearer {patient_account['token']}"},
        data={"title": "Report", "category": "Other"},
        files={"file": (filename, content, content_type)},
    )

    assert response.status_code == 415
    assert response.json()["detail"]
    assert list(medical_record_storage.iterdir()) == []


def test_upload_rejects_files_over_configured_limit(
    client: TestClient,
    patient_account: dict,
    medical_record_storage: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "medical_records_max_upload_size_mb", 1)
    large_pdf = b"%PDF-1.4\n" + b"x" * (1024 * 1024) + b"%%EOF\n"

    response = client.post(
        "/api/v1/medical-records/upload",
        headers={"Authorization": f"Bearer {patient_account['token']}"},
        data={"title": "Large report", "category": "Other"},
        files={"file": ("large.pdf", large_pdf, "application/pdf")},
    )

    assert response.status_code == 413
    assert list(medical_record_storage.iterdir()) == []


def test_patient_cannot_access_another_patients_record(
    client: TestClient,
    patient_account: dict,
    medical_record_storage: Path,
) -> None:
    record = _upload_pdf(client, patient_account["token"])
    other_token = _register_patient(client, "other@example.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}

    assert client.get("/api/v1/medical-records", headers=other_headers).json() == []
    assert (
        client.get(
            f"/api/v1/medical-records/{record['id']}",
            headers=other_headers,
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/medical-records/{record['id']}/download",
            headers=other_headers,
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/v1/medical-records/{record['id']}",
            headers=other_headers,
        ).status_code
        == 404
    )
    assert len(client.get(
        "/api/v1/medical-records",
        headers={"Authorization": f"Bearer {patient_account['token']}"},
    ).json()) == 1
    assert len(list(medical_record_storage.iterdir())) == 1


def test_upload_uses_authenticated_patient_not_submitted_patient_id(
    client: TestClient,
    patient_account: dict,
    medical_record_storage: Path,
) -> None:
    other_token = _register_patient(client, "other@example.com")
    response = client.post(
        "/api/v1/medical-records/upload",
        headers={"Authorization": f"Bearer {other_token}"},
        data={
            "title": "Other patient's report",
            "category": "Other",
            "patient_id": str(patient_account["user"]["id"]),
        },
        files={"file": ("other.pdf", PDF_CONTENT, "application/pdf")},
    )

    assert response.status_code == 201
    own_records = client.get(
        "/api/v1/medical-records",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    victim_records = client.get(
        "/api/v1/medical-records",
        headers={"Authorization": f"Bearer {patient_account['token']}"},
    )
    assert [record["id"] for record in own_records.json()] == [
        response.json()["id"]
    ]
    assert victim_records.json() == []


def test_delete_removes_record_and_stored_file(
    client: TestClient,
    patient_account: dict,
    medical_record_storage: Path,
) -> None:
    record = _upload_pdf(client, patient_account["token"])
    stored_file = next(medical_record_storage.iterdir())
    authorization = {"Authorization": f"Bearer {patient_account['token']}"}

    response = client.delete(
        f"/api/v1/medical-records/{record['id']}",
        headers=authorization,
    )

    assert response.status_code == 204
    assert not stored_file.exists()
    assert client.get("/api/v1/medical-records", headers=authorization).json() == []
    assert (
        client.get(
            f"/api/v1/medical-records/{record['id']}",
            headers=authorization,
        ).status_code
        == 404
    )
