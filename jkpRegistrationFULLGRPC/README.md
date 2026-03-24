# JKP Satsangi Registration — Full gRPC + PostgreSQL

> A type-safe, end-to-end gRPC registration system.
> One `.proto` file defines the entire API — types flow automatically to both
> the Python backend and the React frontend. No REST, no hand-written DTOs.

---

## Table of Contents

1. [Key Concepts](#key-concepts)
2. [Tech Stack](#tech-stack)
3. [Architecture Overview](#architecture-overview)
4. [How Everything Connects](#how-everything-connects)
5. [Server Layers](#server-layers--what-each-does)
6. [Frontend](#frontend)
7. [Project Structure](#project-structure)
8. [Development](#development)
9. [Tutorial: Adding a New RPC End-to-End](#tutorial-adding-a-new-rpc-end-to-end)
10. [Hosting & Deployment](#hosting--deployment)
11. [Production Readiness](#production-readiness)

---

## Key Concepts

If you're new to this codebase, understand these 4 things first:

### What is gRPC?

gRPC is a way for the frontend and backend to talk to each other — like REST,
but instead of JSON over HTTP, it uses **protobuf** (compact binary) over HTTP/2.
You define your API in a `.proto` file, and tools auto-generate typed code
for both sides. No mismatched field names, no missing fields, no guessing.

### What is grpc-web?

Browsers can't speak native gRPC (they lack HTTP/2 trailers). **grpc-web** is
a variant that works over HTTP/1.1. The browser sends base64-encoded protobuf
in a POST request. A proxy translates it to native gRPC for the server.

### What is the proxy doing?

`server/app/main.py` (FastAPI) is **not** the application server. It is a
thin **protocol translator**:

```
Browser POST (grpc-web-text, base64) → Proxy → native gRPC → gRPC Server
```

The proxy does NOT parse your protobuf messages. It just unwraps the framing,
forwards raw bytes, and re-wraps the response. Zero business logic.

### What is the proto file?

`proto/satsangi.proto` is the **single source of truth** for your entire API.
When you change it and run `./proto/generate`, it auto-generates:
- **Python** stubs in `server/app/generated/` (protobuf messages + gRPC service base class)
- **TypeScript** stubs in `client/src/generated/` (typed messages + service descriptor)

You never write request/response types by hand.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **API contract** | Protobuf 3 + buf | Single `.proto` → generated code for both sides |
| **Frontend** | React 19, Vite 8, Bun, TailwindCSS 4 | Modern SPA with fast builds |
| **Frontend ↔ Backend** | ConnectRPC (grpc-web) | Typed gRPC calls from the browser |
| **Proxy** | FastAPI + uvicorn | Async grpc-web → gRPC translation |
| **Backend** | grpcio (Python gRPC server) | ThreadPoolExecutor, reflection, proto stubs |
| **Data models** | Pydantic v2 | Validation, serialization, defaults |
| **Database** | PostgreSQL 17, psycopg2 | Connection pool (2–20), parameterized SQL |
| **Reverse proxy** | Caddy 2 | Auto-TLS, HTTP/3, static files, security headers |
| **Deployment** | Docker Compose (multi-stage) | 3 containers: server, Caddy, tunnel |
| **Internet exposure** | Cloudflare Tunnel | Zero open ports, hidden IP |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET / LAN                                      │
│                                                                                  │
│   Browser (React 19 + ConnectRPC)                                                │
│       │  HTTP/1.1 POST  (grpc-web-text, base64-encoded protobuf)                 │
│       ▼                                                                          │
│   ┌─────────────────────────────────────────────────────┐                        │
│   │              Caddy  (client container)               │                        │
│   │  ┌───────────────────┐  ┌─────────────────────────┐ │                        │
│   │  │ app.yourdomain.com│  │  api.yourdomain.com     │ │                        │
│   │  │ file_server /srv  │  │  reverse_proxy ──────────┼─┼──┐                    │
│   │  │ (built React SPA) │  │  (grpc-web traffic)     │ │  │                    │
│   │  └───────────────────┘  └─────────────────────────┘ │  │                    │
│   │  TLS (internal CA or Let's Encrypt) + gzip/zstd     │  │                    │
│   │  HTTP/3 (QUIC) on :443/udp                          │  │                    │
│   │  Security headers (CSP, HSTS, X-Frame, etc.)        │  │                    │
│   └─────────────────────────────────────────────────────┘  │                    │
│                                                             │                    │
│   ┌─────────────────────────────────────────────────────┐  │                    │
│   │              Server container                        │◄─┘                    │
│   │                                                      │                       │
│   │  ┌────────────────────────────────────────────────┐  │                       │
│   │  │  FastAPI grpc-web Proxy  (:8080, uvicorn)      │  │                       │
│   │  │  • Decodes grpc-web frames (base64 → binary)   │  │                       │
│   │  │  • Async gRPC channel (grpc.aio) — non-blocking│  │                       │
│   │  │  • Identity serializers — zero-copy passthrough │  │                       │
│   │  │  • /healthz endpoint for Caddy health checks   │  │                       │
│   │  └────────────────┬───────────────────────────────┘  │                       │
│   │                   │ HTTP/2 (localhost, multiplexed)   │                       │
│   │  ┌────────────────▼───────────────────────────────┐  │                       │
│   │  │  gRPC Server  (:50051, ThreadPoolExecutor×10)  │  │                       │
│   │  │  • CreateSatsangi, SearchSatsangis, List, Health│  │                       │
│   │  │  • Server reflection (grpcurl/Postman ready)   │  │                       │
│   │  │  • Proto → Pydantic model conversion           │  │                       │
│   │  └────────────────┬───────────────────────────────┘  │                       │
│   │                   │ psycopg2 (threaded conn pool)    │                       │
│   └───────────────────┼──────────────────────────────────┘                       │
│                       │                                                          │
│   ┌───────────────────▼──────────────────────────────────┐                       │
│   │  PostgreSQL 17  (separate server / docker-compose)    │                       │
│   │  • ThreadedConnectionPool 2–20 conns                  │                       │
│   │  • Auto-retry on startup (DB not ready yet? waits)    │                       │
│   │  • Stale connection detection + auto-replace          │                       │
│   │  • Indexes: name, phone, email                        │                       │
│   └──────────────────────────────────────────────────────┘                       │
│                                                                                  │
│   ┌──────────────────────────────────────────────────(optional-if WEB)           │
│   │  Cloudflare Tunnel  (cloudflared container)           │                       │
│   │  • Zero exposed ports — no firewall changes           │                       │
│   │  • Hides server IP from the internet                  │                       │
│   │  • Connects outbound to Cloudflare edge               │                       │
│   │  • CF dashboard maps domains → https://client:443     │                       │
│   └──────────────────────────────────────────────────────┘                       │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## How Everything Connects

### Request lifecycle (browser → DB → browser)

```
1. User clicks "Search" in React UI
2. api.ts calls:  client.searchSatsangis({ query: "Ram" })
3. ConnectRPC encodes SearchRequest as protobuf, wraps in grpc-web frame (base64)
4. HTTP POST → https://api.yourdomain.com/jkp.registration.v1.SatsangiService/SearchSatsangis
5. Caddy terminates TLS, reverse-proxies to server:8080
6. FastAPI proxy (main.py):
   a. Strips base64 → binary grpc-web frame
   b. Extracts protobuf payload from 5-byte frame header
   c. Forwards raw bytes via grpc.aio async channel to localhost:50051
7. gRPC server (grpc_server.py):
   a. Deserializes SearchRequest protobuf
   b. Calls store.search_satsangis("Ram") — borrows DB conn from pool
   c. Executes ILIKE query across 12 fields
   d. Returns SatsangiList protobuf
8. FastAPI proxy wraps response in grpc-web DATA frame + OK trailer, base64-encodes
9. Browser receives response → ConnectRPC deserializes → typed Satsangi[] in React
```

### Connection types at each boundary

| From → To | Protocol | Connection | Multiplexing |
|-----------|----------|------------|-------------|
| Browser → Caddy | HTTPS (HTTP/3 QUIC or HTTP/1.1) | Per-request | Browser-managed |
| Caddy → FastAPI | HTTP/1.1 | Keepalive 30s, 100 idle conns | Caddy conn pool |
| FastAPI → gRPC Server | HTTP/2 (grpc.aio) | **Singleton channel** — 1 TCP conn | HTTP/2 streams (thousands concurrent) |
| gRPC Server → PostgreSQL | TCP (libpq) | **ThreadedConnectionPool** 2–20 conns | One query per conn |

---

## Server Layers — What Each Does

### Layer 1: FastAPI grpc-web Proxy (`server/app/main.py`)

FastAPI is **not** the application server. It is a **protocol translator**.

| Responsibility | Detail |
|---|---|
| Decode grpc-web | Base64 decode → strip 5-byte frame header → raw protobuf bytes |
| Forward to gRPC | `await channel.unary_unary()(payload)` — async, non-blocking |
| Encode response | Protobuf bytes → DATA frame + trailer frame → base64 |
| Health endpoint | `GET /healthz` — polled by Caddy every 10s |
| CORS | Allows browser cross-origin grpc-web requests |

**Key optimizations:**
- **`grpc.aio` async channel** — never blocks the uvicorn event loop
- **Singleton channel** — one TCP conn, HTTP/2 multiplexes all RPCs
- **Identity serializers** — raw bytes pass through, no deserialize/re-serialize
- **Pre-allocated OK trailer** — built once at module load, reused every response

**You do NOT touch `main.py` when adding new RPCs.** It is a generic proxy —
it forwards any `/package.Service/Method` POST to the gRPC server automatically.

### Layer 2: gRPC Server (`server/app/grpc_server.py`)

The actual business logic. Standard `grpc.server` with `ThreadPoolExecutor(10)`.

| RPC | Input | Output | Description |
|-----|-------|--------|-------------|
| `CreateSatsangi` | `SatsangiCreate` | `Satsangi` | Register new satsangi (8-char UUID) |
| `SearchSatsangis` | `SearchRequest` | `SatsangiList` | ILIKE across 12 fields |
| `ListSatsangis` | `ListRequest` | `SatsangiList` | Latest N (default all) |
| `Health` | `HealthRequest` | `HealthResponse` | DB connectivity + timestamp |

**gRPC reflection** is enabled — `grpcurl`, `grpcui`, and Postman can discover
the API without the `.proto` file.

### Layer 3: Data (`server/app/db.py` + `store.py` + `models.py`)

| File | Role |
|------|------|
| `db.py` | ThreadedConnectionPool (2–20), auto-retry on startup, stale conn detection |
| `store.py` | Pre-computed SQL (INSERT, SEARCH with 12 ILIKE fields, LIST), parameterized queries |
| `models.py` | Pydantic models — `SatsangiCreate` (input) extends to `Satsangi` (+ id + timestamp) |

**Resilience features:**
- `init_pool` retries 5× with 2s backoff (survives DB not ready at boot)
- `get_conn` runs `SELECT 1` liveness check; if dead, discards + fetches fresh conn
- If entire pool is lost, `_ensure_pool()` recreates it transparently

---

## Frontend

| Stack | Detail |
|-------|--------|
| React 19 | SPA with React Router 7 (Search, Create, Profile pages) |
| ConnectRPC | `@connectrpc/connect-web` — typed gRPC-web client |
| Protobuf | `@bufbuild/protobuf` — auto-generated from `satsangi.proto` |
| Styling | TailwindCSS 4, lucide-react icons, clsx |
| Forms | react-hook-form + zod validation |
| Build | Vite 8 + Bun |

The entire client API layer is in `client/src/api.ts` — 4 exported functions,
all fully typed from the generated proto code. No hand-written request/response types.

```
client/src/api.ts
  ├── createSatsangi(data)   → Satsangi
  ├── searchSatsangis(query) → Satsangi[]
  ├── listSatsangis(limit)   → Satsangi[]
  └── healthCheck()          → HealthResponse
```

---

## Project Structure

```
jkpRegistrationFULLGRPC/
├── proto/
│   ├── satsangi.proto              ← SINGLE SOURCE OF TRUTH for the API
│   ├── buf.yaml + buf.gen.yaml     ← buf config (TS generation)
│   └── generate                    ← one script → Python + TypeScript stubs
├── server/
│   ├── app/
│   │   ├── main.py                 ← grpc-web proxy (FastAPI + grpc.aio) — DON'T TOUCH for new RPCs
│   │   ├── grpc_server.py          ← gRPC service implementation — ADD NEW RPCs HERE
│   │   ├── store.py                ← PostgreSQL queries — ADD NEW QUERIES HERE
│   │   ├── models.py               ← Pydantic models — ADD NEW MODELS HERE
│   │   ├── db.py                   ← connection pool + retry + reconnect
│   │   └── generated/              ← AUTO-GENERATED — never edit by hand
│   └── pyproject.toml
├── client/
│   ├── src/
│   │   ├── api.ts                  ← ConnectRPC client — ADD NEW CLIENT FUNCTIONS HERE
│   │   ├── generated/              ← AUTO-GENERATED — never edit by hand
│   │   ├── pages/                  ← React pages — ADD NEW UI HERE
│   │   └── components/             ← Reusable UI components
│   └── package.json
├── docker/
│   ├── server/Dockerfile           ← multi-stage (uv build → python:3.12-slim)
│   ├── client/Dockerfile           ← multi-stage (bun build → caddy:2-alpine)
│   ├── client/Caddyfile            ← TLS, static files, reverse proxy, security headers
│   └── db/init.sql                 ← schema bootstrap — ADD NEW TABLES HERE (Docker only)
├── tests/                          ← load simulation + correctness tests
├── docker-compose.yml              ← server + Caddy + tunnel
└── docker-compose.db.yml           ← PostgreSQL (separate machine)
```

---

## Development

```bash
# Terminal 1: Backend (gRPC :50051 + proxy :8080)
cd server && uv run task dev

# Terminal 2: Frontend (Vite :5174, proxies /api → :8080)
cd client && bun run dev

# Regenerate proto (both Python + TypeScript)
cd proto && ./generate
```

### Docker (production)

```bash
# App server
docker compose up -d --build

# DB server (separate machine)
docker compose -f docker-compose.db.yml up -d
```

---

## Tutorial: Adding a New RPC End-to-End

This walks through adding a **`CreateVisit`** RPC — recording when a satsangi
visits the ashram. It touches every layer of the stack so you can see exactly
what files to edit and in what order.

**Goal:** Send `{ satsangi_id, visit_date, purpose }` → get back a `Visit` with
an auto-generated `visit_id` and `created_at` timestamp.

### The files you will edit (in order)

```
 STEP  FILE                              WHAT YOU DO
 ────  ────                              ────────────
  1    proto/satsangi.proto              Define messages + RPC
  2    (run ./proto/generate)            Auto-generate Python + TypeScript stubs
  3    server/app/db.py                  Add CREATE TABLE for visits (or init.sql for Docker)
  4    server/app/models.py              Add Pydantic models
  5    server/app/store.py               Add SQL insert function
  6    server/app/grpc_server.py         Implement the RPC method
  7    client/src/api.ts                 Add typed client function
  8    client/src/pages/SomePage.tsx      Call the function from UI
```

**Note:** You do NOT touch `server/app/main.py` — the proxy is generic and
automatically forwards any gRPC method. You also don't touch Docker or Caddy
configs — they don't care what RPCs exist.

---

### Step 1 — Define the API in proto

Edit `proto/satsangi.proto`. Add the new messages and RPC:

```proto
// ─── Visit messages ───

message VisitCreate {
  string satsangi_id = 1;           // existing satsangi's ID
  string visit_date  = 2;           // e.g. "2026-03-24"
  optional string purpose = 3;      // e.g. "Satsang", "Seva", "Darshan"
  optional string notes   = 4;
}

message Visit {
  string visit_id    = 1;           // auto-generated 8-char UUID
  string created_at  = 2;           // ISO timestamp
  string satsangi_id = 3;
  string visit_date  = 4;
  optional string purpose = 5;
  optional string notes   = 6;
}

message VisitResponse {
  bool   success = 1;
  string message = 2;
  Visit  visit   = 3;
}
```

Then add the RPC to the existing service block:

```proto
service SatsangiService {
  // ... existing RPCs ...
  rpc CreateVisit(VisitCreate) returns (VisitResponse);
}
```

**Why here?** The `.proto` file is the contract. Both Python and TypeScript
code are generated from it. Define the shape of data once, use it everywhere.

---

### Step 2 — Regenerate code

```bash
cd proto && ./generate
```

This runs `buf generate` (TypeScript) and `grpc_tools.protoc` (Python).

**After this, you get FOR FREE:**

| File | What was generated |
|------|-------------------|
| `server/app/generated/satsangi_pb2.py` | `VisitCreate`, `Visit`, `VisitResponse` Python classes |
| `server/app/generated/satsangi_pb2_grpc.py` | `CreateVisit` method stub in `SatsangiServiceServicer` |
| `server/app/generated/satsangi_pb2.pyi` | Python type hints for IDE autocomplete |
| `client/src/generated/satsangi_pb.ts` | `VisitCreate`, `Visit`, `VisitResponse` TypeScript types + `createVisit` in `SatsangiService` |

**You now have typed classes on both sides. You never write these by hand.**

---

### Step 3 — Add the database table

Edit `server/app/db.py` — append to `CREATE_TABLE_SQL`:

```python
CREATE_TABLE_SQL = """
... existing satsangis table ...

CREATE TABLE IF NOT EXISTS visits (
    visit_id     VARCHAR(8) PRIMARY KEY,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    satsangi_id  VARCHAR(8) NOT NULL REFERENCES satsangis(satsangi_id),
    visit_date   VARCHAR(20) NOT NULL,
    purpose      VARCHAR(100),
    notes        TEXT
);

CREATE INDEX IF NOT EXISTS idx_visits_satsangi
    ON visits (satsangi_id);
CREATE INDEX IF NOT EXISTS idx_visits_date
    ON visits (visit_date);
"""
```

If using Docker, also add the same SQL to `docker/db/init.sql`.

**Why?** The `init_pool()` function runs `CREATE_TABLE_SQL` on startup.
New tables are created automatically when the server starts.

---

### Step 4 — Add Pydantic models

Edit `server/app/models.py`:

```python
class VisitCreate(BaseModel):
    satsangi_id: str
    visit_date: str
    purpose: str | None = None
    notes: str | None = None


class Visit(VisitCreate):
    visit_id: str = Field(default_factory=lambda: uuid4().hex[:8].upper())
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
```

**Why?** Pydantic validates input and provides defaults (auto-generated ID,
timestamp). The pattern is the same as the existing `SatsangiCreate` → `Satsangi`.

---

### Step 5 — Add the SQL query

Edit `server/app/store.py`:

```python
from app.models import Visit, VisitCreate  # add to existing imports

_VISIT_INSERT_SQL = """
    INSERT INTO visits (visit_id, satsangi_id, visit_date, purpose, notes)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING visit_id, created_at, satsangi_id, visit_date, purpose, notes
"""

def create_visit(data: VisitCreate) -> Visit:
    """Insert a new visit record and return it."""
    visit = Visit(**data.model_dump())
    values = [visit.visit_id, visit.satsangi_id, visit.visit_date,
              visit.purpose, visit.notes]

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(_VISIT_INSERT_SQL, values)
            row = cur.fetchone()
        conn.commit()

    data = dict(row)
    if data.get("created_at"):
        data["created_at"] = data["created_at"].isoformat()
    return Visit(**data)
```

**Why?** This follows the exact same pattern as `create_satsangi()`:
Pydantic model → SQL INSERT → return the DB row as a model.

---

### Step 6 — Implement the gRPC method

Edit `server/app/grpc_server.py`. Add to the `SatsangiServiceServicer` class:

```python
from app.models import VisitCreate as VisitCreateModel  # add to imports
from app.models import Visit as VisitModel              # add to imports

# Inside the class:
def CreateVisit(
    self,
    request: satsangi_pb2.VisitCreate,
    context: grpc.ServicerContext,
) -> satsangi_pb2.VisitResponse:
    try:
        create_data = VisitCreateModel(
            satsangi_id=request.satsangi_id,
            visit_date=request.visit_date,
            purpose=request.purpose if request.HasField("purpose") else None,
            notes=request.notes if request.HasField("notes") else None,
        )
        visit = store.create_visit(create_data)
        return satsangi_pb2.VisitResponse(
            success=True,
            message="Visit recorded",
            visit=satsangi_pb2.Visit(
                visit_id=visit.visit_id,
                created_at=visit.created_at,
                satsangi_id=visit.satsangi_id,
                visit_date=visit.visit_date,
                purpose=visit.purpose or "",
                notes=visit.notes or "",
            ),
        )
    except Exception as e:
        logger.exception("CreateVisit failed")
        context.set_code(grpc.StatusCode.INTERNAL)
        context.set_details(str(e))
        return satsangi_pb2.VisitResponse(success=False, message=str(e))
```

**Why?** This is where your business logic lives. The pattern is always:
1. Convert protobuf request → Pydantic model
2. Call `store.xxx()` to hit the DB
3. Convert the result back to a protobuf response

**The proxy (`main.py`) already forwards `CreateVisit` automatically** —
because it proxies any `POST /{service}/{method}` to the gRPC server.

---

### Step 7 — Add the client function

Edit `client/src/api.ts`:

```typescript
import type { Visit, VisitResponse } from './generated/satsangi_pb'  // add to imports

export async function createVisit(
  satsangiId: string,
  visitDate: string,
  purpose?: string,
  notes?: string,
): Promise<VisitResponse> {
  return await client.createVisit({
    satsangiId,
    visitDate,
    purpose: purpose ?? '',
    notes: notes ?? '',
  })
}
```

**Why?** `client.createVisit()` was auto-generated in Step 2. It's already
fully typed — your IDE will autocomplete the fields and catch typos.

---

### Step 8 — Call it from the UI

In any React component or page:

```tsx
import { createVisit } from '../api'

async function handleRecordVisit() {
  const result = await createVisit('A1B2C3D4', '2026-03-24', 'Satsang')
  if (result.success) {
    console.log('Visit recorded:', result.visit?.visitId)
  }
}
```

**That's it.** The type of `result` is `VisitResponse`, `result.visit` is
`Visit | undefined` — all auto-typed from the proto definition.

---

### What you did NOT have to touch

| File | Why not |
|------|---------|
| `server/app/main.py` | Generic proxy — forwards all RPCs automatically |
| `docker/client/Caddyfile` | Caddy proxies all traffic to :8080 regardless of RPC |
| `docker-compose.yml` | No new containers or ports needed |
| `client/src/generated/*` | Auto-generated — never edit by hand |
| `server/app/generated/*` | Auto-generated — never edit by hand |

### Summary: the pattern

```
1. proto/satsangi.proto     — define messages + RPC
2. ./proto/generate          — auto-generate both sides
3. server/app/db.py          — create table (if new entity)
4. server/app/models.py      — Pydantic input + output models
5. server/app/store.py       — SQL query
6. server/app/grpc_server.py — implement RPC (proto → model → store → proto)
7. client/src/api.ts         — thin typed wrapper
8. UI component              — call the function, use the typed result
```

Every new RPC follows this exact pattern. The proxy, Caddy, Docker, and
generated code never need to change.

---

## Hosting & Deployment

### Docker Compose — 3 containers

```
docker-compose.yml          ← App server (server + client/Caddy + tunnel)
docker-compose.db.yml       ← DB server (PostgreSQL 17, separate machine)
```

| Container | Image | Ports | Role |
|-----------|-------|-------|------|
| `server` | python:3.12-slim (multi-stage) | expose 8080 (internal only) | gRPC server + grpc-web proxy |
| `client` | caddy:2-alpine (multi-stage) | 80, 443, 443/udp | TLS, static SPA, reverse proxy |
| `tunnel` | cloudflare/cloudflared | none | Cloudflare Tunnel (optional) |
| `db` | postgres:17-alpine | 5433→5432 | PostgreSQL (separate compose) |

### Exposing to the Internet — Cloudflare Tunnel

Zero exposed ports, server IP hidden:

1. Create a tunnel in **Cloudflare Zero Trust** dashboard → get a token
2. Set `CF_TUNNEL_TOKEN` in `.env` next to `docker-compose.yml`
3. In CF dashboard, map:
   - `app.yourdomain.com` → `https://client:443`
   - `api.yourdomain.com` → `https://client:443`
4. Keep `tls internal` in Caddyfile — CF terminates public TLS,
   cloudflared trusts the internal Caddy cert over the encrypted tunnel
5. No firewall/port changes needed on your server

### TLS

- **Default**: Caddy's internal CA (self-signed) — works immediately on LAN
- **Production**: Remove `tls internal` from Caddyfile → Caddy auto-fetches Let's Encrypt certs
- **With CF Tunnel**: Keep `tls internal` — Cloudflare handles public TLS

---

## Production Readiness

### What's solid now
- **Type safety end-to-end** — proto → generated stubs → no drift
- **Async proxy** — `grpc.aio` channel, non-blocking event loop
- **DB resilience** — startup retry, stale conn detection, pool auto-recreate
- **Security** — Caddy handles TLS, security headers (CSP/HSTS/X-Frame), CORS locked to POST+OPTIONS
- **Zero-copy proxy** — identity serializers, pre-allocated trailers
- **Reflection** — introspect API with grpcurl/Postman without `.proto` file

### For scaling beyond POC
- **Multiple uvicorn workers** — requires moving gRPC server to a separate process/container (avoids :50051 port clash)
- **Async DB driver** — switch from psycopg2 to psycopg v3 async if moving gRPC server to `grpc.aio`
- **Observability** — add OpenTelemetry tracing, structured logging, Prometheus metrics
- **Rate limiting** — Caddy `rate_limit` directive or Cloudflare WAF rules
- **Auth** — JWT/session tokens validated at the proxy layer
- **CI/CD** — automated proto generation check, Docker image build, deploy pipeline
