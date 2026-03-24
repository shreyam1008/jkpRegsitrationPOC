import { NavLink, useLocation } from 'react-router'
import { clsx } from 'clsx'
import {
  Search, UserPlus, X, Menu, Activity, Database, LogOut, Shield,
} from 'lucide-react'
import { useState, useEffect, useCallback } from 'react'
import { healthCheck } from '../../api'
import { useAuth } from '../../auth'

const NAV_ITEMS = [
  { to: '/search', label: 'Search', icon: Search, desc: 'Find devotees' },
  { to: '/create', label: 'Add Devotee', icon: UserPlus, desc: 'Register new' },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
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
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-gray-100 bg-white/80 backdrop-blur-md px-4 py-3 lg:hidden">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-[10px] font-bold tracking-tight text-white shadow-sm shadow-brand-600/25">
            JKP
          </div>
          <span className="text-sm font-bold text-gray-900">Registration</span>
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
        'fixed inset-y-0 left-0 z-50 flex w-[260px] flex-col bg-white border-r border-gray-100 transition-transform duration-300 lg:static lg:translate-x-0',
        open ? 'translate-x-0' : '-translate-x-full',
      )}>
        {/* Brand header */}
        <div className="flex items-center gap-3 px-5 py-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-600 to-brand-700 text-xs font-bold tracking-tight text-white shadow-md shadow-brand-600/30">
            JKP
          </div>
          <div>
            <div className="text-[15px] font-bold text-gray-900 leading-tight">JKP Ashram</div>
            <div className="text-[11px] text-gray-400 font-medium">Registration System</div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="mx-4 mb-3 rounded-xl bg-gray-50 border border-gray-100 p-3">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <Activity className="h-3 w-3 text-gray-400" />
              <span className="text-[11px] text-gray-500 font-medium">Server</span>
              <span className={clsx('h-2 w-2 rounded-full', healthy ? 'bg-emerald-400' : 'bg-red-400')} />
            </div>
            <div className="w-px h-3 bg-gray-200" />
            <div className="flex items-center gap-1.5">
              <Database className="h-3 w-3 text-gray-400" />
              <span className="text-[11px] text-gray-500 font-medium">DB</span>
              <span className={clsx('h-2 w-2 rounded-full', healthy && health?.dbStatus === 'connected' ? 'bg-emerald-400' : 'bg-red-400')} />
            </div>
          </div>
        </div>

        {/* Section label */}
        <div className="px-5 pt-2 pb-1">
          <p className="text-[10px] font-bold text-gray-300 uppercase tracking-widest">Navigation</p>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-1 space-y-0.5">
          {NAV_ITEMS.map(({ to, label, icon: Icon, desc }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => clsx(
                'flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all duration-200',
                isActive
                  ? 'bg-brand-50 border border-brand-100'
                  : 'hover:bg-gray-50 border border-transparent',
              )}
            >
              {({ isActive }) => (
                <>
                  <div className={clsx(
                    'flex h-8 w-8 items-center justify-center rounded-lg transition-colors',
                    isActive ? 'bg-brand-600 text-white shadow-sm' : 'bg-gray-100 text-gray-500',
                  )}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <div className={clsx(
                      'text-[13px] font-semibold leading-tight',
                      isActive ? 'text-brand-700' : 'text-gray-700',
                    )}>{label}</div>
                    <div className="text-[11px] text-gray-400">{desc}</div>
                  </div>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* User + Logout */}
        <div className="border-t border-gray-100 px-4 py-3.5">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
              <Shield className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[13px] font-semibold text-gray-700 truncate">{user?.username}</div>
              <div className="text-[10px] text-gray-400 uppercase tracking-wider">{user?.role}</div>
            </div>
            <button
              onClick={logout}
              title="Sign out"
              className="rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-500 transition-colors"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}
