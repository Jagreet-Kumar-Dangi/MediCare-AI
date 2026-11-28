export type UserRole = 'PATIENT' | 'DOCTOR' | 'ADMIN'

export interface PublicUser {
  id: number
  email: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface PatientRegistrationPayload {
  email: string
  password: string
  first_name: string
  last_name: string
}

export interface DoctorRegistrationPayload {
  email: string
  password: string
  full_name: string
  specialization: string
  qualification: string
  medical_registration_number: string
  years_of_experience: number
  phone_number?: string | null
  clinic_or_hospital?: string | null
  consultation_fee?: string | null
  biography?: string | null
}

export type DoctorVerificationStatus =
  | 'PENDING'
  | 'APPROVED'
  | 'REJECTED'
  | 'SUSPENDED'

export interface DoctorSelfProfile {
  id: number
  user_id: number
  full_name: string
  specialization: string
  qualification: string
  years_of_experience: number
  medical_registration_number: string
  phone_number: string | null
  clinic_or_hospital: string | null
  consultation_fee: string | number | null
  biography: string | null
  verification_status: DoctorVerificationStatus
  verification_submitted_at: string
  verified_at: string | null
  rejection_reason: string | null
  created_at: string
  updated_at: string
}

export interface DoctorVerificationDetail extends DoctorSelfProfile {
  email: string
  verified_by: number | null
  verification_events: DoctorVerificationAuditEntry[]
}

export interface DoctorVerificationAuditEntry {
  id: number
  admin_user_id: number
  action: 'APPROVED' | 'REJECTED' | 'SUSPENDED'
  reason: string | null
  created_at: string
}

export interface PublicDoctorProfile {
  id: number
  full_name: string
  specialization: string
  qualification: string
  years_of_experience: number
  clinic_or_hospital: string | null
  consultation_fee: string | number | null
  biography: string | null
}

export interface DoctorDirectoryFilters {
  specialization?: string
  min_experience?: number
  max_experience?: number
  max_consultation_fee?: string | number
  search?: string
}

export const doctorCredentialTypes = [
  'MEDICAL_REGISTRATION_CERTIFICATE',
  'MEDICAL_DEGREE_CERTIFICATE',
  'ADDITIONAL_QUALIFICATION_CERTIFICATE',
] as const

export type DoctorCredentialType = (typeof doctorCredentialTypes)[number]

export type DoctorCredentialStatus = 'PENDING' | 'APPROVED' | 'REJECTED'

export interface DoctorCredential {
  id: number
  document_type: DoctorCredentialType
  original_filename: string
  mime_type: string
  file_size: number
  submitted_at: string
  verification_status: DoctorCredentialStatus
  reviewed_at: string | null
  rejection_reason: string | null
}

export interface DoctorCredentialListResponse {
  credentials: DoctorCredential[]
  required_document_types: DoctorCredentialType[]
  directory_eligible: boolean
}

export interface DoctorCredentialReviewAuditEntry {
  id: number
  admin_user_id: number
  action: 'APPROVED' | 'REJECTED'
  reason: string | null
  created_at: string
}

export interface AdminDoctorCredentialDetail extends DoctorCredential {
  doctor_profile: {
    id: number
    full_name: string
    email: string
  }
  reviewed_by: number | null
  review_events: DoctorCredentialReviewAuditEntry[]
}

export type AppointmentStatus =
  | 'BOOKED'
  | 'CONFIRMED'
  | 'REJECTED'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'NO_SHOW'

export type AppointmentAuditAction =
  | AppointmentStatus
  | 'RESCHEDULED'

export interface AppointmentAuditEvent {
  id: number
  action: AppointmentAuditAction
  reason: string | null
  previous_start: string | null
  previous_end: string | null
  new_start: string | null
  new_end: string | null
  created_at: string
}

export interface AppointmentDoctorSummary {
  id: number
  full_name: string
}

export interface Appointment {
  id: number
  doctor: AppointmentDoctorSummary
  scheduled_start: string
  scheduled_end: string
  status: AppointmentStatus
  reason_for_visit: string
  patient_notes: string | null
  cancellation_reason: string | null
  rejection_reason: string | null
  created_at: string
  updated_at: string
  audit_events: AppointmentAuditEvent[]
  patient_name?: string
  doctor_notes?: string | null
  patient_id?: number
  patient_email?: string
}

export interface DoctorAvailability {
  id: number
  weekday: number
  start_time: string
  end_time: string
  break_start: string | null
  break_end: string | null
  appointment_duration_minutes: number
  created_at: string
  updated_at: string
}

export interface DoctorAvailabilityPayload {
  weekday: number
  start_time: string
  end_time: string
  break_start?: string | null
  break_end?: string | null
  appointment_duration_minutes: number
}

export interface AvailabilityException {
  id: number
  exception_date: string
  start_time: string | null
  end_time: string | null
  reason: string
  created_at: string
}

export interface AvailabilityExceptionPayload {
  exception_date: string
  start_time?: string | null
  end_time?: string | null
  reason: string
}

export interface AvailableSlotsResponse {
  doctor_id: number
  date: string
  timezone: string
  slots: { scheduled_start: string; scheduled_end: string }[]
}

export type NotificationType =
  | 'APPOINTMENT_BOOKED'
  | 'APPOINTMENT_CONFIRMED'
  | 'APPOINTMENT_CANCELLED'
  | 'APPOINTMENT_RESCHEDULED'
  | 'APPOINTMENT_COMPLETED'
  | 'APPOINTMENT_REMINDER_24H'
  | 'APPOINTMENT_REMINDER_1H'

export interface NotificationItem {
  id: number
  notification_type: NotificationType
  title: string
  message: string
  related_appointment_id: number | null
  created_at: string
  read_at: string | null
}

export interface NotificationPreferences {
  email_enabled: boolean
  in_app_enabled: boolean
  reminder_24h_enabled: boolean
  reminder_1h_enabled: boolean
  updated_at: string | null
}

export interface NotificationJobAdmin {
  id: number
  notification_type: NotificationType
  channel: 'EMAIL' | 'REMINDER'
  status: 'PENDING' | 'PROCESSING' | 'SENT' | 'FAILED' | 'CANCELLED' | 'SKIPPED'
  recipient_masked: string
  scheduled_at: string
  attempt_count: number
  next_attempt_at: string | null
  last_error: string | null
  created_at: string
}

export interface NotificationJobAdminListResponse {
  jobs: NotificationJobAdmin[]
  total: number
  limit: number
  offset: number
}

export type AnalyticsPeriod =
  | 'today'
  | 'last_7_days'
  | 'last_30_days'
  | 'last_90_days'
  | 'this_month'
  | 'previous_month'
  | 'custom'

export type AnalyticsGranularity = 'day' | 'week' | 'month'

export interface AnalyticsFilters {
  period: AnalyticsPeriod
  start_date?: string
  end_date?: string
  granularity?: AnalyticsGranularity
}

export interface AnalyticsComparison {
  current: number
  previous: number
  percent_change: number | null
  comparison_available: boolean
}

export interface AnalyticsPeriodResponse {
  period: AnalyticsPeriod
  date_from: string
  date_to: string
  timezone: string
}

export interface AnalyticsTrendPoint {
  bucket: string
  count: number
}

export interface AnalyticsStatusCount {
  status: string
  count: number
}

export interface AdminAnalyticsOverview extends AnalyticsPeriodResponse {
  total_users: number
  total_patients: number
  total_doctors: number
  approved_doctors: number
  pending_doctors: number
  suspended_doctors: number
  total_appointments: number
  upcoming_appointments: number
  completed_appointments: number
  cancelled_appointments: number
  new_users: AnalyticsComparison
  new_patients: AnalyticsComparison
  new_doctors: AnalyticsComparison
  appointments_created: AnalyticsComparison
}

export interface AdminPatientAnalytics extends AnalyticsPeriodResponse {
  total_patients: number
  active_patients: number
  inactive_patients: number
  new_registrations: AnalyticsComparison
  registration_trend: AnalyticsTrendPoint[]
}

export interface AdminDoctorAnalytics extends AnalyticsPeriodResponse {
  total_doctors: number
  active_accounts: number
  inactive_accounts: number
  verification_statuses: AnalyticsStatusCount[]
  credential_statuses: AnalyticsStatusCount[]
  registration_trend: AnalyticsTrendPoint[]
  approval_trend: AnalyticsTrendPoint[]
}

export interface AdminAppointmentAnalytics extends AnalyticsPeriodResponse {
  total_appointments: number
  upcoming_appointments: number
  status_filter: AppointmentStatus | null
  doctor_id: number | null
  status_counts: AnalyticsStatusCount[]
  booking_trend: AnalyticsTrendPoint[]
  cancellation_trend: AnalyticsTrendPoint[]
  completion_trend: AnalyticsTrendPoint[]
}

export interface AdminNotificationAnalytics extends AnalyticsPeriodResponse {
  total_jobs: number
  pending_jobs: number
  processing_jobs: number
  sent_jobs: number
  failed_jobs: number
  cancelled_jobs: number
  skipped_jobs: number
  retried_jobs: number
  total_retries: number
  email_success_rate: number | null
  email_success_rate_available: boolean
  job_trend: AnalyticsTrendPoint[]
}

export interface DoctorPerformanceItem {
  doctor_id: number
  full_name: string
  verification_status: DoctorVerificationStatus
  account_active: boolean
  total_appointments: number
  completed_appointments: number
  cancelled_appointments: number
  upcoming_appointments: number
}

export interface AdminDoctorPerformance extends AnalyticsPeriodResponse {
  items: DoctorPerformanceItem[]
  total: number
  limit: number
  offset: number
}

export interface LoginPayload {
  email: string
  password: string
}

export interface EmailVerificationPayload {
  email: string
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
}

export interface PatientProfile {
  first_name: string
  last_name: string
  date_of_birth: string | null
  phone_number: string | null
  created_at: string
  updated_at: string
}

export interface PatientProfilePayload {
  first_name: string
  last_name: string
  date_of_birth: string | null
  phone_number: string | null
}

export interface HealthResponse {
  status: 'healthy'
  application: string
  version: string
  message: string
}

export const medicalRecordCategories = [
  'Blood Test',
  'Prescription',
  'Radiology',
  'MRI / CT Scan',
  'X-Ray',
  'Discharge Summary',
  'Laboratory Report',
  'Other',
] as const

export type MedicalRecordCategory = (typeof medicalRecordCategories)[number]

export interface MedicalRecord {
  id: number
  title: string
  category: MedicalRecordCategory
  description: string | null
  original_filename: string
  mime_type: string
  file_size: number
  report_date: string | null
  created_at: string
  updated_at: string
}

export interface MedicalRecordUploadPayload {
  title: string
  category: MedicalRecordCategory
  description?: string
  report_date?: string
  file: File
}
