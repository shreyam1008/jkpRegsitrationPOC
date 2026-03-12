import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createSatsangi, searchSatsangis } from '../../client/src/api'

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

beforeEach(() => {
  mockFetch.mockReset()
})

const SAMPLE_INPUT = { first_name: 'Ram', last_name: 'Kumar', phone_number: '9876543210' }
const SAMPLE_RESPONSE = {
  ...SAMPLE_INPUT,
  satsangi_id: 'ABC12345',
  created_at: '2025-01-01T00:00:00',
  nationality: 'Indian',
  country: 'India',
}

describe('createSatsangi', () => {
  it('sends POST with correct body and returns created satsangi', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(SAMPLE_RESPONSE),
    })

    const result = await createSatsangi(SAMPLE_INPUT)

    expect(mockFetch).toHaveBeenCalledWith('/api/satsangis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(SAMPLE_INPUT),
    })
    expect(result.satsangi_id).toBe('ABC12345')
    expect(result.first_name).toBe('Ram')
  })

  it('throws on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      text: () => Promise.resolve('Bad Request'),
    })

    await expect(
      createSatsangi({ first_name: '', last_name: '', phone_number: '' }),
    ).rejects.toThrow('Bad Request')
  })
})

describe('searchSatsangis', () => {
  it('sends GET with query param and returns results', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([SAMPLE_RESPONSE]),
    })

    const result = await searchSatsangis('Ram')
    expect(mockFetch).toHaveBeenCalledWith('/api/satsangis?q=Ram')
    expect(result).toHaveLength(1)
    expect(result[0].first_name).toBe('Ram')
  })

  it('encodes special characters in query', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([]),
    })

    await searchSatsangis('test & value')
    expect(mockFetch).toHaveBeenCalledWith('/api/satsangis?q=test%20%26%20value')
  })

  it('returns empty array on empty query', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([]),
    })

    const result = await searchSatsangis('')
    expect(mockFetch).toHaveBeenCalledWith('/api/satsangis?q=')
    expect(result).toEqual([])
  })

  it('throws on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      text: () => Promise.resolve('Server Error'),
    })

    await expect(searchSatsangis('test')).rejects.toThrow('Server Error')
  })
})
