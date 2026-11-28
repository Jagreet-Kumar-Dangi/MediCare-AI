from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class EmailVerificationRequest(BaseModel):
    email: EmailStr

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class EmailVerificationConfirmation(EmailVerificationRequest):
    code: Annotated[str, Field(pattern=r"^\d{6}$")]


class EmailVerificationResponse(BaseModel):
    message: str
