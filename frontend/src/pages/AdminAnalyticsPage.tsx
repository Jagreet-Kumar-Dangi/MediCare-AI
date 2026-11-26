import {
  Activity,
  ArrowDownToLine,
  CalendarDays,
  CheckCircle2,
  Clock3,
  RefreshCw,
  UsersRound,
  type LucideIcon,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { getApiErrorMessage } from '../api/errors'
import {
  analyticsGranularities,
  analyticsPeriods,
  downloadAdminAnalyticsCsv,
  getAdminAnalyticsOverview,
  getAdminAppointmentAnalytics,
  getAdminDoctorAnalytics,
  getAdminDoctorPerformance,
  getAdminNotificationAnalytics,
  getAdminPatientAnalytics,
} from '../api/adminAnalytics'
import type {
  AdminAnalyticsOverview,
  AdminAppointmentAnalytics,
  AdminDoctorAnalytics,
  AdminDoctorPerformance,
  AdminNotificationAnalytics,
  AdminPatientAnalytics,
  AnalyticsGranularity,
  AnalyticsPeriod,
  AppointmentStatus,
  DoctorVerificationStatus,
} from '../types/api'

type DashboardSection =
  | 'overview'
  | 'patients'
  | 'doctors'
  | 'appointments'
  | 'notifications'
  | 'performance'
  | 'reports'

interface AnalyticsData {
  overview: AdminAnalyticsOverview
  patients: AdminPatientAnalytics
  doctors: AdminDoctorAnalytics
  appointments: AdminAppointmentAnalytics
  notifications: AdminNotificationAnalytics
  performance: AdminDoctorPerformance
}

const chartColors = ['#0c9296', '#3478a3', '#edaa59', '#d86464', '#7166a8', '#8aa8a6']
const numberFormatter = new Intl.NumberFormat('en-IN')

function formatBucket(value: string): string {
  return new Intl.DateTimeFormat('en-IN', {
    timeZone: 'Asia/Kolkata',
    month: 'short',
    day: 'numeric',
    year: '2-digit',
  }).format(new Date(`${value}T00:00:00+05:30`))
}

function formatNumber(value: number): string {
  return numberFormatter.format(value)
}

function statusLabel(status: string): string {
  return status.replaceAll('_', ' ').toLowerCase().replace(/^\w/, (letter) =>
    letter.toUpperCase(),
  )
}

function comparisonLabel(
  comparison: { percent_change: number | null; comparison_available: boolean } | null,
): string {
  if (!comparison?.comparison_available || comparison.percent_change === null) {
    return 'No prior-period comparison'
  }
  const sign = comparison.percent_change > 0 ? '+' : ''
  return `${sign}${comparison.percent_change}% vs previous period`
}

function SectionHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string
  title: string
  description?: string
}) {
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-700">
        {eyebrow}
      </p>
      <h2 className="mt-1 text-xl font-bold tracking-[-0.035em] text-ink-950">
        {title}
      </h2>
      {description && (
        <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-600">
          {description}
        </p>
      )}
    </div>
  )
}

function MetricCard({
  label,
  value,
  detail,
  valueLabel,
  icon: Icon,
}: {
  label: string
  value: number
  detail?: string
  icon: LucideIcon
  valueLabel?: string
}) {
  return (
    <article className="rounded-2xl border border-line bg-white p-4 shadow-sm sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-ink-600">{label}</p>
          <p className="mt-2 text-2xl font-bold tracking-tight text-ink-950">
            {valueLabel ?? formatNumber(value)}
          </p>
        </div>
        <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-brand-100 text-brand-700">
          <Icon aria-hidden="true" size={17} />
        </span>
      </div>
      {detail && <p className="mt-3 text-[11px] leading-4 text-ink-600">{detail}</p>}
    </article>
  )
}

function ChartPanel({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children: ReactNode
}) {
  return (
    <article className="rounded-3xl border border-line bg-white p-5 shadow-sm sm:p-6">
      <div className="mb-4">
        <h3 className="text-sm font-bold text-ink-950">{title}</h3>
        {description && (
          <p className="mt-1 text-xs leading-5 text-ink-600">{description}</p>
        )}
      </div>
      {children}
    </article>
  )
}

function EmptyChart() {
  return (
    <div className="grid h-[250px] place-items-center rounded-2xl bg-sky-50 px-5 text-center text-sm text-ink-600">
      No records for the selected period.
    </div>
  )
}

function TrendChart({
  title,
  data,
  color = '#0c9296',
  kind = 'line',
}: {
  title: string
  data: { bucket: string; count: number }[]
  color?: string
  kind?: 'line' | 'bar'
}) {
  const hasData = data.some((point) => point.count > 0)
  return (
    <ChartPanel title={title}>
      {!hasData ? (
        <EmptyChart />
      ) : (
        <div aria-label={`${title} chart`} className="h-[250px] w-full">
          <ResponsiveContainer height="100%" width="100%">
            {kind === 'bar' ? (
              <BarChart accessibilityLayer data={data}>
                <CartesianGrid stroke="#e8eff1" strokeDasharray="3 5" vertical={false} />
                <XAxis
                  axisLine={false}
                  dataKey="bucket"
                  tickFormatter={formatBucket}
                  tickLine={false}
                  tick={{ fill: '#81939a', fontSize: 10 }}
                />
                <YAxis allowDecimals={false} axisLine={false} tickLine={false} width={30} />
                <Tooltip
                  formatter={(value) => [formatNumber(Number(value)), 'Count']}
                  labelFormatter={(label) => formatBucket(String(label))}
                />
                <Bar dataKey="count" fill={color} name={title} radius={[5, 5, 0, 0]} />
              </BarChart>
            ) : (
              <LineChart accessibilityLayer data={data}>
                <CartesianGrid stroke="#e8eff1" strokeDasharray="3 5" vertical={false} />
                <XAxis
                  axisLine={false}
                  dataKey="bucket"
                  tickFormatter={formatBucket}
                  tickLine={false}
                  tick={{ fill: '#81939a', fontSize: 10 }}
                />
                <YAxis allowDecimals={false} axisLine={false} tickLine={false} width={30} />
                <Tooltip
                  formatter={(value) => [formatNumber(Number(value)), 'Count']}
                  labelFormatter={(label) => formatBucket(String(label))}
                />
                <Line
                  dataKey="count"
                  dot={false}
                  name={title}
                  stroke={color}
                  strokeWidth={2.5}
                  type="monotone"
                />
              </LineChart>
            )}
          </ResponsiveContainer>
        </div>
      )}
    </ChartPanel>
  )
}

function StatusChart({
  title,
  data,
}: {
  title: string
  data: { status: string; count: number }[]
}) {
  const positiveData = data.filter((item) => item.count > 0)
  return (
    <ChartPanel title={title}>
      {positiveData.length === 0 ? (
        <EmptyChart />
      ) : (
        <div aria-label={`${title} chart`} className="h-[250px] w-full">
          <ResponsiveContainer height="100%" width="100%">
            <PieChart accessibilityLayer>
              <Pie
                data={positiveData}
                dataKey="count"
                nameKey="status"
                innerRadius={55}
                outerRadius={88}
                paddingAngle={3}
              >
                {positiveData.map((item, index) => (
                  <Cell fill={chartColors[index % chartColors.length]} key={item.status} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value) => formatNumber(Number(value))}
                labelFormatter={(label) => statusLabel(String(label))}
              />
              <Legend formatter={(label) => statusLabel(String(label))} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </ChartPanel>
  )
}

function LoadingDashboard() {
  return (
    <div aria-label="Loading analytics" aria-live="polite" className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 10 }, (_, index) => (
          <div className="h-28 animate-pulse rounded-2xl bg-slate-200" key={index} />
        ))}
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <div className="h-[320px] animate-pulse rounded-3xl bg-slate-200" />
        <div className="h-[320px] animate-pulse rounded-3xl bg-slate-200" />
      </div>
    </div>
  )
}

export function AdminAnalyticsPage() {
  const [period, setPeriod] = useState<AnalyticsPeriod>('last_30_days')
  const [granularity, setGranularity] = useState<AnalyticsGranularity>('day')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [appointmentStatus, setAppointmentStatus] = useState<
    AppointmentStatus | ''
  >('')
  const [doctorStatus, setDoctorStatus] = useState<DoctorVerificationStatus | ''>('')
  const [doctorIdInput, setDoctorIdInput] = useState('')
  const [section, setSection] = useState<DashboardSection>('overview')
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [exporting, setExporting] = useState<string | null>(null)
  const [refreshVersion, setRefreshVersion] = useState(0)

  const customRangeReady =
    period !== 'custom' || Boolean(startDate && endDate && startDate <= endDate)
  const filters = useMemo(
    () => ({
      period,
      ...(period === 'custom' ? { start_date: startDate, end_date: endDate } : {}),
      granularity,
    }),
    [endDate, granularity, period, startDate],
  )

  useEffect(() => {
    let active = true
    if (!customRangeReady) {
      return () => {
        active = false
      }
    }

    const appointmentFilters = {
      ...filters,
      ...(appointmentStatus ? { status: appointmentStatus } : {}),
      ...(doctorIdInput && Number(doctorIdInput) > 0
        ? { doctor_id: Number(doctorIdInput) }
        : {}),
    }
    const doctorFilters = {
      ...filters,
      ...(doctorStatus ? { verification_status: doctorStatus } : {}),
    }

    void Promise.all([
      getAdminAnalyticsOverview(filters),
      getAdminPatientAnalytics(filters),
      getAdminDoctorAnalytics(doctorFilters),
      getAdminAppointmentAnalytics(appointmentFilters),
      getAdminNotificationAnalytics(filters),
      getAdminDoctorPerformance(doctorFilters),
    ])
      .then(
        ([
          overview,
          patients,
          doctors,
          appointments,
          notifications,
          performance,
        ]) => {
          if (active) {
            setData({
              overview,
              patients,
              doctors,
              appointments,
              notifications,
              performance,
            })
          }
        },
      )
      .catch((requestError: unknown) => {
        if (active) {
          setData(null)
          setError(getApiErrorMessage(requestError))
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [
    appointmentStatus,
    customRangeReady,
    doctorIdInput,
    doctorStatus,
    endDate,
    filters,
    period,
    refreshVersion,
    startDate,
  ])

  async function exportCsv(dataset: 'patients' | 'doctors' | 'appointments' | 'notifications') {
    setExporting(dataset)
    setError(null)
    try {
      const blob = await downloadAdminAnalyticsCsv(dataset, {
        ...filters,
        ...(dataset === 'appointments' && appointmentStatus
          ? { status: appointmentStatus }
          : {}),
        ...(dataset === 'appointments' && doctorIdInput && Number(doctorIdInput) > 0
          ? { doctor_id: Number(doctorIdInput) }
          : {}),
        ...(dataset === 'doctors' && doctorStatus
          ? { verification_status: doctorStatus }
          : {}),
      })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `medicare-${dataset}-analytics.csv`
      document.body.append(link)
      link.click()
      link.remove()
      window.setTimeout(() => window.URL.revokeObjectURL(url), 1000)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setExporting(null)
    }
  }

  const navItems: { value: DashboardSection; label: string }[] = [
    { value: 'overview', label: 'Overview' },
    { value: 'patients', label: 'Patients' },
    { value: 'doctors', label: 'Doctors' },
    { value: 'appointments', label: 'Appointments' },
    { value: 'notifications', label: 'Notifications' },
    { value: 'performance', label: 'Doctor operations' },
    { value: 'reports', label: 'Reports' },
  ]

  const overviewMetrics = data
    ? [
        ['Registered users', data.overview.total_users, data.overview.new_users],
        ['Patients', data.overview.total_patients, data.overview.new_patients],
        ['Doctors', data.overview.total_doctors, data.overview.new_doctors],
        ['Approved doctors', data.overview.approved_doctors, null],
        ['Pending verification', data.overview.pending_doctors, null],
        ['Suspended doctors', data.overview.suspended_doctors, null],
        [
          'Appointments',
          data.overview.total_appointments,
          data.overview.appointments_created,
        ],
        ['Upcoming', data.overview.upcoming_appointments, null],
        ['Completed', data.overview.completed_appointments, null],
        ['Cancelled', data.overview.cancelled_appointments, null],
      ] as const
    : []

  return (
    <div className="space-y-7">
      <header className="flex flex-col justify-between gap-5 xl:flex-row xl:items-end">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-700">
            Administrator workspace
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.045em] text-ink-950">
            Analytics &amp; operations
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-600">
            Database-backed aggregate reporting. Reporting periods use
            Asia/Kolkata; stored timestamps remain UTC. No patient medical
            records or notification contents are included.
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <label className="space-y-1 text-xs font-semibold text-ink-700">
            Reporting period
            <select
              className="block min-h-10 rounded-xl border border-line bg-white px-3 text-sm"
              onChange={(event) => {
                setLoading(true)
                setError(null)
                setPeriod(event.target.value as AnalyticsPeriod)
              }}
              value={period}
            >
              {analyticsPeriods.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1 text-xs font-semibold text-ink-700">
            Trend interval
            <select
              className="block min-h-10 rounded-xl border border-line bg-white px-3 text-sm"
              onChange={(event) => {
                setLoading(true)
                setError(null)
                setGranularity(event.target.value as AnalyticsGranularity)
              }}
              value={granularity}
            >
              {analyticsGranularities.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <button
            aria-label="Refresh analytics"
            className="grid size-10 place-items-center rounded-xl border border-line bg-white text-ink-700 hover:bg-sky-50"
            onClick={() => {
              setLoading(true)
              setError(null)
              setRefreshVersion((version) => version + 1)
            }}
            type="button"
          >
            <RefreshCw aria-hidden="true" size={17} />
          </button>
        </div>
      </header>

      {period === 'custom' && (
        <div className="flex flex-wrap gap-3 rounded-2xl border border-line bg-white p-4">
          <label className="space-y-1 text-xs font-semibold text-ink-700">
            Start date
            <input
              className="block min-h-10 rounded-xl border border-line px-3 text-sm"
              max={endDate || undefined}
              onChange={(event) => {
                setLoading(true)
                setError(null)
                setStartDate(event.target.value)
              }}
              type="date"
              value={startDate}
            />
          </label>
          <label className="space-y-1 text-xs font-semibold text-ink-700">
            End date
            <input
              className="block min-h-10 rounded-xl border border-line px-3 text-sm"
              min={startDate || undefined}
              onChange={(event) => {
                setLoading(true)
                setError(null)
                setEndDate(event.target.value)
              }}
              type="date"
              value={endDate}
            />
          </label>
        </div>
      )}

      <nav aria-label="Analytics sections" className="flex gap-2 overflow-x-auto pb-1">
        {navItems.map((item) => (
          <button
            aria-current={section === item.value ? 'page' : undefined}
            className={`min-h-10 shrink-0 rounded-xl px-4 text-sm font-semibold transition ${
              section === item.value
                ? 'bg-brand-700 text-white'
                : 'border border-line bg-white text-ink-700 hover:bg-sky-50'
            }`}
            key={item.value}
            onClick={() => setSection(item.value)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </nav>

      {error && (
        <div
          className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
          role="alert"
        >
          <span>{error}</span>
          <button
            className="font-semibold underline"
            onClick={() => {
              setLoading(true)
              setError(null)
              setRefreshVersion((version) => version + 1)
            }}
            type="button"
          >
            Try again
          </button>
        </div>
      )}

      {!customRangeReady ? (
        <p
          className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
          role="status"
        >
          {startDate && endDate
            ? 'The end date must be on or after the start date.'
            : 'Choose a start and end date to load analytics.'}
        </p>
      ) : loading ? (
        <LoadingDashboard />
      ) : !data ? (
        <div className="rounded-3xl border border-line bg-white p-10 text-center">
          <CalendarDays aria-hidden="true" className="mx-auto text-brand-700" size={28} />
          <p className="mt-3 text-sm text-ink-600">
            {period === 'custom'
              ? 'Choose a valid start and end date to load analytics.'
              : 'Analytics are not available until the request succeeds.'}
          </p>
        </div>
      ) : (
        <>
          {section === 'overview' && (
            <section aria-label="Analytics overview" className="space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-medium text-ink-600">
                    {data.overview.date_from} to {data.overview.date_to} ·{' '}
                    {data.overview.timezone}
                  </p>
                </div>
                <span className="rounded-full bg-teal-50 px-3 py-1.5 text-xs font-semibold text-teal-800">
                  Live aggregates
                </span>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                {overviewMetrics.map(([label, value, comparison]) => (
                  <MetricCard
                      detail={comparison ? comparisonLabel(comparison) : undefined}
                    icon={label.includes('Appointment') || label === 'Upcoming' ? CalendarDays : UsersRound}
                    key={label}
                    label={label}
                    value={value}
                  />
                ))}
              </div>
              <div className="grid gap-5 xl:grid-cols-2">
                <TrendChart
                  data={data.patients.registration_trend}
                  title="Patient registrations"
                  kind="bar"
                />
                <TrendChart
                  data={data.appointments.booking_trend}
                  title="Appointment bookings"
                  color="#3478a3"
                />
              </div>
            </section>
          )}

          {section === 'patients' && (
            <section className="space-y-5">
              <SectionHeading
                description="Registration and account activity aggregates only. Patient medical records and health details are excluded."
                eyebrow="Patient analytics"
                title="Patient registrations"
              />
              <div className="grid gap-3 sm:grid-cols-3">
                <MetricCard icon={UsersRound} label="Total patients" value={data.patients.total_patients} />
                <MetricCard icon={CheckCircle2} label="Active accounts" value={data.patients.active_patients} />
                <MetricCard icon={Clock3} label="Inactive accounts" value={data.patients.inactive_patients} />
              </div>
              <p className="text-xs text-ink-600">
                New registrations: {formatNumber(data.patients.new_registrations.current)} ·{' '}
                {comparisonLabel(data.patients.new_registrations)}
              </p>
              <TrendChart
                data={data.patients.registration_trend}
                title="Registration trend"
                kind="bar"
              />
            </section>
          )}

          {section === 'doctors' && (
            <section className="space-y-5">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <SectionHeading
                  description="Verification and credential status counts are aggregate-only. Credential files and confidential document details are never returned."
                  eyebrow="Doctor analytics"
                  title="Verification pipeline"
                />
                <label className="space-y-1 text-xs font-semibold text-ink-700">
                  Verification status
                  <select
                    className="block min-h-10 rounded-xl border border-line bg-white px-3 text-sm"
                    onChange={(event) => {
                      setLoading(true)
                      setError(null)
                      setDoctorStatus(event.target.value as DoctorVerificationStatus | '')
                    }}
                    value={doctorStatus}
                  >
                    <option value="">All statuses</option>
                    <option value="PENDING">Pending</option>
                    <option value="APPROVED">Approved</option>
                    <option value="REJECTED">Rejected</option>
                    <option value="SUSPENDED">Suspended</option>
                  </select>
                </label>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <MetricCard icon={UsersRound} label="Doctors in filter" value={data.doctors.total_doctors} />
                <MetricCard icon={CheckCircle2} label="Active accounts" value={data.doctors.active_accounts} />
                <MetricCard icon={Clock3} label="Inactive accounts" value={data.doctors.inactive_accounts} />
              </div>
              <div className="grid gap-5 xl:grid-cols-2">
                <StatusChart title="Doctor verification status" data={data.doctors.verification_statuses} />
                <StatusChart title="Credential review status" data={data.doctors.credential_statuses} />
                <TrendChart data={data.doctors.registration_trend} title="Doctor registrations" kind="bar" />
                <TrendChart data={data.doctors.approval_trend} title="Doctor approval decisions" color="#7166a8" />
              </div>
            </section>
          )}

          {section === 'appointments' && (
            <section className="space-y-5">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <SectionHeading
                  description="Booking trends use appointment creation time; cancellation and completion trends use audited status-change timestamps."
                  eyebrow="Appointment analytics"
                  title="Appointment activity"
                />
                <div className="flex flex-wrap gap-3">
                  <label className="space-y-1 text-xs font-semibold text-ink-700">
                    Status
                    <select
                      className="block min-h-10 rounded-xl border border-line bg-white px-3 text-sm"
                      onChange={(event) => {
                        setLoading(true)
                        setError(null)
                        setAppointmentStatus(event.target.value as AppointmentStatus | '')
                      }}
                      value={appointmentStatus}
                    >
                      <option value="">All statuses</option>
                      {['BOOKED', 'CONFIRMED', 'COMPLETED', 'CANCELLED', 'REJECTED', 'NO_SHOW'].map(
                        (status) => (
                          <option key={status} value={status}>
                            {statusLabel(status)}
                          </option>
                        ),
                      )}
                    </select>
                  </label>
                  <label className="space-y-1 text-xs font-semibold text-ink-700">
                    Doctor profile ID
                    <input
                      className="block min-h-10 w-36 rounded-xl border border-line px-3 text-sm"
                      min="1"
                      onChange={(event) => {
                        setLoading(true)
                        setError(null)
                        setDoctorIdInput(event.target.value)
                      }}
                      placeholder="Any doctor"
                      type="number"
                      value={doctorIdInput}
                    />
                  </label>
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <MetricCard icon={CalendarDays} label="Appointments created in period" value={data.appointments.total_appointments} />
                <MetricCard icon={Clock3} label="Upcoming in selected window" value={data.appointments.upcoming_appointments} />
              </div>
              <div className="grid gap-5 xl:grid-cols-2">
                <StatusChart title="Appointment status distribution" data={data.appointments.status_counts} />
                <TrendChart data={data.appointments.booking_trend} title="Appointment volume" color="#3478a3" kind="bar" />
                <TrendChart data={data.appointments.cancellation_trend} title="Cancellation trend" color="#d86464" />
                <TrendChart data={data.appointments.completion_trend} title="Completion trend" color="#0c9296" />
              </div>
            </section>
          )}

          {section === 'notifications' && (
            <section className="space-y-5">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <SectionHeading
                  description="Job counts and retry totals do not include recipient details, private messages, or SMTP configuration."
                  eyebrow="Notification analytics"
                  title="Delivery operations"
                />
                <Link
                  className="text-sm font-semibold text-brand-700 underline"
                  to="/admin/notification-jobs"
                >
                  Open notification monitoring
                </Link>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <MetricCard icon={Activity} label="Total jobs" value={data.notifications.total_jobs} />
                <MetricCard icon={Clock3} label="Pending / processing" value={data.notifications.pending_jobs + data.notifications.processing_jobs} />
                <MetricCard icon={CheckCircle2} label="Sent" value={data.notifications.sent_jobs} />
                <MetricCard icon={Activity} label="Failed" value={data.notifications.failed_jobs} />
                <MetricCard icon={RefreshCw} label="Jobs retried" value={data.notifications.retried_jobs} />
                <MetricCard icon={RefreshCw} label="Total retries" value={data.notifications.total_retries} />
                <MetricCard
                  detail={
                    data.notifications.email_success_rate_available
                      ? 'Sent / (sent + failed) email jobs'
                      : 'No completed email deliveries in this period'
                  }
                  icon={CheckCircle2}
                  label="Email success rate"
                  value={data.notifications.email_success_rate ?? 0}
                  valueLabel={
                    data.notifications.email_success_rate_available
                      ? `${formatNumber(data.notifications.email_success_rate ?? 0)}%`
                      : 'N/A'
                  }
                />
                <MetricCard icon={Activity} label="Cancelled / skipped" value={data.notifications.cancelled_jobs + data.notifications.skipped_jobs} />
              </div>
              <TrendChart data={data.notifications.job_trend} title="Notification jobs over time" />
            </section>
          )}

          {section === 'performance' && (
            <section className="space-y-5">
              <SectionHeading
                description="Operational appointment counts are not a measure of clinical quality. Upcoming counts include all currently booked or confirmed future appointments."
                eyebrow="Doctor operations"
                title="Appointments by doctor"
              />
              <label className="inline-flex items-center gap-2 text-sm text-ink-700">
                Verification status
                <select
                  className="min-h-10 rounded-xl border border-line bg-white px-3"
                  onChange={(event) => {
                    setLoading(true)
                    setError(null)
                    setDoctorStatus(event.target.value as DoctorVerificationStatus | '')
                  }}
                  value={doctorStatus}
                >
                  <option value="">All statuses</option>
                  <option value="PENDING">Pending</option>
                  <option value="APPROVED">Approved</option>
                  <option value="REJECTED">Rejected</option>
                  <option value="SUSPENDED">Suspended</option>
                </select>
              </label>
              <div className="overflow-hidden rounded-3xl border border-line bg-white">
                {data.performance.items.length === 0 ? (
                  <p className="p-8 text-center text-sm text-ink-600">
                    No doctors match the selected filters.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[780px] text-left text-sm">
                      <caption className="sr-only">
                        Aggregate appointments by doctor, not a quality ranking
                      </caption>
                      <thead className="bg-sky-50 text-xs uppercase tracking-wide text-ink-600">
                        <tr>
                          <th className="px-5 py-3 font-semibold">Doctor</th>
                          <th className="px-5 py-3 font-semibold">Account / review status</th>
                          <th className="px-5 py-3 font-semibold">Bookings</th>
                          <th className="px-5 py-3 font-semibold">Completed</th>
                          <th className="px-5 py-3 font-semibold">Cancelled</th>
                          <th className="px-5 py-3 font-semibold">Upcoming</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-line">
                        {data.performance.items.map((doctor) => (
                          <tr key={doctor.doctor_id}>
                            <td className="px-5 py-4 font-semibold text-ink-950">
                              {doctor.full_name}
                            </td>
                            <td className="px-5 py-4 text-ink-700">
                              {doctor.account_active ? 'Active' : 'Inactive'} ·{' '}
                              {statusLabel(doctor.verification_status)}
                            </td>
                            <td className="px-5 py-4">{formatNumber(doctor.total_appointments)}</td>
                            <td className="px-5 py-4">{formatNumber(doctor.completed_appointments)}</td>
                            <td className="px-5 py-4">{formatNumber(doctor.cancelled_appointments)}</td>
                            <td className="px-5 py-4">{formatNumber(doctor.upcoming_appointments)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <p className="border-t border-line px-5 py-3 text-xs text-ink-600">
                      Showing {data.performance.items.length} of {formatNumber(data.performance.total)} doctors.
                    </p>
                  </div>
                )}
              </div>
            </section>
          )}

          {section === 'reports' && (
            <section className="space-y-5">
              <SectionHeading
                description="Downloads contain date/status/count aggregates only. Spreadsheet formula-like cells are escaped server-side."
                eyebrow="Reports"
                title="Export aggregate reports"
              />
              <div className="grid gap-4 md:grid-cols-2">
                {(
                  [
                    ['patients', 'Patient registrations'],
                    ['doctors', 'Doctor verification'],
                    ['appointments', 'Appointment status'],
                    ['notifications', 'Notification delivery'],
                  ] as const
                ).map(([dataset, title]) => (
                  <article
                    className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-line bg-white p-5"
                    key={dataset}
                  >
                    <div>
                      <h3 className="font-bold text-ink-950">{title}</h3>
                      <p className="mt-1 text-xs text-ink-600">
                        {data.overview.date_from} to {data.overview.date_to} · {granularity}
                      </p>
                    </div>
                    <button
                      className="inline-flex min-h-10 items-center gap-2 rounded-xl bg-brand-700 px-4 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-60"
                      disabled={exporting !== null}
                      onClick={() => void exportCsv(dataset)}
                      type="button"
                    >
                      <ArrowDownToLine aria-hidden="true" size={16} />
                      {exporting === dataset ? 'Preparing…' : 'Download CSV'}
                    </button>
                  </article>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  )
}
