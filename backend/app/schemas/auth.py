from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.doctor import DoctorRegistrationProfile


PasswordInput = Annotated[str, Field(min_length=12, max_length=128)]
LoginPassword = Annotated[str, Field(min_length=1, max_length=128)]


def _validate_registration_password(value: str) -> str:
    if not value.strip():
        raise ValueError("Password must contain a non-whitespace character.")
    return value


class PatientRegistration(BaseModel):
    email: EmailStr
    password: PasswordInput
    first_name: Annotated[str, Field(min_length=1, max_length=100)]
    last_name: Annotated[str, Field(min_length=1, max_length=100)]

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("password")
    @classmethod
    def require_non_whitespace_password(cls, value: str) -> str:
        return _validate_registration_password(value)

    @field_validator("first_name", "last_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name must not be blank.")
        return normalized


class DoctorRegistration(DoctorRegistrationProfile):
    email: EmailStr
    password: PasswordInput

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("password")
    @classmethod
    def require_non_whitespace_password(cls, value: str) -> str:
        return _validate_registration_password(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: LoginPassword

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
