import { BadgeCheck, Download, FileCheck2, ShieldAlert } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { getApiErrorMessage } from '../api/errors'
import {
  approveDoctorCredential,
  downloadDoctorCredential,
  getAdminDoctorCredentials,
  rejectDoctorCredential,
} from '../api/doctorCredentials'
import type {
  AdminDoctorCredentialDetail,
  DoctorCredentialStatus,
  DoctorCredentialType,
} from '../types/api'

type CredentialStatusFilter = DoctorCredentialStatus | 'ALL'

const typeLabels: Record<DoctorCredentialType, string> = {
  MEDICAL_REGISTRATION_CERTIFICATE: 'Medical registration certificate',
  MEDICAL_DEGREE_CERTIFICATE: 'Medical degree certificate',
  ADDITIONAL_QUALIFICATION_CERTIFICATE:
    'Additional professional qualification certificate',
}

function triggerDownload(blob: Blob, filename: string): void {
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
}

export function AdminDoctorCredentialsPage() {
  const [filter, setFilter] = useState<CredentialStatusFilter>('PENDING')
  const [credentials, setCredentials] = useState<
    AdminDoctorCredentialDetail[]
  >([])
  const [selected, setSelected] =
    useState<AdminDoctorCredentialDetail | null>(null)
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [refreshVersion, setRefreshVersion] = useState(0)

  useEffect(() => {
    let active = true
    const status = filter === 'ALL' ? undefined : filter
    void getAdminDoctorCredentials(status)
      .then((result) => {
        if (active) setCredentials(result)
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
  }, [filter, refreshVersion])

  async function handleDownload() {
    if (!selected) return
    setError(null)
    try {
      const blob = await downloadDoctorCredential(selected.id, true)
      triggerDownload(blob, selected.original_filename)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    }
  }

  async function runReview(action: 'approve' | 'reject') {
    if (!selected) return
    if (action === 'reject' && reason.trim().length < 5) {
      setError('Enter a rejection reason of at least five characters.')
      return
    }

    setActing(true)
    setError(null)
    setNotice(null)
    try {
      if (action === 'approve') {
        await approveDoctorCredential(selected.id)
      } else {
        await rejectDoctorCredential(selected.id, reason.trim())
      }
      setNotice(
        action === 'approve'
          ? 'Credential approved.'
          : 'Credential rejected.',
      )
      setSelected(null)
      setReason('')
      setLoading(true)
      setRefreshVersion((version) => version + 1)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setActing(false)
    }
  }

  function handleReject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void runReview('reject')
  }

  return (
    <section className="space-y-6">
      <header>
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-700">
          Administrator workspace
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-ink-950">
          Credential verification
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-600">
          Review private doctor credential submissions. Downloads require
          administrator authorization and each decision is recorded.
        </p>
      </header>

      <div className="flex flex-wrap gap-2" aria-label="Credential status filter">
        {(['PENDING', 'APPROVED', 'REJECTED', 'ALL'] as const).map((value) => (
          <button
            aria-pressed={filter === value}
            className={`min-h-10 rounded-xl px-4 text-sm font-semibold transition ${
              filter === value
                ? 'bg-brand-700 text-white'
                : 'border border-line bg-white text-ink-700 hover:bg-sky-50'
            }`}
            key={value}
            onClick={() => {
              setFilter(value)
              setSelected(null)
              setNotice(null)
              setError(null)
              setLoading(true)
              setCredentials([])
            }}
            type="button"
          >
            {value === 'ALL' ? 'All documents' : value}
          </button>
        ))}
      </div>

      {error && (
        <p
          aria-live="polite"
          className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
          role="alert"
        >
          {error}
        </p>
      )}
      {notice && (
        <p
          aria-live="polite"
          className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900"
          role="status"
        >
          {notice}
        </p>
      )}

      <div className="grid gap-5 xl:grid-cols-[minmax(280px,0.8fr)_minmax(0,1.2fr)]">
        <section className="overflow-hidden rounded-3xl border border-line bg-white shadow-panel">
          <h2 className="border-b border-line px-5 py-4 text-sm font-semibold text-ink-950">
            {filter === 'ALL' ? 'All credentials' : `${filter} credentials`}
          </h2>
          {loading ? (
            <p className="p-5 text-sm text-ink-600">Loading credentials…</p>
          ) : credentials.length === 0 ? (
            <p className="p-5 text-sm text-ink-600">
              No credentials match this filter.
            </p>
          ) : (
            <ul className="divide-y divide-line">
              {credentials.map((credential) => (
                <li key={credential.id}>
                  <button
                    className={`flex min-h-20 w-full items-center justify-between gap-3 px-5 py-4 text-left transition hover:bg-sky-50 ${
                      selected?.id === credential.id ? 'bg-sky-50' : ''
                    }`}
                    onClick={() => setSelected(credential)}
                    type="button"
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-semibold text-ink-950">
                        {credential.doctor_profile.full_name}
                      </span>
                      <span className="mt-1 block truncate text-xs text-ink-600">
                        {typeLabels[credential.document_type]} ·{' '}
                        {credential.doctor_profile.email}
                      </span>
                    </span>
                    <FileCheck2
                      aria-hidden="true"
                      className="shrink-0 text-brand-700"
                      size={17}
                    />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="min-h-64 rounded-3xl border border-line bg-white p-5 shadow-panel sm:p-7">
          {!selected ? (
            <div className="grid min-h-52 place-items-center text-center">
              <div>
                <FileCheck2
                  aria-hidden="true"
                  className="mx-auto text-brand-700"
                  size={30}
                />
                <p className="mt-3 text-sm text-ink-600">
                  Select a credential to review its metadata and document.
                </p>
              </div>
            </div>
          ) : (
            <div>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold text-ink-950">
                    {typeLabels[selected.document_type]}
                  </h2>
                  <p className="mt-1 text-sm text-ink-600">
                    {selected.doctor_profile.full_name} ·{' '}
                    {selected.doctor_profile.email}
                  </p>
                </div>
                <span className="inline-flex items-center gap-2 rounded-full bg-sky-50 px-3 py-1.5 text-xs font-semibold text-brand-800">
                  {selected.verification_status === 'APPROVED' ? (
                    <BadgeCheck aria-hidden="true" size={15} />
                  ) : selected.verification_status === 'REJECTED' ? (
                    <ShieldAlert aria-hidden="true" size={15} />
                  ) : (
                    <FileCheck2 aria-hidden="true" size={15} />
                  )}
                  {selected.verification_status}
                </span>
              </div>
              <dl className="mt-6 grid gap-4 border-t border-line pt-5 sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">
                    Submitted file
                  </dt>
                  <dd className="mt-1 break-all text-sm font-medium text-ink-950">
                    {selected.original_filename}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">
                    File details
                  </dt>
                  <dd className="mt-1 text-sm font-medium text-ink-950">
                    {selected.mime_type} ·{' '}
                    {(selected.file_size / (1024 * 1024)).toFixed(2)} MiB
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">
                    Submitted at
                  </dt>
                  <dd className="mt-1 text-sm text-ink-800">
                    {new Date(selected.submitted_at).toLocaleString()}
                  </dd>
                </div>
                {selected.reviewed_by && selected.reviewed_at && (
                  <div>
                    <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">
                      Reviewed
                    </dt>
                    <dd className="mt-1 text-sm text-ink-800">
                      Administrator #{selected.reviewed_by} ·{' '}
                      {new Date(selected.reviewed_at).toLocaleString()}
                    </dd>
                  </div>
                )}
              </dl>

              <button
                className="mt-5 inline-flex min-h-10 items-center gap-2 rounded-xl border border-line px-4 text-sm font-semibold text-ink-800 hover:bg-sky-50"
                onClick={() => void handleDownload()}
                type="button"
              >
                <Download aria-hidden="true" size={16} />
                Secure download
              </button>

              {selected.rejection_reason && (
                <p className="mt-4 rounded-2xl bg-rose-50 p-4 text-sm text-rose-900">
                  Rejection reason: {selected.rejection_reason}
                </p>
              )}
              <section className="mt-6 border-t border-line pt-5">
                <h3 className="text-sm font-semibold text-ink-950">
                  Review history
                </h3>
                {selected.review_events.length === 0 ? (
                  <p className="mt-2 text-sm text-ink-600">
                    No administrator decisions have been recorded.
                  </p>
                ) : (
                  <ol className="mt-3 space-y-3">
                    {selected.review_events.map((event) => (
                      <li
                        className="rounded-2xl bg-sky-50 p-4 text-sm"
                        key={event.id}
                      >
                        <p className="font-semibold text-ink-950">
                          {event.action} · administrator #{event.admin_user_id}
                        </p>
                        <p className="mt-1 text-xs text-ink-600">
                          {new Date(event.created_at).toLocaleString()}
                        </p>
                        {event.reason && (
                          <p className="mt-2 leading-5 text-ink-800">
                            {event.reason}
                          </p>
                        )}
                      </li>
                    ))}
                  </ol>
                )}
              </section>

              {selected.verification_status === 'PENDING' && (
                <div className="mt-6 flex flex-wrap gap-3 border-t border-line pt-5">
                  <button
                    className="min-h-10 rounded-xl bg-emerald-700 px-4 text-sm font-semibold text-white disabled:opacity-60"
                    disabled={acting}
                    onClick={() => void runReview('approve')}
                    type="button"
                  >
                    Approve credential
                  </button>
                  <form
                    className="flex min-w-full flex-col gap-3 sm:flex-row"
                    onSubmit={handleReject}
                  >
                    <label className="sr-only" htmlFor="credential-rejection-reason">
                      Rejection reason
                    </label>
                    <input
                      className="min-h-10 min-w-0 flex-1 rounded-xl border border-line px-3 text-sm outline-none focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
                      id="credential-rejection-reason"
                      maxLength={500}
                      minLength={5}
                      onChange={(event) => setReason(event.target.value)}
                      placeholder="Required rejection reason"
                      required
                      value={reason}
                    />
                    <button
                      className="min-h-10 rounded-xl border border-rose-200 px-4 text-sm font-semibold text-rose-800 disabled:opacity-60"
                      disabled={acting || reason.trim().length < 5}
                      type="submit"
                    >
                      Reject credential
                    </button>
                  </form>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </section>
  )
}
