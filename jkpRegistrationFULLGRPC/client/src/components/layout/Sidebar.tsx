import { NavLink, useLocation } from 'react-router'
import { clsx } from 'clsx'
import {
  Search, UserPlus, X, Menu, Server, Database,
} from 'lucide-react'
import { useState, useEffect, useCallback } from 'react'
import { healthCheck } from '../../api'

const NAV_ITEMS = [
  { to: '/search', label: 'Search', icon: Search },
  { to: '/create', label: 'Add Devotee', icon: UserPlus },
]

export default function Sidebar() {
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const [health, setHealth] = useState<{ status: string; dbStatus: string; timestamp: string } | null>(null)
  const [healthy, setHealthy] = useState(false)

  const checkHealth = useCallback(async () => {
    try {
      const resp = await healthCheck()
      setHealth({ status: resp.status, dbStatus: resp.dbStatus, timestamp: resp.timestamp })
      setHealthy(true)
    } catch {
      setHealth(null)
      setHealthy(false)
    }
  }, [])

  useEffect(() => {
    checkHealth()
    const id = setInterval(checkHealth, 10_000)
    return () => clearInterval(id)
  }, [checkHealth])

  useEffect(() => {
    setOpen(false)
  }, [location.pathname])

  return (
    <>
      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3 lg:hidden">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-[10px] font-bold tracking-tight text-white">
            JKP
          </div>
          <span className="text-sm font-bold text-gray-900">Registration System</span>
        </div>
        <button
          onClick={() => setOpen(!open)}
          className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 transition"
          aria-label="Toggle menu"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </header>

      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar panel */}
      <aside className={clsx(
        'fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-gray-200 bg-white transition-transform duration-300 lg:static lg:translate-x-0',
        open ? 'translate-x-0' : '-translate-x-full',
      )}>
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-5 py-5 border-b border-gray-100">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-[11px] font-bold tracking-tight text-white shadow-sm">
            JKP
          </div>
          <div>
            <div className="text-sm font-bold text-gray-900 leading-tight">JKP Registration</div>
            <div className="text-[11px] text-gray-400">Full gRPC + PostgreSQL</div>
          </div>
        </div>

        {/* Status — live from Health RPC */}
        <div className="px-5 py-3 border-b border-gray-100">
          <div className="flex items-center gap-4 text-[11px]">
            <span className="flex items-center gap-1.5 text-gray-400">
              <Server className="h-3 w-3" />
              gRPC
              <span className={clsx('h-1.5 w-1.5 rounded-full', healthy ? 'bg-green-400 animate-pulse' : 'bg-red-400')} />
            </span>
            <span className="flex items-center gap-1.5 text-gray-400">
              <Database className="h-3 w-3" />
              PostgreSQL
              <span className={clsx('h-1.5 w-1.5 rounded-full', healthy && health?.dbStatus === 'connected' ? 'bg-green-400 animate-pulse' : 'bg-red-400')} />
            </span>
          </div>
          {health && (
            <p className="mt-1.5 text-[10px] text-gray-300 truncate" title={health.timestamp}>
              {health.status} · {new Date(health.timestamp).toLocaleTimeString()}
            </p>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 sidebar-scroll overflow-y-auto px-3 py-4 space-y-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => clsx(
                'flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition-all duration-200',
                isActive
                  ? 'bg-brand-50 text-brand-700 shadow-sm'
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900',
              )}
            >
              <Icon className="h-[18px] w-[18px]" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="border-t border-gray-100 px-5 py-4">
          <p className="text-[10px] text-gray-300 text-center">JKP Full gRPC + PostgreSQL v1.0</p>
        </div>
      </aside>
    </>
  )
}
