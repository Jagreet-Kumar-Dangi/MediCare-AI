import { apiClient } from './client'
import type {
  MedicalRecord,
  MedicalRecordUploadPayload,
} from '../types/api'

export async function getMedicalRecords(): Promise<MedicalRecord[]> {
  const response = await apiClient.get<MedicalRecord[]>('/medical-records')
  return response.data
}

export async function getMedicalRecord(
  recordId: number,
): Promise<MedicalRecord> {
  const response = await apiClient.get<MedicalRecord>(
    `/medical-records/${recordId}`,
  )
  return response.data
}

export async function uploadMedicalRecord(
  payload: MedicalRecordUploadPayload,
  onProgress: (percentage: number) => void,
): Promise<MedicalRecord> {
  const formData = new FormData()
  formData.append('title', payload.title)
  formData.append('category', payload.category)
  if (payload.description) formData.append('description', payload.description)
  if (payload.report_date) formData.append('report_date', payload.report_date)
  formData.append('file', payload.file)

  const response = await apiClient.post<MedicalRecord>(
    '/medical-records/upload',
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

export async function downloadMedicalRecord(
  recordId: number,
): Promise<Blob> {
  const response = await apiClient.get<Blob>(
    `/medical-records/${recordId}/download`,
    { responseType: 'blob' },
  )
  return response.data
}

export async function deleteMedicalRecord(recordId: number): Promise<void> {
  await apiClient.delete(`/medical-records/${recordId}`)
}
