export interface SatsangiCreate {
  first_name: string
  last_name: string
  phone_number: string
  age?: number | null
  date_of_birth?: string | null
  pan?: string | null
  gender?: string | null
  special_category?: string | null
  nationality?: string
  govt_id_type?: string | null
  govt_id_number?: string | null
  id_expiry_date?: string | null
  id_issuing_country?: string | null
  nick_name?: string | null
  print_on_card?: boolean
  introducer?: string | null
  country?: string
  address?: string | null
  city?: string | null
  district?: string | null
  state?: string | null
  pincode?: string | null
  emergency_contact?: string | null
  ex_center_satsangi_id?: string | null
  introduced_by?: string | null
  has_room_in_ashram?: boolean
  email?: string | null
  banned?: boolean
  first_timer?: boolean
  date_of_first_visit?: string | null
  notes?: string | null
}

export interface Satsangi extends SatsangiCreate {
  satsangi_id: string
  created_at: string
}

const BASE = '/api'

export async function createSatsangi(data: SatsangiCreate): Promise<Satsangi> {
  const res = await fetch(`${BASE}/satsangis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function searchSatsangis(query: string): Promise<Satsangi[]> {
  const res = await fetch(`${BASE}/satsangis?q=${encodeURIComponent(query)}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
