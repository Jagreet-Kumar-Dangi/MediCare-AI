import type { InputHTMLAttributes } from 'react'
import { Eye, EyeOff } from 'lucide-react'

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  id: string
  label?: string
  hint?: string
}

export function FormField({
  id,
  label,
  hint,
  className = '',
  ...inputProps
}: FormFieldProps) {
  const hintId = hint ? `${id}-hint` : undefined

  return (
    <div className="space-y-2">
      {label && (
        <label className="block text-sm font-semibold text-ink-800" htmlFor={id}>
          {label}
        </label>
      )}
      <input
        {...inputProps}
        aria-describedby={hintId}
        className={`min-h-12 w-full rounded-xl border border-line bg-white px-4 py-3 text-[15px] text-ink-950 outline-none transition placeholder:text-ink-600/55 hover:border-ink-600/40 focus:border-brand-600 focus:ring-4 focus:ring-brand-100 disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
        id={id}
      />
      {hint && (
        <p className="text-xs leading-5 text-ink-600" id={hintId}>
          {hint}
        </p>
      )}
    </div>
  )
}

interface PasswordFieldProps {
  id: string
  label: string
  value: string
  onChange: InputHTMLAttributes<HTMLInputElement>['onChange']
  autoComplete: string
  placeholder: string
  visible: boolean
  onToggleVisibility: () => void
  minLength?: number
  maxLength?: number
  hint?: string
}

export function PasswordField({
  id,
  label,
  value,
  onChange,
  autoComplete,
  placeholder,
  visible,
  onToggleVisibility,
  minLength,
  maxLength = 128,
  hint,
}: PasswordFieldProps) {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-semibold text-ink-800" htmlFor={id}>
        {label}
      </label>
      <div className="relative">
        <input
          autoComplete={autoComplete}
          className="min-h-12 w-full rounded-xl border border-line bg-white px-4 py-3 pr-12 text-[15px] text-ink-950 outline-none transition placeholder:text-ink-600/55 hover:border-ink-600/40 focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
          id={id}
          maxLength={maxLength}
          minLength={minLength}
          onChange={onChange}
          placeholder={placeholder}
          required
          type={visible ? 'text' : 'password'}
          value={value}
        />
        <button
          aria-label={visible ? 'Hide password' : 'Show password'}
          className="absolute right-2 top-1/2 grid size-9 -translate-y-1/2 place-items-center rounded-lg text-ink-600 transition hover:bg-sky-50 hover:text-ink-950"
          onClick={onToggleVisibility}
          type="button"
        >
          {visible ? <EyeOff aria-hidden="true" size={17} /> : <Eye aria-hidden="true" size={17} />}
        </button>
      </div>
      {hint && <p className="text-xs leading-5 text-ink-600">{hint}</p>}
    </div>
  )
}
