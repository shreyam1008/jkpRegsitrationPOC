import { useId } from 'react'
import { clsx } from 'clsx'

interface FormInputProps {
  label: string
  name: string
  type?: string
  required?: boolean
  placeholder?: string
  multiline?: boolean
  icon?: React.ReactNode
}

export default function FormInput({
  label, name, type = 'text', required, placeholder, multiline, icon,
}: FormInputProps) {
  const id = useId()
  const base = clsx(
    'block w-full rounded-xl border border-gray-200 bg-white px-3.5 py-2.5 text-sm text-gray-900',
    'placeholder:text-gray-400 transition-all duration-200',
    'hover:border-gray-300',
    'focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500',
    'disabled:bg-gray-50 disabled:text-gray-400',
    icon && 'pl-10',
  )

  return (
    <div className="group">
      <label htmlFor={id} className="mb-1.5 flex items-baseline gap-1 text-[13px] font-semibold text-gray-600 tracking-wide">
        {label}
        {required && <span className="text-red-400 text-xs">*</span>}
      </label>
      <div className="relative">
        {icon && (
          <div className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-brand-500 transition-colors">
            {icon}
          </div>
        )}
        {multiline ? (
          <textarea
            id={id}
            name={name}
            placeholder={placeholder}
            rows={3}
            className={base}
          />
        ) : (
          <input
            id={id}
            name={name}
            type={type}
            placeholder={placeholder}
            className={base}
          />
        )}
      </div>
    </div>
  )
}
