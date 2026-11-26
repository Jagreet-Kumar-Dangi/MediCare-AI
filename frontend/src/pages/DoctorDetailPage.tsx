import { ArrowLeft, Stethoscope } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getApiErrorMessage } from '../api/errors'
import { getDoctor } from '../api/doctors'
import type { PublicDoctorProfile } from '../types/api'

export function DoctorDetailPage() {
  const { doctorId } = useParams()
  return <DoctorDetailContent doctorId={doctorId} key={doctorId} />
}

function DoctorDetailContent({ doctorId }: { doctorId: string | undefined }) {
  const parsedDoctorId = Number(doctorId)
  const validDoctorId = Number.isInteger(parsedDoctorId) && parsedDoctorId > 0
  const [doctor, setDoctor] = useState<PublicDoctorProfile | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    if (!validDoctorId) return
    void getDoctor(parsedDoctorId)
      .then((profile) => {
        if (active) setDoctor(profile)
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
  }, [doctorId, parsedDoctorId, validDoctorId])

  if (!validDoctorId) {
    return (
      <div className="rounded-3xl border border-line bg-white p-8">
        <p className="text-sm text-rose-800">Doctor profile not found.</p>
        <Link className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-brand-700" to="/doctors">
          <ArrowLeft aria-hidden="true" size={16} />
          Back to directory
        </Link>
      </div>
    )
  }
  if (loading) {
    return <p className="rounded-2xl border border-line bg-white p-6">Loading doctor profile…</p>
  }
  if (error || !doctor) {
    return (
      <div className="rounded-3xl border border-line bg-white p-8">
        <p className="text-sm text-rose-800">{error ?? 'Doctor profile not found.'}</p>
        <Link className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-brand-700" to="/doctors">
          <ArrowLeft aria-hidden="true" size={16} />
          Back to directory
        </Link>
      </div>
    )
  }

  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <Link className="inline-flex items-center gap-2 text-sm font-semibold text-brand-700" to="/doctors">
        <ArrowLeft aria-hidden="true" size={16} />
        Back to directory
      </Link>
      <article className="rounded-3xl border border-line bg-white p-6 shadow-panel sm:p-9">
        <div className="grid size-14 place-items-center rounded-2xl bg-brand-100 text-brand-700">
          <Stethoscope aria-hidden="true" size={24} />
        </div>
        <h1 className="mt-5 text-3xl font-semibold tracking-[-0.04em] text-ink-950">
          {doctor.full_name}
        </h1>
        <p className="mt-2 text-base font-semibold text-brand-700">
          {doctor.specialization}
        </p>
        <dl className="mt-7 grid gap-5 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">
              Qualification
            </dt>
            <dd className="mt-1 text-sm font-medium text-ink-950">{doctor.qualification}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">
              Experience
            </dt>
            <dd className="mt-1 text-sm font-medium text-ink-950">
              {doctor.years_of_experience} years
            </dd>
          </div>
          {doctor.clinic_or_hospital && (
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">
                Clinic or hospital
              </dt>
              <dd className="mt-1 text-sm font-medium text-ink-950">
                {doctor.clinic_or_hospital}
              </dd>
            </div>
          )}
          {doctor.consultation_fee !== null && (
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-600">
                Consultation fee
              </dt>
              <dd className="mt-1 text-sm font-medium text-ink-950">
                {doctor.consultation_fee}
              </dd>
            </div>
          )}
        </dl>
        {doctor.biography && (
          <div className="mt-7 border-t border-line pt-6">
            <h2 className="text-sm font-semibold text-ink-950">About</h2>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-ink-600">
              {doctor.biography}
            </p>
          </div>
        )}
        <p className="mt-7 rounded-2xl bg-sky-50 p-4 text-sm leading-6 text-ink-600">
          Appointment booking is not available yet. This profile is listed
          because its doctor account has been approved.
        </p>
      </article>
    </section>
  )
}
