import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router'
import { searchSatsangis, listSatsangis, type Satsangi } from '../api'
import { clsx } from 'clsx'
import {
  Search, UserPlus, AlertCircle, Users, Phone, MapPin,
  ChevronRight, BadgeCheck, Home, Ban, Sparkles, Loader2,
} from 'lucide-react'

const PAGE_SIZE = 20

export default function SearchPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Satsangi[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState('')

  const isSearching = query.trim().length > 0
  const hasMore = !isSearching && results.length < totalCount

  useEffect(() => {
    const timer = setTimeout(async () => {
      setLoading(true)
      setError('')
      try {
        const data = isSearching
          ? await searchSatsangis(query)
          : await listSatsangis(PAGE_SIZE, 0)
        setResults(data.satsangis)
        setTotalCount(data.totalCount)
      } catch {
        setResults([])
        setTotalCount(0)
        setError('Failed to fetch results. Is the server running?')
      } finally {
        setLoading(false)
      }
    }, 250)
    return () => clearTimeout(timer)
  }, [query, isSearching])

  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return
    setLoadingMore(true)
    try {
      const data = await listSatsangis(PAGE_SIZE, results.length)
      setResults((prev) => [...prev, ...data.satsangis])
      setTotalCount(data.totalCount)
    } catch {
      setError('Failed to load more results.')
    } finally {
      setLoadingMore(false)
    }
  }, [loadingMore, hasMore, results.length])

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">Devotees</h1>
          <p className="mt-0.5 text-[13px] text-gray-400">
            {!loading && !error
              ? `${totalCount} registered${isSearching ? ` \u00b7 ${results.length} matched` : ''}`
              : 'Loading\u2026'}
          </p>
        </div>
        <button
          onClick={() => navigate('/create')}
          className={clsx(
            'flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white',
            'bg-brand-600 hover:bg-brand-700 shadow-sm shadow-brand-600/20 hover:shadow-md',
            'transition-all duration-200',
          )}
        >
          <UserPlus className="h-4 w-4" />
          <span className="hidden sm:inline">Add Devotee</span>
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          type="search"
          placeholder="Search by name, phone, email, ID, city\u2026"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
          className={clsx(
            'block w-full rounded-xl border border-gray-200 bg-white py-2.5 pl-10 pr-4 text-sm',
            'placeholder:text-gray-400',
            'focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500',
            'transition-all duration-200',
          )}
        />
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
          {error}
        </div>
      )}

      {/* Shimmer */}
      {loading && (
        <div className="space-y-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="animate-pulse rounded-xl border border-gray-100 bg-white p-4">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-gray-100" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-1/3 rounded bg-gray-100" />
                  <div className="h-3 w-1/2 rounded bg-gray-50" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty */}
      {!loading && results.length === 0 && !error && (
        <div className="py-16 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gray-50 border border-gray-100">
            <Users className="h-6 w-6 text-gray-400" />
          </div>
          <p className="mt-4 text-sm font-medium text-gray-600">No devotees found</p>
          <p className="text-[13px] text-gray-400 mt-1">Try a different search term</p>
          <button
            onClick={() => navigate('/create')}
            className="mt-5 inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 transition"
          >
            <UserPlus className="h-4 w-4" />
            Register New Devotee
          </button>
        </div>
      )}

      {/* Results */}
      {!loading && results.length > 0 && (
        <div className="space-y-1.5">
          {results.map((s, i) => (
            <SatsangiRow
              key={s.satsangiId}
              s={s}
              style={{ animationDelay: `${i * 30}ms` }}
              onClick={() => navigate(`/profile/${s.satsangiId}`, { state: { satsangi: s } })}
            />
          ))}

          {/* Load More */}
          {hasMore && (
            <div className="pt-2 text-center">
              <button
                onClick={loadMore}
                disabled={loadingMore}
                className={clsx(
                  'inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-5 py-2.5',
                  'text-sm font-semibold text-gray-600 hover:border-gray-300 hover:bg-gray-50',
                  'disabled:opacity-50 disabled:cursor-not-allowed',
                  'transition-all duration-200',
                )}
              >
                {loadingMore ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> Loading&hellip;</>
                ) : (
                  <>Load More ({results.length} of {totalCount})</>
                )}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function SatsangiRow({ s, onClick, style }: { s: Satsangi; onClick: () => void; style?: React.CSSProperties }) {
  const initials = `${s.firstName[0] ?? ''}${s.lastName[0] ?? ''}`.toUpperCase()
  const fullName = `${s.firstName} ${s.lastName}`

  return (
    <button
      type="button"
      onClick={onClick}
      style={style}
      className={clsx(
        'animate-card-in w-full text-left flex items-center gap-3.5 rounded-xl border bg-white px-4 py-3 transition-all duration-200',
        'hover:shadow-md hover:border-gray-200 cursor-pointer',
        s.banned ? 'border-red-200 bg-red-50/40' : 'border-gray-100',
      )}
    >
      {/* Avatar */}
      <div className={clsx(
        'flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold',
        s.banned ? 'bg-red-100 text-red-600' : 'bg-brand-50 text-brand-600',
      )}>
        {initials}
      </div>

      {/* Info */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-[14px] font-semibold text-gray-900">{fullName}</span>
          <span className="shrink-0 rounded-md bg-gray-100 px-1.5 py-0.5 text-[10px] font-mono font-semibold text-gray-500">
            {s.satsangiId}
          </span>
        </div>
        <div className="mt-0.5 flex items-center gap-3 text-[12px] text-gray-400">
          <span className="flex items-center gap-1">
            <Phone className="h-3 w-3" />
            {s.phoneNumber}
          </span>
          {(s.city || s.state) && (
            <span className="flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {[s.city, s.state].filter(Boolean).join(', ')}
            </span>
          )}
          {s.gender && <span>{s.gender}{s.age ? `, ${s.age}` : ''}</span>}
        </div>
      </div>

      {/* Tags */}
      <div className="hidden sm:flex items-center gap-1.5 shrink-0">
        {s.firstTimer && (
          <span className="flex items-center gap-1 rounded-md bg-blue-50 border border-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-600">
            <Sparkles className="h-3 w-3" /> New
          </span>
        )}
        {s.hasRoomInAshram && (
          <span className="flex items-center gap-1 rounded-md bg-emerald-50 border border-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-600">
            <Home className="h-3 w-3" /> Room
          </span>
        )}
        {s.banned && (
          <span className="flex items-center gap-1 rounded-md bg-red-50 border border-red-100 px-2 py-0.5 text-[10px] font-semibold text-red-600">
            <Ban className="h-3 w-3" /> Banned
          </span>
        )}
        {s.specialCategory && s.specialCategory !== 'None' && (
          <span className="flex items-center gap-1 rounded-md bg-amber-50 border border-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-600">
            <BadgeCheck className="h-3 w-3" /> {s.specialCategory}
          </span>
        )}
      </div>

      <ChevronRight className="h-4 w-4 shrink-0 text-gray-300" />
    </button>
  )
}
