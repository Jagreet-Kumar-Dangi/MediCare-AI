import { CalendarDays, CalendarOff, Check, Clock3, X } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { getApiErrorMessage } from '../api/errors'
import {
  cancelDoctorAppointment,
  createDoctorAvailability,
  createDoctorAvailabilityException,
  deleteDoctorAvailability,
  deleteDoctorAvailabilityException,
  doctorAppointmentAction,
  getDoctorAppointments,
  getDoctorAvailability,
  getDoctorAvailabilityExceptions,
  rejectDoctorAppointment,
  updateDoctorAppointmentNotes,
} from '../api/appointments'
import type {
  Appointment,
  AvailabilityException,
  DoctorAvailability,
} from '../types/api'

const weekdays = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
]

function dateLabel(value: string): string {
  return new Date(value).toLocaleString()
}

interface DoctorAppointmentsSectionProps {
  canPublishAvailability: boolean
}

export function DoctorAppointmentsSection({
  canPublishAvailability,
}: DoctorAppointmentsSectionProps) {
  const [availability, setAvailability] = useState<DoctorAvailability[]>([])
  const [exceptions, setExceptions] = useState<AvailabilityException[]>([])
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [view, setView] = useState<'upcoming' | 'history'>('upcoming')
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [refreshVersion, setRefreshVersion] = useState(0)
  const [weekday, setWeekday] = useState('0')
  const [startTime, setStartTime] = useState('09:00')
  const [endTime, setEndTime] = useState('17:00')
  const [duration, setDuration] = useState('30')
  const [breakStart, setBreakStart] = useState('')
  const [breakEnd, setBreakEnd] = useState('')
  const [exceptionDate, setExceptionDate] = useState('')
  const [exceptionReason, setExceptionReason] = useState('')
  const [exceptionStart, setExceptionStart] = useState('')
  const [exceptionEnd, setExceptionEnd] = useState('')
  const [rejectingId, setRejectingId] = useState<number | null>(null)
  const [rejectionReason, setRejectionReason] = useState('')
  const [cancellingId, setCancellingId] = useState<number | null>(null)
  const [cancellationReason, setCancellationReason] = useState('')
  const [notes, setNotes] = useState<Record<number, string>>({})

  useEffect(() => {
    let active = true
    void Promise.all([
      getDoctorAvailability(),
      getDoctorAvailabilityExceptions(),
      getDoctorAppointments(view),
    ])
      .then(([rules, blockedDates, items]) => {
        if (!active) return
        setAvailability(rules)
        setExceptions(blockedDates)
        setAppointments(items)
        setNotes(
          Object.fromEntries(
            items.map((item) => [item.id, item.doctor_notes ?? '']),
          ),
        )
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

  function refresh() {
    setLoading(true)
    setError(null)
    setRefreshVersion((version) => version + 1)
  }

  async function handleAvailabilitySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setActing(true)
    setError(null)
    setNotice(null)
    try {
      await createDoctorAvailability({
        weekday: Number(weekday),
        start_time: `${startTime}:00`,
        end_time: `${endTime}:00`,
        break_start: breakStart ? `${breakStart}:00` : null,
        break_end: breakEnd ? `${breakEnd}:00` : null,
        appointment_duration_minutes: Number(duration),
      })
      setNotice('Weekly availability saved.')
      refresh()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setActing(false)
    }
  }

  async function handleExceptionSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setActing(true)
    setError(null)
    setNotice(null)
    try {
      await createDoctorAvailabilityException({
        exception_date: exceptionDate,
        start_time: exceptionStart ? `${exceptionStart}:00` : null,
        end_time: exceptionEnd ? `${exceptionEnd}:00` : null,
        reason: exceptionReason.trim(),
      })
      setNotice('Unavailable date or time saved.')
      setExceptionReason('')
      setExceptionStart('')
      setExceptionEnd('')
      refresh()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setActing(false)
    }
  }

  async function runAppointmentAction(
    appointmentId: number,
    action: 'confirm' | 'complete' | 'no-show',
  ) {
    setActing(true)
    setError(null)
    setNotice(null)
    try {
      await doctorAppointmentAction(appointmentId, action)
      setNotice(`Appointment ${action === 'no-show' ? 'marked no-show' : `${action}ed`}.`)
      refresh()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setActing(false)
    }
  }

  async function handleReject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (rejectingId === null) return
    setActing(true)
    setError(null)
    try {
      await rejectDoctorAppointment(rejectingId, rejectionReason.trim())
      setNotice('Appointment request rejected.')
      setRejectingId(null)
      setRejectionReason('')
      refresh()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setActing(false)
    }
  }

  async function handleDoctorCancel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (cancellingId === null) return
    setActing(true)
    setError(null)
    try {
      await cancelDoctorAppointment(cancellingId, cancellationReason.trim())
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

  async function saveNotes(appointmentId: number) {
    setActing(true)
    setError(null)
    try {
      await updateDoctorAppointmentNotes(appointmentId, notes[appointmentId] ?? '')
      setNotice('Private clinical notes saved.')
      refresh()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setActing(false)
    }
  }

  async function removeAvailability(id: number) {
    setActing(true)
    setError(null)
    try {
      await deleteDoctorAvailability(id)
      setNotice('Availability window removed.')
      refresh()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setActing(false)
    }
  }

  async function removeException(item: AvailabilityException) {
    setActing(true)
    setError(null)
    try {
      await deleteDoctorAvailabilityException(item.id)
      setNotice('Unavailable date removed.')
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
          Scheduling
        </p>
        <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-ink-950">
          Availability and appointments
        </h2>
        <p className="mt-2 text-sm leading-6 text-ink-600">
          Weekly times use the configured clinic timezone. Confirmed and booked
          appointments are protected from overlapping bookings.
        </p>
      </header>

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

      <div className="grid gap-5 xl:grid-cols-2">
        <section className="rounded-3xl border border-line bg-white p-5 shadow-panel sm:p-6">
          <div className="flex items-center gap-2">
            <CalendarDays aria-hidden="true" className="text-brand-700" size={18} />
            <h3 className="text-lg font-semibold text-ink-950">Weekly availability</h3>
          </div>
          {!canPublishAvailability && (
            <p className="mt-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">
              Availability can be published after the doctor profile and required
              credentials are approved.
            </p>
          )}
          {canPublishAvailability && (
            <form className="mt-4 grid gap-3 sm:grid-cols-2" onSubmit={(event) => void handleAvailabilitySubmit(event)}>
              <label className="space-y-1 text-xs font-semibold text-ink-700">
                Working day
                <select className="min-h-10 w-full rounded-xl border border-line px-3 text-sm" onChange={(event) => setWeekday(event.target.value)} value={weekday}>
                  {weekdays.map((day, index) => <option key={day} value={index}>{day}</option>)}
                </select>
              </label>
              <label className="space-y-1 text-xs font-semibold text-ink-700">
                Appointment duration
                <select className="min-h-10 w-full rounded-xl border border-line px-3 text-sm" onChange={(event) => setDuration(event.target.value)} value={duration}>
                  {[15, 20, 30, 45, 60].map((minutes) => <option key={minutes} value={minutes}>{minutes} minutes</option>)}
                </select>
              </label>
              <label className="space-y-1 text-xs font-semibold text-ink-700">
                Start time
                <input className="min-h-10 w-full rounded-xl border border-line px-3 text-sm" onChange={(event) => setStartTime(event.target.value)} required type="time" value={startTime} />
              </label>
              <label className="space-y-1 text-xs font-semibold text-ink-700">
                End time
                <input className="min-h-10 w-full rounded-xl border border-line px-3 text-sm" onChange={(event) => setEndTime(event.target.value)} required type="time" value={endTime} />
              </label>
              <label className="space-y-1 text-xs font-semibold text-ink-700">
                Break starts (optional)
                <input className="min-h-10 w-full rounded-xl border border-line px-3 text-sm" onChange={(event) => setBreakStart(event.target.value)} type="time" value={breakStart} />
              </label>
              <label className="space-y-1 text-xs font-semibold text-ink-700">
                Break ends (optional)
                <input className="min-h-10 w-full rounded-xl border border-line px-3 text-sm" onChange={(event) => setBreakEnd(event.target.value)} type="time" value={breakEnd} />
              </label>
              <button className="min-h-10 rounded-xl bg-brand-700 px-4 text-sm font-semibold text-white disabled:opacity-60 sm:col-span-2" disabled={acting || (Boolean(breakStart) !== Boolean(breakEnd))} type="submit">
                Save availability
              </button>
            </form>
          )}
          <ul className="mt-5 divide-y divide-line">
            {availability.map((rule) => (
              <li className="flex items-center justify-between gap-3 py-3" key={rule.id}>
                <span className="text-sm text-ink-800">
                  <strong>{weekdays[rule.weekday]}</strong> · {rule.start_time.slice(0, 5)}–{rule.end_time.slice(0, 5)} · {rule.appointment_duration_minutes} min
                  {rule.break_start && rule.break_end ? ` · break ${rule.break_start.slice(0, 5)}–${rule.break_end.slice(0, 5)}` : ''}
                </span>
                <button aria-label={`Remove ${weekdays[rule.weekday]} availability`} className="rounded-lg p-2 text-rose-800 hover:bg-rose-50" disabled={acting} onClick={() => void removeAvailability(rule.id)} type="button">
                  <X aria-hidden="true" size={16} />
                </button>
              </li>
            ))}
            {!loading && availability.length === 0 && (
              <li className="py-3 text-sm text-ink-600">No weekly availability configured.</li>
            )}
          </ul>
        </section>

        <section className="rounded-3xl border border-line bg-white p-5 shadow-panel sm:p-6">
          <div className="flex items-center gap-2">
            <CalendarOff aria-hidden="true" className="text-brand-700" size={18} />
            <h3 className="text-lg font-semibold text-ink-950">Unavailable dates</h3>
          </div>
          {canPublishAvailability && (
            <form className="mt-4 grid gap-3 sm:grid-cols-2" onSubmit={(event) => void handleExceptionSubmit(event)}>
              <label className="space-y-1 text-xs font-semibold text-ink-700">
                Date
                <input className="min-h-10 w-full rounded-xl border border-line px-3 text-sm" min={localNowDate()} onChange={(event) => setExceptionDate(event.target.value)} required type="date" value={exceptionDate} />
              </label>
              <label className="space-y-1 text-xs font-semibold text-ink-700">
                Reason
                <input className="min-h-10 w-full rounded-xl border border-line px-3 text-sm" minLength={3} onChange={(event) => setExceptionReason(event.target.value)} required value={exceptionReason} />
              </label>
              <label className="space-y-1 text-xs font-semibold text-ink-700">
                Block from (blank = full day)
                <input className="min-h-10 w-full rounded-xl border border-line px-3 text-sm" onChange={(event) => setExceptionStart(event.target.value)} type="time" value={exceptionStart} />
              </label>
              <label className="space-y-1 text-xs font-semibold text-ink-700">
                Block until
                <input className="min-h-10 w-full rounded-xl border border-line px-3 text-sm" onChange={(event) => setExceptionEnd(event.target.value)} type="time" value={exceptionEnd} />
              </label>
              <button className="min-h-10 rounded-xl border border-line px-4 text-sm font-semibold text-ink-800 disabled:opacity-60 sm:col-span-2" disabled={acting || Boolean(exceptionStart) !== Boolean(exceptionEnd)} type="submit">
                Block time
              </button>
            </form>
          )}
          <ul className="mt-5 divide-y divide-line">
            {exceptions.map((item) => (
              <li className="flex items-center justify-between gap-3 py-3" key={item.id}>
                <span className="text-sm text-ink-800">
                  <strong>{item.exception_date}</strong>
                  {item.start_time && item.end_time ? ` · ${item.start_time.slice(0, 5)}–${item.end_time.slice(0, 5)}` : ' · Full day'}
                  <span className="block text-xs text-ink-600">{item.reason}</span>
                </span>
                <button aria-label={`Remove unavailable date ${item.exception_date}`} className="rounded-lg p-2 text-rose-800 hover:bg-rose-50" disabled={acting} onClick={() => void removeException(item)} type="button">
                  <X aria-hidden="true" size={16} />
                </button>
              </li>
            ))}
            {!loading && exceptions.length === 0 && (
              <li className="py-3 text-sm text-ink-600">No unavailable dates configured.</li>
            )}
          </ul>
        </section>
      </div>

      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-brand-700">
              <Clock3 aria-hidden="true" size={15} /> Appointment management
            </p>
            <h3 className="mt-2 text-xl font-semibold text-ink-950">
              {view === 'upcoming' ? 'Incoming and upcoming' : 'Appointment history'}
            </h3>
          </div>
          <div className="flex gap-2">
            {(['upcoming', 'history'] as const).map((value) => (
              <button aria-pressed={view === value} className={`min-h-9 rounded-xl px-3 text-sm font-semibold capitalize ${view === value ? 'bg-brand-700 text-white' : 'border border-line bg-white text-ink-700'}`} key={value} onClick={() => { setLoading(true); setError(null); setView(value) }} type="button">
                {value}
              </button>
            ))}
          </div>
        </div>
        {loading ? (
          <p className="rounded-2xl border border-line bg-white p-5 text-sm text-ink-600">Loading appointments…</p>
        ) : appointments.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-line bg-white p-6 text-sm text-ink-600">No appointments in this view.</p>
        ) : (
          <div className="space-y-3">
            {appointments.map((appointment) => (
              <article className="rounded-3xl border border-line bg-white p-5 shadow-panel" key={appointment.id}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h4 className="font-semibold text-ink-950">{appointment.patient_name ?? 'Patient'}</h4>
                    <p className="mt-1 text-xs text-ink-600">{dateLabel(appointment.scheduled_start)} · {appointment.status}</p>
                    <p className="mt-2 text-sm text-ink-700">{appointment.reason_for_visit}</p>
                    {appointment.patient_notes && <p className="mt-2 text-sm text-ink-600">Patient notes: {appointment.patient_notes}</p>}
                    {appointment.rejection_reason && <p className="mt-2 text-sm text-rose-800">Rejection reason: {appointment.rejection_reason}</p>}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {appointment.status === 'BOOKED' && (
                      <>
                        <button className="inline-flex min-h-9 items-center gap-1 rounded-xl bg-emerald-700 px-3 text-sm font-semibold text-white disabled:opacity-60" disabled={acting} onClick={() => void runAppointmentAction(appointment.id, 'confirm')} type="button"><Check aria-hidden="true" size={15} /> Confirm</button>
                        <button className="min-h-9 rounded-xl border border-rose-200 px-3 text-sm font-semibold text-rose-800" disabled={acting} onClick={() => { setRejectingId(appointment.id); setRejectionReason('') }} type="button">Reject</button>
                      </>
                    )}
                    {appointment.status === 'CONFIRMED' && (
                      <>
                        <button className="min-h-9 rounded-xl bg-brand-700 px-3 text-sm font-semibold text-white disabled:opacity-60" disabled={acting} onClick={() => void runAppointmentAction(appointment.id, 'complete')} type="button">Complete</button>
                        <button className="min-h-9 rounded-xl border border-line px-3 text-sm font-semibold text-ink-800 disabled:opacity-60" disabled={acting} onClick={() => void runAppointmentAction(appointment.id, 'no-show')} type="button">Mark no-show</button>
                        <button className="min-h-9 rounded-xl border border-rose-200 px-3 text-sm font-semibold text-rose-800" disabled={acting} onClick={() => { setCancellingId(appointment.id); setCancellationReason('') }} type="button">Cancel</button>
                      </>
                    )}
                  </div>
                </div>
                {rejectingId === appointment.id && (
                  <form className="mt-4 flex flex-wrap gap-2 border-t border-line pt-4" onSubmit={(event) => void handleReject(event)}>
                    <input className="min-h-10 min-w-0 flex-1 rounded-xl border border-line px-3 text-sm" minLength={5} onChange={(event) => setRejectionReason(event.target.value)} placeholder="Required rejection reason" required value={rejectionReason} />
                    <button className="min-h-10 rounded-xl bg-rose-700 px-4 text-sm font-semibold text-white disabled:opacity-60" disabled={acting || rejectionReason.trim().length < 5} type="submit">Reject request</button>
                  </form>
                )}
                {cancellingId === appointment.id && (
                  <form className="mt-4 flex flex-wrap gap-2 border-t border-line pt-4" onSubmit={(event) => void handleDoctorCancel(event)}>
                    <input className="min-h-10 min-w-0 flex-1 rounded-xl border border-line px-3 text-sm" minLength={5} onChange={(event) => setCancellationReason(event.target.value)} placeholder="Required cancellation reason" required value={cancellationReason} />
                    <button className="min-h-10 rounded-xl bg-rose-700 px-4 text-sm font-semibold text-white disabled:opacity-60" disabled={acting || cancellationReason.trim().length < 5} type="submit">Confirm cancellation</button>
                  </form>
                )}
                <div className="mt-4 border-t border-line pt-4">
                  <label className="block space-y-1 text-xs font-semibold text-ink-700">
                    Private doctor notes
                    <textarea className="min-h-20 w-full rounded-xl border border-line p-3 text-sm font-normal" maxLength={4000} onChange={(event) => setNotes((current) => ({ ...current, [appointment.id]: event.target.value }))} value={notes[appointment.id] ?? ''} />
                  </label>
                  <button className="mt-2 min-h-9 rounded-xl border border-line px-3 text-sm font-semibold text-ink-800 disabled:opacity-60" disabled={acting} onClick={() => void saveNotes(appointment.id)} type="button">Save private notes</button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  )
}

function localNowDate(): string {
  const now = new Date()
  const offset = now.getTimezoneOffset()
  return new Date(now.getTime() - offset * 60_000).toISOString().slice(0, 10)
}
