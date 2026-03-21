import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "@tanstack/react-router";
import {
  ArrowLeft, User, Phone, Mail, MapPin, Calendar, Globe, CreditCard,
  FileText, Home, Shield, AlertTriangle, Star, Loader2, MapPinHouse,
} from "lucide-react";
import { getDevoteeById, getVisitsForDevotee } from "@/api/satsangisApi";
import type { Visit } from "@/api/satsangisApi";

export function SatsangiDetailPage() {
  const { id } = useParams({ from: "/satsangi/$id" });

  const { data: s, isLoading, error } = useQuery({
    queryKey: ["devotee", id],
    queryFn: () => getDevoteeById(id),
  });

  const { data: visits = [] } = useQuery({
    queryKey: ["visits", id],
    queryFn: () => getVisitsForDevotee(id),
    enabled: !!s,
  });

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Loader2 size={32} className="animate-spin text-muted" />
      </div>
    );
  }

  if (error || !s) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4">
        <AlertTriangle size={48} className="text-danger" />
        <p className="text-lg font-medium">Devotee not found</p>
        <Link to="/" className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary transition-opacity hover:opacity-80">
          Back to Search
        </Link>
      </div>
    );
  }

  const fullName = `${s.first_name} ${s.last_name}`;
  const initials = `${s.first_name[0]}${s.last_name[0]}`.toUpperCase();

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      {/* Back link */}
      <Link to="/" className="mb-6 inline-flex items-center gap-2 text-sm text-muted transition-colors hover:text-foreground">
        <ArrowLeft size={16} />
        Back to Search
      </Link>

      {/* ─── Profile Header ─── */}
      <div className="flex flex-col gap-5 rounded-2xl border border-border bg-surface p-6 sm:flex-row sm:items-center">
        <div className={[
          "flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl text-2xl font-bold",
          s.banned ? "bg-danger/10 text-danger" : "bg-primary/10 text-primary",
        ].join(" ")}>
          {initials}
        </div>
        <div className="flex-1">
          <h1 className="text-2xl font-bold tracking-tight">{fullName}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <IdBadge label="Satsangi ID" value={s.satsangi_id} />
            {s.gender && <span className="text-sm text-muted">· {s.gender}</span>}
            {s.nationality && <span className="text-sm text-muted">· {s.nationality}</span>}
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {s.first_timer && <StatusTag color="blue">First Timer</StatusTag>}
            {s.has_room_in_ashram && <StatusTag color="green">Has Room</StatusTag>}
            {s.banned && <StatusTag color="red">Banned</StatusTag>}
            {s.special_category && s.special_category !== "None" && (
              <StatusTag color="blue">{s.special_category}</StatusTag>
            )}
          </div>
        </div>
      </div>

      {/* ─── Two-column grid ─── */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Left column: Personal + Government ID */}
        <div className="space-y-6">
          <DetailCard title="Personal Details" icon={User}>
            <DetailRow icon={User} label="Full Name" value={fullName} />
            <DetailRow icon={User} label="Gender" value={s.gender} />
            <DetailRow icon={Calendar} label="Date of Birth" value={formatDob(s.date_of_birth, s.age)} />
            <DetailRow icon={Globe} label="Nationality" value={s.nationality} />
            <DetailRow icon={Phone} label="Phone" value={s.phone_number} />
            <DetailRow icon={Mail} label="Email" value={s.email} />
            {s.nick_name && <DetailRow icon={Star} label="Nick Name" value={s.nick_name} />}
            {s.pan && <DetailRow icon={CreditCard} label="PAN" value={s.pan} />}
            {s.notes && <DetailRow icon={FileText} label="Notes" value={s.notes} />}
          </DetailCard>

          {s.govt_id_type && (
            <DetailCard title="Government ID" icon={CreditCard}>
              <DetailRow icon={CreditCard} label="ID Type" value={s.govt_id_type} />
              <DetailRow icon={CreditCard} label="ID Number" value={s.govt_id_number} />
              {s.id_expiry_date && <DetailRow icon={Calendar} label="Expiry Date" value={s.id_expiry_date} />}
              {s.id_issuing_country && <DetailRow icon={Globe} label="Issuing Country" value={s.id_issuing_country} />}
            </DetailCard>
          )}
        </div>

        {/* Right column: Address + Other + Visits */}
        <div className="space-y-6">
          <DetailCard title="Address" icon={MapPinHouse}>
            {s.address && <DetailRow icon={Home} label="Address" value={s.address} />}
            <DetailRow icon={MapPin} label="City" value={s.city} />
            <DetailRow icon={MapPin} label="District" value={s.district} />
            <DetailRow icon={MapPin} label="State" value={s.state} />
            <DetailRow icon={MapPin} label="Pincode" value={s.pincode} />
            <DetailRow icon={Globe} label="Country" value={s.country} />
          </DetailCard>

          <DetailCard title="Other Details" icon={Shield}>
            {s.emergency_contact && <DetailRow icon={Phone} label="Emergency Contact" value={s.emergency_contact} />}
            {s.introducer && <DetailRow icon={User} label="Introducer" value={s.introducer} />}
            {s.introduced_by && <DetailRow icon={User} label="Introduced By" value={s.introduced_by} />}
            {s.ex_center_satsangi_id && <DetailRow icon={CreditCard} label="Ex-Center ID" value={s.ex_center_satsangi_id} />}
            {s.date_of_first_visit && <DetailRow icon={Calendar} label="First Visit" value={s.date_of_first_visit} />}
            <DetailRow icon={Calendar} label="Registered" value={new Date(s.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })} />
          </DetailCard>

          {/* Visits */}
          <div className="rounded-2xl border border-border bg-surface p-5">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar size={18} className="text-primary" />
                <h2 className="text-base font-semibold">Visits</h2>
              </div>
              <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary">
                {visits.length}
              </span>
            </div>
            {visits.length === 0 ? (
              <p className="text-sm text-faint">No visits recorded yet.</p>
            ) : (
              <div className="space-y-3">
                {visits.map((v) => (
                  <VisitRow key={v.id} v={v} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Sub-components ───

function VisitRow({ v }: { v: Visit }) {
  return (
    <div className="rounded-xl border border-border bg-surface-alt px-4 py-3">
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium">{v.location ?? "Ashram"}</div>
        {v.purpose && <span className="rounded-lg bg-primary/5 px-2 py-0.5 text-[11px] font-medium text-primary">{v.purpose}</span>}
      </div>
      <div className="mt-1 flex items-center gap-3 text-xs text-muted">
        <span>Arrival: {v.arrival_date ?? "—"}</span>
        <span>Departure: {v.departure_date ?? "—"}</span>
      </div>
      {v.notes && <p className="mt-1 text-xs text-faint">{v.notes}</p>}
    </div>
  );
}

function IdBadge({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-lg border border-primary/20 bg-primary/5 px-2.5 py-1 text-xs font-semibold">
      <span className="text-muted">{label}:</span>
      <span className="font-mono text-primary">{value}</span>
    </span>
  );
}

function StatusTag({ children, color }: { children: React.ReactNode; color: "blue" | "green" | "red" }) {
  const palette = {
    blue: "bg-tag-blue-bg text-tag-blue-text border-tag-blue-border",
    green: "bg-tag-green-bg text-tag-green-text border-tag-green-border",
    red: "bg-tag-red-bg text-tag-red-text border-tag-red-border",
  };
  return (
    <span className={`inline-flex items-center rounded-lg border px-2 py-0.5 text-[11px] font-semibold ${palette[color]}`}>
      {children}
    </span>
  );
}

function DetailCard({ title, icon: Icon, children }: { title: string; icon: typeof User; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-5">
      <div className="mb-4 flex items-center gap-2">
        <Icon size={18} className="text-primary" />
        <h2 className="text-base font-semibold">{title}</h2>
      </div>
      <div className="space-y-3">
        {children}
      </div>
    </div>
  );
}

function DetailRow({ icon: Icon, label, value }: { icon: typeof User; label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-3 text-sm">
      <Icon size={14} className="mt-0.5 shrink-0 text-faint" />
      <div>
        <span className="text-faint">{label}</span>
        <p className="font-medium">{value}</p>
      </div>
    </div>
  );
}

function formatDob(dob?: string | null, age?: number | null): string | null {
  if (!dob && !age) return null;
  const parts: string[] = [];
  if (dob) parts.push(new Date(dob).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" }));
  if (age) parts.push(`(${age} yr old)`);
  return parts.join(" ");
}
