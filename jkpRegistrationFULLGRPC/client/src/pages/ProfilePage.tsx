import { useLocation, useNavigate, useParams } from 'react-router'
import { useState, useEffect } from 'react'
import { searchSatsangis, type Satsangi } from '../api'
import {
  ArrowLeft, Phone, Mail, MapPin, Calendar, CreditCard, Shield,
  Globe, User, Home, Ban, Sparkles, BadgeCheck, FileText,
  ClipboardList, Camera, Clock, StickyNote, Upload,
} from 'lucide-react'

export default function ProfilePage() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const [satsangi, setSatsangi] = useState<Satsangi | null>(
    (location.state as { satsangi?: Satsangi })?.satsangi ?? null
  )
  const [loading, setLoading] = useState(!satsangi)

  useEffect(() => {
    if (satsangi) return
    if (!id) return
    setLoading(true)
    searchSatsangis(id).then((results) => {
      const found = results.find((s) => s.satsangiId === id)
      if (found) setSatsangi(found)
    }).finally(() => setLoading(false))
  }, [id, satsangi])

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-5 w-28 rounded bg-gray-100" />
        <div className="h-20 rounded-xl bg-gray-100" />
        <div className="grid grid-cols-5 gap-3">
          <div className="col-span-3 h-64 rounded-xl bg-gray-50" />
          <div className="col-span-2 h-64 rounded-xl bg-gray-50" />
        </div>
      </div>
    )
  }

  if (!satsangi) {
    return (
      <div className="py-20 text-center">
        <p className="text-sm text-gray-500">Devotee not found</p>
        <button onClick={() => navigate('/search')} className="mt-3 text-sm text-brand-600 font-semibold hover:underline">
          Back to Search
        </button>
      </div>
    )
  }

  const s = satsangi
  const initials = `${s.firstName[0] ?? ''}${s.lastName[0] ?? ''}`.toUpperCase()
  const fullName = `${s.firstName} ${s.lastName}`

  return (
    <div className="space-y-4">
      {/* Back */}
      <button
        onClick={() => navigate('/search')}
        className="flex items-center gap-1.5 text-[13px] font-medium text-gray-400 hover:text-gray-600 transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back
      </button>

      {/* Compact hero — avatar + name + badges inline */}
      <div className="flex items-center gap-4 rounded-xl border border-gray-100 bg-white px-5 py-4">
        <div className="photo-upload relative h-14 w-14 shrink-0 rounded-full bg-linear-to-br from-brand-500 to-brand-700 flex items-center justify-center cursor-pointer">
          <span className="text-lg font-bold text-white">{initials}</span>
          <div className="photo-overlay absolute inset-0 rounded-full bg-black/40 flex items-center justify-center opacity-0 transition-opacity">
            <Camera className="h-4 w-4 text-white" />
          </div>
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-bold text-gray-900 truncate">{fullName}</h1>
            <span className="shrink-0 font-mono text-[11px] font-semibold text-brand-600 bg-brand-50 px-2 py-0.5 rounded-md border border-brand-100">
              {s.satsangiId}
            </span>
          </div>
          <div className="mt-0.5 flex flex-wrap items-center gap-3 text-[12px] text-gray-400">
            {s.nickName && <span>"{s.nickName}"</span>}
            {s.gender && <span>{s.gender}{s.age ? `, ${s.age} yrs` : ''}</span>}
            <span className="flex items-center gap-1"><Phone className="h-3 w-3" />{s.phoneNumber}</span>
            {s.email && <span className="flex items-center gap-1"><Mail className="h-3 w-3" />{s.email}</span>}
            {(s.city || s.state) && (
              <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{[s.city, s.state].filter(Boolean).join(', ')}</span>
            )}
          </div>
        </div>
        {/* Badges */}
        <div className="hidden sm:flex items-center gap-1.5 shrink-0">
          {s.firstTimer && (
            <span className="flex items-center gap-1 rounded-lg bg-blue-50 border border-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-600">
              <Sparkles className="h-3 w-3" /> New
            </span>
          )}
          {s.hasRoomInAshram && (
            <span className="flex items-center gap-1 rounded-lg bg-emerald-50 border border-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-600">
              <Home className="h-3 w-3" /> Room
            </span>
          )}
          {s.banned && (
            <span className="flex items-center gap-1 rounded-lg bg-red-50 border border-red-100 px-2 py-0.5 text-[10px] font-semibold text-red-600">
              <Ban className="h-3 w-3" /> Banned
            </span>
          )}
          {s.specialCategory && s.specialCategory !== 'None' && (
            <span className="flex items-center gap-1 rounded-lg bg-amber-50 border border-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-600">
              <BadgeCheck className="h-3 w-3" /> {s.specialCategory}
            </span>
          )}
        </div>
      </div>

      {/* Two-column layout: Details left, Visits + Documents right */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
        {/* LEFT — All details (3/5 width) */}
        <div className="lg:col-span-3 space-y-3">
          {/* Personal + Govt ID side by side */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <InfoCard title="Personal" icon={<User className="h-3.5 w-3.5" />}>
              <InfoRow label="First Name" value={s.firstName} />
              <InfoRow label="Last Name" value={s.lastName} />
              <InfoRow label="DOB" value={s.dateOfBirth} icon={<Calendar className="h-3 w-3" />} />
              <InfoRow label="PAN" value={s.pan} icon={<CreditCard className="h-3 w-3" />} />
              <InfoRow label="Nationality" value={s.nationality} icon={<Globe className="h-3 w-3" />} />
              <InfoRow label="Nick Name" value={s.nickName} />
              <InfoRow label="Introducer" value={s.introducer} />
              <InfoRow label="Introduced By" value={s.introducedBy} />
            </InfoCard>

            <InfoCard title="Government ID" icon={<Shield className="h-3.5 w-3.5" />}>
              <InfoRow label="ID Type" value={s.govtIdType} />
              <InfoRow label="ID Number" value={s.govtIdNumber} />
              <InfoRow label="Expiry" value={s.idExpiryDate} icon={<Calendar className="h-3 w-3" />} />
              <InfoRow label="Issuing Country" value={s.idIssuingCountry} icon={<Globe className="h-3 w-3" />} />
            </InfoCard>
          </div>

          {/* Address + Other side by side */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <InfoCard title="Address" icon={<MapPin className="h-3.5 w-3.5" />}>
              <InfoRow label="Country" value={s.country} />
              <InfoRow label="State" value={s.state} />
              <InfoRow label="City" value={s.city} />
              <InfoRow label="District" value={s.district} />
              <InfoRow label="Pincode" value={s.pincode} />
              <InfoRow label="Address" value={s.address} />
            </InfoCard>

            <InfoCard title="Other" icon={<StickyNote className="h-3.5 w-3.5" />}>
              <InfoRow label="Emergency" value={s.emergencyContact} icon={<Phone className="h-3 w-3" />} />
              <InfoRow label="Email" value={s.email} icon={<Mail className="h-3 w-3" />} />
              <InfoRow label="Ex-center ID" value={s.exCenterSatsangiId} />
              <InfoRow label="First Visit" value={s.dateOfFirstVisit} icon={<Calendar className="h-3 w-3" />} />
              <InfoRow label="Registered" value={s.createdAt ? new Date(s.createdAt).toLocaleDateString() : undefined} icon={<Clock className="h-3 w-3" />} />
            </InfoCard>
          </div>

          {/* Notes — full width if exists */}
          {s.notes && (
            <div className="rounded-xl border border-gray-100 bg-white px-4 py-3">
              <p className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">Notes</p>
              <p className="text-[13px] text-gray-600 leading-relaxed">{s.notes}</p>
            </div>
          )}
        </div>

        {/* RIGHT — Visits + Documents (2/5 width) */}
        <div className="lg:col-span-2 space-y-3">
          {/* Visits */}
          <div className="rounded-xl border border-gray-100 bg-white p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-md bg-brand-50 text-brand-600">
                  <ClipboardList className="h-3.5 w-3.5" />
                </div>
                <h3 className="text-[13px] font-bold text-gray-700">Visits</h3>
              </div>
              <span className="text-[11px] font-semibold text-gray-300">Coming soon</span>
            </div>
            <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50/50 py-8 text-center">
              <ClipboardList className="h-5 w-5 text-gray-300 mx-auto" />
              <p className="mt-2 text-[12px] text-gray-400">Visit history will appear here</p>
            </div>
          </div>

          {/* Documents */}
          <div className="rounded-xl border border-gray-100 bg-white p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-md bg-brand-50 text-brand-600">
                  <FileText className="h-3.5 w-3.5" />
                </div>
                <h3 className="text-[13px] font-bold text-gray-700">Documents</h3>
              </div>
              <button className="text-[11px] font-semibold text-brand-600 hover:text-brand-700 flex items-center gap-1 transition-colors">
                <Upload className="h-3 w-3" /> Upload
              </button>
            </div>
            <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50/50 py-8 text-center">
              <FileText className="h-5 w-5 text-gray-300 mx-auto" />
              <p className="mt-2 text-[12px] text-gray-400">No documents uploaded yet</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function InfoCard({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white px-4 py-3.5">
      <div className="flex items-center gap-2 mb-3">
        <div className="flex h-6 w-6 items-center justify-center rounded-md bg-brand-50 text-brand-600">
          {icon}
        </div>
        <h3 className="text-[12px] font-bold text-gray-600 uppercase tracking-wider">{title}</h3>
      </div>
      <div className="space-y-2">{children}</div>
    </div>
  )
}

function InfoRow({ label, value, icon }: { label: string; value?: string | null; icon?: React.ReactNode }) {
  if (!value) return null
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="text-[11px] text-gray-400 shrink-0 flex items-center gap-1">
        {icon}
        {label}
      </span>
      <span className="text-[12px] font-medium text-gray-700 text-right">{value}</span>
    </div>
  )
}
