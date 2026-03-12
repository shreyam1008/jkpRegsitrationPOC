# Benchmark Results: REST vs Partial gRPC vs Full gRPC + PostgreSQL

**Date**: 2026-03-12
**Machine**: Linux (local dev)
**Test**: 200 requests per operation, sequential (single client)
**Tool**: `bench_all.py` — measures end-to-end HTTP latency as the browser would see it

---

## Understanding the 3 Implementations

### Architecture Diagrams

```
1. REST (jkpRegsitrationPOC)
   ┌─────────┐   HTTP/JSON   ┌─────────┐   Python    ┌───────────┐
   │ Browser  │ ────────────► │ FastAPI  │ ──────────► │ JSON file │
   └─────────┘               │  :8000   │             └───────────┘
                              └─────────┘
   Hops: 1 (Browser → Server)
   Storage: JSON file on disk

2. Partial gRPC (jkpRegsitrationPOCgrpc)
   ┌─────────┐   HTTP/JSON   ┌─────────┐  gRPC/Proto  ┌──────────┐  Python   ┌───────────┐
   │ Browser  │ ────────────► │ FastAPI  │ ───────────► │   gRPC   │ ────────► │ JSON file │
   └─────────┘               │ Gateway  │              │  Server  │           └───────────┘
                              │  :8000   │              │  :50051  │
                              └─────────┘              └──────────┘
   Hops: 2 (Browser → Gateway → gRPC Server)
   Storage: JSON file on disk

3. Full gRPC + PostgreSQL (jkpRegistrationFULLGRPC)
   ┌─────────┐   HTTP/JSON   ┌─────────┐  gRPC/Proto  ┌──────────┐   SQL    ┌────────────┐
   │ Browser  │ ────────────► │ FastAPI  │ ───────────► │   gRPC   │ ───────► │ PostgreSQL │
   └─────────┘               │ Gateway  │              │  Server  │          │   :5432    │
                              │  :8000   │              │  :50051  │          └────────────┘
                              └─────────┘              └──────────┘
   Hops: 3 (Browser → Gateway → gRPC Server → PostgreSQL)
   Storage: PostgreSQL database
```

### Key Insight: Where Is gRPC?

**gRPC is NOT between the browser and the server.** In both gRPC implementations, the browser still speaks plain HTTP/JSON (REST). gRPC is used **only** as the internal communication protocol between the FastAPI gateway and the gRPC backend server.

Browsers **cannot** speak native gRPC because:
- gRPC requires HTTP/2 binary framing with trailers
- Browser `fetch()` API doesn't expose raw HTTP/2 frames
- Browsers enforce CORS, which gRPC doesn't natively handle

To make browsers talk gRPC directly, you'd need **gRPC-Web** + an Envoy proxy — a different architecture entirely.

### What's Actually Different Between #2 and #3?

| Aspect | Partial gRPC | Full gRPC + PG |
|--------|-------------|----------------|
| Browser → Gateway protocol | HTTP/JSON (same) | HTTP/JSON (same) |
| Gateway → Server protocol | gRPC/Protobuf (same) | gRPC/Protobuf (same) |
| Storage backend | JSON file | **PostgreSQL** |
| Data durability | File on disk (fragile) | **ACID database** |
| Search | Python string matching | **SQL ILIKE queries** |
| Concurrency safety | No (file locking issues) | **Yes (PG handles it)** |

**The gRPC layer is identical.** The only real difference is the storage backend.

---

## Benchmark Results (200 requests each, as seen by the browser)

### 1. CREATE Latency

| Metric | REST | Partial gRPC (JSON) | Full gRPC + PG | Notes |
|--------|------|---------------------|----------------|-------|
| Median | **5.83 ms** | 8.80 ms | 19.18 ms | REST fastest (fewest hops) |
| Mean | **6.16 ms** | 8.86 ms | 21.23 ms | |
| p95 | **10.70 ms** | 14.91 ms | 28.07 ms | |
| p99 | **18.66 ms** | 22.76 ms | 56.85 ms | PG has occasional slow queries |
| Min | **1.95 ms** | 3.58 ms | 17.46 ms | |
| Max | **26.17 ms** | 29.16 ms | 63.04 ms | |

### 2. SEARCH Latency

| Metric | REST | Partial gRPC (JSON) | Full gRPC + PG | Notes |
|--------|------|---------------------|----------------|-------|
| Median | **5.45 ms** | 11.01 ms | 31.96 ms | |
| Mean | **6.15 ms** | 12.55 ms | 33.09 ms | |
| p95 | **11.24 ms** | 23.11 ms | 46.58 ms | |
| p99 | **14.52 ms** | 32.28 ms | 74.67 ms | |
| Min | **4.21 ms** | 5.79 ms | 18.23 ms | |
| Max | **19.20 ms** | 38.84 ms | 88.67 ms | |

### 3. LIST ALL Latency

| Metric | REST | Partial gRPC (JSON) | Full gRPC + PG |
|--------|------|---------------------|----------------|
| Median | **5.61 ms** | 11.87 ms | 32.79 ms |
| Avg response size | 141,201 B | 141,201 B | 142,401 B |

### 4. Throughput (200 sequential creates, burst)

| Metric | REST | Partial gRPC (JSON) | Full gRPC + PG |
|--------|------|---------------------|----------------|
| Requests/sec | 49.4 | **54.1** | 46.5 |
| Total time | 4.05 s | **3.70 s** | 4.30 s |

### 5. Payload Size (HTTP layer, as seen by browser)

| Metric | REST | Partial gRPC (JSON) | Full gRPC + PG |
|--------|------|---------------------|----------------|
| Request body | 248 B | 248 B | 248 B |
| Response (1 create) | 705 B | 705 B | 711 B |
| Search response (avg) | 121,433 B | 121,433 B | 122,465 B |

**All identical!** Because the browser always sees HTTP/JSON. The protobuf encoding only happens internally between gateway ↔ gRPC server — it's invisible to the benchmark client.

---

## Why REST "Wins" These Benchmarks

This is expected and honest. Here's why:

### REST is fastest because it has the fewest hops

```
REST:         Browser → FastAPI → JSON file              (1 hop)
Partial gRPC: Browser → FastAPI → gRPC → JSON file       (2 hops)
Full gRPC+PG: Browser → FastAPI → gRPC → PostgreSQL      (3 hops, + network to PG)
```

Every hop adds:
- **Serialization**: JSON → Protobuf → JSON (encode + decode at gateway)
- **Network**: localhost TCP connection to gRPC server
- **Context switching**: between FastAPI async loop and gRPC thread pool

### Full gRPC+PG is slowest because PostgreSQL is doing real work

- JSON file: read entire file into memory, append, write back (fast for small data)
- PostgreSQL: parse SQL, plan query, execute, return results via TCP (proper database work)

**But this changes completely at scale:**

| Data Size | JSON File | PostgreSQL |
|-----------|-----------|------------|
| 100 records | Fast ✅ | Slower ❌ |
| 10,000 records | Very slow ❌ | Fast ✅ |
| 1,000,000 records | Crashes ❌ | Still fast ✅ |
| Concurrent writes | Data corruption ❌ | Safe ✅ |
| Power failure | Data loss ❌ | ACID safe ✅ |

---

## When Does gRPC Actually Help?

### ❌ NOT in this setup (single server, browser client)

In our setup, gRPC adds overhead because:
1. Browser can't speak gRPC — needs a REST gateway (extra hop)
2. Everything runs on localhost — no network latency to save
3. Single server — no microservice communication

### ✅ In real microservice architectures

```
                    ┌─────────────┐
                    │ Auth Service │
                    └──────▲──────┘
                           │ gRPC (fast, typed, binary)
┌─────────┐  REST   ┌─────┴─────┐  gRPC   ┌──────────────┐
│ Browser  │ ──────► │  API GW   │ ──────► │ User Service  │
└─────────┘         └─────┬─────┘         └──────┬───────┘
                          │ gRPC                  │ gRPC
                    ┌─────▼─────┐          ┌─────▼───────┐
                    │ Log Svc   │          │ Payment Svc  │
                    └───────────┘          └─────────────┘
```

Here, gRPC saves time on **every internal call** because:
- **No JSON overhead**: Binary protobuf is 3x smaller, 10x faster to serialize
- **HTTP/2 multiplexing**: Multiple concurrent RPCs on one connection
- **Type safety**: `.proto` contract prevents breaking changes across teams
- **Streaming**: Server-push, bidirectional streaming for real-time data
- **Connection reuse**: HTTP/2 persistent connections (no TCP handshake per request)

### The Right Way to Think About It

| Layer | Best Protocol | Why |
|-------|---------------|-----|
| Browser → Server | **REST/HTTP** | Browsers only speak HTTP, caching, CORS |
| Server → Server | **gRPC** | Speed, type safety, streaming, binary |
| Server → Database | **SQL/Driver** | Native database protocol |

---

## Summary: All 3 Compared

| Category | REST | Partial gRPC | Full gRPC + PG | Best for Production |
|----------|------|-------------|----------------|---------------------|
| CREATE median | **5.83 ms** | 8.80 ms | 19.18 ms | — |
| SEARCH median | **5.45 ms** | 11.01 ms | 31.96 ms | — |
| Throughput | 49.4 rps | **54.1 rps** | 46.5 rps | — |
| Payload (browser sees) | 248/705 B | 248/705 B | 248/711 B | Identical |
| Data durability | ❌ JSON file | ❌ JSON file | ✅ **PostgreSQL** | **Full gRPC + PG** |
| Concurrent safety | ❌ No | ❌ No | ✅ **ACID** | **Full gRPC + PG** |
| Scales to 1M records | ❌ No | ❌ No | ✅ **Yes** | **Full gRPC + PG** |
| Type-safe contracts | ❌ No | ✅ Protobuf | ✅ Protobuf | **gRPC variants** |
| Microservice-ready | ❌ No | ✅ Yes | ✅ **Yes** | **Full gRPC + PG** |
| Simplicity | ✅ **Simplest** | Medium | Complex | REST (for simple apps) |

### Bottom Line

- **For a simple app with a browser**: REST is the simplest and fastest
- **For production with real data**: Full gRPC + PostgreSQL is the right choice (durability, concurrency, scalability)
- **For microservices**: gRPC between services is the industry standard (Google, Netflix, Uber all use it)
- **The partial gRPC**: Has the downsides of both (gRPC overhead + JSON file fragility) — exists only as a learning step
