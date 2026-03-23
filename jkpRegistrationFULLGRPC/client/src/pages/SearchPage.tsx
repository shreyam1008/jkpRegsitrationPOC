import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { searchSatsangis, listSatsangis, type Satsangi } from '../api'
import { clsx } from 'clsx'
import {
  Search, UserPlus, AlertCircle, Users, Phone, Mail, MapPin, Calendar,
} from 'lucide-react'

export default function SearchPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Satsangi[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const timer = setTimeout(async () => {
      setLoading(true)
      setError('')
      try {
        const data = query.trim()
          ? await searchSatsangis(query)
          : await listSatsangis(50)
        setResults(data)
      } catch {
        setResults([])
        setError('Failed to fetch results. Is the server running?')
      } finally {
        setLoading(false)
      }
    }, 250)
    return () => clearTimeout(timer)
  }, [query])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Search Devotees</h1>
          <p className="mt-1 text-sm text-gray-500">Find registered satsangis by name, phone, ID, or any field</p>
        </div>
        <button
          onClick={() => navigate('/create')}
          className={clsx(
            'hidden sm:flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white',
            'bg-brand-600 hover:bg-brand-700 shadow-sm shadow-brand-600/25 hover:shadow-md',
            'transition-all duration-200',
          )}
        >
          <UserPlus className="h-4 w-4" />
          Add New
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="pointer-events-none absolute left-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-gray-400" />
        <input
          type="search"
          placeholder="Search by name, phone, email, PAN, ID, city, Satsangi ID…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
          className={clsx(
            'block w-full rounded-2xl border border-gray-200 bg-white py-3.5 pl-11 pr-4 text-sm',
            'shadow-sm placeholder:text-gray-400',
            'focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500',
            'transition-all duration-200',
          )}
        />
      </div>

      {/* Result count */}
      {!loading && !error && (
        <p className="text-xs font-medium text-gray-400 tracking-wide">
          {results.length} result{results.length !== 1 ? 's' : ''} found
        </p>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3.5 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
          {error}
        </div>
      )}

      {/* Shimmer loading */}
      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse rounded-2xl border border-gray-100 bg-white p-5">
              <div className="flex items-center gap-4">
                <div className="h-11 w-11 rounded-xl bg-gray-100" />
                <div className="flex-1 space-y-2.5">
                  <div className="h-4 w-2/5 rounded-lg bg-gray-100" />
                  <div className="h-3 w-3/5 rounded-lg bg-gray-50" />
                </div>
                <div className="h-6 w-20 rounded-lg bg-gray-100" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && results.length === 0 && !error && (
        <div className="py-16 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gray-100">
            <Users className="h-7 w-7 text-gray-400" />
          </div>
          <p className="mt-4 text-sm font-medium text-gray-500">No satsangis found.</p>
          <p className="text-xs text-gray-400 mt-1">Try a different search or register a new satsangi.</p>
          <button
            onClick={() => navigate('/create')}
            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 transition"
          >
            <UserPlus className="h-4 w-4" />
            Register New Satsangi
          </button>
        </div>
      )}

      {/* Results */}
      <div className="space-y-3">
        {results.map((s) => (
          <SatsangiCard key={s.satsangiId} s={s} />
        ))}
      </div>
    </div>
  )
}

function SatsangiCard({ s }: { s: Satsangi }) {
  const initials = `${s.firstName[0]}${s.lastName[0]}`.toUpperCase()
  const fullName = `${s.firstName} ${s.lastName}`

  return (
    <div className={clsx(
      'group rounded-2xl border border-gray-200 bg-white p-5 transition-all duration-200',
      'hover:border-gray-300 hover:shadow-md',
      s.banned && 'border-red-200 bg-red-50/30',
    )}>
      <div className="flex items-start gap-4">
        {/* Avatar */}
        <div className={clsx(
          'flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-sm font-bold transition-colors',
          s.banned
            ? 'bg-red-100 text-red-600'
            : 'bg-brand-100 text-brand-600 group-hover:bg-brand-600 group-hover:text-white',
        )}>
          {initials}
        </div>

        <div className="min-w-0 flex-1">
          {/* Name + ID */}
          <div className="flex items-center justify-between gap-3">
            <h3 className="truncate text-[15px] font-semibold text-gray-900">{fullName}</h3>
            <span className="shrink-0 rounded-lg bg-brand-50 px-2.5 py-1 text-xs font-mono font-semibold text-brand-600 border border-brand-100">
              {s.satsangiId}
            </span>
          </div>

          {/* Quick info */}
          <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Phone className="h-3 w-3" />
              {s.phoneNumber}
            </span>
            {s.email && (
              <span className="flex items-center gap-1">
                <Mail className="h-3 w-3" />
                {s.email}
              </span>
            )}
            {(s.city || s.state) && (
              <span className="flex items-center gap-1">
                <MapPin className="h-3 w-3" />
                {[s.city, s.state].filter(Boolean).join(', ')}
              </span>
            )}
            {s.gender && <span>{s.gender}</span>}
            {s.age && <span>Age {s.age}</span>}
            {s.createdAt && (
              <span className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                {new Date(s.createdAt).toLocaleDateString()}
              </span>
            )}
          </div>

          {/* Tags */}
          {(s.govtIdType || s.nickName || s.introducedBy || s.firstTimer || s.banned || s.hasRoomInAshram) && (
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              {s.govtIdType && (
                <Tag>{s.govtIdType}: {s.govtIdNumber}</Tag>
              )}
              {s.nickName && <Tag>Nick: {s.nickName}</Tag>}
              {s.introducedBy && <Tag>Via {s.introducedBy}</Tag>}
              {s.firstTimer && <Tag color="blue">First Timer</Tag>}
              {s.hasRoomInAshram && <Tag color="green">Has Room</Tag>}
              {s.banned && <Tag color="red">Banned</Tag>}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function Tag({ children, color }: { children: React.ReactNode; color?: 'blue' | 'green' | 'red' }) {
  const palette = {
    blue: 'bg-blue-50 text-blue-600 border-blue-100',
    green: 'bg-emerald-50 text-emerald-600 border-emerald-100',
    red: 'bg-red-50 text-red-600 border-red-100',
  }
  return (
    <span className={clsx(
      'inline-flex items-center rounded-lg border px-2 py-0.5 text-[11px] font-semibold',
      color ? palette[color] : 'bg-gray-50 text-gray-500 border-gray-100',
    )}>
      {children}
    </span>
  )
}
