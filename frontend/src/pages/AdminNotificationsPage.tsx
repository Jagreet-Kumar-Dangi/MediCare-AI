import { Activity, RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getApiErrorMessage } from '../api/errors'
import { getAdminNotificationJobs } from '../api/notifications'
import type {
  NotificationJobAdmin,
  NotificationJobAdminListResponse,
} from '../types/api'

type JobStatus = NotificationJobAdmin['status'] | 'ALL'
type JobChannel = NotificationJobAdmin['channel'] | 'ALL'

function dateLabel(value: string): string {
  return new Date(value).toLocaleString()
}

export function AdminNotificationsPage() {
  const [statusFilter, setStatusFilter] = useState<JobStatus>('ALL')
  const [channelFilter, setChannelFilter] = useState<JobChannel>('ALL')
  const [result, setResult] =
    useState<NotificationJobAdminListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshVersion, setRefreshVersion] = useState(0)

  useEffect(() => {
    let active = true
    void getAdminNotificationJobs({
      status: statusFilter === 'ALL' ? undefined : statusFilter,
      channel: channelFilter === 'ALL' ? undefined : channelFilter,
    })
      .then((jobs) => {
        if (active) setResult(jobs)
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
  }, [channelFilter, refreshVersion, statusFilter])

  return (
    <section className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-700">
            Administrator workspace
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-ink-950">
            Notification jobs
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-600">
            Inspect queued delivery and reminder status. Recipient addresses are
            masked; this view does not expose message content.
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

      <div className="flex flex-wrap gap-3">
        <label className="space-y-1 text-xs font-semibold text-ink-700">
          Status
          <select
            className="block min-h-10 rounded-xl border border-line bg-white px-3 text-sm"
            onChange={(event) => {
              setLoading(true)
              setError(null)
              setStatusFilter(event.target.value as JobStatus)
            }}
            value={statusFilter}
          >
            <option value="ALL">All statuses</option>
            {(
              [
                'PENDING',
                'PROCESSING',
                'SENT',
                'FAILED',
                'CANCELLED',
                'SKIPPED',
              ] as const
            ).map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1 text-xs font-semibold text-ink-700">
          Channel
          <select
            className="block min-h-10 rounded-xl border border-line bg-white px-3 text-sm"
            onChange={(event) => {
              setLoading(true)
              setError(null)
              setChannelFilter(event.target.value as JobChannel)
            }}
            value={channelFilter}
          >
            <option value="ALL">All channels</option>
            <option value="EMAIL">Email</option>
            <option value="REMINDER">Reminder</option>
          </select>
        </label>
      </div>

      {error && (
        <p
          className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
          role="alert"
        >
          {error}
        </p>
      )}
      <section className="overflow-hidden rounded-3xl border border-line bg-white shadow-panel">
        {loading ? (
          <p className="p-6 text-sm text-ink-600">Loading notification jobs…</p>
        ) : !result || result.jobs.length === 0 ? (
          <div className="p-8 text-center">
            <Activity aria-hidden="true" className="mx-auto text-brand-700" size={26} />
            <p className="mt-3 text-sm text-ink-600">
              No jobs match the selected filters.
            </p>
          </div>
        ) : (
          <>
            <p className="border-b border-line px-5 py-3 text-xs text-ink-600">
              {result.total} job{result.total === 1 ? '' : 's'}
            </p>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="bg-sky-50 text-xs uppercase tracking-wide text-ink-600">
                  <tr>
                    <th className="px-5 py-3 font-semibold">Job</th>
                    <th className="px-5 py-3 font-semibold">Recipient</th>
                    <th className="px-5 py-3 font-semibold">Channel / status</th>
                    <th className="px-5 py-3 font-semibold">Attempts</th>
                    <th className="px-5 py-3 font-semibold">Scheduled</th>
                    <th className="px-5 py-3 font-semibold">Last result</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {result.jobs.map((job) => (
                    <tr key={job.id}>
                      <td className="px-5 py-4">
                        <span className="block font-semibold text-ink-950">
                          #{job.id} · {job.notification_type.replaceAll('_', ' ')}
                        </span>
                        <span className="mt-1 block text-xs text-ink-600">
                          Created {dateLabel(job.created_at)}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-ink-700">
                        {job.recipient_masked}
                      </td>
                      <td className="px-5 py-4 text-ink-700">
                        {job.channel} · {job.status}
                      </td>
                      <td className="px-5 py-4 text-ink-700">
                        {job.attempt_count}
                      </td>
                      <td className="px-5 py-4 text-ink-700">
                        {dateLabel(job.scheduled_at)}
                        {job.next_attempt_at && (
                          <span className="mt-1 block text-xs text-ink-600">
                            Retry {dateLabel(job.next_attempt_at)}
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-4 text-xs text-ink-600">
                        {job.last_error ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </section>
  )
}
