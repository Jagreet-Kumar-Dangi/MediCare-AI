import { Bell, CheckCheck, RefreshCw, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  deleteNotification,
  getNotificationPreferences,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  updateNotificationPreferences,
} from '../api/notifications'
import { getApiErrorMessage } from '../api/errors'
import type { NotificationItem, NotificationPreferences } from '../types/api'

type PreferenceKey = keyof Omit<NotificationPreferences, 'updated_at'>

const preferenceOptions: { key: PreferenceKey; label: string }[] = [
  { key: 'in_app_enabled', label: 'In-app notifications' },
  { key: 'email_enabled', label: 'Appointment email notifications' },
  { key: 'reminder_24h_enabled', label: '24-hour appointment reminders' },
  { key: 'reminder_1h_enabled', label: '1-hour appointment reminders' },
]

const defaultPreferences: NotificationPreferences = {
  email_enabled: true,
  in_app_enabled: true,
  reminder_24h_enabled: true,
  reminder_1h_enabled: true,
  updated_at: null,
}

function notificationTime(value: string): string {
  return new Date(value).toLocaleString()
}

export function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [preferences, setPreferences] =
    useState<NotificationPreferences>(defaultPreferences)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [refreshVersion, setRefreshVersion] = useState(0)

  useEffect(() => {
    let active = true
    void Promise.all([getNotifications(), getNotificationPreferences()])
      .then(([items, currentPreferences]) => {
        if (!active) return
        setNotifications(items)
        setPreferences(currentPreferences)
      })
      .catch((requestError: unknown) => {
        if (active) setError(getApiErrorMessage(requestError))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [refreshVersion])

  async function handleRead(notificationId: number) {
    setError(null)
    try {
      const updated = await markNotificationRead(notificationId)
      setNotifications((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      )
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    }
  }

  async function handleDelete(notificationId: number) {
    setError(null)
    try {
      await deleteNotification(notificationId)
      setNotifications((current) =>
        current.filter((item) => item.id !== notificationId),
      )
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    }
  }

  async function handleMarkAllRead() {
    setError(null)
    try {
      await markAllNotificationsRead()
      const now = new Date().toISOString()
      setNotifications((current) =>
        current.map((item) => ({ ...item, read_at: item.read_at ?? now })),
      )
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    }
  }

  async function handleSavePreferences() {
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const saved = await updateNotificationPreferences({
        email_enabled: preferences.email_enabled,
        in_app_enabled: preferences.in_app_enabled,
        reminder_24h_enabled: preferences.reminder_24h_enabled,
        reminder_1h_enabled: preferences.reminder_1h_enabled,
      })
      setPreferences(saved)
      setNotice('Notification preferences saved.')
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-700">
            Your account
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-ink-950">
            Notifications
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-600">
            Review appointment updates and choose which reminders you receive.
          </p>
        </div>
        <button
          className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-line bg-white px-4 text-sm font-semibold text-ink-800 hover:bg-sky-50"
          onClick={() => {
            setLoading(true)
            setError(null)
            setRefreshVersion((version) => version + 1)
          }}
          type="button"
        >
          <RefreshCw aria-hidden="true" size={16} />
          Refresh
        </button>
      </header>

      {error && (
        <p
          className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
          role="alert"
        >
          {error}
        </p>
      )}
      {notice && (
        <p
          className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900"
          role="status"
        >
          {notice}
        </p>
      )}

      <section className="rounded-3xl border border-line bg-white p-5 shadow-panel sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-ink-950">
              Notification preferences
            </h2>
            <p className="mt-1 text-sm text-ink-600">
              Email delivery requires the server notification worker and SMTP configuration.
            </p>
          </div>
          <button
            className="min-h-10 rounded-xl bg-brand-700 px-4 text-sm font-semibold text-white disabled:opacity-60"
            disabled={saving}
            onClick={() => void handleSavePreferences()}
            type="button"
          >
            {saving ? 'Saving…' : 'Save preferences'}
          </button>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {preferenceOptions.map(({ key, label }) => (
            <label
              className="flex min-h-12 items-center gap-3 rounded-xl border border-line px-4 text-sm font-medium text-ink-800"
              key={key}
            >
              <input
                checked={preferences[key]}
                className="size-4 accent-brand-700"
                onChange={(event) =>
                  setPreferences((current) => ({
                    ...current,
                    [key]: event.target.checked,
                  }))
                }
                type="checkbox"
              />
              {label}
            </label>
          ))}
        </div>
      </section>

      <section className="overflow-hidden rounded-3xl border border-line bg-white shadow-panel">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
          <div className="flex items-center gap-2">
            <Bell aria-hidden="true" className="text-brand-700" size={18} />
            <h2 className="text-sm font-semibold text-ink-950">
              Recent updates
            </h2>
          </div>
          <button
            className="inline-flex min-h-9 items-center gap-2 rounded-xl border border-line px-3 text-xs font-semibold text-ink-700 hover:bg-sky-50 disabled:opacity-50"
            disabled={!notifications.some((item) => item.read_at === null)}
            onClick={() => void handleMarkAllRead()}
            type="button"
          >
            <CheckCheck aria-hidden="true" size={15} />
            Mark all as read
          </button>
        </div>
        {loading ? (
          <p className="p-6 text-sm text-ink-600">Loading notifications…</p>
        ) : notifications.length === 0 ? (
          <div className="p-8 text-center">
            <Bell aria-hidden="true" className="mx-auto text-brand-700" size={26} />
            <p className="mt-3 text-sm text-ink-600">You have no notifications.</p>
          </div>
        ) : (
          <ul className="divide-y divide-line">
            {notifications.map((item) => (
              <li
                className={`flex flex-wrap items-center justify-between gap-4 px-5 py-4 ${
                  item.read_at ? '' : 'bg-sky-50/70'
                }`}
                key={item.id}
              >
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-ink-950">
                    {item.title}
                    {!item.read_at && (
                      <span className="ml-2 inline-block size-2 rounded-full bg-brand-700" />
                    )}
                  </p>
                  <p className="mt-1 text-sm text-ink-700">{item.message}</p>
                  <p className="mt-1 text-xs text-ink-600">
                    {notificationTime(item.created_at)}
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  {!item.read_at && (
                    <button
                      className="min-h-9 rounded-lg border border-line px-3 text-xs font-semibold text-ink-700 hover:bg-white"
                      onClick={() => void handleRead(item.id)}
                      type="button"
                    >
                      Mark read
                    </button>
                  )}
                  <button
                    aria-label={`Delete ${item.title}`}
                    className="grid size-9 place-items-center rounded-lg border border-line text-ink-600 hover:bg-white hover:text-rose-700"
                    onClick={() => void handleDelete(item.id)}
                    type="button"
                  >
                    <Trash2 aria-hidden="true" size={15} />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  )
}
