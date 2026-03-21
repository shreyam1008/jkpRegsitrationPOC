/**
 * Minimal gRPC demo — lists devotees from PostgreSQL via gRPC.
 *
 * Data flow when you load this page:
 *   1. React calls listDevotees()
 *   2. api.ts creates an Empty protobuf → serializes to binary
 *   3. grpc-web wraps binary in 5-byte frame, base64 encodes, POSTs to proxy
 *   4. Proxy (:8080) decodes frame → forwards to gRPC server (:50051) over HTTP/2
 *   5. gRPC server queries PostgreSQL → returns DevoteeList protobuf
 *   6. Response flows back: gRPC → proxy → grpc-web → React
 *   7. React renders the list below
 */

import { useEffect, useState } from 'react'
import { listDevotees, type Devotee } from './api'

export default function App() {
  const [devotees, setDevotees] = useState<Devotee[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    listDevotees()
      .then(setDevotees)
      .catch((e) => setError(e.message || 'Failed to fetch'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b bg-white px-6 py-4 shadow-sm">
        <h1 className="text-xl font-bold text-gray-900">
          gRPC Minimal Demo
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Browser → grpc-web proxy (:8080) → gRPC server (:50051) → PostgreSQL
        </p>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8">
        {/* Status */}
        {loading && (
          <p className="text-center text-gray-500">Loading via gRPC…</p>
        )}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Devotee count */}
        {!loading && !error && (
          <p className="mb-4 text-sm text-gray-500">
            {devotees.length} devotees loaded via <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs font-mono">ListDevotees</code> gRPC call
          </p>
        )}

        {/* Table */}
        {devotees.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  <th className="px-4 py-3">Satsangi ID</th>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Phone</th>
                  <th className="px-4 py-3">City</th>
                  <th className="px-4 py-3">Gender</th>
                  <th className="px-4 py-3">Age</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {devotees.map((d) => (
                  <tr key={d.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-indigo-600">
                      {d.satsangi_id}
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {d.first_name} {d.last_name}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{d.phone_number}</td>
                    <td className="px-4 py-3 text-gray-600">
                      {d.city}{d.state ? `, ${d.state}` : ''}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{d.gender ?? '—'}</td>
                    <td className="px-4 py-3 text-gray-600">{d.age ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
