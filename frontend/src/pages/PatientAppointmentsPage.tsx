import { CalendarClock, CalendarX2, Clock3, Stethoscope } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { getApiErrorMessage } from '../api/errors'
import {
  cancelAppointment,
  getAvailableSlots,
  getMyAppointments,
  rescheduleAppointment,
} from '../api/appointments'
import type { Appointment, AvailableSlotsResponse } from '../types/api'

function localDateAfter(days: number): string {
  const date = new Date()
  date.setDate(date.getDate() + days)
  const offset = date.getTimezoneOffset()
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 10)
}

function appointmentTime(value: string): string {
  return new Date(value).toLocaleString()
}

export function PatientAppointmentsPage() {
  const [view, setView] = useState<'upcoming' | 'history'>('upcoming')
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [refreshVersion, setRefreshVersion] = useState(0)
  const [cancellingId, setCancellingId] = useState<number | null>(null)
  const [cancellationReason, setCancellationReason] = useState('')
  const [reschedulingId, setReschedulingId] = useState<number | null>(null)
  const [rescheduleDate, setRescheduleDate] = useState(localDateAfter(7))
  const [available, setAvailable] = useState<AvailableSlotsResponse | null>(null)
  const [selectedStart, setSelectedStart] = useState('')
  const [rescheduleReason, setRescheduleReason] = useState('')

  useEffect(() => {
    let active = true
    void getMyAppointments(view)
      .then((result) => {
        if (active) setAppointments(result)
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
  }, [refreshVersion, view])

  useEffect(() => {
    let active = true
    if (reschedulingId === null) return
    const appointment = appointments.find((item) => item.id === reschedulingId)
    if (!appointment) return
    void getAvailableSlots(
      appointment.doctor.id,
      rescheduleDate,
    )
      .then((result) => {
        if (active) {
          setAvailable(result)
          setSelectedStart('')
        }
      })
      .catch((requestError: unknown) => {
        if (active) setError(getApiErrorMessage(requestError))
      })
    return () => {
      active = false
    }
  }, [appointments, rescheduleDate, reschedulingId])

  function refresh() {
    setLoading(true)
    setError(null)
    setRefreshVersion((version) => version + 1)
  }

  async function handleCancel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (cancellingId === null) return
    setActing(true)
    setError(null)
    setNotice(null)
    try {
      await cancelAppointment(cancellingId, cancellationReason.trim())
      setNotice('Appointment cancelled.')
      setCancellingId(null)
      setCancellationReason('')
      refresh()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setActing(false)
    }
  }

  async function handleReschedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (reschedulingId === null || !selectedStart) return
    setActing(true)
    setError(null)
    setNotice(null)
    try {
      await rescheduleAppointment(
        reschedulingId,
        selectedStart,
        rescheduleReason.trim(),
      )
      setNotice('Appointment rescheduled. The doctor will need to confirm the new time.')
      setReschedulingId(null)
      setRescheduleReason('')
      setAvailable(null)
      refresh()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setActing(false)
    }
  }

  return (
    <section className="space-y-6">
      <header>
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-700">
          Patient portal
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-ink-950">
          My appointments
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-600">
          Review your bookings, request a new time, or cancel outside the configured
          24-hour cutoff.
        </p>
      </header>

      <div className="flex flex-wrap gap-2" aria-label="Appointment list">
        {(['upcoming', 'history'] as const).map((value) => (
          <button
            aria-pressed={view === value}
            className={`min-h-10 rounded-xl px-4 text-sm font-semibold capitalize ${
              view === value
                ? 'bg-brand-700 text-white'
                : 'border border-line bg-white text-ink-700 hover:bg-sky-50'
            }`}
            key={value}
            onClick={() => {
              setLoading(true)
              setError(null)
              setView(value)
            }}
            type="button"
          >
            {value}
          </button>
        ))}
      </div>

      {error && (
        <p className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900" role="status">
          {notice}
        </p>
      )}

      {loading ? (
        <p className="rounded-2xl border border-line bg-white p-6 text-sm text-ink-600">
          Loading appointments…
        </p>
      ) : appointments.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-line bg-white p-10 text-center">
          <CalendarClock aria-hidden="true" className="mx-auto text-brand-700" size={28} />
          <h2 className="mt-3 text-lg font-semibold text-ink-950">
            No {view} appointments
          </h2>
          <p className="mt-2 text-sm text-ink-600">
            Approved doctors and available times are listed in the doctor directory.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {appointments.map((appointment) => (
            <article
              className="rounded-3xl border border-line bg-white p-5 shadow-panel sm:p-6"
              key={appointment.id}
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="flex items-center gap-2 text-lg font-semibold text-ink-950">
                    <Stethoscope aria-hidden="true" className="text-brand-700" size={18} />
                    {appointment.doctor.full_name}
                  </p>
                  <p className="mt-2 flex items-center gap-2 text-sm text-ink-700">
                    <Clock3 aria-hidden="true" size={15} />
                    {appointmentTime(appointment.scheduled_start)}
                  </p>
                  <p className="mt-2 text-sm text-ink-600">
                    {appointment.reason_for_visit}
                  </p>
                </div>
                <span className="rounded-full bg-sky-50 px-3 py-1.5 text-xs font-bold text-brand-800">
                  {appointment.status}
                </span>
              </div>
              {appointment.cancellation_reason && (
                <p className="mt-3 rounded-xl bg-sky-50 p-3 text-sm text-ink-700">
                  Cancellation reason: {appointment.cancellation_reason}
                </p>
              )}
              {appointment.rejection_reason && (
                <p className="mt-3 rounded-xl bg-rose-50 p-3 text-sm text-rose-900">
                  Doctor response: {appointment.rejection_reason}
                </p>
              )}
              {appointment.status === 'BOOKED' || appointment.status === 'CONFIRMED' ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    className="min-h-10 rounded-xl border border-line px-4 text-sm font-semibold text-ink-800 hover:bg-sky-50"
                    onClick={() => {
                      setError(null)
                      setReschedulingId(appointment.id)
                      setRescheduleDate(localDateAfter(7))
                      setAvailable(null)
                    }}
                    type="button"
                  >
                    Reschedule
                  </button>
                  <button
                    className="min-h-10 rounded-xl border border-rose-200 px-4 text-sm font-semibold text-rose-800 hover:bg-rose-50"
                    onClick={() => {
                      setError(null)
                      setCancellingId(appointment.id)
                      setCancellationReason('')
                    }}
                    type="button"
                  >
                    <CalendarX2 aria-hidden="true" className="mr-2 inline" size={15} />
                    Cancel appointment
                  </button>
                </div>
              ) : null}

              {cancellingId === appointment.id && (
                <form className="mt-4 flex flex-col gap-3 border-t border-line pt-4 sm:flex-row" onSubmit={(event) => void handleCancel(event)}>
                  <label className="sr-only" htmlFor={`cancel-reason-${appointment.id}`}>
                    Cancellation reason
                  </label>
                  <input
                    className="min-h-10 min-w-0 flex-1 rounded-xl border border-line px-3 text-sm"
                    id={`cancel-reason-${appointment.id}`}
                    minLength={5}
                    onChange={(event) => setCancellationReason(event.target.value)}
                    placeholder="Reason for cancellation"
                    required
                    value={cancellationReason}
                  />
                  <button className="min-h-10 rounded-xl bg-rose-700 px-4 text-sm font-semibold text-white disabled:opacity-60" disabled={acting || cancellationReason.trim().length < 5} type="submit">
                    Confirm cancellation
                  </button>
                  <button className="min-h-10 rounded-xl border border-line px-4 text-sm font-semibold" onClick={() => setCancellingId(null)} type="button">
                    Keep
                  </button>
                </form>
              )}

              {reschedulingId === appointment.id && (
                <form className="mt-4 space-y-3 border-t border-line pt-4" onSubmit={(event) => void handleReschedule(event)}>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="space-y-1 text-xs font-semibold text-ink-700">
                      New date
                      <input
                        className="min-h-10 w-full rounded-xl border border-line px-3 text-sm"
                        min={localDateAfter(1)}
                        onChange={(event) => {
                          setError(null)
                          setAvailable(null)
                          setRescheduleDate(event.target.value)
                        }}
                        type="date"
                        value={rescheduleDate}
                      />
                    </label>
                    <label className="space-y-1 text-xs font-semibold text-ink-700">
                      Available time
                      <select
                        className="min-h-10 w-full rounded-xl border border-line px-3 text-sm"
                        onChange={(event) => setSelectedStart(event.target.value)}
                        required
                        value={selectedStart}
                      >
                        <option value="">Select a time</option>
                        {available?.slots.map((slot) => (
                          <option key={slot.scheduled_start} value={slot.scheduled_start}>
                            {new Date(slot.scheduled_start).toLocaleTimeString([], {
                              hour: 'numeric',
                              minute: '2-digit',
                              timeZone: available.timezone,
                            })}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                  {reschedulingId !== null && available?.date !== rescheduleDate && !error && (
                    <p className="text-sm text-ink-600">Loading available times…</p>
                  )}
                  {available?.date === rescheduleDate && available.slots.length === 0 && (
                    <p className="text-sm text-ink-600">No available times on this date.</p>
                  )}
                  <label className="block space-y-1 text-xs font-semibold text-ink-700">
                    Reason for rescheduling
                    <input
                      className="min-h-10 w-full rounded-xl border border-line px-3 text-sm"
                      minLength={5}
                      onChange={(event) => setRescheduleReason(event.target.value)}
                      required
                      value={rescheduleReason}
                    />
                  </label>
                  <div className="flex gap-2">
                    <button className="min-h-10 rounded-xl bg-brand-700 px-4 text-sm font-semibold text-white disabled:opacity-60"                     disabled={acting || available?.date !== rescheduleDate || !selectedStart || rescheduleReason.trim().length < 5} type="submit">
                      Confirm new time
                    </button>
                    <button className="min-h-10 rounded-xl border border-line px-4 text-sm font-semibold" onClick={() => setReschedulingId(null)} type="button">
                      Keep current time
                    </button>
                  </div>
                </form>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
