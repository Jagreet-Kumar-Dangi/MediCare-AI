import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './useAuth'
import { PageLoader } from '../components/PageLoader'
import type { UserRole } from '../types/api'

interface ProtectedRouteProps {
  children: ReactNode
  allowedRoles?: UserRole[]
}

function roleHome(role: UserRole): string {
  if (role === 'DOCTOR') return '/doctor/dashboard'
  if (role === 'ADMIN') return '/admin/doctors'
  return '/dashboard'
}

export function ProtectedRoute({
  children,
  allowedRoles = ['PATIENT'],
}: ProtectedRouteProps) {
  const { status, restoreError, retrySessionRestore, user } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return <PageLoader label="Restoring your patient portal…" />
  }

  if (status === 'error') {
    return (
      <main className="grid min-h-screen place-items-center px-5">
        <section className="max-w-md rounded-3xl border border-line bg-white p-8 text-center shadow-panel">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand-700">
            Connection issue
          </p>
          <h1 className="mt-3 text-2xl font-semibold text-ink-950">
            We couldn’t restore your session
          </h1>
          <p className="mt-3 text-sm leading-6 text-ink-600">
            {restoreError}
          </p>
          <button
            className="mt-6 rounded-xl bg-brand-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-600"
            onClick={() => void retrySessionRestore()}
            type="button"
          >
            Try again
          </button>
        </section>
      </main>
    )
  }

  if (status !== 'authenticated' || !user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location, message: restoreError }}
      />
    )
  }

  if (!allowedRoles.includes(user.role)) {
    return <Navigate to={roleHome(user.role)} replace />
  }

  return children
}
