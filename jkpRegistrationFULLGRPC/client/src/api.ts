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
  baseUrl: 'http://localhost:8080',
})

const client = createClient(SatsangiService, transport)

// ---------------------------------------------------------------------------
// Re-export generated types so UI imports from one place
// ---------------------------------------------------------------------------

export type { Satsangi, SatsangiCreate }

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export async function createSatsangi(data: Partial<SatsangiCreate>): Promise<Satsangi> {
  return await client.createSatsangi({
    firstName: data.firstName ?? '',
    lastName: data.lastName ?? '',
    phoneNumber: data.phoneNumber ?? '',
    nationality: data.nationality ?? 'Indian',
    country: data.country ?? 'India',
    printOnCard: data.printOnCard ?? false,
    hasRoomInAshram: data.hasRoomInAshram ?? false,
    banned: data.banned ?? false,
    firstTimer: data.firstTimer ?? false,
    ...data,
  })
}

export async function listSatsangis(limit: number = 50): Promise<Satsangi[]> {
  const result = await client.listSatsangis({ limit })
  return result.satsangis
}

export async function searchSatsangis(query: string): Promise<Satsangi[]> {
  if (query.trim()) {
    const result = await client.searchSatsangis({ query })
    return result.satsangis
  }
  return listSatsangis(50)
}

export async function healthCheck(): Promise<HealthResponse> {
  return await client.health({})
}
