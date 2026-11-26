import { ArrowLeft, CalendarDays, Stethoscope } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { createAppointment, getAvailableSlots } from '../api/appointments'
import { getApiErrorMessage } from '../api/errors'
import { getDoctor } from '../api/doctors'
import { useAuth } from '../auth/useAuth'
import type { AvailableSlotsResponse, PublicDoctorProfile } from '../types/api'

function localDateAfter(days: number): string {
  const date = new Date()
  date.setDate(date.getDate() + days)
  const offset = date.getTimezoneOffset()
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 10)
}

export function DoctorDetailPage() {
  const { doctorId } = useParams()
  return <DoctorDetailContent doctorId={doctorId} key={doctorId} />
}

function DoctorDetailContent({ doctorId }: { doctorId: string | undefined }) {
  const parsedDoctorId = Number(doctorId)
  const validDoctorId = Number.isInteger(parsedDoctorId) && parsedDoctorId > 0
  const { status: authStatus, user } = useAuth()
  const [doctor, setDoctor] = useState<PublicDoctorProfile | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [appointmentDate, setAppointmentDate] = useState(localDateAfter(7))
  const [availableSlots, setAvailableSlots] =
    useState<AvailableSlotsResponse | null>(null)
  const [booking, setBooking] = useState(false)
  const [bookingError, setBookingError] = useState<string | null>(null)
  const [bookingNotice, setBookingNotice] = useState<string | null>(null)
  const [selectedStart, setSelectedStart] = useState('')
  const [visitReason, setVisitReason] = useState('')
  const [patientNotes, setPatientNotes] = useState('')
  const [slotRefreshVersion, setSlotRefreshVersion] = useState(0)

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

  useEffect(() => {
    let active = true
    if (!doctor || authStatus !== 'authenticated' || user?.role !== 'PATIENT') {
      return
    }
    void getAvailableSlots(doctor.id, appointmentDate)
      .then((result) => {
        if (active) {
          setAvailableSlots(result)
          setSelectedStart('')
        }
      })
      .catch((requestError: unknown) => {
        if (active) setBookingError(getApiErrorMessage(requestError))
      })
    return () => {
      active = false
    }
  }, [appointmentDate, authStatus, doctor, slotRefreshVersion, user?.role])

  async function handleBooking(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!doctor || !selectedStart) return
    setBooking(true)
    setBookingError(null)
    setBookingNotice(null)
    try {
      const appointment = await createAppointment({
        doctor_id: doctor.id,
        scheduled_start: selectedStart,
        reason_for_visit: visitReason.trim(),
        patient_notes: patientNotes.trim() || undefined,
      })
      setBookingNotice(
        `Appointment requested for ${new Date(appointment.scheduled_start).toLocaleString()}.`,
      )
      setAvailableSlots(null)
      setVisitReason('')
      setPatientNotes('')
      setSelectedStart('')
      setSlotRefreshVersion((version) => version + 1)
    } catch (requestError) {
      setBookingError(getApiErrorMessage(requestError))
    } finally {
      setBooking(false)
    }
  }

  const slotsLoading =
    authStatus === 'authenticated'
    && user?.role === 'PATIENT'
    && Boolean(doctor)
    && availableSlots?.date !== appointmentDate
    && !bookingError

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
      </article>
      {authStatus === 'authenticated' && user?.role === 'PATIENT' ? (
        <section className="rounded-3xl border border-line bg-white p-6 shadow-panel sm:p-8">
          <div className="flex items-center gap-2">
            <CalendarDays aria-hidden="true" className="text-brand-700" size={20} />
            <h2 className="text-xl font-semibold text-ink-950">Request an appointment</h2>
          </div>
          <p className="mt-2 text-sm text-ink-600">
            Times are shown in {availableSlots?.timezone ?? 'the configured clinic timezone'}.
            The doctor must confirm your request.
          </p>
          {bookingError && (
            <p className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800" role="alert">
              {bookingError}
            </p>
          )}
          {bookingNotice && (
            <p className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900" role="status">
              {bookingNotice}
            </p>
          )}
          <form className="mt-5 grid gap-4 sm:grid-cols-2" onSubmit={(event) => void handleBooking(event)}>
            <label className="space-y-2 text-sm font-semibold text-ink-800">
              Appointment date
              <input
                className="min-h-11 w-full rounded-xl border border-line px-3 text-sm font-normal"
                min={localDateAfter(1)}
                onChange={(event) => {
                  setBookingError(null)
                  setAppointmentDate(event.target.value)
                }}
                required
                type="date"
                value={appointmentDate}
              />
            </label>
            <label className="space-y-2 text-sm font-semibold text-ink-800">
              Available time
              <select
                className="min-h-11 w-full rounded-xl border border-line px-3 text-sm font-normal"
                onChange={(event) => setSelectedStart(event.target.value)}
                required
                value={selectedStart}
              >
                <option value="">Select a time</option>
                {availableSlots?.date === appointmentDate && availableSlots.slots.map((slot) => (
                  <option key={slot.scheduled_start} value={slot.scheduled_start}>
                    {new Date(slot.scheduled_start).toLocaleTimeString([], {
                      hour: 'numeric',
                      minute: '2-digit',
                      timeZone: availableSlots.timezone,
                    })}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2 text-sm font-semibold text-ink-800 sm:col-span-2">
              Reason for visit
              <input
                className="min-h-11 w-full rounded-xl border border-line px-3 text-sm font-normal"
                maxLength={1000}
                minLength={1}
                onChange={(event) => setVisitReason(event.target.value)}
                required
                value={visitReason}
              />
            </label>
            <label className="space-y-2 text-sm font-semibold text-ink-800 sm:col-span-2">
              Optional notes for the doctor
              <textarea
                className="min-h-20 w-full rounded-xl border border-line p-3 text-sm font-normal"
                maxLength={4000}
                onChange={(event) => setPatientNotes(event.target.value)}
                value={patientNotes}
              />
            </label>
            {slotsLoading && (
              <p className="text-sm text-ink-600 sm:col-span-2">Loading available times…</p>
            )}
            {!slotsLoading && availableSlots?.date === appointmentDate && availableSlots.slots.length === 0 && (
              <p className="text-sm text-ink-600 sm:col-span-2">No available times on this date.</p>
            )}
            <button
              className="min-h-11 rounded-xl bg-brand-700 px-5 text-sm font-semibold text-white disabled:opacity-60 sm:col-span-2 sm:justify-self-start"
              disabled={booking || slotsLoading || !selectedStart || !visitReason.trim()}
              type="submit"
            >
              {booking ? 'Requesting…' : 'Request appointment'}
            </button>
          </form>
        </section>
      ) : authStatus === 'authenticated' ? (
        <p className="rounded-2xl bg-sky-50 p-4 text-sm text-ink-700">
          Appointment requests are available to patient accounts.
        </p>
      ) : (
        <p className="rounded-2xl bg-sky-50 p-4 text-sm text-ink-700">
          <Link className="font-semibold text-brand-700 underline" to="/login">
            Sign in as a patient
          </Link>{' '}
          to request an appointment.
        </p>
      )}
    </section>
  )
}
