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
