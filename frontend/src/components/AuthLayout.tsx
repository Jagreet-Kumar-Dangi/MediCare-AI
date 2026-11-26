import { ArrowUpRight, Check, HeartHandshake } from 'lucide-react'
import type { PropsWithChildren, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Brand } from './Brand'

interface AuthLayoutProps extends PropsWithChildren {
  title: string
  description: string
  footer: ReactNode
}

const reassurance = [
  'Your account stays in your control',
  'A clear place for your personal details',
  'No health readings are invented or assumed',
]

const copyrightYear = new Date().getFullYear()

export function AuthLayout({
  title,
  description,
  footer,
  children,
}: AuthLayoutProps) {
  return (
    <main className="min-h-screen bg-white">
      <div className="mx-auto grid min-h-screen max-w-[1440px] lg:grid-cols-[1.02fr_0.98fr]">
        <section className="relative hidden overflow-hidden bg-[#123b48] px-12 py-10 text-white lg:flex lg:flex-col xl:px-20">
          <div className="absolute -right-36 -top-32 size-[440px] rounded-full border border-white/10" />
          <div className="absolute -right-16 top-6 size-[290px] rounded-full border border-white/10" />
          <div className="absolute -bottom-48 -left-36 size-[500px] rounded-full bg-brand-600/15 blur-3xl" />
          <Brand light />
          <div className="relative my-auto max-w-[520px] py-16">
            <div className="mb-7 grid size-14 place-items-center rounded-2xl bg-white/10 text-[#9de2d8] ring-1 ring-white/15">
              <HeartHandshake aria-hidden="true" size={27} strokeWidth={1.7} />
            </div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#9de2d8]">
              A more considered care experience
            </p>
            <h1 className="mt-4 text-4xl font-semibold leading-[1.15] tracking-[-0.045em] text-white xl:text-[48px]">
              Your care journey,
              <br />
              in a clearer place.
            </h1>
            <p className="mt-5 max-w-[430px] text-base leading-7 text-white/70">
              Sign in to manage your patient profile and keep your account
              details together.
            </p>
            <ul className="mt-9 space-y-4">
              {reassurance.map((item) => (
                <li
                  className="flex items-center gap-3 text-sm text-white/85"
                  key={item}
                >
                  <span className="grid size-6 shrink-0 place-items-center rounded-full bg-white/10 text-[#9de2d8]">
                    <Check aria-hidden="true" size={14} />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <p className="relative flex items-center gap-2 text-xs text-white/50">
            A thoughtful foundation for digital healthcare
            <ArrowUpRight aria-hidden="true" size={13} />
          </p>
        </section>

        <section className="flex min-h-screen flex-col px-5 py-6 sm:px-10 lg:px-14 xl:px-20">
          <div className="flex items-center justify-between lg:justify-end">
            <span className="lg:hidden">
              <Brand />
            </span>
            <Link
              className="inline-flex min-h-10 items-center rounded-full px-3 text-sm font-semibold text-ink-600 transition hover:bg-sky-50 hover:text-brand-700"
              to="/"
            >
              Back to home
            </Link>
          </div>
          <div className="mx-auto flex w-full max-w-[430px] flex-1 flex-col justify-center py-10">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-700">
              Patient portal
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-[-0.045em] text-ink-950 sm:text-[36px]">
              {title}
            </h2>
            <p className="mt-3 text-sm leading-6 text-ink-600">{description}</p>
            <div className="mt-8">{children}</div>
            <div className="mt-7 border-t border-line pt-6 text-center text-sm text-ink-600">
              {footer}
            </div>
          </div>
          <p className="pb-2 text-center text-xs text-ink-600/75">
            © {copyrightYear} MediCare AI
          </p>
        </section>
      </div>
    </main>
  )
}
