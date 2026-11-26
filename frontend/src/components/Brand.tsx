import { HeartPulse } from 'lucide-react'
import { Link } from 'react-router-dom'

interface BrandProps {
  to?: string
  light?: boolean
}

export function Brand({ to = '/', light = false }: BrandProps) {
  return (
    <Link
      aria-label="MediCare AI home"
      className="inline-flex items-center gap-2.5"
      to={to}
    >
      <span className="grid size-10 place-items-center rounded-[14px] bg-brand-700 text-white shadow-sm">
        <HeartPulse aria-hidden="true" size={21} strokeWidth={2.2} />
      </span>
      <span
        className={`text-[18px] font-bold tracking-[-0.04em] ${
          light ? 'text-white' : 'text-ink-950'
        }`}
      >
        MediCare<span className="text-brand-600"> AI</span>
      </span>
    </Link>
  )
}
