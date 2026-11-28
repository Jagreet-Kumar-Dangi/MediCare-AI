import { apiClient } from './client'
import type {
  LoginPayload,
  DoctorRegistrationPayload,
  EmailVerificationPayload,
  PatientRegistrationPayload,
  PublicUser,
  TokenResponse,
} from '../types/api'

export async function registerPatient(
  payload: PatientRegistrationPayload,
): Promise<PublicUser> {
  const response = await apiClient.post<PublicUser>(
    '/auth/register/patient',
    payload,
  )
  return response.data
}

export async function registerDoctor(
  payload: DoctorRegistrationPayload,
): Promise<PublicUser> {
  const response = await apiClient.post<PublicUser>(
    '/auth/register/doctor',
    payload,
  )
  return response.data
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/auth/login', payload)
  return response.data
}

export async function sendVerificationEmail(
  payload: EmailVerificationPayload,
): Promise<void> {
  await apiClient.post('/auth/verify-email/send', payload)
}

export async function resendVerificationEmail(
  payload: EmailVerificationPayload,
): Promise<void> {
  await apiClient.post('/auth/verify-email/resend', payload)
}

export async function confirmEmailVerification(
  payload: EmailVerificationPayload & { code: string },
): Promise<void> {
  await apiClient.post('/auth/verify-email/confirm', payload)
}

export async function getCurrentUser(): Promise<PublicUser> {
  const response = await apiClient.get<PublicUser>('/auth/me')
  return response.data
}

export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout')
}
