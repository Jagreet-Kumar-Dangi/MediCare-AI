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
