import { BadgeCheck, Clock3, ShieldAlert, Stethoscope } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getApiErrorMessage } from '../api/errors'
import { getMyDoctorProfile } from '../api/doctors'
import type { DoctorSelfProfile } from '../types/api'

const statusPresentation = {
  PENDING: {
    label: 'Pending review',
    className: 'bg-amber-50 text-amber-900',
    icon: Clock3,
    message:
      'Your application is awaiting administrator review. Your profile is not listed in doctor discovery yet.',
  },
  APPROVED: {
    label: 'Approved',
    className: 'bg-emerald-50 text-emerald-900',
    icon: BadgeCheck,
    message:
      'Your professional profile is approved and may appear in the patient doctor directory.',
  },
  REJECTED: {
    label: 'Rejected',
    className: 'bg-rose-50 text-rose-900',
    icon: ShieldAlert,
    message:
      'Your application was not approved. Review the administrator’s reason below.',
  },
  SUSPENDED: {
    label: 'Suspended',
    className: 'bg-rose-50 text-rose-900',
    icon: ShieldAlert,
    message:
      'Your profile is suspended and is not visible in patient doctor discovery.',
  },
} as const

export function DoctorDashboardPage() {
  const [profile, setProfile] = useState<DoctorSelfProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void getMyDoctorProfile()
      .then((data) => {
        if (active) setProfile(data)
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
  }, [])

  if (loading) {
    return <p className="rounded-2xl border border-line bg-white p-6">Loading your doctor profile…</p>
  }
  if (error || !profile) {
    return (
      <p className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800" role="alert">
        {error ?? 'Doctor profile could not be loaded.'}
      </p>
    )
  }

  const status = statusPresentation[profile.verification_status]
  const StatusIcon = status.icon

  return (
    <section className="space-y-6">
      <header>
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-700">
          Doctor workspace
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-ink-950">
          Welcome, {profile.full_name}
        </h1>
        <p className="mt-2 text-sm text-ink-600">
          Your application and verification status are shown here.
        </p>
      </header>
      <article className="rounded-3xl border border-line bg-white p-6 shadow-panel sm:p-8">
        <div className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-semibold ${status.className}`}>
          <StatusIcon aria-hidden="true" size={16} />
          {status.label}
        </div>
        <p className="mt-4 max-w-3xl text-sm leading-6 text-ink-600">{status.message}</p>
        {profile.rejection_reason && (
          <p className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm leading-6 text-rose-900">
            <strong>Administrator reason:</strong> {profile.rejection_reason}
          </p>
        )}
        <dl className="mt-7 grid gap-5 border-t border-line pt-6 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">Specialization</dt>
            <dd className="mt-1 text-sm font-medium text-ink-950">{profile.specialization}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">Qualification</dt>
            <dd className="mt-1 text-sm font-medium text-ink-950">{profile.qualification}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">Registration number</dt>
            <dd className="mt-1 text-sm font-medium text-ink-950">{profile.medical_registration_number}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">Experience</dt>
            <dd className="mt-1 text-sm font-medium text-ink-950">{profile.years_of_experience} years</dd>
          </div>
          {profile.clinic_or_hospital && (
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">Clinic or hospital</dt>
              <dd className="mt-1 text-sm font-medium text-ink-950">{profile.clinic_or_hospital}</dd>
            </div>
          )}
          {profile.consultation_fee !== null && (
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">Consultation fee</dt>
              <dd className="mt-1 text-sm font-medium text-ink-950">{profile.consultation_fee}</dd>
            </div>
          )}
        </dl>
      </article>
      <aside className="flex items-start gap-3 rounded-2xl border border-line bg-white p-5 text-sm leading-6 text-ink-600">
        <Stethoscope aria-hidden="true" className="mt-0.5 shrink-0 text-brand-700" size={18} />
        Availability management and appointment requests are part of the next
        implementation subphase.
      </aside>
    </section>
  )
}
