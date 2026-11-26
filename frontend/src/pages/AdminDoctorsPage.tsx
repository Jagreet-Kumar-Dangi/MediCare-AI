import { BadgeCheck, Clock3, Eye, ShieldAlert, UserRoundCheck } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { getApiErrorMessage } from '../api/errors'
import {
  approveDoctor,
  getDoctorApplication,
  listApprovedDoctorsForAdmin,
  listPendingDoctors,
  listSuspendedDoctors,
  rejectDoctor,
  suspendDoctor,
} from '../api/doctors'
import type { DoctorVerificationDetail } from '../types/api'

type ApplicationView = 'pending' | 'approved' | 'suspended'

const viewLabels: Record<ApplicationView, string> = {
  pending: 'Pending applications',
  approved: 'Approved doctors',
  suspended: 'Suspended doctors',
}

export function AdminDoctorsPage() {
  const [view, setView] = useState<ApplicationView>('pending')
  const [applications, setApplications] = useState<DoctorVerificationDetail[]>([])
  const [selected, setSelected] = useState<DoctorVerificationDetail | null>(null)
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [refreshVersion, setRefreshVersion] = useState(0)

  useEffect(() => {
    let active = true
    const loaders = {
      pending: listPendingDoctors,
      approved: listApprovedDoctorsForAdmin,
      suspended: listSuspendedDoctors,
    }
    void loaders[view]()
      .then((result) => {
        if (active) setApplications(result)
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
  }, [view, refreshVersion])

  async function openApplication(id: number) {
    setError(null)
    try {
      setSelected(await getDoctorApplication(id))
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    }
  }

  async function runAction(action: 'approve' | 'reject' | 'suspend') {
    if (!selected) return
    if (action !== 'approve' && reason.trim().length < 5) {
      setError('Enter a reason of at least five characters.')
      return
    }
    setActing(true)
    setError(null)
    setNotice(null)
    try {
      if (action === 'approve') await approveDoctor(selected.id)
      if (action === 'reject') await rejectDoctor(selected.id, reason.trim())
      if (action === 'suspend') await suspendDoctor(selected.id, reason.trim())
      setSelected(null)
      setReason('')
      setNotice(
        action === 'approve'
          ? 'Doctor application approved.'
          : action === 'reject'
            ? 'Doctor application rejected.'
            : 'Doctor profile suspended.',
      )
      setLoading(true)
      setRefreshVersion((version) => version + 1)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setActing(false)
    }
  }

  function handleReasonSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const action = view === 'pending' ? 'reject' : 'suspend'
    void runAction(action)
  }

  const canApproveOrReject =
    view === 'pending' && selected?.verification_status === 'PENDING'
  const canSuspend =
    view === 'approved' && selected?.verification_status === 'APPROVED'

  return (
    <section className="space-y-6">
      <header>
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-700">
          Administrator workspace
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-ink-950">
          Doctor verification
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-600">
          Review submitted profile information and record a verification
          decision. Each decision is associated with your administrator account.
        </p>
      </header>

      <div className="flex flex-wrap gap-2" aria-label="Doctor application status">
        {(Object.keys(viewLabels) as ApplicationView[]).map((value) => (
          <button
            aria-pressed={view === value}
            className={`min-h-10 rounded-xl px-4 text-sm font-semibold transition ${
              view === value
                ? 'bg-brand-700 text-white'
                : 'border border-line bg-white text-ink-700 hover:bg-sky-50'
            }`}
            key={value}
            onClick={() => {
              setView(value)
              setSelected(null)
              setNotice(null)
              setError(null)
              setLoading(true)
              setApplications([])
            }}
            type="button"
          >
            {viewLabels[value]}
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
            {viewLabels[view]}
          </h2>
          {loading ? (
            <p className="p-5 text-sm text-ink-600">Loading applications…</p>
          ) : applications.length === 0 ? (
            <p className="p-5 text-sm text-ink-600">No doctors in this list.</p>
          ) : (
            <ul className="divide-y divide-line">
              {applications.map((application) => (
                <li key={application.id}>
                  <button
                    className={`flex min-h-20 w-full items-center justify-between gap-3 px-5 py-4 text-left transition hover:bg-sky-50 ${
                      selected?.id === application.id ? 'bg-sky-50' : ''
                    }`}
                    onClick={() => void openApplication(application.id)}
                    type="button"
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-semibold text-ink-950">
                        {application.full_name}
                      </span>
                      <span className="mt-1 block truncate text-xs text-ink-600">
                        {application.specialization} · {application.email}
                      </span>
                    </span>
                    <Eye aria-hidden="true" className="shrink-0 text-brand-700" size={17} />
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
                <UserRoundCheck aria-hidden="true" className="mx-auto text-brand-700" size={30} />
                <p className="mt-3 text-sm text-ink-600">
                  Select an application to review its profile information.
                </p>
              </div>
            </div>
          ) : (
            <div>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold text-ink-950">
                    {selected.full_name}
                  </h2>
                  <p className="mt-1 text-sm text-ink-600">{selected.email}</p>
                </div>
                <span className="inline-flex items-center gap-2 rounded-full bg-sky-50 px-3 py-1.5 text-xs font-semibold text-brand-800">
                  {selected.verification_status === 'APPROVED' ? (
                    <BadgeCheck aria-hidden="true" size={15} />
                  ) : selected.verification_status === 'PENDING' ? (
                    <Clock3 aria-hidden="true" size={15} />
                  ) : (
                    <ShieldAlert aria-hidden="true" size={15} />
                  )}
                  {selected.verification_status}
                </span>
              </div>
              <dl className="mt-6 grid gap-4 border-t border-line pt-5 sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">Specialization</dt>
                  <dd className="mt-1 text-sm font-medium text-ink-950">{selected.specialization}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">Qualification</dt>
                  <dd className="mt-1 text-sm font-medium text-ink-950">{selected.qualification}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">Registration number</dt>
                  <dd className="mt-1 text-sm font-medium text-ink-950">{selected.medical_registration_number}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">Experience</dt>
                  <dd className="mt-1 text-sm font-medium text-ink-950">{selected.years_of_experience} years</dd>
                </div>
                {selected.phone_number && (
                  <div>
                    <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">Phone</dt>
                    <dd className="mt-1 text-sm font-medium text-ink-950">{selected.phone_number}</dd>
                  </div>
                )}
                {selected.clinic_or_hospital && (
                  <div>
                    <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">Clinic or hospital</dt>
                    <dd className="mt-1 text-sm font-medium text-ink-950">{selected.clinic_or_hospital}</dd>
                  </div>
                )}
                {selected.biography && (
                  <div className="sm:col-span-2">
                    <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">Biography</dt>
                    <dd className="mt-1 whitespace-pre-wrap text-sm leading-6 text-ink-800">{selected.biography}</dd>
                  </div>
                )}
                {selected.rejection_reason && (
                  <div className="sm:col-span-2">
                    <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">Previous rejection reason</dt>
                    <dd className="mt-1 text-sm text-ink-800">{selected.rejection_reason}</dd>
                  </div>
                )}
              </dl>
              <section className="mt-6 border-t border-line pt-5">
                <h3 className="text-sm font-semibold text-ink-950">
                  Verification audit trail
                </h3>
                {selected.verification_events.length === 0 ? (
                  <p className="mt-2 text-sm text-ink-600">
                    No administrator decisions have been recorded.
                  </p>
                ) : (
                  <ol className="mt-3 space-y-3">
                    {selected.verification_events.map((event) => (
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
              <p className="mt-5 rounded-2xl bg-amber-50 p-4 text-xs leading-5 text-amber-900">
                Credential documents are not collected in this subphase. Verify
                registration through the organization’s trusted process before
                approving.
              </p>

              {canApproveOrReject && (
                <div className="mt-5 flex flex-wrap gap-3">
                  <button
                    className="min-h-10 rounded-xl bg-emerald-700 px-4 text-sm font-semibold text-white disabled:opacity-60"
                    disabled={acting}
                    onClick={() => void runAction('approve')}
                    type="button"
                  >
                    Approve
                  </button>
                  <form className="flex min-w-full flex-col gap-3 sm:flex-row" onSubmit={handleReasonSubmit}>
                    <label className="sr-only" htmlFor="verification-reason">Rejection reason</label>
                    <input
                      className="min-h-10 min-w-0 flex-1 rounded-xl border border-line px-3 text-sm outline-none focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
                      id="verification-reason"
                      maxLength={500}
                      minLength={5}
                      onChange={(event) => setReason(event.target.value)}
                      placeholder="Required reason for rejection"
                      required
                      value={reason}
                    />
                    <button
                      className="min-h-10 rounded-xl border border-rose-200 px-4 text-sm font-semibold text-rose-800 disabled:opacity-60"
                      disabled={acting || reason.trim().length < 5}
                      type="submit"
                    >
                      Reject
                    </button>
                  </form>
                </div>
              )}
              {canSuspend && (
                <form className="mt-5 flex flex-col gap-3 sm:flex-row" onSubmit={handleReasonSubmit}>
                  <label className="sr-only" htmlFor="suspension-reason">Suspension reason</label>
                  <input
                    className="min-h-10 min-w-0 flex-1 rounded-xl border border-line px-3 text-sm outline-none focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
                    id="suspension-reason"
                    maxLength={500}
                    minLength={5}
                    onChange={(event) => setReason(event.target.value)}
                    placeholder="Required reason for suspension"
                    required
                    value={reason}
                  />
                  <button
                    className="min-h-10 rounded-xl border border-rose-200 px-4 text-sm font-semibold text-rose-800 disabled:opacity-60"
                    disabled={acting || reason.trim().length < 5}
                    type="submit"
                  >
                    Suspend doctor
                  </button>
                </form>
              )}
            </div>
          )}
        </section>
      </div>
    </section>
  )
}
