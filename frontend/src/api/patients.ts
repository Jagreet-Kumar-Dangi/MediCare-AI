import { apiClient } from './client'
import type { PatientProfile, PatientProfilePayload } from '../types/api'

export async function getMyPatientProfile(): Promise<PatientProfile> {
  const response = await apiClient.get<PatientProfile>('/patients/me')
  return response.data
}

export async function updateMyPatientProfile(
  payload: PatientProfilePayload,
): Promise<PatientProfile> {
  const response = await apiClient.put<PatientProfile>(
    '/patients/me',
    payload,
  )
  return response.data
}
