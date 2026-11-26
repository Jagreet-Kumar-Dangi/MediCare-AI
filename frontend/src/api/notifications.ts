import { apiClient } from './client'
import type {
  NotificationItem,
  NotificationJobAdminListResponse,
  NotificationPreferences,
} from '../types/api'

export async function getNotifications(params?: {
  unread_only?: boolean
}): Promise<NotificationItem[]> {
  const response = await apiClient.get<NotificationItem[]>('/notifications', {
    params,
  })
  return response.data
}

export async function markNotificationRead(
  notificationId: number,
): Promise<NotificationItem> {
  const response = await apiClient.patch<NotificationItem>(
    `/notifications/${notificationId}/read`,
  )
  return response.data
}

export async function markAllNotificationsRead(): Promise<number> {
  const response = await apiClient.patch<{ updated_count: number }>(
    '/notifications/read-all',
  )
  return response.data.updated_count
}

export async function deleteNotification(notificationId: number): Promise<void> {
  await apiClient.delete(`/notifications/${notificationId}`)
}

export async function getNotificationPreferences(): Promise<NotificationPreferences> {
  const response = await apiClient.get<NotificationPreferences>(
    '/notifications/preferences',
  )
  return response.data
}

export async function updateNotificationPreferences(
  preferences: Omit<NotificationPreferences, 'updated_at'>,
): Promise<NotificationPreferences> {
  const response = await apiClient.put<NotificationPreferences>(
    '/notifications/preferences',
    preferences,
  )
  return response.data
}

export async function getAdminNotificationJobs(filters?: {
  status?: NotificationJobAdminListResponse['jobs'][number]['status']
  channel?: NotificationJobAdminListResponse['jobs'][number]['channel']
}): Promise<NotificationJobAdminListResponse> {
  const response = await apiClient.get<NotificationJobAdminListResponse>(
    '/admin/notifications/jobs',
    { params: filters },
  )
  return response.data
}
