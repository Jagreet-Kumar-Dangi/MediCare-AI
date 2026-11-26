import { apiClient } from './client'
import type {
  AdminDoctorCredentialDetail,
  DoctorCredential,
  DoctorCredentialListResponse,
  DoctorCredentialStatus,
  DoctorCredentialType,
} from '../types/api'

export async function getMyDoctorCredentials(): Promise<DoctorCredentialListResponse> {
  const response = await apiClient.get<DoctorCredentialListResponse>(
    '/doctor-credentials/me',
  )
  return response.data
}

export async function uploadDoctorCredential(
  documentType: DoctorCredentialType,
  file: File,
  onProgress: (percentage: number) => void,
): Promise<DoctorCredential> {
  const formData = new FormData()
  formData.append('document_type', documentType)
  formData.append('file', file)

  const response = await apiClient.post<DoctorCredential>(
    '/doctor-credentials',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (event) => {
        if (event.total) {
          onProgress(Math.round((event.loaded / event.total) * 100))
        }
      },
    },
  )
  return response.data
}

export async function getAdminDoctorCredentials(
  status?: DoctorCredentialStatus,
): Promise<AdminDoctorCredentialDetail[]> {
  const response = await apiClient.get<AdminDoctorCredentialDetail[]>(
    '/admin/doctor-credentials',
    { params: status ? { status } : undefined },
  )
  return response.data
}

export async function getAdminDoctorCredential(
  credentialId: number,
): Promise<AdminDoctorCredentialDetail> {
  const response = await apiClient.get<AdminDoctorCredentialDetail>(
    `/admin/doctor-credentials/${credentialId}`,
  )
  return response.data
}

export async function downloadDoctorCredential(
  credentialId: number,
  admin = false,
): Promise<Blob> {
  const endpoint = admin
    ? `/admin/doctor-credentials/${credentialId}/download`
    : `/doctor-credentials/${credentialId}/download`
  const response = await apiClient.get<Blob>(endpoint, {
    responseType: 'blob',
  })
  return response.data
}

export async function deleteDoctorCredential(
  credentialId: number,
): Promise<void> {
  await apiClient.delete(`/doctor-credentials/${credentialId}`)
}

export async function approveDoctorCredential(
  credentialId: number,
): Promise<void> {
  await apiClient.post(`/admin/doctor-credentials/${credentialId}/approve`)
}

export async function rejectDoctorCredential(
  credentialId: number,
  reason: string,
): Promise<void> {
  await apiClient.post(`/admin/doctor-credentials/${credentialId}/reject`, {
    reason,
  })
}
