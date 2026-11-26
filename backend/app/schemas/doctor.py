from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from app.models.doctor_profile import (
    DoctorVerificationAction,
    DoctorVerificationStatus,
)

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DoctorRegistrationProfile(BaseModel):
    full_name: Annotated[NonEmptyText, Field(max_length=160)]
    specialization: Annotated[NonEmptyText, Field(max_length=120)]
    qualification: Annotated[NonEmptyText, Field(max_length=160)]
    medical_registration_number: Annotated[NonEmptyText, Field(max_length=64)]
    years_of_experience: int = Field(ge=0, le=80)
    phone_number: Annotated[str, Field(max_length=32)] | None = None
    clinic_or_hospital: Annotated[str, Field(max_length=200)] | None = None
    consultation_fee: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    biography: Annotated[str, Field(max_length=4000)] | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("medical_registration_number")
    @classmethod
    def normalize_registration_number(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Medical registration number must not be blank.")
        return normalized

    @field_validator("phone_number", "clinic_or_hospital", "biography")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class DoctorRegistrationResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    specialization: str
    qualification: str
    years_of_experience: int
    verification_status: DoctorVerificationStatus
    verification_submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DoctorSelfProfile(DoctorRegistrationResponse):
    medical_registration_number: str
    phone_number: str | None
    clinic_or_hospital: str | None
    consultation_fee: Decimal | None
    biography: str | None
    verified_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime


class PublicDoctorProfile(BaseModel):
    id: int
    full_name: str
    specialization: str
    qualification: str
    years_of_experience: int
    clinic_or_hospital: str | None
    consultation_fee: Decimal | None
    biography: str | None

    model_config = ConfigDict(from_attributes=True)


class DoctorVerificationAuditEntry(BaseModel):
    id: int
    admin_user_id: int
    action: DoctorVerificationAction
    reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DoctorVerificationDetail(DoctorSelfProfile):
    email: str
    verified_by: int | None
    verification_events: list[DoctorVerificationAuditEntry] = Field(
        default_factory=list
    )


class DoctorRejectionRequest(BaseModel):
    reason: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=5, max_length=500)
    ]

    model_config = ConfigDict(extra="forbid")


class DoctorSuspensionRequest(DoctorRejectionRequest):
    pass
