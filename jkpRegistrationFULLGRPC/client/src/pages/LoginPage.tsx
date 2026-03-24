import { useState } from 'react'
import { useAuth } from '../auth'
import { LogIn, AlertCircle } from 'lucide-react'
import { clsx } from 'clsx'

export default function LoginPage() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)

    setTimeout(() => {
      const ok = login(username, password)
      if (!ok) setError('Invalid username or password')
      setLoading(false)
    }, 400)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 via-white to-brand-50 px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-600 to-brand-700 text-lg font-bold tracking-tight text-white shadow-lg shadow-brand-600/25">
            JKP
          </div>
          <h1 className="mt-4 text-xl font-bold text-gray-900">JKP Registration</h1>
          <p className="mt-1 text-sm text-gray-400">Sign in to continue</p>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
          {error && (
            <div className="mb-4 flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-600">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-[13px] font-semibold text-gray-600">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                autoFocus
                required
                className={clsx(
                  'block w-full rounded-xl border border-gray-200 bg-white px-3.5 py-2.5 text-sm',
                  'placeholder:text-gray-400 transition-all',
                  'focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500',
                )}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-[13px] font-semibold text-gray-600">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                required
                className={clsx(
                  'block w-full rounded-xl border border-gray-200 bg-white px-3.5 py-2.5 text-sm',
                  'placeholder:text-gray-400 transition-all',
                  'focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500',
                )}
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className={clsx(
                'flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white',
                'bg-brand-600 hover:bg-brand-700 active:bg-brand-800',
                'shadow-sm shadow-brand-600/20 hover:shadow-md',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'transition-all duration-200',
              )}
            >
              <LogIn className="h-4 w-4" />
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </div>

        <p className="mt-4 text-center text-[11px] text-gray-300">
          POC &middot; admin / admin123
        </p>
      </div>
    </div>
  )
}
