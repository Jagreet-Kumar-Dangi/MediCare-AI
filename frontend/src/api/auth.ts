import { apiClient } from './client'
import type {
  LoginPayload,
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

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/auth/login', payload)
  return response.data
}

export async function getCurrentUser(): Promise<PublicUser> {
  const response = await apiClient.get<PublicUser>('/auth/me')
  return response.data
}

export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout')
}
