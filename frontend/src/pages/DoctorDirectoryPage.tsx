import { Search, Stethoscope } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { getApiErrorMessage } from '../api/errors'
import { listDoctors } from '../api/doctors'
import type { PublicDoctorProfile } from '../types/api'

export function DoctorDirectoryPage() {
  const [doctors, setDoctors] = useState<PublicDoctorProfile[]>([])
  const [specialization, setSpecialization] = useState('')
  const [search, setSearch] = useState('')
  const [minExperience, setMinExperience] = useState('')
  const [maxExperience, setMaxExperience] = useState('')
  const [maxFee, setMaxFee] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void listDoctors()
      .then((result) => {
        if (active) setDoctors(result)
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

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    try {
      setDoctors(
        await listDoctors({
          specialization: specialization.trim() || undefined,
          search: search.trim() || undefined,
          min_experience: minExperience ? Number(minExperience) : undefined,
          max_experience: maxExperience ? Number(maxExperience) : undefined,
          max_consultation_fee: maxFee || undefined,
        }),
      )
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="space-y-7">
      <header className="max-w-3xl">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-700">
          Doctor directory
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-ink-950">
          Find a verified doctor
        </h1>
        <p className="mt-3 text-sm leading-6 text-ink-600">
          Only approved, active doctor accounts appear here. Appointment
          scheduling is not available in this release.
        </p>
      </header>

      <form
        className="grid gap-4 rounded-3xl border border-line bg-white p-5 shadow-panel sm:grid-cols-2 lg:grid-cols-5"
        onSubmit={handleSearch}
      >
        <label className="space-y-2 text-sm font-semibold text-ink-800">
          Doctor name
          <input
            className="min-h-11 w-full rounded-xl border border-line px-3 text-sm font-normal outline-none focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by name"
            value={search}
          />
        </label>
        <label className="space-y-2 text-sm font-semibold text-ink-800">
          Specialization
          <input
            className="min-h-11 w-full rounded-xl border border-line px-3 text-sm font-normal outline-none focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
            onChange={(event) => setSpecialization(event.target.value)}
            placeholder="e.g. cardiology"
            value={specialization}
          />
        </label>
        <label className="space-y-2 text-sm font-semibold text-ink-800">
          Minimum experience
          <input
            className="min-h-11 w-full rounded-xl border border-line px-3 text-sm font-normal outline-none focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
            min={0}
            max={80}
            onChange={(event) => setMinExperience(event.target.value)}
            type="number"
            value={minExperience}
          />
        </label>
        <label className="space-y-2 text-sm font-semibold text-ink-800">
          Maximum experience
          <input
            className="min-h-11 w-full rounded-xl border border-line px-3 text-sm font-normal outline-none focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
            min={0}
            max={80}
            onChange={(event) => setMaxExperience(event.target.value)}
            type="number"
            value={maxExperience}
          />
        </label>
        <label className="space-y-2 text-sm font-semibold text-ink-800">
          Maximum fee
          <input
            className="min-h-11 w-full rounded-xl border border-line px-3 text-sm font-normal outline-none focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
            min={0}
            onChange={(event) => setMaxFee(event.target.value)}
            step="0.01"
            type="number"
            value={maxFee}
          />
        </label>
        <div className="sm:col-span-2 lg:col-span-5">
          <button
            className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-brand-700 px-4 text-sm font-semibold text-white transition hover:bg-brand-600"
            type="submit"
          >
            <Search aria-hidden="true" size={16} />
            Search directory
          </button>
        </div>
      </form>

      {error && (
        <p
          aria-live="polite"
          className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
          role="alert"
        >
          {error}
        </p>
      )}
      {loading ? (
        <p className="rounded-2xl border border-line bg-white p-6 text-sm text-ink-600">
          Loading verified doctors…
        </p>
      ) : doctors.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-line bg-white p-10 text-center">
          <Stethoscope aria-hidden="true" className="mx-auto text-brand-700" size={28} />
          <h2 className="mt-3 text-lg font-semibold text-ink-950">
            No doctors match these filters
          </h2>
          <p className="mt-2 text-sm text-ink-600">
            Try a different name, specialization, or experience range.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {doctors.map((doctor) => (
            <article
              className="rounded-3xl border border-line bg-white p-6 shadow-panel"
              key={doctor.id}
            >
              <div className="grid size-11 place-items-center rounded-2xl bg-brand-100 text-brand-700">
                <Stethoscope aria-hidden="true" size={20} />
              </div>
              <h2 className="mt-4 text-lg font-semibold text-ink-950">
                {doctor.full_name}
              </h2>
              <p className="mt-1 text-sm font-semibold text-brand-700">
                {doctor.specialization}
              </p>
              <p className="mt-3 text-sm text-ink-600">{doctor.qualification}</p>
              <p className="mt-1 text-sm text-ink-600">
                {doctor.years_of_experience} years of experience
              </p>
              <Link
                className="mt-5 inline-flex min-h-10 items-center rounded-xl border border-line px-3 text-sm font-semibold text-ink-800 transition hover:bg-sky-50"
                to={`/doctors/${doctor.id}`}
              >
                View doctor profile
              </Link>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
