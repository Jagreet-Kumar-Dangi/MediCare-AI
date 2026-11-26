import {
  Activity,
  ArrowRight,
  CalendarDays,
  CircleCheck,
  FileHeart,
  RefreshCw,
  ShieldCheck,
  UserRound,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from 'recharts'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getApiErrorMessage } from '../api/errors'
import { getHealth } from '../api/health'
import { getMyPatientProfile } from '../api/patients'
import { useAuth } from '../auth/useAuth'
import type { HealthResponse, PatientProfile } from '../types/api'

const illustrativeActivity = [
  { day: 'Mon', sample: 2 },
  { day: 'Tue', sample: 4 },
  { day: 'Wed', sample: 3 },
  { day: 'Thu', sample: 5 },
  { day: 'Fri', sample: 3 },
  { day: 'Sat', sample: 6 },
  { day: 'Sun', sample: 4 },
]

const todayLabel = new Intl.DateTimeFormat('en', {
  weekday: 'long',
  month: 'long',
  day: 'numeric',
}).format(new Date())

export function DashboardPage() {
  const { user } = useAuth()
  const [profile, setProfile] = useState<PatientProfile | null>(null)
  const [profileError, setProfileError] = useState<string | null>(null)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthError, setHealthError] = useState(false)
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    let active = true

    void getMyPatientProfile()
      .then((result) => {
        if (active) setProfile(result)
      })
      .catch((error: unknown) => {
        if (active) setProfileError(getApiErrorMessage(error))
      })

    void getHealth()
      .then((result) => {
        if (active) setHealth(result)
      })
      .catch(() => {
        if (active) setHealthError(true)
      })

    return () => {
      active = false
    }
  }, [retry])

  const firstName = profile?.first_name

  return (
    <div className="page-enter space-y-8">
      <section className="relative overflow-hidden rounded-[26px] bg-[#123b48] px-6 py-7 text-white shadow-panel sm:px-9 sm:py-9">
        <div className="absolute -right-20 -top-32 size-80 rounded-full border border-white/10" />
        <div className="absolute -right-3 -top-16 size-52 rounded-full border border-white/10" />
        <div className="absolute -bottom-36 right-[27%] size-64 rounded-full bg-brand-600/20 blur-3xl" />
        <div className="relative flex flex-col justify-between gap-7 md:flex-row md:items-end">
          <div className="max-w-[660px]">
            <p className="text-xs font-bold uppercase tracking-[0.17em] text-[#9de2d8]">
              {todayLabel}
            </p>
            <h2 className="mt-3 text-3xl font-semibold leading-tight tracking-[-0.045em] sm:text-[40px]">
              {firstName ? `Welcome, ${firstName}.` : 'Welcome to your care space.'}
            </h2>
            <p className="mt-3 max-w-[540px] text-sm leading-6 text-white/70 sm:text-base">
              Your patient profile and account status, together in one clear
              view. No clinical readings are connected yet.
            </p>
          </div>
          <Link
            className="inline-flex min-h-12 shrink-0 items-center justify-center gap-2 rounded-xl bg-white px-5 text-sm font-bold text-ink-950 transition hover:bg-[#e2f4f3]"
            to="/profile"
          >
            Review my profile <ArrowRight aria-hidden="true" size={16} />
          </Link>
        </div>
        <div className="relative mt-7 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-white/15 pt-5 text-xs text-white/70">
          {healthError ? (
            <span className="inline-flex items-center gap-2">
              <span className="size-2 rounded-full bg-amber-300" />
              API status unavailable
            </span>
          ) : (
            <span className="inline-flex items-center gap-2">
              <span
                className={`size-2 rounded-full ${health?.status === 'healthy' ? 'bg-[#8de1c6]' : 'animate-pulse bg-white/50'}`}
              />
              {health?.status === 'healthy' ? 'Portal connected' : 'Checking portal connection'}
            </span>
          )}
          <span className="inline-flex items-center gap-2">
            <ShieldCheck aria-hidden="true" size={14} />
            Signed in as {user?.email}
          </span>
        </div>
      </section>

      <section aria-labelledby="overview-heading">
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.15em] text-brand-700">
              Your account
            </p>
            <h2
              className="mt-1 text-xl font-bold tracking-[-0.035em] text-ink-950"
              id="overview-heading"
            >
              A simple overview
            </h2>
          </div>
          <button
            aria-label="Refresh dashboard information"
            className="grid size-10 place-items-center rounded-xl border border-line bg-white text-ink-600 transition hover:border-brand-600/30 hover:text-brand-700"
            onClick={() => {
              setProfileError(null)
              setHealthError(false)
              setRetry((value) => value + 1)
            }}
            type="button"
          >
            <RefreshCw aria-hidden="true" size={16} />
          </button>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <OverviewCard
            detail={profileError ?? 'Your personal details are available to you.'}
            icon={UserRound}
            label="Patient profile"
            status={profile ? 'Available' : profileError ? 'Unavailable' : 'Loading'}
            tone={profileError ? 'amber' : 'teal'}
          />
          <OverviewCard
            detail="Your account is the only one signed in on this session."
            icon={ShieldCheck}
            label="Account access"
            status={user?.is_active ? 'Active' : 'Check account'}
            tone="blue"
          />
          <OverviewCard
            detail="Upload and review your reports in private patient storage."
            icon={FileHeart}
            label="Medical records"
            status="Available"
            tone="teal"
          />
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
        <article className="rounded-[24px] border border-line bg-white p-5 shadow-sm sm:p-7">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
            <div>
              <div className="flex items-center gap-2">
                <Activity aria-hidden="true" className="text-brand-700" size={18} />
                <h2 className="text-base font-bold tracking-tight text-ink-950">
                  A preview of your overview
                </h2>
              </div>
              <p className="mt-2 text-xs leading-5 text-ink-600">
                Illustrative interface data only — no personal health readings
                or activity have been loaded.
              </p>
            </div>
            <span className="w-fit rounded-full bg-sky-50 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.12em] text-ink-600">
              Demo preview
            </span>
          </div>
          <div aria-label="Illustrative demo chart" className="mt-5 h-[205px] w-full">
            <ResponsiveContainer height="100%" width="100%">
              <AreaChart
                accessibilityLayer
                data={illustrativeActivity}
                margin={{ top: 8, right: 6, left: -24, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="demoFill" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#0c9296" stopOpacity={0.19} />
                    <stop offset="95%" stopColor="#0c9296" stopOpacity={0.01} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  stroke="#e8eff1"
                  strokeDasharray="3 5"
                  vertical={false}
                />
                <XAxis
                  axisLine={false}
                  dataKey="day"
                  tick={{ fill: '#81939a', fontSize: 11 }}
                  tickLine={false}
                  tickMargin={12}
                />
                <Tooltip
                  contentStyle={{
                    border: '1px solid #e3ecef',
                    borderRadius: 12,
                    fontSize: 12,
                  }}
                  formatter={(value) => [`${value} (demo)`, 'Preview value']}
                />
                <Area
                  dataKey="sample"
                  fill="url(#demoFill)"
                  isAnimationActive={false}
                  stroke="#0c9296"
                  strokeLinecap="round"
                  strokeWidth={2.5}
                  type="monotone"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="rounded-[24px] border border-line bg-white p-5 shadow-sm sm:p-7">
          <div className="flex items-center gap-2">
            <CalendarDays aria-hidden="true" className="text-brand-700" size={18} />
            <h2 className="text-base font-bold tracking-tight text-ink-950">
              Recent activity
            </h2>
          </div>
          <div className="mt-6 flex min-h-[190px] flex-col items-center justify-center rounded-2xl border border-dashed border-line bg-sky-50/60 px-5 text-center">
            <span className="grid size-11 place-items-center rounded-2xl bg-white text-brand-700 shadow-sm">
              <CalendarDays aria-hidden="true" size={20} />
            </span>
            <p className="mt-3 text-sm font-semibold text-ink-800">
              Nothing to show yet
            </p>
            <p className="mt-1 max-w-[260px] text-xs leading-5 text-ink-600">
              Activity will appear here when connected services provide it.
              No history is being assumed.
            </p>
          </div>
        </article>
      </section>

      <section aria-labelledby="quick-actions-heading">
        <div className="mb-4">
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-brand-700">
            Get started
          </p>
          <h2
            className="mt-1 text-xl font-bold tracking-[-0.035em] text-ink-950"
            id="quick-actions-heading"
          >
            Quick actions
          </h2>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Link
            className="group flex items-center justify-between rounded-2xl border border-line bg-white p-4 transition hover:border-brand-600/30 hover:shadow-sm sm:p-5"
            to="/profile"
          >
            <span className="flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-xl bg-brand-100 text-brand-700">
                <UserRound aria-hidden="true" size={18} />
              </span>
              <span>
                <span className="block text-sm font-bold text-ink-950">
                  {profile ? 'Review your profile' : 'Complete your profile'}
                </span>
                <span className="mt-0.5 block text-xs text-ink-600">
                  Manage the details you’ve shared
                </span>
              </span>
            </span>
            <ArrowRight
              aria-hidden="true"
              className="text-ink-600 transition group-hover:translate-x-1 group-hover:text-brand-700"
              size={17}
            />
          </Link>
          <Link
            className="group flex items-center justify-between rounded-2xl border border-line bg-white p-4 transition hover:border-brand-600/30 hover:shadow-sm sm:p-5"
            to="/medical-records"
          >
            <span className="flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-xl bg-sky-100 text-brand-700">
                <FileHeart aria-hidden="true" size={18} />
              </span>
              <span>
                <span className="block text-sm font-bold text-ink-950">
                  Manage medical records
                </span>
                <span className="mt-0.5 block text-xs text-ink-600">
                  Upload or review your reports
                </span>
              </span>
            </span>
            <ArrowRight
              aria-hidden="true"
              className="text-ink-600 transition group-hover:translate-x-1 group-hover:text-brand-700"
              size={17}
            />
          </Link>
          <div className="flex items-center gap-3 rounded-2xl border border-line bg-white p-4 sm:p-5 sm:col-span-2">
            <span className="grid size-10 place-items-center rounded-xl bg-[#fff1ec] text-coral-500">
              <CircleCheck aria-hidden="true" size={18} />
            </span>
            <span>
              <span className="block text-sm font-bold text-ink-950">
                Your information stays yours
              </span>
              <span className="mt-0.5 block text-xs text-ink-600">
                Sign out when you finish on a shared device
              </span>
            </span>
          </div>
        </div>
      </section>
    </div>
  )
}

interface OverviewCardProps {
  detail: string
  icon: typeof UserRound
  label: string
  status: string
  tone: 'teal' | 'blue' | 'coral' | 'amber'
}

function OverviewCard({ detail, icon: Icon, label, status, tone }: OverviewCardProps) {
  const iconTone = {
    teal: 'bg-brand-100 text-brand-700',
    blue: 'bg-sky-100 text-[#47738a]',
    coral: 'bg-[#fff1ec] text-coral-500',
    amber: 'bg-amber-50 text-amber-700',
  }[tone]

  return (
    <article className="rounded-[22px] border border-line bg-white p-5 shadow-sm transition hover:shadow-panel">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold text-ink-600">{label}</p>
          <p className="mt-2 text-xl font-bold tracking-tight text-ink-950">
            {status}
          </p>
        </div>
        <span className={`grid size-11 shrink-0 place-items-center rounded-2xl ${iconTone}`}>
          <Icon aria-hidden="true" size={20} strokeWidth={1.8} />
        </span>
      </div>
      <p className="mt-3 min-h-10 text-xs leading-5 text-ink-600">{detail}</p>
    </article>
  )
}
