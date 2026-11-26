from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.medical_record import MedicalRecordCategory


class MedicalRecordResponse(BaseModel):
    id: int
    title: str
    category: MedicalRecordCategory
    description: str | None
    original_filename: str
    mime_type: str
    file_size: int
    report_date: date | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
