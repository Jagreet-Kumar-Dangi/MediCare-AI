import { LoaderCircle, Stethoscope } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/errors'
import { useAuth } from '../auth/useAuth'
import { AuthLayout } from '../components/AuthLayout'
import { FormField, PasswordField } from '../components/FormField'

const initialForm = {
  full_name: '',
  email: '',
  password: '',
  confirm_password: '',
  specialization: '',
  qualification: '',
  medical_registration_number: '',
  years_of_experience: '',
  phone_number: '',
  clinic_or_hospital: '',
  consultation_fee: '',
  biography: '',
}

export function DoctorRegisterPage() {
  const { registerDoctor, status, user } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [passwordVisible, setPasswordVisible] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (status === 'authenticated' && user) {
    const home =
      user.role === 'DOCTOR'
        ? '/doctor/dashboard'
        : user.role === 'ADMIN'
          ? '/admin/doctors'
          : '/dashboard'
    return <Navigate to={home} replace />
  }

  function updateField(field: keyof typeof initialForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    if (form.password.length < 12 || !form.password.trim()) {
      setError('Use a password of 12–128 characters with at least one non-space character.')
      return
    }
    if (form.password !== form.confirm_password) {
      setError('The passwords do not match.')
      return
    }

    setSubmitting(true)
    try {
      await registerDoctor({
        email: form.email.trim(),
        password: form.password,
        full_name: form.full_name.trim(),
        specialization: form.specialization.trim(),
        qualification: form.qualification.trim(),
        medical_registration_number: form.medical_registration_number.trim(),
        years_of_experience: Number(form.years_of_experience),
        phone_number: form.phone_number.trim() || null,
        clinic_or_hospital: form.clinic_or_hospital.trim() || null,
        consultation_fee: form.consultation_fee.trim() || null,
        biography: form.biography.trim() || null,
      })
      navigate('/login', {
        replace: true,
        state: {
          message:
            'Your doctor application was submitted for verification. Sign in to view its status.',
        },
      })
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      description="Submit your professional details for administrator review. New doctor accounts remain pending until approved."
      footer={
        <>
          Already registered?{' '}
          <Link className="font-bold text-brand-700 hover:text-brand-600" to="/login">
            Sign in
          </Link>
        </>
      }
      title="Apply as a doctor"
    >
      {error && (
        <div
          aria-live="polite"
          className="mb-5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-5 text-rose-800"
          role="alert"
        >
          {error}
        </div>
      )}
      <form className="space-y-4" onSubmit={(event) => void handleSubmit(event)}>
        <FormField
          autoComplete="name"
          id="doctor-full-name"
          label="Full name"
          maxLength={160}
          onChange={(event) => updateField('full_name', event.target.value)}
          required
          value={form.full_name}
        />
        <FormField
          autoComplete="email"
          id="doctor-email"
          label="Email address"
          maxLength={254}
          onChange={(event) => updateField('email', event.target.value)}
          required
          type="email"
          value={form.email}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            id="doctor-specialization"
            label="Specialization"
            maxLength={120}
            onChange={(event) => updateField('specialization', event.target.value)}
            required
            value={form.specialization}
          />
          <FormField
            id="doctor-qualification"
            label="Qualification"
            maxLength={160}
            onChange={(event) => updateField('qualification', event.target.value)}
            required
            value={form.qualification}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            id="doctor-registration-number"
            label="Medical registration number"
            maxLength={64}
            onChange={(event) =>
              updateField('medical_registration_number', event.target.value)
            }
            required
            value={form.medical_registration_number}
          />
          <FormField
            id="doctor-experience"
            label="Years of experience"
            max={80}
            min={0}
            onChange={(event) =>
              updateField('years_of_experience', event.target.value)
            }
            required
            type="number"
            value={form.years_of_experience}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            autoComplete="tel"
            id="doctor-phone"
            label="Phone number (optional)"
            maxLength={32}
            onChange={(event) => updateField('phone_number', event.target.value)}
            value={form.phone_number}
          />
          <FormField
            id="doctor-clinic"
            label="Clinic or hospital (optional)"
            maxLength={200}
            onChange={(event) =>
              updateField('clinic_or_hospital', event.target.value)
            }
            value={form.clinic_or_hospital}
          />
        </div>
        <FormField
          id="doctor-fee"
          label="Consultation fee (optional)"
          min="0"
          onChange={(event) => updateField('consultation_fee', event.target.value)}
          step="0.01"
          type="number"
          value={form.consultation_fee}
        />
        <div className="space-y-2">
          <label
            className="block text-sm font-semibold text-ink-800"
            htmlFor="doctor-biography"
          >
            Professional biography (optional)
          </label>
          <textarea
            className="min-h-28 w-full rounded-xl border border-line bg-white px-4 py-3 text-[15px] text-ink-950 outline-none transition placeholder:text-ink-600/55 hover:border-ink-600/40 focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
            id="doctor-biography"
            maxLength={4000}
            onChange={(event) => updateField('biography', event.target.value)}
            value={form.biography}
          />
        </div>
        <PasswordField
          autoComplete="new-password"
          id="doctor-password"
          label="Password"
          maxLength={128}
          minLength={12}
          onChange={(event) => updateField('password', event.target.value)}
          onToggleVisibility={() => setPasswordVisible((visible) => !visible)}
          placeholder="At least 12 characters"
          value={form.password}
          visible={passwordVisible}
        />
        <FormField
          autoComplete="new-password"
          id="doctor-confirm-password"
          label="Confirm password"
          maxLength={128}
          minLength={12}
          onChange={(event) => updateField('confirm_password', event.target.value)}
          required
          type="password"
          value={form.confirm_password}
        />
        <button
          className="inline-flex min-h-[50px] w-full items-center justify-center gap-2 rounded-xl bg-brand-700 px-5 text-sm font-bold text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-65"
          disabled={submitting}
          type="submit"
        >
          {submitting ? (
            <>
              <LoaderCircle aria-hidden="true" className="animate-spin" size={17} />
              Submitting application…
            </>
          ) : (
            <>
              <Stethoscope aria-hidden="true" size={17} />
              Submit for verification
            </>
          )}
        </button>
        <p className="text-center text-xs leading-5 text-ink-600">
          Registration details are reviewed by an administrator. This form does
          not upload credential documents.
        </p>
      </form>
    </AuthLayout>
  )
}
