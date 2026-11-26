import { apiClient } from './client'
import type {
  AdminAnalyticsOverview,
  AdminAppointmentAnalytics,
  AdminDoctorAnalytics,
  AdminDoctorPerformance,
  AdminNotificationAnalytics,
  AdminPatientAnalytics,
  AnalyticsFilters,
  AnalyticsGranularity,
  AnalyticsPeriod,
  AppointmentStatus,
  DoctorVerificationStatus,
} from '../types/api'

export interface AdminAnalyticsQuery extends AnalyticsFilters {
  status?: AppointmentStatus
  doctor_id?: number
  verification_status?: DoctorVerificationStatus
}

export async function getAdminAnalyticsOverview(
  filters: AnalyticsFilters,
): Promise<AdminAnalyticsOverview> {
  const response = await apiClient.get<AdminAnalyticsOverview>(
    '/admin/analytics/overview',
    { params: filters },
  )
  return response.data
}

export async function getAdminPatientAnalytics(
  filters: AnalyticsFilters,
): Promise<AdminPatientAnalytics> {
  const response = await apiClient.get<AdminPatientAnalytics>(
    '/admin/analytics/patients',
    { params: filters },
  )
  return response.data
}

export async function getAdminDoctorAnalytics(
  filters: AdminAnalyticsQuery,
): Promise<AdminDoctorAnalytics> {
  const response = await apiClient.get<AdminDoctorAnalytics>(
    '/admin/analytics/doctors',
    { params: filters },
  )
  return response.data
}

export async function getAdminAppointmentAnalytics(
  filters: AdminAnalyticsQuery,
): Promise<AdminAppointmentAnalytics> {
  const response = await apiClient.get<AdminAppointmentAnalytics>(
    '/admin/analytics/appointments',
    { params: filters },
  )
  return response.data
}

export async function getAdminNotificationAnalytics(
  filters: AnalyticsFilters,
): Promise<AdminNotificationAnalytics> {
  const response = await apiClient.get<AdminNotificationAnalytics>(
    '/admin/analytics/notifications',
    { params: filters },
  )
  return response.data
}

export async function getAdminDoctorPerformance(
  filters: AdminAnalyticsQuery,
): Promise<AdminDoctorPerformance> {
  const response = await apiClient.get<AdminDoctorPerformance>(
    '/admin/analytics/doctor-performance',
    { params: filters },
  )
  return response.data
}

export async function downloadAdminAnalyticsCsv(
  dataset: 'patients' | 'doctors' | 'appointments' | 'notifications',
  filters: AdminAnalyticsQuery,
): Promise<Blob> {
  const response = await apiClient.get<Blob>('/admin/analytics/export', {
    params: { dataset, ...filters },
    responseType: 'blob',
  })
  return response.data
}

export const analyticsPeriods: {
  value: AnalyticsPeriod
  label: string
}[] = [
  { value: 'today', label: 'Today' },
  { value: 'last_7_days', label: 'Last 7 days' },
  { value: 'last_30_days', label: 'Last 30 days' },
  { value: 'last_90_days', label: 'Last 90 days' },
  { value: 'this_month', label: 'This month' },
  { value: 'previous_month', label: 'Previous month' },
  { value: 'custom', label: 'Custom range' },
]

export const analyticsGranularities: {
  value: AnalyticsGranularity
  label: string
}[] = [
  { value: 'day', label: 'Daily' },
  { value: 'week', label: 'Weekly' },
  { value: 'month', label: 'Monthly' },
]

