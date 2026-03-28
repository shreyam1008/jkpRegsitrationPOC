# JKP Registration — Tech Stack & Architecture (Dev Reference)

Last updated: 28 March 2026
Status: Living document — add decisions as they're made.
POC reference: `jkpRegistrationFULLGRPC/`
Companion doc: [`006-project-plan.md`](./006-project-plan.md) — product features, policies & roadmap.

---

## Summary

Internal web app for satsangi (devotee) registration at JKP ashrams. Self-hosted on internal network behind site-to-site VPN. Two-server topology — stateless compute node + stateful storage node. Target scale: ~200k–500k records, 50–60 concurrent staff, 4–5 geographies.

The POC validates the full vertical slice: React SPA → gRPC-web → FastAPI proxy → async gRPC server → PostgreSQL. Everything async end-to-end. No threads.

---

## Architecture (Request Flow)

```
Browser (React SPA, ConnectRPC)
    │  grpc-web-text (base64, HTTP/1.1 POST)
    ▼
Caddy (TLS termination, static files, compression, HTTP/3)
    │  reverse_proxy (keepalive, health-check)
    ▼
FastAPI grpc-web Proxy (:8080, uvicorn, async)
    │  HTTP/2 multiplexed, singleton grpc.aio channel
    │  identity serializers — raw bytes pass-through, zero deser
    ▼
gRPC Server (:50051, grpc.aio.server, in-process, fully async)
    │  async pooled connections (psycopg v3 AsyncConnectionPool)
    ▼
PostgreSQL 17
```

Target production adds: Keycloak (auth), MinIO (photos/docs), background workers (PG-backed queue), and separates proxy from gRPC server into independent containers.

---

## Frontend

| What | Choice | Version | Notes |
|------|--------|---------|-------|
| Framework | React | 19.2 | |
| Language | TypeScript | 6.0 | Strict. No `any`. Explicit interfaces everywhere. |
| Build | Vite | 8.x | |
| Package manager | Bun | 1.3 | Replaces npm/yarn everywhere. Lockfile: `bun.lock` |
| Styling | TailwindCSS | 4.2 | Vite plugin (`@tailwindcss/vite`). No CSS-in-JS. |
| Routing | TanStack Router | latest | Type-safe routing with search params validation. |
| Data fetching | TanStack Query | latest | Server-state caching, loading/error states, automatic retries. |
| Tables | TanStack Table | latest | Headless, performant data tables. |
| Hotkeys | TanStack Hotkeys | latest | Keyboard shortcut management for power users. |
| Forms | React Hook Form + Zod + @hookform/resolvers | latest | Zod for schema validation, resolver bridges it to RHF. |
| State management | Zustand | latest | Lightweight global state when React Context is insufficient. |
| Icons | Lucide React | latest | Tree-shakeable, consistent icon set. (TBD — may evaluate alternatives.) |
| Utility | clsx | 2.x | Conditional class merging. |
| Client-side fuzzy search | Fuse.js | latest | In-browser fuzzy matching over cached satsangi lists. |
| gRPC client | @connectrpc/connect + connect-web | 2.x | grpc-web transport. Typed client from generated code. |
| Proto types | @bufbuild/protobuf | 2.x | Auto-generated from `.proto`. Never hand-write proto types. |
| Linting/Formatting | oxlint / oxfmt | latest | Rust-based, fast. Replaces ESLint + Prettier. |
| Type checking | `tsc -b` (build mode) | — | Part of `bun run build`. |

### Frontend rules
- **No `any`.** Use `unknown` + type narrowing if truly unknown.
- **No manual `fetch()` or `axios` to gRPC backend.** All comms via ConnectRPC generated client.
- **Exception:** media uploads use native `fetch` with pre-signed MinIO URLs (future).
- **Server state:** `@tanstack/react-query` for caching/retries/loading states.
- **Local UI state:** `useState` / React Context / Zustand. No Redux unless complexity demands it.
- **UI primitives** live in `src/components/ui/`. Reusable, accessible (`useId` for labels).
- **Design system:** Inter font, brand indigo palette (`--color-brand-*`), custom scrollbar, CSS grid animations.

---

## Proto / API Contract

| What | Choice | Notes |
|------|--------|-------|
| IDL | Protocol Buffers 3 (`proto3`) | Single source of truth for data shape |
| Package | `jkp.registration.v1` | Versioned package for future evolution |
| TS codegen | `buf` CLI + remote plugin (`buf.build/bufbuild/es`) | Outputs to `client/src/generated/` |
| Python codegen | `grpcio-tools` (via `uv run python -m grpc_tools.protoc`) | Outputs to `server/app/generated/` |
| Generation script | `./proto/generate` | Single bash script, generates both languages, fixes Python imports via `sed` |

### Why proto / gRPC
- Strict compile-time contract between frontend and backend. No type drift.
- ~10x faster serialization, ~2.5x smaller payloads vs JSON.
- Schema evolution via numbered field tags — add/remove fields without breaking old clients.
- AI tooling makes debugging binary payloads easy.

### Current RPCs

| RPC | What it does |
|-----|-------------|
| `CreateSatsangi` | Register new devotee → returns full record with generated ID |
| `SearchSatsangis` | ILIKE search across 12 fields |
| `ListSatsangis` | Paginated list (limit/offset), returns total_count |
| `Health` | Service liveness + DB connectivity check |

---

## Backend

| What | Choice | Version | Notes |
|------|--------|---------|-------|
| Language | Python | ≥3.12 | |
| gRPC server | grpcio (`grpc.aio`) | 1.78 | Fully async. No ThreadPoolExecutor. |
| gRPC reflection | grpcio-reflection | 1.78 | Enables grpcurl/grpcui/Postman discovery |
| Protobuf runtime | protobuf | 6.33 | |
| HTTP proxy | FastAPI | 0.135 | **Only** for grpc-web proxy + webhooks. No business logic here. |
| ASGI server | uvicorn | 0.41 | Single worker (in-process gRPC binds :50051) |
| DB driver | psycopg v3 (async, binary) | ≥3.2 | `psycopg[binary]` |
| DB pool | psycopg-pool (`AsyncConnectionPool`) | ≥3.2 | 2–20 conns, auto-recovery, retry on boot (5 attempts, 2s backoff) |
| Validation | Pydantic | 2.12 | Models for internal data, proto conversion in servicer |
| Linting | Ruff | 0.15 | Rules: E, F, I, UP. Line length 100. |
| Type checking | Pyright (strict) | — | `exclude: app/generated` |
| Task runner | taskipy | ≥1.14 | `uv run task dev` |
| Package manager | uv | latest | Lockfile: `uv.lock`. No pip/poetry. |

### Backend rules
- **FastAPI is a dumb proxy.** Core logic lives in gRPC servicers. FastAPI's job: translate grpc-web frames ↔ native gRPC. Period.
- **Generated code is isolated.** `app/generated/` — never edit, never put logic here.
- **All functions are async.** Proxy, servicer, store, DB pool — zero blocking calls on the event loop.
- **Identity serializers in proxy.** Raw protobuf bytes pass through without deserialize/re-serialize. Proxy only handles framing.
- **Strict type hints.** All function args and return types. `typing` module, `from __future__ import annotations`.
- **Connection pooling mandatory.** Every DB call goes through `get_conn()` → `AsyncConnectionPool`. Never raw `psycopg.connect()`.
- **Streaming for large datasets.** Don't load 50k rows into RAM. Use cursors + generators.
- **Background tasks >1–2s** must be decoupled from the request cycle (PG-backed queue, Phase 1).

### How the grpc-web proxy works (POC, in-process)
1. Browser sends ConnectRPC grpc-web-text (base64, 5-byte framed protobuf) via POST
2. FastAPI catch-all decodes frame, extracts raw protobuf bytes
3. Forwards to in-process gRPC server via async `channel.unary_unary()` with identity serializers
4. Wraps response in grpc-web DATA + TRAILER frames, base64-encodes, returns

Production plan: separate proxy and gRPC server into independent containers.

---

## Concurrency Model

### One process. One thread. One event loop. Zero threads.

```
┌─────────────────────────────────────────────────┐
│              Single Python Process               │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │           asyncio Event Loop              │   │
│  │                                           │   │
│  │  uvicorn (FastAPI proxy, :8080)           │   │
│  │  grpc.aio.server (servicer, :50051)       │   │
│  │  AsyncConnectionPool (2–20 DB conns)      │   │
│  │  grpc.aio.Channel (singleton, HTTP/2)     │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  CPU core: 1                                     │
│  OS threads: 1 (the main thread)                 │
│  ThreadPoolExecutor: NONE                        │
└─────────────────────────────────────────────────┘
```

**Async is not multi-threading.** There is exactly one OS thread running
Python code. The event loop achieves concurrency by **never blocking**:

1. Request A arrives, calls `await cur.execute(SQL)`.
2. The `await` **yields control** back to the event loop — A is now waiting
   for PostgreSQL to respond over the network.
3. The event loop picks up Request B, starts processing it.
4. When PostgreSQL responds to A, the loop resumes A where it left off.

This is **cooperative multitasking** — each coroutine voluntarily yields at
every `await` point. No preemption, no locks, no race conditions, no GIL
contention. The single thread is never idle as long as there's work to do.

### Why this works for us

Registration is **I/O-bound**: receive request → query DB → return response.
The CPU does almost nothing — it's waiting on network and disk. Async is
purpose-built for this. One core can handle thousands of concurrent I/O
operations because it's never waiting.

---

## DB Connection Pool — Borrow, Use, Return

```python
# db.py
_pool = AsyncConnectionPool(conninfo=..., min_size=2, max_size=20)
```

The pool maintains **2 to 20 persistent TCP connections** to PostgreSQL.
These connections are **not created or destroyed per request**. They are
long-lived and recycled.

### Lifecycle of a DB call

```
Request arrives
    │
    ▼
get_conn() — borrow a connection from the pool
    │
    ▼
await cur.execute(SQL) — send query, yield to event loop while waiting
    │
    ▼
await cur.fetchone() — read result
    │
    ▼
exit `async with` — connection returned to pool (NOT closed)
    │
    ▼
Connection is now free for the next request to borrow
```

### Key properties

| Property | Behavior |
|----------|----------|
| **Connections per request** | 1 borrowed, returned after use. NOT 1 created. |
| **Connection after use** | Returns to pool, stays alive. NOT destroyed. |
| **21st concurrent request** | Waits in queue until a connection is returned. |
| **Dead connection** | Pool detects and replaces it automatically. |
| **DB not ready at boot** | Pool retries 5 times with 2s exponential backoff. |

### Why not 1 connection per request?

Opening a TCP connection to PostgreSQL takes ~5–10ms (TLS handshake, auth).
With pooling, that cost is paid once at startup. Every subsequent request
borrows in ~0.01ms. At 1000 req/s, pooling saves ~5–10 **seconds** of
cumulative connection overhead per second.

### Why max=20?

PostgreSQL's default `max_connections` is 100. Each connection consumes ~10MB
of RAM on the DB server. 20 connections is plenty for 50–60 concurrent staff
members (most requests complete in <10ms, so connections are freed fast).
Increase to 50 if sustained load demands it, but beyond that consider
PgBouncer or read replicas.

---

## gRPC Channel — One Connection, Many RPCs

```python
# main.py
_channel = grpc.aio.insecure_channel(GRPC_TARGET)
```

This is a **single TCP connection** from the FastAPI proxy to the in-process
gRPC server. HTTP/2 **multiplexes** — every RPC is a separate "stream" on
that one connection:

```
proxy ──── 1 TCP conn (HTTP/2) ──── gRPC server
              stream #1: CreateSatsangi     ← concurrent
              stream #2: SearchSatsangis    ← concurrent
              stream #3: ListSatsangis      ← concurrent
              stream #4: Health             ← concurrent
              ... thousands at once
```

No need for multiple connections. HTTP/2 was designed for this — it
eliminates HTTP/1.1's head-of-line blocking problem entirely.

---

## CPU-Heavy Work — The One Thing Async Can't Do

If code does heavy **CPU computation** (encryption, PDF generation, image
processing, CSV parsing of 100k rows), it blocks the event loop. While the
CPU is crunching, **every other request is frozen**. The waiter is stuck
carrying a 200kg plate.

### Decision: We do NOT use `ProcessPoolExecutor`

`ProcessPoolExecutor` spawns separate Python **processes** for CPU work. It
bypasses the GIL and uses multiple cores. However, it brings complexity we
don't need:

| Footgun | Impact |
|---------|--------|
| **IPC overhead** | Data must be pickled/unpickled to cross process boundaries. Large payloads (e.g., 10MB document) are serialized twice. |
| **Memory duplication** | Each worker process is a full Python interpreter. 4 workers = 4× base memory. |
| **Startup cost** | Spawning a process is ~100ms. Not viable for latency-sensitive paths. |
| **Debugging** | Stack traces, logging, and profiling become fragmented across processes. |
| **Shared state** | No shared memory. Need `multiprocessing.Manager` or external store for coordination. |
| **Zombie processes** | Crashed workers need cleanup. OOM in a worker can leak resources. |

For our workload (occasional document encryption, not continuous ML
inference), this is overkill.

### Decision: Two tools, both simple

#### Tool 1: `asyncio.to_thread()` — For occasional CPU work (<5s)

```python
import asyncio

async def encrypt_and_store(document: bytes) -> str:
    # Runs in a *thread* — OS can schedule on another core
    encrypted = await asyncio.to_thread(encrypt_document, document)
    # Back on the event loop — store result in DB
    async with get_conn() as conn:
        await conn.execute("INSERT INTO ...", [encrypted])
    return "done"
```

- Built into Python 3.9+. Zero dependencies.
- Runs the function in a **thread** (from the default `ThreadPoolExecutor`).
- The OS can schedule that thread on any available CPU core.
- The event loop is **not blocked** — it continues serving other requests.
- The GIL is released during C-extension work (e.g., `cryptography` library,
  `hashlib`, `zlib` — all release the GIL internally).
- **Use for:** encryption, compression, hashing, image resize — anything
  where the heavy lifting happens in a C extension.

#### Tool 2: PostgreSQL-Backed Task Queue — For background jobs (>5s)

For work that shouldn't block the request at all — bulk CSV import, batch
encryption, ETL, report generation — push a task to the queue and return
immediately.

```sql
-- Schema
CREATE TABLE task_queue (
    id          BIGSERIAL PRIMARY KEY,
    task_type   TEXT NOT NULL,           -- 'encrypt_document', 'csv_import', etc.
    payload     JSONB NOT NULL,          -- task-specific data
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending → processing → done / failed
    result      JSONB,                   -- output data (optional)
    error       TEXT,                    -- error message if failed
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    claimed_at  TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

CREATE INDEX idx_task_queue_pending ON task_queue (id) WHERE status = 'pending';
```

```sql
-- Worker claims next task (atomic, skip locked = no double-processing)
UPDATE task_queue
SET    status = 'processing', claimed_at = NOW()
WHERE  id = (
    SELECT id FROM task_queue
    WHERE  status = 'pending'
    ORDER BY id
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
RETURNING *;
```

**How it works:**

```
gRPC Request                          Worker Process
    │                                      │
    ▼                                      │
INSERT INTO task_queue (...)               │
    │                                      │
    ▼                                      │
Return immediately to client               │
    (task_id for status polling)           │
                                           ▼
                              SELECT ... FOR UPDATE SKIP LOCKED
                                           │
                                           ▼
                                    Do heavy work (encrypt, ETL)
                                           │
                                           ▼
                              UPDATE task_queue SET status='done'
```

**The worker is a separate process** — a simple Python script running in its
own container/systemd unit. It polls `task_queue`, claims tasks, does the
work, writes results back. It runs on whatever CPU core the OS assigns.
The main event loop is never touched.

**No Celery, no Redis, no RabbitMQ.** Just PostgreSQL, which we already have.
ACID-compliant, survives crashes (unclaimed tasks stay `pending`), trivial
to monitor (`SELECT count(*) FROM task_queue WHERE status = 'pending'`).

**PostgreSQL extensions for this (optional, evaluate later):**

| Extension | What it adds |
|-----------|-------------|
| `pg_cron` | Schedule recurring tasks (e.g., nightly cleanup) inside PostgreSQL itself. No external cron. |
| `LISTEN/NOTIFY` | Push-based wakeup — worker sleeps until PG notifies "new task available." Eliminates polling. More efficient than sleep-poll loops. |
| `pgmq` | Full message queue semantics inside PG. Visibility timeouts, dead-letter queue, exactly-once delivery. Drop-in if our simple `FOR UPDATE SKIP LOCKED` isn't enough. |

For Phase 1, raw `FOR UPDATE SKIP LOCKED` + a polling worker is sufficient.
Add `LISTEN/NOTIFY` for efficiency when the worker is built. Evaluate `pgmq`
only if we need retry policies or dead-letter queues.

---

## Exposing REST APIs to Other Ashram Apps

### The scenario

Other internal ashram applications (e.g., accommodation system, prasad
distribution, event management) need to read satsangi data from our system.
They speak REST/JSON — they can't speak gRPC.

### Decision: REST endpoints live in the FastAPI layer

This is **exactly** what FastAPI is for in our architecture. The coding
standards (`005-coding-standards.md`) already say:

> FastAPI: Strictly limited to the grpc-web proxy and specific HTTP-only
> endpoints like Webhooks, **and REST to be used by FastAPI only on a need
> basis like exposing API to other apps.**

```
                    ┌─────────────────────────┐
                    │    FastAPI (:8080)       │
                    │                          │
 Browser ──────────►│  /jkp.registration.v1/* │──► gRPC server ──► DB
 (grpc-web)         │  (grpc-web proxy)        │
                    │                          │
 Other apps ───────►│  /api/v1/satsangis/*    │──► gRPC server ──► DB
 (REST/JSON)        │  (REST endpoints)        │
                    │                          │
                    └─────────────────────────┘
```

### How it works — REST routes call gRPC internally

```python
# main.py (or a dedicated rest_api.py)

@app.get("/api/v1/satsangis")
async def list_satsangis_rest(q: str = "", limit: int = 20, offset: int = 0):
    """REST endpoint for other internal apps."""
    if q:
        req = satsangi_pb2.SearchRequest(query=q)
        resp = await _stub.SearchSatsangis(req)
    else:
        req = satsangi_pb2.ListRequest(limit=limit, offset=offset)
        resp = await _stub.ListSatsangis(req)
    # Convert protobuf → JSON-serializable dict
    return {
        "satsangis": [MessageToDict(s) for s in resp.satsangis],
        "total_count": resp.total_count,
    }
```

**Key points:**

- REST routes are **thin wrappers** — they call gRPC internally, never
  touch the DB directly. Business logic stays in the gRPC servicer.
- The gRPC call goes through the **same async channel** (singleton,
  in-process). It's effectively a function call — no network hop.
- This runs on the **same event loop, same core, same process**. No extra
  cores needed just for REST.
- JSON serialization (`MessageToDict`) is lightweight CPU work — negligible.

### Does this need another core?

**No.** REST endpoints are I/O-bound (call gRPC → wait → return JSON). The
event loop handles them the same way it handles grpc-web requests. A few
dozen internal API consumers add negligible load compared to 50–60 browser
clients.

If an internal app hammers us with 10,000 req/s, then yes — add uvicorn
workers (`--workers N`) or rate-limit. But that's a bridge to cross later.

---

## Scaling Roadmap

### Phase 0 — Current (POC)

```
1 process, 1 event loop, 1 core
Capacity: ~1000–3000 req/s, ~200–500 concurrent users
```

Sufficient for: 50–60 staff across 4–5 ashrams. Easily handles the load.

### Phase 1 — Production

```
Same architecture + background worker process
├── Main process: proxy + gRPC + event loop (1 core)
├── Worker process: polls task_queue, does CPU work (1+ cores)
└── PostgreSQL: on separate server (Server B)
```

Add when: background jobs are needed (CSV import, document encryption, bulk
operations).

### Phase 2 — If We Outgrow One Core

```
Multiple uvicorn workers (--workers N)
├── Worker 1: proxy + gRPC on :8080/:50051
├── Worker 2: proxy + gRPC on :8080/:50052
├── ...
└── Caddy load-balances across workers
```

**Caveat:** Each worker is an independent process with its own gRPC server
on a different port. Caddy or an internal load balancer distributes requests.
DB pool is per-worker (so max_size should be reduced to avoid exhausting
PG's `max_connections`).

Add when: single-core CPU utilization consistently >80% under normal load.
Unlikely for our scale.

### Phase 3 — Horizontal (If Ever Needed)

```
Multiple containers across machines
├── Server A1: full stack (proxy + gRPC + worker)
├── Server A2: full stack (proxy + gRPC + worker)
└── Server B: PostgreSQL + MinIO (shared)
```

Add when: 10,000+ concurrent users or multi-region requirements. Not
expected for ashram registration.

---

## Database

| What | Choice | Notes |
|------|--------|-------|
| Engine | PostgreSQL | 17 (Alpine image in Docker) |
| Schema management | `CREATE TABLE IF NOT EXISTS` at app startup + `init.sql` for Docker | Alembic deferred to when first migration is needed |
| Search | ILIKE across 12 columns (POC). Target: `pg_trgm` + full-text search for fuzzy matching at scale |
| Indexes | name (lower), phone, email (partial) | |
| Connection | Env vars: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | App is DB-location-agnostic. Can swap to RDS with zero code changes. |
| Backups (target) | Automated `pg_dump` to secondary in-house server. WAL archiving as stretch goal. | |

---

## Infrastructure & Deployment

| What | Choice | Notes |
|------|--------|-------|
| Containers | Docker Compose | Separate compose files: app server vs DB server |
| Web server / TLS | Caddy 2 | Auto-TLS (internal CA for LAN, Let's Encrypt option). HTTP/3. Zstd+Gzip. Security headers (HSTS, CSP, X-Frame, etc). |
| Tunnel (POC) | Cloudflare Tunnel | For internet access during POC. Production uses site-to-site VPN instead. |
| Client image | Multi-stage: `oven/bun:1-alpine` → build → `caddy:2-alpine` (serves static) | |
| Server image | Multi-stage: `python:3.12-slim` + uv → build → `python:3.12-slim` + libpq5 | Runs as non-root `appuser` |
| CI/CD (target) | GitHub Actions → build images → push to registry. Deploy: manual pull on VPN server. | Hybrid: automated build, manual deploy. |

### Production topology (target)
- **Server A (Compute, stateless):** Caddy + grpc-web proxy + gRPC backend + Keycloak + background workers
- **Server B (Storage, stateful):** PostgreSQL + MinIO
- **Staging:** Single machine running the full stack. Not backed up.
- **Network:** Site-to-site VPN across 4–5 offices. App is invisible to public internet.

### Caddy responsibilities
- TLS termination (self-signed on LAN, Cloudflare on internet)
- Serve static React SPA from `/srv` with immutable cache headers on hashed assets
- Reverse proxy API traffic to backend with keepalive + health polling
- SPA fallback (`try_files {path} /index.html`)
- Security headers, rate limiting, body size limits

---

## Auth

| What | Choice | Notes |
|------|--------|-------|
| POC | Hardcoded client-side (`admin`/`admin123`, localStorage) | Not for production |
| Production | Keycloak (self-hosted, OIDC) | Free, no user limits, SSO hub for future apps |
| JWT validation | gRPC interceptor on backend | Proxy passes token through, backend validates |
| Public self-reg (Phase 2) | Firebase OTP | SMS verification, no Keycloak account needed |

---

## File Storage (Target)

| What | Choice | Notes |
|------|--------|-------|
| Engine | MinIO (self-hosted, S3-compatible) | On storage node |
| Upload path | Browser → pre-signed URL → direct PUT to MinIO | Bypasses Python backend entirely |
| URL generation | gRPC RPC returns pre-signed URL | Backend generates, client uploads directly |
| Backup | MinIO built-in mirroring to secondary server | |
| Budget | <200GB total for photos + ID proofs + Form C docs | |

---

## Testing

| Layer | Tool | What it covers |
|-------|------|----------------|
| Backend gRPC | pytest + grpcio | All RPCs directly against :50051 |
| Backend proxy | pytest + httpx | grpc-web framing, base64 encoding, error codes |
| Frontend API | vitest | `api.ts` integration through real running server |
| E2E | Playwright | Real browser — pages render, data loads, nav works, forms work |

### Test principles
- **No mocking.** Tests talk to running test servers. No fake DB, no fake gRPC.
- **Each layer tests its boundary.** pytest for Python, vitest for TS, Playwright for everything.
- **Fast.** Unit <5s, integration <15s, e2e <30s.
- **Isolated.** `tests/` dir never ships in production images (dockerignored).

---

## Dev Tooling

| Tool | What it does |
|------|-------------|
| `bun` | JS package manager + script runner. Replaces npm everywhere. |
| `uv` | Python package manager. Replaces pip/poetry. |
| `buf` | Protobuf codegen (TS). Remote plugin, no local protoc needed for TS. |
| `grpcio-tools` | Protobuf codegen (Python). Guarantees protobuf version compatibility. |
| `ruff` | Python lint + format + import sort. Single tool. |
| `pyright` | Python type checker. Strict mode. |
| `grpcui` | Browser GUI for gRPC. Like Swagger UI for gRPC. |
| `taskipy` | Python task runner (`uv run task dev`). |

---

## Dev Commands

```bash
# Frontend
cd client && bun run dev          # Vite dev server (:5174)
cd client && bun run build        # Production build

# Backend
cd server && uv run task dev      # FastAPI + gRPC (:8080 / :50051)

# Proto generation (both languages)
cd proto && ./generate

# Database (local dev)
docker compose -f docker-compose.db.yml up -d

# Full deploy
docker compose up -d --build

# Tests
cd tests && ../server/.venv/bin/python -m pytest backend/ -v
cd tests && bun run test:unit
cd tests && bun run test:e2e
cd tests && bun run test:all

# gRPC debugging
grpcurl -plaintext localhost:50051 list
```

---

## Decision Summary

| Decision | Choice | Reasoning |
|----------|--------|-----------|
| Concurrency model | Single-process async event loop | I/O-bound workload. No threads needed. Simplest correct solution. |
| DB connections | Pool (2–20), borrow/return | Amortize connection cost. Never create/destroy per request. |
| gRPC channel | Singleton, HTTP/2 multiplexed | One connection handles thousands of concurrent RPCs. |
| Occasional CPU work (<5s) | `asyncio.to_thread()` | Zero dependencies. OS schedules thread on free core. GIL released during C-extension work. |
| Background jobs (>5s) | PG-backed task queue (`FOR UPDATE SKIP LOCKED`) | Zero new infra. ACID. Separate worker process. |
| `ProcessPoolExecutor` | **Rejected** | IPC overhead, memory duplication, debugging complexity. Not justified for our workload. |
| Celery / Redis queue | **Rejected (Phase 1)** | Extra infra. PG queue is sufficient. Re-evaluate if we need retry policies or massive throughput. |
| REST API for other apps | FastAPI thin routes → gRPC internally | Same process, same event loop. No extra cores. Business logic stays in gRPC servicer. |
| Scaling path | Vertical first (workers), horizontal later | Single core handles our scale. Add workers only when CPU-bound. |

---

## What's Not Built Yet (Production Gaps)

- [ ] Real auth (Keycloak integration, JWT validation)
- [ ] Role-based access control (5 roles)
- [ ] Photo upload (MinIO + pre-signed URLs)
- [ ] Background job queue (PG-backed)
- [ ] pg_trgm / full-text search indexes
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Database migrations tooling (Alembic)
- [ ] Audit log
- [ ] Bulk import/export (CSV)
- [ ] Printer setup for ID card printing
- [ ] Sentry integration (frontend + backend)
