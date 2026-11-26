from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.notifications import NotificationJobChannel, NotificationJobStatus, NotificationType


class NotificationResponse(BaseModel):
    id: int
    notification_type: NotificationType
    title: str
    message: str
    related_appointment_id: int | None
    created_at: datetime
    read_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferencesResponse(BaseModel):
    email_enabled: bool
    in_app_enabled: bool
    reminder_24h_enabled: bool
    reminder_1h_enabled: bool
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferencesUpdate(BaseModel):
    email_enabled: bool
    in_app_enabled: bool
    reminder_24h_enabled: bool
    reminder_1h_enabled: bool

    model_config = ConfigDict(extra="forbid")


class NotificationJobAdminResponse(BaseModel):
    id: int
    notification_type: NotificationType
    channel: NotificationJobChannel
    status: NotificationJobStatus
    recipient_masked: str
    scheduled_at: datetime
    attempt_count: int
    next_attempt_at: datetime | None
    last_error: str | None
    created_at: datetime


class NotificationJobAdminListResponse(BaseModel):
    jobs: list[NotificationJobAdminResponse]
    total: int
    limit: int
    offset: int
