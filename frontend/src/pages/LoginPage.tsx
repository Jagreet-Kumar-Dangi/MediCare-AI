import { LoaderCircle, LockKeyhole } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import axios from 'axios'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/errors'
import { AuthLayout } from '../components/AuthLayout'
import { useAuth } from '../auth/useAuth'
import { FormField, PasswordField } from '../components/FormField'
import type { UserRole } from '../types/api'

interface LoginLocationState {
  from?: { pathname?: string }
  message?: string
}

function homeForRole(role: UserRole): string {
  if (role === 'DOCTOR') return '/doctor/dashboard'
  if (role === 'ADMIN') return '/admin/doctors'
  return '/dashboard'
}

function canOpenPath(role: UserRole, path: string): boolean {
  const allowedRoots =
    role === 'PATIENT'
      ? ['/dashboard', '/profile', '/medical-records', '/doctors']
      : role === 'DOCTOR'
        ? ['/doctor']
        : ['/admin']
  return allowedRoots.some(
    (root) => path === root || path.startsWith(`${root}/`),
  )
}

export function LoginPage() {
  const { signIn, status, user } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const routeState = location.state as LoginLocationState | null
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordVisible, setPasswordVisible] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [verificationRequired, setVerificationRequired] = useState(false)

  if (status === 'authenticated' && user) {
    return <Navigate to={homeForRole(user.role)} replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setVerificationRequired(false)
    setSubmitting(true)
    try {
      const signedInUser = await signIn({ email: email.trim(), password })
      const requestedPath = routeState?.from?.pathname
      const safePath =
        requestedPath?.startsWith('/') &&
        !requestedPath.startsWith('//') &&
        canOpenPath(signedInUser.role, requestedPath)
          ? requestedPath
          : homeForRole(signedInUser.role)
      navigate(safePath, { replace: true })
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
      setVerificationRequired(
        axios.isAxiosError(requestError) &&
          requestError.response?.status === 403,
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      description="Welcome back. Sign in to continue to your MediCare AI workspace."
      footer={
        <>
          New to MediCare AI?{' '}
          <Link
            className="font-bold text-brand-700 hover:text-brand-600"
            to="/register"
          >
            Create an account
          </Link>
        </>
      }
      title="Welcome back"
    >
      {(routeState?.message || error) && (
        <div
          aria-live="polite"
          className="mb-5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-5 text-rose-800"
          role="alert"
        >
          {error ?? routeState?.message}
        </div>
      )}
      {verificationRequired && (
        <button
          className="mb-5 w-full rounded-xl border border-brand-200 px-4 py-3 text-sm font-bold text-brand-700 hover:bg-brand-50"
          onClick={() =>
            navigate('/verify-email', {
              state: { email: email.trim(), autoSend: true },
            })
          }
          type="button"
        >
          Verify your email address
        </button>
      )}
      <form className="space-y-5" onSubmit={(event) => void handleSubmit(event)}>
        <FormField
          autoComplete="email"
          id="email"
          label="Email address"
          maxLength={254}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@example.com"
          required
          type="email"
          value={email}
        />
        <PasswordField
          autoComplete="current-password"
          id="password"
          label="Password"
          onChange={(event) => setPassword(event.target.value)}
          onToggleVisibility={() => setPasswordVisible((visible) => !visible)}
          placeholder="Enter your password"
          value={password}
          visible={passwordVisible}
        />
        <button
          className="inline-flex min-h-[50px] w-full items-center justify-center gap-2 rounded-xl bg-brand-700 px-5 text-sm font-bold text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-65"
          disabled={submitting}
          type="submit"
        >
          {submitting ? (
            <>
              <LoaderCircle aria-hidden="true" className="animate-spin" size={17} />
              Signing in…
            </>
          ) : (
            <>
              <LockKeyhole aria-hidden="true" size={16} />
              Sign in to your account
            </>
          )}
        </button>
      </form>
      <p className="mt-5 text-center text-xs leading-5 text-ink-600">
        Your session stays on this device until you sign out or close the tab.
      </p>
    </AuthLayout>
  )
}
