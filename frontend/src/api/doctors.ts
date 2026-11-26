import { apiClient } from './client'
import type {
  DoctorDirectoryFilters,
  DoctorSelfProfile,
  DoctorVerificationDetail,
  PublicDoctorProfile,
} from '../types/api'

export async function getMyDoctorProfile(): Promise<DoctorSelfProfile> {
  const response = await apiClient.get<DoctorSelfProfile>('/doctors/me')
  return response.data
}

export async function listDoctors(
  filters: DoctorDirectoryFilters = {},
): Promise<PublicDoctorProfile[]> {
  const response = await apiClient.get<PublicDoctorProfile[]>('/doctors', {
    params: filters,
  })
  return response.data
}

export async function getDoctor(
  doctorId: number,
): Promise<PublicDoctorProfile> {
  const response = await apiClient.get<PublicDoctorProfile>(
    `/doctors/${doctorId}`,
  )
  return response.data
}

export async function listPendingDoctors(): Promise<
  DoctorVerificationDetail[]
> {
  const response = await apiClient.get<DoctorVerificationDetail[]>(
    '/admin/doctors/pending',
  )
  return response.data
}

export async function listSuspendedDoctors(): Promise<
  DoctorVerificationDetail[]
> {
  const response = await apiClient.get<DoctorVerificationDetail[]>(
    '/admin/doctors/suspended',
  )
  return response.data
}

export async function listApprovedDoctorsForAdmin(): Promise<
  DoctorVerificationDetail[]
> {
  const response = await apiClient.get<DoctorVerificationDetail[]>(
    '/admin/doctors/approved',
  )
  return response.data
}

export async function getDoctorApplication(
  doctorId: number,
): Promise<DoctorVerificationDetail> {
  const response = await apiClient.get<DoctorVerificationDetail>(
    `/admin/doctors/${doctorId}`,
  )
  return response.data
}

export async function approveDoctor(doctorId: number): Promise<void> {
  await apiClient.post(`/admin/doctors/${doctorId}/approve`)
}

export async function rejectDoctor(
  doctorId: number,
  reason: string,
): Promise<void> {
  await apiClient.post(`/admin/doctors/${doctorId}/reject`, { reason })
}

export async function suspendDoctor(
  doctorId: number,
  reason: string,
): Promise<void> {
  await apiClient.post(`/admin/doctors/${doctorId}/suspend`, { reason })
}
