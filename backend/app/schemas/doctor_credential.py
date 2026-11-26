from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.doctor_credentials import (
    DoctorCredentialReviewAction,
    DoctorCredentialStatus,
    DoctorCredentialType,
)


class DoctorCredentialResponse(BaseModel):
    id: int
    document_type: DoctorCredentialType
    original_filename: str
    mime_type: str
    file_size: int
    submitted_at: datetime
    verification_status: DoctorCredentialStatus
    reviewed_at: datetime | None
    rejection_reason: str | None

    model_config = ConfigDict(from_attributes=True)


class DoctorCredentialListResponse(BaseModel):
    credentials: list[DoctorCredentialResponse]
    required_document_types: list[DoctorCredentialType]
    directory_eligible: bool


class DoctorCredentialReviewAuditEntry(BaseModel):
    id: int
    admin_user_id: int
    action: DoctorCredentialReviewAction
    reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CredentialDoctorProfile(BaseModel):
    id: int
    full_name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class AdminDoctorCredentialDetail(DoctorCredentialResponse):
    doctor_profile: CredentialDoctorProfile
    reviewed_by: int | None
    review_events: list[DoctorCredentialReviewAuditEntry] = Field(
        default_factory=list
    )


class DoctorCredentialRejectionRequest(BaseModel):
    reason: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=5, max_length=500)
    ]

    model_config = ConfigDict(extra="forbid")
