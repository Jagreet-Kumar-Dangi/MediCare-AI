from datetime import date

from pydantic import BaseModel

from app.core.analytics import AnalyticsPeriod


class PeriodResponse(BaseModel):
    period: AnalyticsPeriod
    date_from: date
    date_to: date
    timezone: str


class ComparisonMetric(BaseModel):
    current: int
    previous: int
    percent_change: float | None
    comparison_available: bool


class OverviewResponse(PeriodResponse):
    total_users: int
    total_patients: int
    total_doctors: int
    approved_doctors: int
    pending_doctors: int
    suspended_doctors: int
    total_appointments: int
    upcoming_appointments: int
    completed_appointments: int
    cancelled_appointments: int
    new_users: ComparisonMetric
    new_patients: ComparisonMetric
    new_doctors: ComparisonMetric
    appointments_created: ComparisonMetric


class TrendPoint(BaseModel):
    bucket: date
    count: int


class StatusCount(BaseModel):
    status: str
    count: int


class PatientAnalyticsResponse(PeriodResponse):
    total_patients: int
    active_patients: int
    inactive_patients: int
    new_registrations: ComparisonMetric
    registration_trend: list[TrendPoint]


class DoctorAnalyticsResponse(PeriodResponse):
    total_doctors: int
    active_accounts: int
    inactive_accounts: int
    verification_statuses: list[StatusCount]
    credential_statuses: list[StatusCount]
    registration_trend: list[TrendPoint]
    approval_trend: list[TrendPoint]


class AppointmentAnalyticsResponse(PeriodResponse):
    total_appointments: int
    upcoming_appointments: int
    status_filter: str | None
    doctor_id: int | None
    status_counts: list[StatusCount]
    booking_trend: list[TrendPoint]
    cancellation_trend: list[TrendPoint]
    completion_trend: list[TrendPoint]


class NotificationAnalyticsResponse(PeriodResponse):
    total_jobs: int
    pending_jobs: int
    processing_jobs: int
    sent_jobs: int
    failed_jobs: int
    cancelled_jobs: int
    skipped_jobs: int
    retried_jobs: int
    total_retries: int
    email_success_rate: float | None
    email_success_rate_available: bool
    job_trend: list[TrendPoint]


class DoctorPerformanceItem(BaseModel):
    doctor_id: int
    full_name: str
    verification_status: str
    account_active: bool
    total_appointments: int
    completed_appointments: int
    cancelled_appointments: int
    upcoming_appointments: int


class DoctorPerformanceResponse(PeriodResponse):
    items: list[DoctorPerformanceItem]
    total: int
    limit: int
    offset: int
