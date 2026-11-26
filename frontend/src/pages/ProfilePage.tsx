import { Check, LoaderCircle, RotateCcw, Save, UserRound } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { getApiErrorMessage } from '../api/errors'
import { getMyPatientProfile, updateMyPatientProfile } from '../api/patients'
import { FormField } from '../components/FormField'
import type { PatientProfile } from '../types/api'

interface ProfileFormState {
  first_name: string
  last_name: string
  date_of_birth: string
  phone_number: string
}

const emptyForm: ProfileFormState = {
  first_name: '',
  last_name: '',
  date_of_birth: '',
  phone_number: '',
}

function toFormState(profile: PatientProfile): ProfileFormState {
  return {
    first_name: profile.first_name,
    last_name: profile.last_name,
    date_of_birth: profile.date_of_birth ?? '',
    phone_number: profile.phone_number ?? '',
  }
}

function getTodayInputValue(): string {
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function ProfilePage() {
  const [form, setForm] = useState<ProfileFormState>(emptyForm)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let active = true
    void getMyPatientProfile()
      .then((profile) => {
        if (active) setForm(toFormState(profile))
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
  }, [reloadKey])

  function reloadProfile() {
    setLoading(true)
    setError(null)
    setSaved(false)
    setReloadKey((value) => value + 1)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSaved(false)
    setSaving(true)
    try {
      const updatedProfile = await updateMyPatientProfile({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        date_of_birth: form.date_of_birth || null,
        phone_number: form.phone_number.trim() || null,
      })
      setForm(toFormState(updatedProfile))
      setSaved(true)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page-enter mx-auto max-w-[980px]">
      <div className="mb-7">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-700">
          Personal details
        </p>
        <h2 className="mt-2 text-3xl font-semibold tracking-[-0.045em] text-ink-950">
          My profile
        </h2>
        <p className="mt-2 max-w-[600px] text-sm leading-6 text-ink-600">
          Review and update the details in your patient profile. Only the
          information you submit is saved.
        </p>
      </div>

      <section className="overflow-hidden rounded-[24px] border border-line bg-white shadow-sm">
        <div className="flex items-center gap-3 border-b border-line bg-sky-50/75 px-5 py-5 sm:px-7">
          <span className="grid size-11 place-items-center rounded-2xl bg-white text-brand-700 shadow-sm">
            <UserRound aria-hidden="true" size={20} />
          </span>
          <div>
            <h3 className="text-sm font-bold text-ink-950">Patient details</h3>
            <p className="mt-0.5 text-xs text-ink-600">
              Profile information associated with your account
            </p>
          </div>
        </div>

        <div className="p-5 sm:p-7">
          {loading ? (
            <div
              aria-busy="true"
              className="flex min-h-48 items-center justify-center gap-3 text-sm text-ink-600"
              role="status"
            >
              <LoaderCircle aria-hidden="true" className="animate-spin text-brand-700" size={18} />
              Loading your profile…
            </div>
          ) : error && !form.first_name ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5">
              <p className="text-sm font-semibold text-rose-800" role="alert">
                {error}
              </p>
              <button
                className="mt-4 inline-flex items-center gap-2 text-sm font-bold text-brand-700 hover:text-brand-600"
                onClick={reloadProfile}
                type="button"
              >
                <RotateCcw aria-hidden="true" size={15} />
                Try loading again
              </button>
            </div>
          ) : (
            <form
              className="space-y-6"
              onSubmit={(event) => void handleSubmit(event)}
            >
              {error && (
                <div
                  aria-live="polite"
                  className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
                  role="alert"
                >
                  {error}
                </div>
              )}
              {saved && (
                <div
                  aria-live="polite"
                  className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800"
                  role="status"
                >
                  <Check aria-hidden="true" size={16} />
                  Your profile was saved.
                </div>
              )}
              <div className="grid gap-5 sm:grid-cols-2">
                <FormField
                  autoComplete="given-name"
                  id="profile-first-name"
                  label="First name"
                  maxLength={100}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      first_name: event.target.value,
                    }))
                  }
                  required
                  value={form.first_name}
                />
                <FormField
                  autoComplete="family-name"
                  id="profile-last-name"
                  label="Last name"
                  maxLength={100}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      last_name: event.target.value,
                    }))
                  }
                  required
                  value={form.last_name}
                />
                <FormField
                  autoComplete="bday"
                  id="profile-date-of-birth"
                  label="Date of birth"
                  max={getTodayInputValue()}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      date_of_birth: event.target.value,
                    }))
                  }
                  type="date"
                  value={form.date_of_birth}
                />
                <FormField
                  autoComplete="tel"
                  id="profile-phone"
                  label="Phone number"
                  maxLength={32}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      phone_number: event.target.value,
                    }))
                  }
                  pattern="\\+?[0-9][0-9 ().-]{6,31}"
                  placeholder="+1 555 0100"
                  type="tel"
                  value={form.phone_number}
                />
              </div>
              <div className="rounded-xl bg-sky-50 px-4 py-3 text-xs leading-5 text-ink-600">
                Health records and clinical information are not managed on this
                profile page.
              </div>
              <div className="flex flex-col-reverse gap-3 border-t border-line pt-5 sm:flex-row sm:justify-end">
                <button
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-line px-5 text-sm font-semibold text-ink-800 transition hover:bg-sky-50 disabled:opacity-60"
                  disabled={saving}
                  onClick={reloadProfile}
                  type="button"
                >
                  <RotateCcw aria-hidden="true" size={15} />
                  Reset changes
                </button>
                <button
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-brand-700 px-5 text-sm font-bold text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={saving || loading}
                  type="submit"
                >
                  {saving ? (
                    <>
                      <LoaderCircle aria-hidden="true" className="animate-spin" size={16} />
                      Saving…
                    </>
                  ) : (
                    <>
                      <Save aria-hidden="true" size={16} />
                      Save profile
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </section>
    </div>
  )
}
