import {
  Activity,
  ArrowUpRight,
  CircleUserRound,
  FileHeart,
  LayoutDashboard,
  LogOut,
  Menu,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/errors'
import { useAuth } from '../auth/useAuth'
import { Brand } from './Brand'

const navigation = [
  { label: 'Overview', to: '/dashboard', icon: LayoutDashboard },
  { label: 'My profile', to: '/profile', icon: CircleUserRound },
  { label: 'Medical records', to: '/medical-records', icon: FileHeart },
]

export function PatientLayout() {
  const { user, signOut } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [logoutError, setLogoutError] = useState<string | null>(null)

  const pageTitle =
    location.pathname === '/profile'
      ? 'My profile'
      : location.pathname === '/medical-records'
        ? 'Medical records'
        : 'Patient overview'

  async function handleSignOut() {
    setLogoutError(null)
    try {
      await signOut()
      navigate('/login', { replace: true })
    } catch (error) {
      setLogoutError(getApiErrorMessage(error))
    }
  }

  function renderNavigation(mobile = false) {
    return (
      <nav aria-label="Patient portal" className="space-y-1">
        {navigation.map(({ label, to, icon: Icon }) => (
          <NavLink
            className={({ isActive }) =>
              `group flex min-h-11 items-center gap-3 rounded-xl px-3.5 text-sm font-semibold transition ${
                isActive
                  ? 'bg-brand-100 text-brand-700'
                  : 'text-ink-600 hover:bg-sky-50 hover:text-ink-950'
              }`
            }
            end
            key={to}
            onClick={() => mobile && setMobileMenuOpen(false)}
            to={to}
          >
            <Icon aria-hidden="true" size={18} strokeWidth={1.9} />
            {label}
          </NavLink>
        ))}
      </nav>
    )
  }

  return (
    <div className="min-h-screen bg-sky-50 text-ink-950">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[252px] flex-col border-r border-line bg-white px-5 py-7 lg:flex">
        <Brand to="/dashboard" />
        <div className="mb-3 mt-12 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-ink-600/70">
          Patient space
        </div>
        {renderNavigation()}
        <div className="mt-auto rounded-2xl bg-sky-50 p-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-brand-700">
            <Activity aria-hidden="true" size={16} />
            Your care, clearly
          </div>
          <p className="mt-2 text-xs leading-5 text-ink-600">
            Your profile and private report storage are ready for use.
          </p>
        </div>
      </aside>

      <div className="lg:pl-[252px]">
        <header className="sticky top-0 z-20 border-b border-line/80 bg-white/90 backdrop-blur-xl">
          <div className="mx-auto flex h-[72px] max-w-[1440px] items-center justify-between px-4 sm:px-7 lg:px-10">
            <div className="flex items-center gap-3">
              <button
                aria-expanded={mobileMenuOpen}
                aria-label={mobileMenuOpen ? 'Close navigation' : 'Open navigation'}
                className="grid size-10 place-items-center rounded-xl border border-line text-ink-800 lg:hidden"
                onClick={() => setMobileMenuOpen((open) => !open)}
                type="button"
              >
                {mobileMenuOpen ? <X size={19} /> : <Menu size={19} />}
              </button>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-ink-600/75">
                  MediCare AI
                </p>
                <h1 className="text-sm font-bold text-ink-950">{pageTitle}</h1>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="hidden max-w-[220px] truncate text-sm font-medium text-ink-600 sm:block">
                {user?.email}
              </span>
              <button
                aria-label="Sign out"
                className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-line px-3 text-sm font-semibold text-ink-800 transition hover:border-brand-600/30 hover:bg-brand-100 hover:text-brand-700"
                onClick={() => void handleSignOut()}
                type="button"
              >
                <LogOut aria-hidden="true" size={16} />
                <span className="hidden sm:inline">Sign out</span>
              </button>
            </div>
          </div>
          {mobileMenuOpen && (
            <div className="border-t border-line bg-white px-4 py-3 lg:hidden">
              {renderNavigation(true)}
            </div>
          )}
          {logoutError && (
            <p className="border-t border-amber-200 bg-amber-50 px-5 py-2 text-center text-sm text-amber-900">
              Sign out did not reach the server. Your session is still active;
              please try again. {logoutError}
            </p>
          )}
        </header>

        <main className="mx-auto min-h-[calc(100vh-72px)] max-w-[1440px] px-4 py-7 sm:px-7 sm:py-9 lg:px-10">
          <Outlet />
        </main>

        <footer className="border-t border-line/80 px-5 py-5 text-center text-xs text-ink-600">
          MediCare AI patient portal · Your account details stay yours
          <ArrowUpRight aria-hidden="true" className="ml-1 inline" size={12} />
        </footer>
      </div>
    </div>
  )
}
