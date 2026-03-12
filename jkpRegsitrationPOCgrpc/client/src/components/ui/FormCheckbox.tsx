import { clsx } from 'clsx'

interface FormCheckboxProps {
  label: string
  name: string
  danger?: boolean
}

export default function FormCheckbox({ label, name, danger }: FormCheckboxProps) {
  return (
    <label className="group relative flex cursor-pointer items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 transition-all duration-200 hover:border-gray-300 hover:shadow-sm has-checked:border-brand-500 has-checked:bg-brand-50/50 has-checked:shadow-sm">
      <input
        type="checkbox"
        name={name}
        className="peer sr-only"
      />
      <div className={clsx(
        'flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2 transition-all duration-200',
        danger
          ? 'border-gray-300 peer-checked:group-[]:border-red-500 peer-checked:group-[]:bg-red-500'
          : 'border-gray-300 peer-checked:group-[]:border-brand-600 peer-checked:group-[]:bg-brand-600',
      )}>
        <svg className="h-3 w-3 text-white opacity-0 peer-checked:group-[]:opacity-100 transition-opacity" viewBox="0 0 12 10" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="1.5 5 4.5 8 10.5 2" />
        </svg>
      </div>
      <span className={clsx(
        'text-sm font-medium transition-colors',
        danger ? 'text-gray-600 peer-checked:group-[]:text-red-700' : 'text-gray-600 peer-checked:group-[]:text-brand-700',
      )}>
        {label}
      </span>
    </label>
  )
}
