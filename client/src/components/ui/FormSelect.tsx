import { useId } from 'react'
import { clsx } from 'clsx'
import { ChevronDown } from 'lucide-react'

interface FormSelectProps {
  label: string
  name: string
  options: string[]
  defaultValue?: string
  required?: boolean
  placeholder?: string
}

export default function FormSelect({
  label, name, options, defaultValue, required, placeholder = 'Select…',
}: FormSelectProps) {
  const id = useId()
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 flex items-baseline gap-1 text-[13px] font-semibold text-gray-600 tracking-wide">
        {label}
        {required && <span className="text-red-400 text-xs">*</span>}
      </label>
      <div className="relative">
        <select
          id={id}
          name={name}
          defaultValue={defaultValue ?? ''}
          className={clsx(
            'block w-full appearance-none rounded-xl border border-gray-200 bg-white',
            'px-3.5 py-2.5 pr-10 text-sm text-gray-900',
            'transition-all duration-200',
            'hover:border-gray-300',
            'focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500',
          )}
        >
          <option value="" disabled className="text-gray-400">{placeholder}</option>
          {options.map((o) => (
            <option key={o} value={o}>{o}</option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
      </div>
    </div>
  )
}
