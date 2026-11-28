from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AnyHttpUrl,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.doctor_credentials import DoctorCredentialType


class Settings(BaseSettings):
    application_name: str = "MediCare AI"
    app_title: str = "MediCare AI API"
    app_version: str = "1.0.0"
    api_v1_prefix: str = "/api/v1"
    database_url: str
    jwt_secret_key: SecretStr
    access_token_expire_minutes: int = 30
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    medical_records_storage_dir: Path = (
        Path(__file__).resolve().parents[2] / "storage" / "medical-records"
    )
    medical_records_max_upload_size_mb: int = Field(default=10, gt=0)
    doctor_credentials_storage_dir: Path = (
        Path(__file__).resolve().parents[2] / "storage" / "doctor-credentials"
    )
    doctor_credentials_max_upload_size_mb: int = Field(default=10, gt=0)
    required_doctor_credential_types: list[DoctorCredentialType] = [
        DoctorCredentialType.MEDICAL_REGISTRATION_CERTIFICATE,
        DoctorCredentialType.MEDICAL_DEGREE_CERTIFICATE,
    ]
    appointment_timezone: str = "UTC"
    patient_appointment_cancellation_cutoff_hours: int = Field(
        default=24, ge=0, le=720
    )
    patient_appointment_rescheduling_cutoff_hours: int = Field(
        default=24, ge=0, le=720
    )
    appointment_reminder_24h_minutes: int = Field(default=1440, gt=0, le=10080)
    appointment_reminder_1h_minutes: int = Field(default=60, gt=0, le=10080)
    notification_worker_poll_seconds: int = Field(default=5, ge=1, le=300)
    notification_max_attempts: int = Field(default=5, ge=1, le=10)
    notification_retry_base_seconds: int = Field(default=60, ge=1, le=3600)
    notification_retry_max_seconds: int = Field(default=21600, ge=1, le=86400)
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from_email: EmailStr | None = None
    smtp_from_name: str = "MediCare AI"
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    frontend_base_url: AnyHttpUrl | None = None

    @model_validator(mode="after")
    def validate_notification_settings(self) -> "Settings":
        if self.smtp_use_tls and self.smtp_use_ssl:
            raise ValueError("SMTP_USE_TLS and SMTP_USE_SSL cannot both be enabled.")
        if bool(self.smtp_username) != bool(self.smtp_password):
            raise ValueError("SMTP_USERNAME and SMTP_PASSWORD must be configured together.")
        if self.notification_retry_base_seconds > self.notification_retry_max_seconds:
            raise ValueError(
                "NOTIFICATION_RETRY_BASE_SECONDS cannot exceed "
                "NOTIFICATION_RETRY_MAX_SECONDS."
            )
        return self

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if len(secret.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 bytes.")
        if secret.startswith("replace-this-"):
            raise ValueError("Replace the example JWT_SECRET_KEY with a random key.")
        return value

    @field_validator("access_token_expire_minutes")
    @classmethod
    def validate_access_token_expiry(cls, value: int) -> int:
        if not 1 <= value <= 1440:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be between 1 and 1440.")
        return value

    @field_validator("appointment_timezone")
    @classmethod
    def validate_appointment_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("APPOINTMENT_TIMEZONE must be a valid IANA timezone.") from error
        return value

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


settings = Settings()
