# Concurrency Model, CPU Offloading & Scaling Strategy

Last updated: 26 March 2026
Status: Living document — update as decisions evolve.

---

## 1. The Async Model — What We Actually Have

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

## 2. The DB Connection Pool — Borrow, Use, Return

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

## 3. The gRPC Channel — One Connection, Many RPCs

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

## 4. CPU-Heavy Work — The One Thing Async Can't Do

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

## 5. Exposing REST APIs to Other Ashram Apps

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

## 6. Scaling Roadmap

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

## 7. Decision Summary

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
