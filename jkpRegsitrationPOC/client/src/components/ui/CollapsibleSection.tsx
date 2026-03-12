import { useState } from 'react'
import { clsx } from 'clsx'
import { ChevronDown, Check } from 'lucide-react'

interface CollapsibleSectionProps {
  title: string
  icon: React.ReactNode
  complete?: boolean
  defaultOpen?: boolean
  children: React.ReactNode
}

export default function CollapsibleSection({
  title, icon, complete, defaultOpen = false, children,
}: CollapsibleSectionProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <section className={clsx(
      'rounded-2xl border bg-white transition-all duration-300',
      open ? 'border-gray-200 shadow-sm' : 'border-gray-100',
      complete && !open && 'border-green-200 bg-green-50/30',
    )}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-3 px-5 py-4 text-left"
      >
        <div className={clsx(
          'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl transition-colors duration-200',
          complete ? 'bg-green-100 text-green-600' : open ? 'bg-brand-100 text-brand-600' : 'bg-gray-100 text-gray-400',
        )}>
          {complete ? <Check className="h-4.5 w-4.5" /> : icon}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className={clsx(
            'text-sm font-semibold transition-colors',
            complete ? 'text-green-700' : open ? 'text-gray-900' : 'text-gray-600',
          )}>
            {title}
          </h3>
          {complete && !open && (
            <p className="text-xs text-green-500 mt-0.5">Section completed</p>
          )}
        </div>
        <ChevronDown className={clsx(
          'h-4 w-4 text-gray-400 transition-transform duration-300',
          open && 'rotate-180',
        )} />
      </button>

      <div className="collapse-content" data-open={open}>
        <div>
          <div className="border-t border-gray-100 px-5 pb-5 pt-4 space-y-5">
            {children}
          </div>
        </div>
      </div>
    </section>
  )
}
