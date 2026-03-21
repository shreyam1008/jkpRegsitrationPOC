// ─── Devotee ───

export interface Devotee {
  id: number;
  satsangi_id: string;
  first_name: string;
  last_name: string;
  phone_number: string;
  email?: string | null;
  gender?: string | null;
  date_of_birth?: string | null;
  age?: number | null;
  nationality?: string;
  special_category?: string | null;
  nick_name?: string | null;
  pan?: string | null;
  govt_id_type?: string | null;
  govt_id_number?: string | null;
  id_expiry_date?: string | null;
  id_issuing_country?: string | null;
  country?: string;
  address?: string | null;
  city?: string | null;
  district?: string | null;
  state?: string | null;
  pincode?: string | null;
  emergency_contact?: string | null;
  introducer?: string | null;
  introduced_by?: string | null;
  ex_center_satsangi_id?: string | null;
  print_on_card?: boolean;
  has_room_in_ashram?: boolean;
  banned?: boolean;
  first_timer?: boolean;
  date_of_first_visit?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export type DevoteeCreate = Omit<Devotee, "id" | "satsangi_id" | "created_at" | "updated_at">;

// ─── Visit ───

export interface Visit {
  id: number;
  devotee_id: number;
  location?: string | null;
  arrival_date?: string | null;
  departure_date?: string | null;
  purpose?: string | null;
  notes?: string | null;
  created_at: string;
}

export interface VisitCreate {
  devotee_id: number;
  location?: string | null;
  arrival_date?: string | null;
  departure_date?: string | null;
  purpose?: string | null;
  notes?: string | null;
}

// ─── API ───

const BASE = "/api";

export async function searchDevotees(query: string): Promise<Devotee[]> {
  const res = await fetch(`${BASE}/devotees?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getDevoteeById(id: string): Promise<Devotee> {
  const res = await fetch(`${BASE}/devotees/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function createDevotee(data: DevoteeCreate): Promise<Devotee> {
  const res = await fetch(`${BASE}/devotees`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getVisitsForDevotee(satsangiId: string): Promise<Visit[]> {
  const res = await fetch(`${BASE}/devotees/${encodeURIComponent(satsangiId)}/visits`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function createVisit(data: VisitCreate): Promise<Visit> {
  const res = await fetch(`${BASE}/visits`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
