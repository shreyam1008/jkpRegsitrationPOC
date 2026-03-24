/**
 * gRPC-web API layer — powered by @connectrpc/connect-web.
 *
 * All types are AUTO-GENERATED from proto/satsangi.proto via `bun run generate`.
 * No hand-written protobuf classes. No getter/setter boilerplate.
 *
 * Communication path:
 *   Browser  --grpc-web-->  Proxy (:8080)  --gRPC-->  Server (:50051)  --SQL-->  PostgreSQL
 */

import { createClient } from '@connectrpc/connect'
import { createGrpcWebTransport } from '@connectrpc/connect-web'
import { SatsangiService } from './generated/satsangi_pb'
import type { HealthResponse, Satsangi, SatsangiCreate } from './generated/satsangi_pb'

// ---------------------------------------------------------------------------
// gRPC-web transport — connects to the grpc-web proxy
// ---------------------------------------------------------------------------

const transport = createGrpcWebTransport({
  baseUrl: import.meta.env.VITE_GRPC_URL || 'http://localhost:8080',
})

const client = createClient(SatsangiService, transport)

// ---------------------------------------------------------------------------
// Re-export generated types so UI imports from one place
// ---------------------------------------------------------------------------

export type { Satsangi, SatsangiCreate }

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/** Require the 3 mandatory fields; everything else is optional. */
type CreateInput = Pick<SatsangiCreate, 'firstName' | 'lastName' | 'phoneNumber'> &
  Partial<Omit<SatsangiCreate, 'firstName' | 'lastName' | 'phoneNumber' | '$typeName' | '$unknown'>>

export async function createSatsangi(data: CreateInput): Promise<Satsangi> {
  return await client.createSatsangi({
    nationality: 'Indian',
    country: 'India',
    printOnCard: false,
    hasRoomInAshram: false,
    banned: false,
    firstTimer: false,
    ...data,
  })
}

export interface PaginatedResult {
  satsangis: Satsangi[]
  totalCount: number
}

export async function listSatsangis(limit: number = 20, offset: number = 0): Promise<PaginatedResult> {
  const result = await client.listSatsangis({ limit, offset })
  return { satsangis: result.satsangis, totalCount: result.totalCount }
}

export async function searchSatsangis(query: string): Promise<PaginatedResult> {
  if (query.trim()) {
    const result = await client.searchSatsangis({ query })
    return { satsangis: result.satsangis, totalCount: result.totalCount }
  }
  return listSatsangis(20)
}

export async function healthCheck(): Promise<HealthResponse> {
  return await client.health({})
}
