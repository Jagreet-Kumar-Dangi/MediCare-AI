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

export interface LoginPayload {
  email: string
  password: string
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
