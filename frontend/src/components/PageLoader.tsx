import { HeartPulse } from 'lucide-react'

interface PageLoaderProps {
  label?: string
}

export function PageLoader({
  label = 'Preparing your care portal…',
}: PageLoaderProps) {
  return (
    <main
      aria-busy="true"
      aria-live="polite"
      className="grid min-h-screen place-items-center bg-sky-50 px-5"
    >
      <div className="flex items-center gap-3 text-sm font-medium text-ink-600">
        <span className="grid size-10 animate-pulse place-items-center rounded-2xl bg-brand-100 text-brand-700">
          <HeartPulse aria-hidden="true" size={20} />
        </span>
        {label}
      </div>
    </main>
  )
}
