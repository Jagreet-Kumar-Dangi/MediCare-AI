import {
  Check,
  LoaderCircle,
  Pencil,
  RotateCcw,
  Save,
  UserRound,
  X,
} from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { getApiErrorMessage } from '../api/errors'
import { getMyPatientProfile, updateMyPatientProfile } from '../api/patients'
import { useAuth } from '../auth/useAuth'
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

function validateProfileForm(form: ProfileFormState): string | null {
  if (!form.first_name.trim() || !form.last_name.trim()) {
    return 'Enter both your first name and last name.'
  }
  if (form.date_of_birth && form.date_of_birth > getTodayInputValue()) {
    return 'Date of birth cannot be in the future.'
  }

  const phoneNumber = form.phone_number.trim()
  if (
    phoneNumber &&
    (phoneNumber.length < 7 ||
      phoneNumber.length > 32 ||
      !/^\+?[0-9][0-9 ().-]*$/.test(phoneNumber))
  ) {
    return 'Enter a phone number using 7–32 characters: digits, spaces, parentheses, periods, or hyphens, with an optional leading +.'
  }
  return null
}

function formatDate(value: string | null): string {
  if (!value) return 'Not provided'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'long' }).format(
    new Date(`${value}T00:00:00`),
  )
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

interface ProfileValueProps {
  label: string
  value: string
}

function ProfileValue({ label, value }: ProfileValueProps) {
  return (
    <div className="min-w-0 rounded-xl bg-sky-50/70 px-4 py-3">
      <dt className="text-xs font-medium text-ink-600">{label}</dt>
      <dd className="mt-1 break-words text-sm font-semibold text-ink-950">
        {value}
      </dd>
    </div>
  )
}

export function ProfilePage() {
  const { user } = useAuth()
  const [profile, setProfile] = useState<PatientProfile | null>(null)
  const [form, setForm] = useState<ProfileFormState>(emptyForm)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let active = true
    void getMyPatientProfile()
      .then((result) => {
        if (!active) return
        setProfile(result)
        setForm(toFormState(result))
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

  function startEditing() {
    if (!profile) return
    setForm(toFormState(profile))
    setError(null)
    setSaved(false)
    setEditing(true)
  }

  function cancelEditing() {
    if (profile) setForm(toFormState(profile))
    setEditing(false)
    setError(null)
    setSaved(false)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSaved(false)

    const validationError = validateProfileForm(form)
    if (validationError) {
      setError(validationError)
      return
    }

    setSaving(true)
    try {
      const updatedProfile = await updateMyPatientProfile({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        date_of_birth: form.date_of_birth || null,
        phone_number: form.phone_number.trim() || null,
      })
      setProfile(updatedProfile)
      setForm(toFormState(updatedProfile))
      setEditing(false)

      try {
        const refreshedProfile = await getMyPatientProfile()
        setProfile(refreshedProfile)
        setForm(toFormState(refreshedProfile))
        setSaved(true)
      } catch (refreshError) {
        setError(
          `Your changes were saved, but we couldn't refresh your profile. ${getApiErrorMessage(refreshError)}`,
        )
      }
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page-enter mx-auto max-w-[980px] space-y-6">
      <div>
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
        <div className="flex flex-col gap-4 border-b border-line bg-sky-50/75 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-7">
          <div className="flex items-center gap-3">
            <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-white text-brand-700 shadow-sm">
              <UserRound aria-hidden="true" size={20} />
            </span>
            <div>
              <h3 className="text-sm font-bold text-ink-950">Patient details</h3>
              <p className="mt-0.5 text-xs text-ink-600">
                Profile information associated with your account
              </p>
            </div>
          </div>
          {profile && !loading && (
            <div className="flex flex-col-reverse gap-2 sm:flex-row">
              {editing ? (
                <button
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-line bg-white px-4 text-sm font-semibold text-ink-800 transition hover:bg-sky-50 disabled:opacity-60"
                  disabled={saving}
                  onClick={cancelEditing}
                  type="button"
                >
                  <X aria-hidden="true" size={16} />
                  Cancel
                </button>
              ) : (
                <button
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-brand-700 px-4 text-sm font-bold text-white transition hover:bg-brand-600"
                  onClick={startEditing}
                  type="button"
                >
                  <Pencil aria-hidden="true" size={15} />
                  Edit profile
                </button>
              )}
            </div>
          )}
        </div>

        <div className="p-5 sm:p-7">
          {loading ? (
            <div
              aria-busy="true"
              className="flex min-h-48 items-center justify-center gap-3 text-sm text-ink-600"
              role="status"
            >
              <LoaderCircle
                aria-hidden="true"
                className="animate-spin text-brand-700"
                size={18}
              />
              Loading your profile…
            </div>
          ) : error && !profile ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5">
              <p className="text-sm font-semibold text-rose-800" role="alert">
                {error}
              </p>
              <button
                className="mt-4 inline-flex min-h-10 items-center gap-2 text-sm font-bold text-brand-700 hover:text-brand-600"
                onClick={reloadProfile}
                type="button"
              >
                <RotateCcw aria-hidden="true" size={15} />
                Try loading again
              </button>
            </div>
          ) : !profile ? (
            <div className="rounded-2xl border border-dashed border-line bg-sky-50/60 p-6 text-center">
              <p className="text-sm font-semibold text-ink-800">
                No patient profile details are available for this account.
              </p>
              <button
                className="mt-4 inline-flex min-h-10 items-center gap-2 text-sm font-bold text-brand-700 hover:text-brand-600"
                onClick={reloadProfile}
                type="button"
              >
                <RotateCcw aria-hidden="true" size={15} />
                Try loading again
              </button>
            </div>
          ) : (
            <>
              {error && (
                <div
                  aria-live="polite"
                  className="mb-5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
                  role="alert"
                >
                  {error}
                </div>
              )}
              {saved && (
                <div
                  aria-live="polite"
                  className="mb-5 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800"
                  role="status"
                >
                  <Check aria-hidden="true" size={16} />
                  Your profile was saved.
                </div>
              )}

              {editing ? (
                <form
                  className="space-y-6"
                  onSubmit={(event) => void handleSubmit(event)}
                >
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
                      placeholder="+1 555 0100"
                      type="tel"
                      value={form.phone_number}
                    />
                  </div>
                  <div className="rounded-xl bg-sky-50 px-4 py-3 text-xs leading-5 text-ink-600">
                    Health records and clinical information are not managed on
                    this profile page.
                  </div>
                  <div className="flex flex-col-reverse gap-3 border-t border-line pt-5 sm:flex-row sm:justify-end">
                    <button
                      className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-line px-5 text-sm font-semibold text-ink-800 transition hover:bg-sky-50 disabled:opacity-60"
                      disabled={saving}
                      onClick={cancelEditing}
                      type="button"
                    >
                      <X aria-hidden="true" size={15} />
                      Cancel
                    </button>
                    <button
                      className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-brand-700 px-5 text-sm font-bold text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={saving}
                      type="submit"
                    >
                      {saving ? (
                        <>
                          <LoaderCircle
                            aria-hidden="true"
                            className="animate-spin"
                            size={16}
                          />
                          Saving…
                        </>
                      ) : (
                        <>
                          <Save aria-hidden="true" size={16} />
                          Save changes
                        </>
                      )}
                    </button>
                  </div>
                </form>
              ) : (
                <dl className="grid gap-3 sm:grid-cols-2">
                  <ProfileValue label="First name" value={profile.first_name} />
                  <ProfileValue label="Last name" value={profile.last_name} />
                  <ProfileValue
                    label="Date of birth"
                    value={formatDate(profile.date_of_birth)}
                  />
                  <ProfileValue
                    label="Phone number"
                    value={profile.phone_number || 'Not provided'}
                  />
                  <ProfileValue
                    label="Profile created"
                    value={formatDateTime(profile.created_at)}
                  />
                  <ProfileValue
                    label="Last updated"
                    value={formatDateTime(profile.updated_at)}
                  />
                </dl>
              )}
            </>
          )}
        </div>
      </section>

      <section
        aria-labelledby="account-information-heading"
        className="rounded-[24px] border border-line bg-white p-5 shadow-sm sm:p-7"
      >
        <div className="mb-5">
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-brand-700">
            Account information
          </p>
          <h3
            className="mt-1 text-lg font-bold tracking-[-0.035em] text-ink-950"
            id="account-information-heading"
          >
            Your account
          </h3>
          <p className="mt-1 text-sm text-ink-600">
            These details are managed by your account and cannot be changed here.
          </p>
        </div>
        <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <ProfileValue
            label="Email"
            value={user?.email ?? 'Unavailable'}
          />
          <ProfileValue
            label="Patient ID"
            value={user ? String(user.id) : 'Unavailable'}
          />
          <ProfileValue
            label="Account status"
            value={
              user ? (user.is_active ? 'Active' : 'Inactive') : 'Unavailable'
            }
          />
        </dl>
      </section>
    </div>
  )
}
