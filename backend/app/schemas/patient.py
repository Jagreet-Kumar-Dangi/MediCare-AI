from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


PatientName = Annotated[str, Field(min_length=1, max_length=100)]
PhoneNumber = Annotated[
    str,
    Field(
        min_length=7,
        max_length=32,
        pattern=r"^\+?[0-9][0-9 ().-]*$",
    ),
]


class PatientProfileUpdate(BaseModel):
    first_name: PatientName
    last_name: PatientName
    date_of_birth: date | None
    phone_number: PhoneNumber | None

    model_config = ConfigDict(extra="forbid")

    @field_validator("first_name", "last_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name must not be blank.")
        return normalized

    @field_validator("date_of_birth")
    @classmethod
    def reject_future_date_of_birth(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return value

    @field_validator("phone_number")
    @classmethod
    def normalize_phone_number(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Phone number must not be blank.")
        return normalized


class PatientProfileResponse(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date | None
    phone_number: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
