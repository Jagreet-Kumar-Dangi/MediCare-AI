import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/errors'
import {
  confirmEmailVerification,
  resendVerificationEmail,
  sendVerificationEmail,
} from '../api/auth'
import { AuthLayout } from '../components/AuthLayout'
import { FormField } from '../components/FormField'

interface VerificationLocationState {
  email?: string
  autoSend?: boolean
  initialError?: string
}

function maskEmail(email: string): string {
  const [name, domain] = email.split('@')
  if (!name || !domain) return email
  const visible = name.length < 3 ? name.slice(0, 1) : name.slice(0, 2)
  return `${visible}${'*'.repeat(Math.max(3, name.length - visible.length))}@${domain}`
}

export function EmailVerificationPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const routeState = location.state as VerificationLocationState | null
  const [email, setEmail] = useState(routeState?.email ?? '')
  const [code, setCode] = useState('')
  const [countdown, setCountdown] = useState(
    routeState?.autoSend ? 0 : routeState?.email ? 60 : 0,
  )
  const [busy, setBusy] = useState(false)
  const [verified, setVerified] = useState(false)
  const [error, setError] = useState<string | null>(
    routeState?.initialError ?? null,
  )
  const [notice, setNotice] = useState<string | null>(
    routeState?.email && !routeState.autoSend && !routeState.initialError
      ? 'A verification code has been sent.'
      : null,
  )
  const autoSendHandled = useRef(false)
  const hasCountdown = countdown > 0

  useEffect(() => {
    if (!hasCountdown) return
    const timer = window.setInterval(
      () => setCountdown((remaining) => Math.max(0, remaining - 1)),
      1000,
    )
    return () => window.clearInterval(timer)
  }, [hasCountdown])

  const requestCode = useCallback(
    async (resend: boolean) => {
      setError(null)
      setNotice(null)
      setBusy(true)
      try {
        if (resend) {
          await resendVerificationEmail({ email: email.trim() })
        } else {
          await sendVerificationEmail({ email: email.trim() })
        }
        setCountdown(60)
        setNotice('If this address can be verified, a code has been sent.')
      } catch (requestError) {
        setError(getApiErrorMessage(requestError))
      } finally {
        setBusy(false)
      }
    },
    [email],
  )

  useEffect(() => {
    if (!routeState?.autoSend || autoSendHandled.current || !email) return
    autoSendHandled.current = true
    void requestCode(false)
  }, [email, requestCode, routeState?.autoSend])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setNotice(null)
    if (!/^\d{6}$/.test(code)) {
      setError('Enter the six-digit verification code.')
      return
    }
    setBusy(true)
    try {
      await confirmEmailVerification({ email: email.trim(), code })
      setVerified(true)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout
      description="Confirm that you own the email address used for your account."
      footer={
        <>
          Need help?{' '}
          <Link className="font-bold text-brand-700 hover:text-brand-600" to="/login">
            Return to sign in
          </Link>
        </>
      }
      title="Verify your email"
    >
      {verified ? (
        <div className="space-y-5 text-center">
          <p
            aria-live="polite"
            className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"
            role="status"
          >
            Your email address is verified. You can now sign in.
          </p>
          <button
            className="min-h-[50px] w-full rounded-xl bg-brand-700 px-5 text-sm font-bold text-white transition hover:bg-brand-600"
            onClick={() =>
              navigate('/login', {
                replace: true,
                state: { message: 'Your email is verified. Sign in to continue.' },
              })
            }
            type="button"
          >
            Continue to sign in
          </button>
        </div>
      ) : (
        <>
          {email && (
            <p className="mb-5 text-sm text-ink-600">
              Verification destination: <strong>{maskEmail(email)}</strong>
            </p>
          )}
          {error && (
            <div
              aria-live="polite"
              className="mb-5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-5 text-rose-800"
              role="alert"
            >
              {error}
            </div>
          )}
          {notice && (
            <p aria-live="polite" className="mb-5 text-sm text-ink-600" role="status">
              {notice}
            </p>
          )}
          <form className="space-y-4" onSubmit={(event) => void handleSubmit(event)}>
            <FormField
              autoComplete="email"
              id="verification-email"
              label="Email address"
              maxLength={254}
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
            <FormField
              autoComplete="one-time-code"
              id="verification-code"
              inputMode="numeric"
              label="Six-digit code"
              maxLength={6}
              onChange={(event) =>
                setCode(event.target.value.replace(/\D/g, '').slice(0, 6))
              }
              pattern="\d{6}"
              required
              value={code}
            />
            <button
              className="min-h-[50px] w-full rounded-xl bg-brand-700 px-5 text-sm font-bold text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-65"
              disabled={busy || code.length !== 6 || !email.trim()}
              type="submit"
            >
              {busy ? 'Verifying…' : 'Verify email'}
            </button>
          </form>
          <button
            className="mt-4 min-h-11 w-full rounded-xl border border-brand-200 px-4 text-sm font-bold text-brand-700 hover:bg-brand-50 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={busy || countdown > 0 || !email.trim()}
            onClick={() => void requestCode(true)}
            type="button"
          >
            {countdown > 0
              ? `Resend code in ${countdown}s`
              : busy
                ? 'Sending…'
                : 'Resend verification code'}
          </button>
          <p className="mt-4 text-center text-xs leading-5 text-ink-600">
            Codes expire after five minutes. Never share your code with anyone.
          </p>
        </>
      )}
    </AuthLayout>
  )
}
