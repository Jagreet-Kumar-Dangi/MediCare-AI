import { LoaderCircle, UserRoundPlus } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/errors'
import { AuthLayout } from '../components/AuthLayout'
import { useAuth } from '../auth/useAuth'
import { FormField, PasswordField } from '../components/FormField'

export function RegisterPage() {
  const { registerPatient, status } = useAuth()
  const navigate = useNavigate()
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordVisible, setPasswordVisible] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (status === 'authenticated') {
    return <Navigate to="/dashboard" replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    if (password.length < 12) {
      setError('Use at least 12 characters for your password.')
      return
    }
    if (!password.trim()) {
      setError('Your password needs at least one non-space character.')
      return
    }
    if (password !== confirmPassword) {
      setError('The passwords do not match.')
      return
    }

    setSubmitting(true)
    try {
      await registerPatient({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim(),
        password,
      })
      navigate('/login', {
        replace: true,
        state: { message: 'Your patient account is ready. Sign in to continue.' },
      })
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      description="Create a patient account to manage your profile in one clear, personal space."
      footer={
        <>
          Already have an account?{' '}
          <Link
            className="font-bold text-brand-700 hover:text-brand-600"
            to="/login"
          >
            Sign in
          </Link>
        </>
      }
      title="Create your account"
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
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            autoComplete="given-name"
            id="first-name"
            label="First name"
            maxLength={100}
            onChange={(event) => setFirstName(event.target.value)}
            placeholder="Avery"
            required
            value={firstName}
          />
          <FormField
            autoComplete="family-name"
            id="last-name"
            label="Last name"
            maxLength={100}
            onChange={(event) => setLastName(event.target.value)}
            placeholder="Morgan"
            required
            value={lastName}
          />
        </div>
        <FormField
          autoComplete="email"
          id="register-email"
          label="Email address"
          maxLength={254}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@example.com"
          required
          type="email"
          value={email}
        />
        <PasswordField
          autoComplete="new-password"
          hint="Use 12–128 characters. Spaces at the beginning or end are preserved."
          id="register-password"
          label="Password"
          maxLength={128}
          minLength={12}
          onChange={(event) => setPassword(event.target.value)}
          onToggleVisibility={() => setPasswordVisible((visible) => !visible)}
          placeholder="At least 12 characters"
          value={password}
          visible={passwordVisible}
        />
        <FormField
          autoComplete="new-password"
          id="confirm-password"
          label="Confirm password"
          maxLength={128}
          onChange={(event) => setConfirmPassword(event.target.value)}
          placeholder="Enter your password again"
          required
          type="password"
          value={confirmPassword}
        />
        <button
          className="inline-flex min-h-[50px] w-full items-center justify-center gap-2 rounded-xl bg-brand-700 px-5 text-sm font-bold text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-65"
          disabled={submitting}
          type="submit"
        >
          {submitting ? (
            <>
              <LoaderCircle aria-hidden="true" className="animate-spin" size={17} />
              Creating your account…
            </>
          ) : (
            <>
              <UserRoundPlus aria-hidden="true" size={17} />
              Create patient account
            </>
          )}
        </button>
        <p className="text-center text-xs leading-5 text-ink-600">
          Registration creates a patient account only. Your password is never
          shown in the portal.
        </p>
      </form>
    </AuthLayout>
  )
}
