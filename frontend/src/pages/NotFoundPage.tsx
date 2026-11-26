import { ArrowLeft, HeartPulse } from 'lucide-react'
import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-sky-50 px-5 py-10">
      <div className="max-w-lg text-center">
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-brand-100 text-brand-700">
          <HeartPulse aria-hidden="true" size={25} />
        </span>
        <p className="mt-7 text-xs font-bold uppercase tracking-[0.18em] text-brand-700">
          Page not found
        </p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.05em] text-ink-950">
          This page isn’t here.
        </h1>
        <p className="mt-4 text-sm leading-6 text-ink-600">
          The link may be out of date, or the page may have moved. Let’s get you
          back to a familiar place.
        </p>
        <Link
          className="mt-7 inline-flex min-h-12 items-center gap-2 rounded-xl bg-brand-700 px-5 text-sm font-bold text-white transition hover:bg-brand-600"
          to="/"
        >
          <ArrowLeft aria-hidden="true" size={16} />
          Return home
        </Link>
      </div>
    </main>
  )
}
