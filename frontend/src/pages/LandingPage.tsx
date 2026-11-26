import {
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  Check,
  HeartPulse,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
  UserRound,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { Brand } from '../components/Brand'

const features = [
  {
    icon: UserRound,
    title: 'Your details, together',
    description:
      'Keep the personal information in your patient profile easy to review and update.',
  },
  {
    icon: ShieldCheck,
    title: 'A private patient space',
    description:
      'Your account is designed around your own sign-in and patient profile.',
  },
  {
    icon: Sparkles,
    title: 'Built to grow thoughtfully',
    description:
      'A calm foundation for connected care features as they become available.',
  },
]

export function LandingPage() {
  const { status, user } = useAuth()
  const portalPath = status === 'authenticated' && user ? '/dashboard' : '/register'

  return (
    <div className="overflow-hidden bg-white text-ink-950">
      <header className="relative z-10 mx-auto flex h-[82px] max-w-[1240px] items-center justify-between px-5 sm:px-8">
        <Brand />
        <nav aria-label="Main navigation" className="flex items-center gap-2 sm:gap-4">
          <a
            className="hidden px-3 py-2 text-sm font-semibold text-ink-600 transition hover:text-brand-700 sm:inline-flex"
            href="#approach"
          >
            Our approach
          </a>
          {status === 'authenticated' ? (
            <Link
              className="inline-flex min-h-10 items-center gap-2 rounded-full bg-brand-700 px-5 text-sm font-semibold text-white transition hover:bg-brand-600"
              to="/dashboard"
            >
              Open portal <ArrowRight aria-hidden="true" size={16} />
            </Link>
          ) : (
            <>
              <Link
                className="hidden min-h-10 items-center rounded-full px-4 text-sm font-semibold text-ink-800 transition hover:bg-sky-50 sm:inline-flex"
                to="/login"
              >
                Sign in
              </Link>
              <Link
                className="inline-flex min-h-10 items-center gap-2 rounded-full bg-brand-700 px-5 text-sm font-semibold text-white transition hover:bg-brand-600"
                to="/register"
              >
                Create account <ArrowRight aria-hidden="true" size={16} />
              </Link>
            </>
          )}
        </nav>
      </header>

      <main>
        <section className="relative isolate bg-sky-50">
          <div className="absolute -right-44 -top-56 size-[630px] rounded-full border border-[#dcecef]" />
          <div className="absolute -right-20 -top-32 size-[390px] rounded-full border border-[#dcecef]" />
          <div className="relative mx-auto grid max-w-[1240px] items-center gap-12 px-5 pb-20 pt-12 sm:px-8 sm:pb-24 lg:grid-cols-[1fr_0.95fr] lg:gap-10 lg:pb-28 lg:pt-16">
            <div className="page-enter max-w-[600px]">
              <span className="inline-flex items-center gap-2 rounded-full border border-brand-600/15 bg-white/80 px-3.5 py-2 text-xs font-bold uppercase tracking-[0.13em] text-brand-700 shadow-sm">
                <span className="size-1.5 rounded-full bg-brand-600" />
                A thoughtful patient portal
              </span>
              <h1 className="mt-7 text-balance text-[42px] font-semibold leading-[1.08] tracking-[-0.055em] text-ink-950 sm:text-[58px] lg:text-[66px]">
                Care feels better
                <span className="block text-brand-700">when it’s clear.</span>
              </h1>
              <p className="mt-6 max-w-[510px] text-base leading-7 text-ink-600 sm:text-lg sm:leading-8">
                A calmer place to manage your patient profile and keep your
                account details close at hand.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link
                  className="inline-flex min-h-[52px] items-center justify-center gap-2 rounded-xl bg-brand-700 px-6 text-sm font-bold text-white shadow-[0_12px_24px_rgb(8_124_128/18%)] transition hover:-translate-y-0.5 hover:bg-brand-600"
                  to={portalPath}
                >
                  {status === 'authenticated' ? 'Open your portal' : 'Get started'}
                  <ArrowRight aria-hidden="true" size={17} />
                </Link>
                <Link
                  className="inline-flex min-h-[52px] items-center justify-center rounded-xl border border-line bg-white px-6 text-sm font-bold text-ink-800 transition hover:border-brand-600/30 hover:bg-brand-100/40"
                  to="/login"
                >
                  I already have an account
                </Link>
              </div>
              <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3 text-xs font-medium text-ink-600">
                <span className="inline-flex items-center gap-2">
                  <LockKeyhole aria-hidden="true" size={15} className="text-brand-700" />
                  Private account access
                </span>
                <span className="inline-flex items-center gap-2">
                  <Check aria-hidden="true" size={15} className="text-brand-700" />
                  Your profile, your control
                </span>
              </div>
            </div>

            <div
              aria-label="Illustration of the patient portal"
              className="relative mx-auto w-full max-w-[540px] page-enter"
            >
              <div className="absolute -left-5 top-16 z-10 hidden rounded-2xl border border-white/80 bg-white px-4 py-3 shadow-panel sm:block">
                <div className="flex items-center gap-3">
                  <span className="grid size-10 place-items-center rounded-xl bg-brand-100 text-brand-700">
                    <ShieldCheck aria-hidden="true" size={20} />
                  </span>
                  <span>
                    <span className="block text-xs font-bold text-ink-950">
                      Patient-first
                    </span>
                    <span className="mt-0.5 block text-[11px] text-ink-600">
                      Your account, your space
                    </span>
                  </span>
                </div>
              </div>
              <div className="relative overflow-hidden rounded-[30px] border border-white/90 bg-white p-5 shadow-[0_32px_80px_rgb(17_59_72/14%)] sm:p-7">
                <div className="absolute -right-12 -top-16 size-56 rounded-full bg-[#def2f0] blur-2xl" />
                <div className="relative flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="grid size-11 place-items-center rounded-2xl bg-brand-700 text-white">
                      <HeartPulse aria-hidden="true" size={21} />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-ink-950">
                        Your care space
                      </p>
                      <p className="mt-0.5 text-xs text-ink-600">
                        A clear place to begin
                      </p>
                    </div>
                  </div>
                  <span className="grid size-9 place-items-center rounded-full bg-sky-50 text-ink-600">
                    <ArrowUpRight aria-hidden="true" size={17} />
                  </span>
                </div>
                <div className="relative mt-7 rounded-2xl bg-[#f7fafb] p-4 sm:p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-ink-600">
                        Patient profile
                      </p>
                      <p className="mt-1 text-lg font-bold tracking-tight text-ink-950">
                        Your details, in one view
                      </p>
                    </div>
                    <div className="grid size-11 place-items-center rounded-full bg-[#d7eeeb] text-brand-700">
                      <UserRound aria-hidden="true" size={21} />
                    </div>
                  </div>
                  <div className="mt-5 grid grid-cols-2 gap-3">
                    <div className="rounded-xl border border-line bg-white p-3.5">
                      <p className="text-[11px] font-medium text-ink-600">
                        Account
                      </p>
                      <p className="mt-1.5 flex items-center gap-1.5 text-xs font-bold text-brand-700">
                        <span className="size-1.5 rounded-full bg-brand-600" />
                        Connected
                      </p>
                    </div>
                    <div className="rounded-xl border border-line bg-white p-3.5">
                      <p className="text-[11px] font-medium text-ink-600">
                        Health data
                      </p>
                      <p className="mt-1.5 text-xs font-bold text-ink-800">
                        Not connected
                      </p>
                    </div>
                  </div>
                </div>
                <div className="relative mt-4 flex items-center gap-3 rounded-2xl border border-[#dcefeb] bg-[#f1faf7] p-4">
                  <span className="grid size-10 place-items-center rounded-xl bg-white text-brand-700 shadow-sm">
                    <CalendarDays aria-hidden="true" size={19} />
                  </span>
                  <p className="text-xs leading-5 text-ink-600">
                    <span className="block font-bold text-ink-950">
                      A foundation that grows with you
                    </span>
                    Connected care tools will appear as they become available.
                  </p>
                </div>
                <div className="pointer-events-none absolute -bottom-12 -right-5 -z-10 size-40 rounded-full bg-[#9bd8d2]/35 blur-3xl" />
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-[1240px] px-5 py-20 sm:px-8 sm:py-24" id="approach">
          <div className="mx-auto max-w-[650px] text-center">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-700">
              Made for clarity
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-[-0.045em] text-ink-950 sm:text-[42px]">
              Start with what matters.
            </h2>
            <p className="mt-4 text-sm leading-7 text-ink-600 sm:text-base">
              A simple patient experience today, designed to make room for
              thoughtful digital care tomorrow.
            </p>
          </div>
          <div className="mt-12 grid gap-4 md:grid-cols-3">
            {features.map(({ icon: Icon, title, description }, index) => (
              <article
                className="group rounded-[24px] border border-line bg-white p-6 transition duration-300 hover:-translate-y-1 hover:border-brand-600/25 hover:shadow-panel sm:p-7"
                key={title}
              >
                <div
                  className={`grid size-12 place-items-center rounded-2xl ${
                    index === 1
                      ? 'bg-[#e4f5f1] text-brand-700'
                      : 'bg-sky-100 text-ink-800'
                  }`}
                >
                  <Icon aria-hidden="true" size={22} strokeWidth={1.8} />
                </div>
                <h3 className="mt-6 text-lg font-bold tracking-tight text-ink-950">
                  {title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-ink-600">
                  {description}
                </p>
              </article>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-[1240px] px-5 pb-20 sm:px-8 sm:pb-24">
          <div className="flex flex-col items-start justify-between gap-6 rounded-[28px] bg-[#123b48] px-6 py-9 text-white sm:px-10 md:flex-row md:items-center md:px-12 md:py-11">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.17em] text-[#9de2d8]">
                Your patient space is ready
              </p>
              <h2 className="mt-3 max-w-[580px] text-2xl font-semibold leading-tight tracking-[-0.04em] sm:text-3xl">
                Take the first step toward a more connected experience.
              </h2>
            </div>
            <Link
              className="inline-flex min-h-12 shrink-0 items-center gap-2 rounded-xl bg-white px-5 text-sm font-bold text-ink-950 transition hover:bg-[#e2f4f3]"
              to={portalPath}
            >
              {status === 'authenticated' ? 'Go to your portal' : 'Create your account'}
              <ArrowRight aria-hidden="true" size={16} />
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-line bg-white">
        <div className="mx-auto flex max-w-[1240px] flex-col gap-3 px-5 py-6 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <Brand />
          <p className="text-xs text-ink-600">
            A patient portal foundation · Care tools shown only when connected
          </p>
          <Link
            className="inline-flex items-center gap-1 text-xs font-semibold text-ink-600 transition hover:text-brand-700"
            to="/login"
          >
            Patient sign in <ArrowUpRight aria-hidden="true" size={13} />
          </Link>
        </div>
      </footer>
    </div>
  )
}
