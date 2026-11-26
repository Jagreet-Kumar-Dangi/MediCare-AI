from enum import Enum


class NotificationType(str, Enum):
    APPOINTMENT_BOOKED = "APPOINTMENT_BOOKED"
    APPOINTMENT_CONFIRMED = "APPOINTMENT_CONFIRMED"
    APPOINTMENT_CANCELLED = "APPOINTMENT_CANCELLED"
    APPOINTMENT_RESCHEDULED = "APPOINTMENT_RESCHEDULED"
    APPOINTMENT_COMPLETED = "APPOINTMENT_COMPLETED"
    APPOINTMENT_REMINDER_24H = "APPOINTMENT_REMINDER_24H"
    APPOINTMENT_REMINDER_1H = "APPOINTMENT_REMINDER_1H"


class NotificationJobChannel(str, Enum):
    EMAIL = "EMAIL"
    REMINDER = "REMINDER"


class NotificationJobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"


NOTIFICATION_TYPE_VALUES = ", ".join(
    f"'{notification_type.value}'" for notification_type in NotificationType
)
NOTIFICATION_CHANNEL_VALUES = ", ".join(
    f"'{channel.value}'" for channel in NotificationJobChannel
)
NOTIFICATION_JOB_STATUS_VALUES = ", ".join(
    f"'{job_status.value}'" for job_status in NotificationJobStatus
)
