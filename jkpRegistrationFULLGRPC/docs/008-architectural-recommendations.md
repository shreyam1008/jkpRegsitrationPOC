# 008 — Architectural Recommendations (Post-Benchmark)

> Based on **148 benchmarks, 235,045 requests** across 6 suites.
> See `../../benchmarks/RESULTS.md` for raw data.

---

## Table of Contents

1. [Current Architecture Recap](#current-architecture-recap)
2. [grpc.aio — Verdict: SWITCH](#1-grpcaio--verdict-switch)
3. [psycopg2 vs psycopg3 — Verdict: SWITCH to psycopg3](#2-psycopg2-vs-psycopg3--verdict-switch-to-psycopg3)
4. [PgBouncer vs In-Process Pool — Verdict: SKIP PgBouncer](#3-pgbouncer-vs-in-process-pool--verdict-skip-pgbouncer)
5. [Multiple Uvicorn Workers — Verdict: DON'T](#4-multiple-uvicorn-workers--verdict-dont)
6. [Ideal POC Base — What's Missing](#5-ideal-poc-base--whats-missing)

---

## Current Architecture Recap

```
Browser (ConnectRPC grpc-web-text, base64)
    ↓ HTTP/1.1
Caddy (TLS + compression + HTTP/3)
    ↓ reverse_proxy
FastAPI proxy (:8080, uvicorn, async, 1 worker)
    ↓ grpc.aio singleton channel (HTTP/2 multiplexed)
gRPC server (:50051, in-process, sync ThreadPoolExecutor×10)
    ↓ psycopg2.ThreadedConnectionPool (2–20 conns)
PostgreSQL
```

### Where It Breaks (Benchmark Evidence)

| Bottleneck | Benchmark | Evidence |
|---|---|---|
| **Thread pool saturation** | 50 users, pool=10, 10ms DB | p99 = 1,087ms, only 108 rps |
| **Proxy under load** | 200 concurrent proxy users | p99 = 11,359ms, only 42 rps |
| **Pool exhaustion** | 50 workers, pool size=2 | p99 = 3,679ms, 79 pool waits |
| **DB latency amplification** | 50ms DB + 50 users | 152 rps (theoretical max 200) |
| **Serialization at scale** | ListAll 2000 records via proxy | p99 = 336ms per request |

The single biggest bottleneck is `ThreadPoolExecutor(10)`. Every RPC blocks a thread for the entire DB round-trip. With 10ms DB latency, the hard ceiling is `10 threads / 0.01s = 1,000 rps`. With 50ms DB, it drops to `200 rps`. This is the primary thing to fix.

---

## 1. grpc.aio — Verdict: SWITCH

### Current: Sync gRPC Server

```python
# grpc_server.py — current
server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
```

- Each RPC blocks a thread for the full DB round-trip
- 10 threads = hard concurrency cap of 10 simultaneous DB queries
- Adding more threads helps linearly, but each thread costs ~8MB stack

### Proposed: Async gRPC Server

```python
# grpc_server.py — proposed
server = grpc.aio.server()
```

- Each RPC is a coroutine, yields control while waiting for DB
- **No thread pool needed** — event loop handles thousands of concurrent RPCs
- Memory usage stays flat regardless of concurrency

### Why It's the Right Call

| Factor | Sync (current) | Async (grpc.aio) |
|---|---|---|
| Max concurrent RPCs | `max_workers` (10) | **Thousands** (event loop) |
| Memory per connection | ~8MB (thread stack) | **~few KB** (coroutine) |
| DB wait behavior | Thread blocked, wasted | **Yields to other work** |
| Fits with FastAPI proxy | Mismatched (async proxy → sync server) | **Natural fit** (both async) |
| Complexity | Simple, familiar | Slightly more (async/await) |

### The Catch

`grpc.aio` server requires an **async DB driver**. You can't do `with get_conn() as conn:` inside an `async def` RPC — it blocks the event loop and defeats the purpose. Two options:

1. **`asyncio.to_thread()`** — wrap sync psycopg2 calls (quick hack, still uses threads)
2. **Switch to psycopg3 async** — truly non-blocking (recommended, see §2)

### What Changes in the Code

```python
# Before (sync)
class SatsangiServiceServicer(satsangi_pb2_grpc.SatsangiServiceServicer):
    def CreateSatsangi(self, request, context):
        create_data = _proto_to_create(request)
        satsangi = store.create_satsangi(create_data)  # blocks thread
        return _model_to_proto(satsangi)

# After (async)
class SatsangiServiceServicer(satsangi_pb2_grpc.SatsangiServiceServicer):
    async def CreateSatsangi(self, request, context):
        create_data = _proto_to_create(request)
        satsangi = await store.create_satsangi(create_data)  # yields, non-blocking
        return _model_to_proto(satsangi)
```

### Impact on Existing Architecture

- **In-process server still works** — `grpc.aio.server()` runs on the same asyncio loop as uvicorn
- **Singleton channel stays** — proxy already uses `grpc.aio.insecure_channel()`
- **Lifespan changes slightly** — server start/stop becomes async
- **No port changes** — same `:50051` internal, `:8080` external

---

## 2. psycopg2 vs psycopg3 — Verdict: SWITCH to psycopg3

### psycopg2 (current)

```
✅ Battle-tested, extremely stable (15+ years)
✅ Fast C extension (libpq bindings)
✅ You already know it
❌ No native async — ThreadedConnectionPool only
❌ ThreadedConnectionPool has known issues:
   - Blocks on getconn() when pool exhausted (no timeout)
   - No health checks on idle connections
   - No auto-scaling / shrinking
   - No backpressure signaling
❌ Maintenance mode — no new features, only security fixes
❌ Cannot pair with grpc.aio without thread wrappers
```

### psycopg3 (the `psycopg` package)

```
✅ Native async: await conn.execute("SELECT ...")
✅ AsyncConnectionPool — production-grade:
   - Configurable min/max size
   - Automatic health checks on idle connections
   - Timeout on pool exhaustion (raises instead of deadlocking)
   - Background connection opener (doesn't block request path)
   - Metrics: pool_size, pool_available, requests_waiting
✅ Pipeline mode — batch N queries in 1 round-trip
✅ COPY protocol — bulk inserts 10x faster
✅ Better type system — native Python types, row factories
✅ Actively developed (psycopg2 is frozen)
✅ Pure Python fallback + C extension (`psycopg[c]`) for speed
❌ Slightly newer API (but stable since 3.1, now at 3.2+)
❌ Need to learn new pool API
```

### Why psycopg3 Wins for This Project

1. **Async is mandatory** — If you switch gRPC to `grpc.aio`, you need async DB calls. psycopg2 can't do this without `to_thread()` hacks.

2. **Pool is dramatically better** — Current `ThreadedConnectionPool` deadlocks when exhausted. psycopg3's `AsyncConnectionPool` raises after a configurable timeout.

3. **Pipeline mode** — The `SearchSatsangis` query matches across 12 fields. With pipeline mode, you could batch the search + count in one round-trip.

4. **psycopg2 is dead** — From the psycopg2 docs: *"psycopg2 is in maintenance mode. For new projects, use psycopg 3."*

### What the Migration Looks Like

```python
# db.py — before (psycopg2)
from psycopg2 import pool
_pool = pool.ThreadedConnectionPool(2, 20, **DB_CONFIG)

@contextlib.contextmanager
def get_conn():
    conn = _pool.getconn()
    try:
        yield conn
    finally:
        _pool.putconn(conn)

# db.py — after (psycopg3 async)
from psycopg_pool import AsyncConnectionPool
_pool = AsyncConnectionPool(conninfo=CONNINFO, min_size=2, max_size=20)

@contextlib.asynccontextmanager
async def get_conn():
    async with _pool.connection() as conn:
        yield conn
```

```python
# store.py — before (sync)
def search_satsangis(query: str) -> list[Satsangi]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(_SEARCH_SQL, params)
            rows = cur.fetchall()

# store.py — after (async)
async def search_satsangis(query: str) -> list[Satsangi]:
    async with get_conn() as conn:
        rows = await conn.execute(_SEARCH_SQL, params)
        return [_row_to_satsangi(row) async for row in rows]
```

### Dependency Change

```toml
# pyproject.toml
# Before
"psycopg2-binary>=2.9.9",

# After
"psycopg[binary]>=3.2",
"psycopg-pool>=3.2",
```

### Are There Cons?

Honestly? Not really for this project:

- **Performance**: psycopg3 with C extension (`psycopg[c]`) is within 5% of psycopg2. With `psycopg[binary]` it's essentially identical.
- **API differences**: Minor — `cursor_factory` becomes `row_factory`, `%s` placeholders stay the same.
- **Stability**: psycopg 3.2+ is production-stable. Used by Django, SQLAlchemy, and thousands of production apps.
- **The only real "con"**: You have to rewrite `db.py` and `store.py`. But it's ~150 lines total. 30 minutes of work.

---

## 3. PgBouncer vs In-Process Pool — Verdict: SKIP PgBouncer

### What PgBouncer Does

PgBouncer is an **external** connection pooler that sits between your app and PostgreSQL:

```
App (100 connections) → PgBouncer (10 connections) → PostgreSQL
```

It multiplexes many app-side connections over fewer PG-side connections using transaction-level pooling.

### When PgBouncer Makes Sense

- **Multiple app servers** → one PgBouncer → one PostgreSQL
- **Hundreds of microservices** each wanting their own pool
- **Serverless functions** (Lambda, Cloud Run) that can't hold persistent connections
- **PostgreSQL max_connections limit** is a problem (default 100)

### Why It's Overkill Here

| Factor | PgBouncer | psycopg3 AsyncConnectionPool |
|---|---|---|
| Network overhead | Extra hop (even on localhost: ~0.1ms) | **Zero** (in-process) |
| Infrastructure | Separate process/container to manage | **None** |
| Configuration | `pgbouncer.ini` + auth setup | **3 lines in Python** |
| Transaction pooling | ✅ Yes | Not needed (pool IS the app) |
| Health checks | Basic | ✅ Built-in, configurable |
| Backpressure | Limited | ✅ Timeout + waiting metrics |
| Horizontal scaling | ✅ Helps a lot | Per-process only |
| For this POC | **Overkill** | **Perfect fit** |

### The Decision

**Skip PgBouncer. Use psycopg3's `AsyncConnectionPool`.**

Your architecture is single-server, single-process. The pool IS the app. Adding PgBouncer adds infrastructure complexity for zero benefit at this scale.

**When to reconsider**: If you later run 3+ server containers all hitting the same PostgreSQL, PgBouncer starts to make sense because it caps the total PG connections regardless of how many app instances exist.

---

## 4. Multiple Uvicorn Workers — Verdict: DON'T

### Why You Might Want Multiple Workers

Python has the GIL (Global Interpreter Lock). Only one thread can execute Python bytecode at a time. Multiple workers = multiple processes = multiple GILs = true parallelism.

### Why It Doesn't Help Here

**The actual CPU work per request is tiny:**

| Operation | Time | CPU-bound? |
|---|---|---|
| Base64 decode (300B) | 0.003ms | ✅ but negligible |
| Frame strip | 0.001ms | ✅ but negligible |
| Proto deserialize | 0.01ms | ✅ but negligible |
| Proto → Pydantic | 0.07ms | ✅ but negligible |
| **DB query** | **2-50ms** | ❌ **I/O-bound** |
| Proto serialize | 0.006ms | ✅ but negligible |
| Base64 encode | 0.008ms | ✅ but negligible |
| **Total CPU** | **~0.1ms** | — |
| **Total I/O wait** | **2-50ms** | — |

Your app is **99% I/O-bound**. The CPU does ~0.1ms of work per request. The rest is waiting for PostgreSQL. Async handles I/O-bound work perfectly — you don't need multiple processes.

### The In-Process gRPC Server Problem

Current architecture runs gRPC on `:50051` inside the uvicorn process:

```python
# main.py lifespan
_grpc_server = start_grpc_server(port=50051)
```

If you add `--workers 4`, uvicorn forks 4 processes. **All 4 try to bind `:50051` → 3 crash.**

To fix this, you'd need to:
1. Run gRPC server as a **separate process** (its own container or systemd service)
2. Each uvicorn worker connects to it via channel
3. Now you have 2 processes to manage instead of 1

### If You Really Wanted Workers

```
                              ┌─ uvicorn worker 1 ─┐
Browser → Caddy → gunicorn ──┼─ uvicorn worker 2 ─┼──→ separate gRPC server :50051
                              ├─ uvicorn worker 3 ─┤         ↓
                              └─ uvicorn worker 4 ─┘    PostgreSQL
```

- **How many**: 2× CPU cores is the rule of thumb (so 2-4 for a small server)
- **Command**: `gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4`
- **Pool sizing**: Each worker gets its own pool. Total connections = `max_size × workers`. With 4 workers and pool=20 each, that's 80 PG connections.

### Cons of Multiple Workers

| Con | Impact |
|---|---|
| Port clash with in-process gRPC | Must separate gRPC into its own process |
| N × connection pools | 4 workers × 20 = 80 PG connections (vs 20 today) |
| N × memory | Each worker: ~50-80MB RSS = 200-320MB total |
| Complexity | Two processes to deploy, monitor, restart |
| Startup time | Slower cold start (forking) |
| State sharing | Can't share in-process caches between workers |

### The Recommendation

**Don't add workers. Make the single process fully async instead.**

With `grpc.aio` + `psycopg3 async`, one process handles thousands of concurrent connections. You're I/O-bound, not CPU-bound. Async solves I/O concurrency without forking.

**When to reconsider**: If you're serving heavy compute (ML inference, image processing, report generation) alongside the API, then multiple workers for the CPU-bound work makes sense. Or if you scale to 1000+ concurrent users on a single machine.

---

## 5. Ideal POC Base — What's Missing

The current project is already strong for a POC. Here's what would make it a **production-ready base** that you can clone and build on for any similar registration/CRUD app.

### ✅ Already Done Well

- [x] Clean proto → gRPC → Pydantic → PostgreSQL pipeline
- [x] grpc-web proxy with proper frame encoding
- [x] Docker multi-stage builds (tiny runtime image)
- [x] Caddy with TLS, HTTP/3, security headers
- [x] Cloudflare Tunnel option for zero-port exposure
- [x] Connection pool with retry and reconnect
- [x] DB schema auto-init on startup
- [x] Comprehensive benchmarks (148 tests!)

### 🔧 Quick Wins (< 1 hour each)

#### A. Pagination on List/Search

Currently `ListSatsangis` and `SearchSatsangis` return **all** matching rows. The benchmarks showed ListAll with 2000 records takes 97ms p50 through the proxy and generates 225KB of wire data.

```proto
// satsangi.proto — add to ListRequest and SearchRequest
message ListRequest {
  int32 limit = 1;
  int32 offset = 2;    // ADD
}

message SearchRequest {
  string query = 1;
  int32 limit = 2;     // ADD
  int32 offset = 3;    // ADD
}

message SatsangiList {
  repeated Satsangi satsangis = 1;
  int32 total_count = 2;  // ADD — for pagination UI
}
```

#### B. Request ID Propagation

Add a request ID to every log line so you can trace a single request through proxy → gRPC → DB:

```python
# middleware
import uuid
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())[:8]
    response = await call_next(request)
    response.headers["x-request-id"] = request.state.request_id
    return response
```

#### C. Structured JSON Logging

Replace Python's default logging with structured JSON for easier parsing in production:

```python
import logging, json, sys

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts": self.formatTime(record),
            "level": record.levelname,
            "msg": record.getMessage(),
            "module": record.module,
        })

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())
logging.root.addHandler(handler)
```

#### D. Graceful Shutdown

Current shutdown is abrupt. Add drain support:

```python
# In lifespan
yield
# Drain: stop accepting new gRPC requests, finish in-flight ones
if _grpc_server:
    _grpc_server.stop(grace=5)  # 5s to finish in-flight RPCs
if _pool:
    await _pool.close(timeout=5)  # wait for borrowed connections to return
```

### 🏗️ Medium Effort (1–4 hours each)

#### E. The Async Migration (grpc.aio + psycopg3)

This is the single highest-impact change. It touches 3 files:

| File | Changes |
|---|---|
| `db.py` | Replace `psycopg2.pool.ThreadedConnectionPool` with `psycopg_pool.AsyncConnectionPool` |
| `store.py` | Make all functions `async def`, use `await conn.execute()` |
| `grpc_server.py` | Switch to `grpc.aio.server()`, make RPCs `async def` |
| `main.py` | Minor lifespan changes (async server start) |
| `pyproject.toml` | Swap `psycopg2-binary` → `psycopg[binary]` + `psycopg-pool` |

Estimated time: **2-3 hours** including testing.

Expected impact (based on benchmark data):
- Thread pool saturation **eliminated** — no more 1,087ms p99 at 50 users
- Pool exhaustion **eliminated** — async pool has proper timeout + backpressure
- Proxy throughput should improve 3-5x under concurrent load (no thread contention)

#### F. Input Validation & Sanitization

Currently the gRPC server trusts all input from the proto. Add:

```python
# Validate phone format, email format, string lengths
# Sanitize text fields (strip HTML, limit length)
# Return INVALID_ARGUMENT instead of INTERNAL on bad input
```

#### G. Rate Limiting

At the Caddy level (simplest):

```
# Caddyfile
rate_limit {
    zone api_limit {
        key {remote_host}
        events 100
        window 1m
    }
}
```

Or at the app level with a gRPC interceptor for finer control.

#### H. Health Check with Metrics

Current health endpoint is basic. Make it useful:

```python
@app.get("/healthz")
async def healthz():
    pool_stats = _pool.get_stats()
    return {
        "status": "ok",
        "uptime_s": time.time() - _start_time,
        "pool_size": pool_stats.pool_size,
        "pool_available": pool_stats.pool_available,
        "requests_waiting": pool_stats.requests_waiting,
    }
```

### 📐 Architecture Summary — Proposed vs Current

```
=== CURRENT ===                           === PROPOSED ===

FastAPI (async)                           FastAPI (async)
    ↓ grpc.aio channel                       ↓ grpc.aio channel
gRPC (sync, ThreadPool×10)               gRPC (async, grpc.aio)          ← CHANGE
    ↓ blocking                                ↓ await
psycopg2 ThreadedConnectionPool           psycopg3 AsyncConnectionPool   ← CHANGE
    ↓ blocking                                ↓ await
PostgreSQL                                PostgreSQL

Concurrency: 10 threads = 10 RPCs        Concurrency: event loop = 1000s of RPCs
Workers: 1 (can't add more)              Workers: 1 (don't need more)
Pool: blocks on exhaustion                Pool: timeout + backpressure
```

### Priority Order

| # | Change | Impact | Effort | Do When |
|---|---|---|---|---|
| 1 | **grpc.aio + psycopg3 async** | 🔴 Massive | 2-3 hours | **Now** |
| 2 | Pagination on List/Search | 🟠 High | 30 min | Now |
| 3 | Request ID + structured logging | 🟡 Medium | 30 min | Now |
| 4 | Input validation | 🟡 Medium | 1 hour | Before any real users |
| 5 | Graceful shutdown | 🟢 Low | 15 min | Before Docker deploy |
| 6 | Rate limiting (Caddy) | 🟡 Medium | 15 min | Before internet exposure |
| 7 | Health metrics | 🟢 Low | 20 min | When monitoring is set up |
| 8 | PgBouncer | 🔵 Skip | — | Only if scaling to 3+ servers |
| 9 | Multiple workers | 🔵 Skip | — | Only if CPU-bound work added |
