import { clsx } from 'clsx'

interface FormRadioGroupProps {
  label: string
  name: string
  options: string[]
}

export default function FormRadioGroup({ label, name, options }: FormRadioGroupProps) {
  return (
    <fieldset>
      <legend className="mb-2 text-[13px] font-semibold text-gray-600 tracking-wide">{label}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => (
          <label
            key={opt}
            className={clsx(
              'group relative flex cursor-pointer items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2.5',
              'transition-all duration-200 hover:border-gray-300 hover:shadow-sm',
              'has-checked:border-brand-500 has-checked:bg-brand-50/50 has-checked:shadow-sm',
            )}
          >
            <input type="radio" name={name} value={opt} className="peer sr-only" />
            <div className={clsx(
              'flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2 border-gray-300 transition-all duration-200',
              'peer-checked:border-brand-600',
            )}>
              <div className="h-2 w-2 rounded-full bg-brand-600 scale-0 peer-checked:group-[]:scale-100 transition-transform duration-200" />
            </div>
            <span className="text-sm font-medium text-gray-600 peer-checked:group-[]:text-brand-700 transition-colors">{opt}</span>
          </label>
        ))}
      </div>
    </fieldset>
  )
}
