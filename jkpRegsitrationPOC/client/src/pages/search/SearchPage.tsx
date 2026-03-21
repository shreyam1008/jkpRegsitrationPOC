import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Search, AlertCircle, Users, Phone, Mail, MapPin, Calendar } from "lucide-react";
import { useDevoteeSearch } from "@/hooks/useSatsangiSearch";
import type { Devotee } from "@/api/satsangisApi";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const { data: results = [], isLoading, error } = useDevoteeSearch(query);

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      {/* Search bar */}
      <div className="relative">
        <Search className="pointer-events-none absolute left-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-faint" />
        <input
          type="search"
          placeholder="Search by name, phone, email, PAN, ID, city, Satsangi ID…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
          className="block w-full rounded-2xl border border-border bg-surface py-3.5 pl-11 pr-4 text-sm shadow-sm placeholder:text-faint transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
        />
      </div>

      {/* Result count */}
      {!isLoading && !error && (
        <p className="text-xs font-medium text-faint tracking-wide">
          {results.length} result{results.length !== 1 ? "s" : ""} found
        </p>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-danger/30 bg-danger/5 px-4 py-3.5 text-sm text-danger">
          <AlertCircle className="h-4 w-4 shrink-0" />
          Failed to fetch results. Is the server running?
        </div>
      )}

      {/* Shimmer loading */}
      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse rounded-2xl border border-border bg-surface p-5">
              <div className="flex items-center gap-4">
                <div className="h-11 w-11 rounded-xl bg-hover" />
                <div className="flex-1 space-y-2.5">
                  <div className="h-4 w-2/5 rounded-lg bg-hover" />
                  <div className="h-3 w-3/5 rounded-lg bg-hover/50" />
                </div>
                <div className="h-6 w-20 rounded-lg bg-hover" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && results.length === 0 && !error && (
        <div className="py-16 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-hover">
            <Users className="h-7 w-7 text-muted" />
          </div>
          <p className="mt-4 text-sm font-medium text-muted">No satsangis found.</p>
          <p className="mt-1 text-xs text-faint">Try a different search term.</p>
        </div>
      )}

      {/* Results */}
      <div className="space-y-3">
        {results.map((s) => (
          <SatsangiCard key={s.satsangi_id} s={s} />
        ))}
      </div>
    </div>
  );
}

function SatsangiCard({ s }: { s: Devotee }) {
  const initials = `${s.first_name[0]}${s.last_name[0]}`.toUpperCase();
  const fullName = `${s.first_name} ${s.last_name}`;

  return (
    <Link
      to="/satsangi/$id"
      params={{ id: s.satsangi_id }}
      className={[
        "group block rounded-2xl border bg-surface p-5 transition-all duration-200 hover:shadow-md cursor-pointer",
        s.banned ? "border-danger/30 bg-danger/5" : "border-border hover:border-muted",
      ].join(" ")}
    >
      <div className="flex items-start gap-4">
        {/* Avatar */}
        <div
          className={[
            "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-sm font-bold transition-colors",
            s.banned
              ? "bg-danger/10 text-danger"
              : "bg-primary/10 text-primary group-hover:bg-primary group-hover:text-on-primary",
          ].join(" ")}
        >
          {initials}
        </div>

        <div className="min-w-0 flex-1">
          {/* Name + ID */}
          <div className="flex items-center justify-between gap-3">
            <h3 className="truncate text-[15px] font-semibold">{fullName}</h3>
            <span className="shrink-0 rounded-lg bg-primary/5 px-2.5 py-1 text-xs font-mono font-semibold text-primary border border-primary/10">
              {s.satsangi_id}
            </span>
          </div>

          {/* Quick info */}
          <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
            <span className="flex items-center gap-1">
              <Phone className="h-3 w-3" />
              {s.phone_number}
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
                {[s.city, s.state].filter(Boolean).join(", ")}
              </span>
            )}
            {s.gender && <span>{s.gender}</span>}
            {s.age && <span>Age {s.age}</span>}
            {s.created_at && (
              <span className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                {new Date(s.created_at).toLocaleDateString()}
              </span>
            )}
          </div>

          {/* Tags */}
          {(s.govt_id_type || s.nick_name || s.introduced_by || s.first_timer || s.banned || s.has_room_in_ashram) && (
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              {s.govt_id_type && (
                <Tag>{s.govt_id_type}: {s.govt_id_number}</Tag>
              )}
              {s.nick_name && <Tag>Nick: {s.nick_name}</Tag>}
              {s.introduced_by && <Tag>Via {s.introduced_by}</Tag>}
              {s.first_timer && <Tag color="blue">First Timer</Tag>}
              {s.has_room_in_ashram && <Tag color="green">Has Room</Tag>}
              {s.banned && <Tag color="red">Banned</Tag>}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}

function Tag({ children, color }: { children: React.ReactNode; color?: "blue" | "green" | "red" }) {
  /* eslint-disable */
  const palette = {
    blue: "bg-tag-blue-bg text-tag-blue-text border-tag-blue-border",
    green: "bg-tag-green-bg text-tag-green-text border-tag-green-border",
    red: "bg-tag-red-bg text-tag-red-text border-tag-red-border",
  };
  return (
    <span
      className={[
        "inline-flex items-center rounded-lg border px-2 py-0.5 text-[11px] font-semibold",
        color ? palette[color] : "bg-tag-default-bg text-tag-default-text border-tag-default-border",
      ].join(" ")}
    >
      {children}
    </span>
  );
}
