/**
 * API layer — connects the React UI to the gRPC backend.
 *
 * Data flow:
 *   React component calls listDevotees()
 *   → DevoteeServiceClient creates protobuf binary
 *   → grpc-web POSTs to proxy (:8080)
 *   → proxy forwards to gRPC server (:50051)
 *   → gRPC server queries PostgreSQL
 *   → response flows back the same way
 */

import { DevoteeServiceClient } from './generated/DevoteeServiceClientPb'
import { DevoteeList, Empty } from './generated/devotee_pb'

// gRPC-web proxy URL
const GRPC_WEB_URL = 'http://localhost:8080'
const client = new DevoteeServiceClient(GRPC_WEB_URL)

// ─── TypeScript interface (used by UI components) ───

export interface Devotee {
  id: number
  satsangi_id: string
  first_name: string
  last_name: string
  phone_number: string
  gender: string | null
  age: number | null
  city: string | null
  state: string | null
  nationality: string
  created_at: string
}

// ─── The one and only API function ───

export async function listDevotees(): Promise<Devotee[]> {
  // 1. Create an Empty protobuf message (ListDevotees takes no parameters)
  const request = new Empty()

  // 2. Call the gRPC service (grpc-web handles all the binary magic)
  const response: DevoteeList = await client.listDevotees(request)

  // 3. Convert protobuf messages → plain TypeScript objects
  return response.getDevoteesList().map((msg) => ({
    id: msg.getId(),
    satsangi_id: msg.getSatsangiId(),
    first_name: msg.getFirstName(),
    last_name: msg.getLastName(),
    phone_number: msg.getPhoneNumber(),
    gender: msg.getGender() || null,
    age: msg.hasAge() ? msg.getAge()! : null,
    city: msg.getCity() || null,
    state: msg.getState() || null,
    nationality: msg.getNationality() || 'Indian',
    created_at: msg.getCreatedAt(),
  }))
}
