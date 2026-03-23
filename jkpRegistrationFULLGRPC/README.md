# JKP Registration — Full gRPC + PostgreSQL

## Architecture

```
Browser (React :5174)  ──grpc-web──►  Proxy (FastAPI :8080)  ──gRPC/HTTP2──►  gRPC Server (:50051)  ──SQL──►  PostgreSQL
```

## Project Structure

```
jkpRegistrationFULLGRPC/
├── proto/                          ← SHARED: single source of truth
│   └── satsangi.proto              ← define messages + RPCs here
├── server/
│   ├── app/
│   │   ├── generated/              ← auto-generated Python code
│   │   │   ├── satsangi_pb2.py     ← protobuf messages
│   │   │   ├── satsangi_pb2_grpc.py ← gRPC stubs
│   │   │   └── satsangi_pb2.pyi    ← type hints
│   │   ├── grpc_server.py          ← YOU implement RPCs here
│   │   ├── store.py                ← database queries
│   │   ├── models.py               ← Pydantic models
│   │   ├── db.py                   ← PostgreSQL connection
│   │   └── main.py                 ← grpc-web proxy (FastAPI)
│   └── pyproject.toml
├── client/
│   ├── buf.gen.yaml                ← buf config for TS generation
│   ├── src/
│   │   ├── generated/              ← auto-generated TypeScript code
│   │   │   └── satsangi_pb.ts      ← types + service descriptor
│   │   ├── api.ts                  ← connect-web client (thin wrapper)
│   │   ├── pages/                  ← React pages
│   │   └── components/             ← React components
│   └── package.json
└── README.md
```

## Running

```bash
# Terminal 1: Backend (starts gRPC server :50051 + proxy :8080)
cd server
uv run python -m uvicorn app.main:app --port 8080

# Terminal 2: Frontend
cd client
bun run dev
# Open http://localhost:5174
```

## Code Generation

When you change `proto/satsangi.proto`, regenerate code for **both** sides in one command:

```bash
./proto/generate
```

This generates Python (`server/app/generated/`) and TypeScript (`client/src/generated/`) in one shot.
All config lives inside `proto/` — uses remote buf plugins, no local protoc needed.

## Current RPCs

| RPC | Input | Output | Description |
|-----|-------|--------|-------------|
| `CreateSatsangi` | `SatsangiCreate` | `Satsangi` | Register a new satsangi |
| `ListSatsangis` | `ListRequest { limit }` | `SatsangiList` | Latest N satsangis (default 50) |
| `SearchSatsangis` | `SearchRequest { query }` | `SatsangiList` | Search by name, phone, email, etc. |

---

## Exercise: Add a Health Endpoint

Follow these steps to add a `Health` RPC yourself:

### Step 1: Edit `proto/satsangi.proto`

Add a new message and RPC:

```proto
// Add this message
message HealthResponse {
  string status = 1;
  string timestamp = 2;
}

// Add this RPC inside the service block
service SatsangiService {
  ...existing RPCs...
  rpc Health (Empty) returns (HealthResponse);
}
```

### Step 2: Regenerate code

```bash
./proto/generate
```

### Step 3: Implement on the server

In `server/app/grpc_server.py`, add to the servicer class:

```python
def Health(self, request, context):
    from datetime import datetime
    return satsangi_pb2.HealthResponse(
        status="ok",
        timestamp=datetime.now().isoformat(),
    )
```

### Step 4: Call from the frontend

In `client/src/api.ts`, add:

```typescript
export async function checkHealth() {
  return await client.health({})
}
```

### Step 5: Verify

Check `client/src/generated/satsangi_pb.ts` — you should see `HealthResponse` type and
`health` method in `SatsangiService` were auto-generated. No hand-writing needed.

That's it. **Proto → generate → implement → use.** The types flow automatically.
