import { CalendarClock, Filter } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getApiErrorMessage } from '../api/errors'
import { getAdminAppointments } from '../api/appointments'
import type { Appointment, AppointmentStatus } from '../types/api'

const filters: ('ALL' | AppointmentStatus)[] = [
  'ALL',
  'BOOKED',
  'CONFIRMED',
  'REJECTED',
  'COMPLETED',
  'CANCELLED',
  'NO_SHOW',
]

export function AdminAppointmentsPage() {
  const [filter, setFilter] = useState<(typeof filters)[number]>('ALL')
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void getAdminAppointments(filter === 'ALL' ? undefined : filter)
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
  }, [filter])

  return (
    <section className="space-y-6">
      <header>
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-700">
          Administrator workspace
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-ink-950">
          Appointment overview
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-600">
          Read-only appointment inspection is restricted to administrators. Patient
          and doctor management actions remain with the appointment participants.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-2" aria-label="Appointment status filter">
        <Filter aria-hidden="true" className="mr-1 text-brand-700" size={17} />
        {filters.map((value) => (
          <button
            aria-pressed={filter === value}
            className={`min-h-9 rounded-xl px-3 text-xs font-semibold ${
              filter === value
                ? 'bg-brand-700 text-white'
                : 'border border-line bg-white text-ink-700 hover:bg-sky-50'
            }`}
            key={value}
            onClick={() => {
              setLoading(true)
              setError(null)
              setFilter(value)
            }}
            type="button"
          >
            {value === 'ALL' ? 'All statuses' : value}
          </button>
        ))}
      </div>

      {error && (
        <p className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert">
          {error}
        </p>
      )}
      {loading ? (
        <p className="rounded-2xl border border-line bg-white p-6 text-sm text-ink-600">
          Loading appointment records…
        </p>
      ) : appointments.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-line bg-white p-10 text-center">
          <CalendarClock aria-hidden="true" className="mx-auto text-brand-700" size={28} />
          <p className="mt-3 text-sm text-ink-600">No appointments match this filter.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {appointments.map((appointment) => (
            <article className="rounded-3xl border border-line bg-white p-5 shadow-panel" key={appointment.id}>
              <div className="flex flex-wrap justify-between gap-3">
                <div>
                  <h2 className="font-semibold text-ink-950">
                    {appointment.patient_name} · {appointment.doctor.full_name}
                  </h2>
                  <p className="mt-1 text-sm text-ink-600">
                    {new Date(appointment.scheduled_start).toLocaleString()} ·{' '}
                    {appointment.status}
                  </p>
                  <p className="mt-2 text-sm text-ink-800">{appointment.reason_for_visit}</p>
                  <p className="mt-1 text-xs text-ink-600">
                    Patient #{appointment.patient_id} · {appointment.patient_email}
                  </p>
                </div>
              </div>
              {appointment.audit_events.length > 0 && (
                <ol className="mt-4 space-y-2 border-t border-line pt-4">
                  {appointment.audit_events.map((event) => (
                    <li className="text-xs text-ink-600" key={event.id}>
                      {event.action} · {new Date(event.created_at).toLocaleString()}
                      {event.reason ? ` · ${event.reason}` : ''}
                    </li>
                  ))}
                </ol>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
