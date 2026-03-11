import type { components } from './generated/api'

export type SatsangiCreate = components['schemas']['SatsangiCreate']
export type Satsangi = components['schemas']['Satsangi']

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
