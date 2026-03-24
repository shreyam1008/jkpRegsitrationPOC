/**
 * Frontend integration tests — verifies the TypeScript API layer
 * (ConnectRPC transport + api.ts wrappers) against the running server.
 *
 * Prerequisite: cd server && uv run task dev
 *
 * Why integration instead of mocks?
 *   api.ts is 4 thin wrappers. Mocking ConnectRPC across directory
 *   boundaries is brittle. Testing against the real server verifies
 *   the entire TS→gRPC-web→proxy→gRPC chain actually works.
 */

import { describe, it, expect } from 'vitest'

const {
  createSatsangi,
  listSatsangis,
  searchSatsangis,
  healthCheck,
} = await import('@client/api')

// ---------------------------------------------------------------------------
// Tests — server must be running on :8080
// ---------------------------------------------------------------------------

describe('healthCheck', () => {
  it('returns healthy status', async () => {
    const result = await healthCheck()
    expect(result.status).toBe('healthy')
    expect(result.dbStatus).toBe('connected')
    expect(result.message).toBeTruthy()
    expect(result.timestamp).toBeTruthy()
  })
})

describe('createSatsangi', () => {
  it('creates and returns with 8-char ID', async () => {
    const result = await createSatsangi({
      firstName: 'VitestCreate',
      lastName: 'Test',
      phoneNumber: '8000000001',
    })
    expect(result.satsangiId).toHaveLength(8)
    expect(result.firstName).toBe('VitestCreate')
    expect(result.lastName).toBe('Test')
    expect(result.phoneNumber).toBe('8000000001')
  })

  it('applies default values', async () => {
    const result = await createSatsangi({
      firstName: 'VitestDefaults',
      lastName: 'Test',
      phoneNumber: '8000000002',
    })
    expect(result.nationality).toBe('Indian')
    expect(result.country).toBe('India')
    expect(result.banned).toBe(false)
    expect(result.firstTimer).toBe(false)
  })
})

describe('listSatsangis', () => {
  it('returns array with limit', async () => {
    const results = await listSatsangis(3)
    expect(results.length).toBeLessThanOrEqual(3)
    expect(results.length).toBeGreaterThan(0)
  })

  it('each result has required fields', async () => {
    const results = await listSatsangis(1)
    const s = results[0]
    expect(s.satsangiId).toBeTruthy()
    expect(s.firstName).toBeTruthy()
    expect(s.lastName).toBeTruthy()
    expect(s.createdAt).toBeTruthy()
  })
})

describe('searchSatsangis', () => {
  it('finds by first name', async () => {
    const results = await searchSatsangis('VitestCreate')
    expect(results.some(s => s.firstName === 'VitestCreate')).toBe(true)
  })

  it('returns results for empty query (falls back to list)', async () => {
    const results = await searchSatsangis('')
    expect(results.length).toBeGreaterThan(0)
  })
})
