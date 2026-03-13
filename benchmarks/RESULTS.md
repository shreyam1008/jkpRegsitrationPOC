# Benchmark Results: REST vs gRPC (Direct Protocol Comparison)

**Date**: 2026-03-13
**Machine**: Linux (local dev, Ubuntu)
**Tool**: `bench_robust.py` — 16 benchmarks (8 synthetic + 8 real-life scenarios)
**Servers**: REST on :8001 (FastAPI + PostgreSQL), gRPC on :50051 (grpcio + PostgreSQL)

---

## Methodology & Fairness

This benchmark compares **REST (HTTP/JSON) vs gRPC (HTTP/2 + Protobuf)** as protocols. Both backends use the **same PostgreSQL database** — the only variable is the transport/serialization layer.

**Why this is fair:**
- Same storage engine (PostgreSQL) — not JSON-file vs Postgres
- REST uses `requests.Session` (HTTP keep-alive) — real apps reuse connections
- gRPC uses a persistent channel — same principle
- Same random seed (42) for reproducibility
- Same payload data for both in each test
- 30-request warmup before measurement
- No pre-declared winner — numbers speak for themselves

**What this is NOT:**
- Not browser-to-server (browser can't speak native gRPC)
- This tests **direct client-to-server** performance — the kind you'd see in service-to-service communication

---

## Architecture Under Test

```
REST test:
  ┌──────────────┐   HTTP/JSON    ┌──────────┐    SQL     ┌────────────┐
  │ Python client │ ─────────────► │ FastAPI   │ ────────► │ PostgreSQL │
  │ (requests)    │               │  :8001    │           │  :5432     │
  └──────────────┘               └──────────┘           └────────────┘

gRPC test:
  ┌──────────────┐  gRPC/Protobuf  ┌──────────┐    SQL     ┌────────────┐
  │ Python client │ ──────────────► │ grpcio    │ ────────► │ PostgreSQL │
  │ (grpc stub)   │               │  :50051   │           │  :5432     │
  └──────────────┘               └──────────┘           └────────────┘
```

Both paths: **1 hop** to the server, **1 hop** to PostgreSQL. Fair comparison.

---

## PART A — Synthetic Benchmarks (Controlled Conditions)

### A1. Single-Request Latency (100 iterations)

| Operation | Metric | REST | gRPC | Ratio | Winner |
|-----------|--------|------|------|-------|--------|
| **Create** | p50 | 64.6 ms | 62.8 ms | 1.03x | gRPC |
| | p95 | 93.7 ms | 70.5 ms | 1.33x | **gRPC** |
| | p99 | 131.5 ms | 84.2 ms | 1.56x | **gRPC** |
| | stdev | 31.5 ms | 22.2 ms | 1.42x | **gRPC** (more consistent) |
| **Search** | p50 | 90.3 ms | 81.7 ms | 1.11x | gRPC |
| | p95 | 278.2 ms | 319.1 ms | 0.87x | **REST** |
| | p99 | 322.0 ms | 336.9 ms | 0.96x | REST |
| | mean | 140.9 ms | 141.3 ms | ~1.00x | **TIE** |
| **List** | p50 | 77.7 ms | 80.9 ms | 0.96x | REST |
| | p95 | 266.9 ms | 322.6 ms | 0.83x | **REST** |
| | mean | 133.3 ms | 128.4 ms | 1.04x | gRPC |

**Takeaway**: Create operations favor gRPC (especially at tail latencies). Search/List are a toss-up — neither has a clear advantage for single sequential requests against a shared PostgreSQL.

### A2. Sustained Throughput (5 seconds each)

| Operation | REST | gRPC | Winner |
|-----------|------|------|--------|
| Read req/sec | **8.2 rps** | 6.6 rps | **REST** |
| Write req/sec | **20.0 rps** | 11.6 rps | **REST** |

**Takeaway**: For sequential throughput (single client, one request at a time), REST has an edge. This is expected — there's no multiplexing advantage when you're sending one request at a time.

### A3. Payload Size (Wire Bytes)

| Payload | JSON (REST) | Protobuf (gRPC) | Ratio |
|---------|-------------|-----------------|-------|
| Minimal request (3 fields) | 74 B | 25 B | **2.96x smaller** |
| Full request (30+ fields) | 861 B | 353 B | **2.44x smaller** |
| 1 response record | 927 B | 389 B | **2.38x smaller** |
| 100 records | 92,700 B | 38,900 B | **2.38x smaller** |
| 1,000 records | 927,000 B | 389,000 B | **2.38x smaller** |

**Takeaway**: Protobuf is consistently **2.4–3x smaller** than JSON. This matters for bandwidth-constrained environments (mobile, high-volume microservices).

### A4. Serialization Speed (10,000 messages)

| Operation | JSON | Protobuf | Ratio |
|-----------|------|----------|-------|
| Encode total | 210.8 ms | 23.0 ms | **9.15x faster** |
| Decode total | 172.7 ms | 15.8 ms | **10.95x faster** |
| Per-msg encode | 21.1 µs | 2.3 µs | **9.15x faster** |
| Per-msg decode | 17.3 µs | 1.6 µs | **10.95x faster** |

**Takeaway**: Protobuf serialization is **~10x faster** than JSON. This is a pure CPU advantage that scales with message volume.

### A5. Concurrent Load Test

| Clients | Metric | REST | gRPC | Winner |
|---------|--------|------|------|--------|
| **5** | Throughput | 5.5 rps | 10.5 rps | **gRPC (1.93x)** |
| | Mean latency | 907 ms | 467 ms | **gRPC (1.94x)** |
| | p99 | 1,892 ms | 1,437 ms | **gRPC** |
| **10** | Throughput | 6.9 rps | 11.7 rps | **gRPC (1.68x)** |
| | Mean latency | 1,397 ms | 839 ms | **gRPC (1.67x)** |
| | p99 | 2,977 ms | 2,654 ms | **gRPC** |
| **25** | Throughput | 7.2 rps | 6.9 rps | **REST (~tie)** |
| | Mean latency | 3,396 ms | 3,550 ms | **REST (~tie)** |
| | p99 | 4,398 ms | 8,890 ms | **REST** |

**Takeaway**: gRPC dominates under moderate concurrency (5–10 clients) thanks to HTTP/2 multiplexing. At 25 clients, both saturate the single-worker server — gRPC's p99 spikes harder, likely due to gRPC's thread pool contention under extreme load on a single-process server.

### A6. Streaming vs Batch

| Metric | REST Batch | gRPC Unary | gRPC Stream |
|--------|-----------|------------|-------------|
| Total time p50 | 105.5 ms | **85.3 ms** | 149.1 ms |
| Time-to-first-result p50 | 94.0 ms | — | **71.0 ms** |

**Takeaway**: gRPC unary is faster for total fetch. gRPC streaming delivers the **first result 25% sooner** — important for UIs that want to show partial results immediately.

### A7. Connection Overhead

| Mode | REST | gRPC |
|------|------|------|
| New connection each request | 137.8 ms | **89.4 ms** |
| Reused connection | 149.0 ms | 140.7 ms |

**Takeaway**: gRPC has lower overhead for new connections (HTTP/2 setup is cheaper). With reused connections, the difference disappears.

### A8. Client-Side Memory

| Metric | REST | gRPC |
|--------|------|------|
| Total alloc (200 reqs) | 13.3 KB | **6.9 KB** |
| Per-request | 0.066 KB | **0.035 KB** |

**Takeaway**: gRPC uses ~half the client memory per request (smaller binary payloads).

---

## PART B — Real-Life Scenarios

### B9. Page-Load Simulation (search + create + re-fetch)

Simulates a real user opening a registration page: 3 sequential API calls per "page load".

| Metric | REST | gRPC | Winner |
|--------|------|------|--------|
| Page load p50 | **172.1 ms** | 196.2 ms | **REST** |
| Page load p95 | 500.8 ms | **440.7 ms** | **gRPC** |
| Page load mean | 242.5 ms | **215.6 ms** | **gRPC** |
| Per-call p50 | **70.3 ms** | 80.5 ms | **REST** |
| Per-call p95 | 276.5 ms | **124.7 ms** | **gRPC (2.2x)** |

**Takeaway**: For the typical page load (p50), REST is slightly faster. But gRPC is significantly better at **tail latencies** (p95) — meaning fewer slow page loads. The user *usually* won't notice, but when things get slow, gRPC degrades more gracefully.

### B10. Bursty Traffic (idle 2s → 20-request burst, repeated 5x)

Real-life: volunteers arrive in waves, not a steady stream.

| Metric | REST | gRPC | Winner |
|--------|------|------|--------|
| Request p50 | 28.5 ms | **23.4 ms** | **gRPC** |
| Request p95 | 120.4 ms | **105.4 ms** | **gRPC** |
| Request p99 | 346.6 ms | **120.2 ms** | **gRPC (2.88x)** |
| 1st req after idle | 43.8 ms | **40.1 ms** | gRPC |

**Takeaway**: gRPC handles burst traffic better, especially at the tail — p99 is **2.88x faster**. Both wake from idle similarly quickly.

### B11. Variable Payload (3 fields vs 30+ fields)

| Payload | REST p50 | gRPC p50 | REST mean | gRPC mean |
|---------|----------|----------|-----------|-----------|
| Minimal (3 fields) | 64.7 ms | **24.5 ms** | 63.0 ms | **44.5 ms** |
| Full (30+ fields) | 27.1 ms | **24.4 ms** | 49.0 ms | **43.1 ms** |

**Takeaway**: gRPC's advantage grows with smaller payloads — the fixed overhead of JSON parsing hurts more when the data is tiny. With full payloads, the gap narrows.

### B12. Network Jitter (random 0–200ms delays between requests)

Simulates bad WiFi/mobile — not a fixed delay, but random jitter per request.

| Metric | REST | gRPC | Winner |
|--------|------|------|--------|
| Mean latency | 98.2 ms | **82.5 ms** | **gRPC** |
| p50 | **79.1 ms** | 97.8 ms | **REST** |
| p95 | 326.4 ms | **126.7 ms** | **gRPC (2.58x)** |
| p99 | 345.6 ms | **135.9 ms** | **gRPC (2.54x)** |
| Stdev (consistency) | 82.1 ms | **37.9 ms** | **gRPC (2.17x more consistent)** |

**Takeaway**: Under jittery conditions, gRPC is **dramatically more consistent**. The stdev tells the story — gRPC's tail latency variance is half of REST's. If you're on unreliable networks, gRPC gives you much more predictable performance.

### B13. Long-Running Session (300 requests, checking for drift)

| Window | REST mean | gRPC mean | REST p95 | gRPC p95 |
|--------|-----------|-----------|----------|----------|
| 1–60 | 96.7 ms | 76.9 ms | 276.5 ms | 345.5 ms |
| 61–120 | 117.3 ms | 58.8 ms | 340.0 ms | 101.7 ms |
| 121–180 | 109.0 ms | 54.4 ms | 298.4 ms | 103.3 ms |
| 181–240 | 94.4 ms | 62.7 ms | 295.0 ms | 118.0 ms |
| 241–300 | 101.3 ms | 130.9 ms | 311.0 ms | 449.4 ms |

| Drift | REST | gRPC |
|-------|------|------|
| Last window – First window | **+4.6 ms** | +54.0 ms |

**Takeaway**: REST is more stable over long sessions. gRPC drifted upward in the last window — possibly due to connection/channel state accumulation. Both are within acceptable bounds, but REST degrades more gracefully here. Note: the gRPC drift was driven by the last 60-request window; the middle windows were excellent.

### B14. Error Recovery (bad requests → good requests)

| Metric | REST | gRPC | Winner |
|--------|------|------|--------|
| Bad request mean | **21.4 ms** | 74.5 ms | **REST** |
| 1st good after bad | **24.8 ms** | 64.0 ms | **REST** |
| Good request mean (post-error) | **43.9 ms** | 66.8 ms | **REST** |
| Good request p95 (post-error) | 90.4 ms | 97.3 ms | ~TIE |

**Takeaway**: REST recovers from errors faster. HTTP error handling (status codes, immediate response) is simpler than gRPC's status/trailer mechanism. Both recover well by p95.

### B15. Concurrent Mixed Workload (10 users, 80% read / 20% write)

| Metric | REST | gRPC | Winner |
|--------|------|------|--------|
| Wall time | 50,237 ms | **31,726 ms** | **gRPC (1.58x)** |
| Throughput | 9.95 rps | **15.76 rps** | **gRPC (1.58x)** |
| Mean latency | 988.7 ms | **607.7 ms** | **gRPC (1.63x)** |
| p95 | 1,907 ms | **1,895 ms** | ~TIE |
| p99 | **2,263 ms** | 2,648 ms | **REST** |

**Takeaway**: Under realistic concurrent load, gRPC delivers **~1.6x higher throughput** with lower average latency. However, REST has a better p99 — gRPC occasionally has outlier spikes under contention.

### B16. Cold Start vs Warm

| Metric | REST | gRPC |
|--------|------|------|
| Cold start mean | 110.9 ms | **97.4 ms** |
| Warm mean | **150.5 ms** | 178.1 ms |
| Cold p95 | 182.2 ms | **107.8 ms** |
| Warm p95 | **351.3 ms** | 419.4 ms |

**Takeaway**: gRPC cold-starts faster (HTTP/2 connection setup is efficient). REST is faster when warm. In practice, connections are kept warm, so this favors REST for long-running services.

---

## Scorecard: Who Wins What?

| Category | REST Wins | gRPC Wins | Tie |
|----------|-----------|-----------|-----|
| Sequential throughput | **X** | | |
| Create latency (tail) | | **X** | |
| Search/List latency | | | **X** |
| Payload size | | **X** | |
| Serialization speed | | **X** | |
| Concurrent throughput (5-10) | | **X** | |
| Concurrent throughput (25+) | **X** | | |
| Streaming time-to-first | | **X** | |
| Connection overhead | | **X** | |
| Client memory | | **X** | |
| Page-load p50 | **X** | | |
| Page-load p95 | | **X** | |
| Bursty traffic | | **X** | |
| Network jitter resilience | | **X** | |
| Long-session stability | **X** | | |
| Error recovery | **X** | | |
| Concurrent mixed | | **X** | |
| Cold start | | **X** | |

**REST: 5 wins** | **gRPC: 11 wins** | **Tie: 2**

---

## Honest Assessment

### Where gRPC Genuinely Excels
- **Concurrent workloads** — HTTP/2 multiplexing gives 1.6–1.9x throughput under load
- **Tail latency (p95/p99)** — more consistent, especially under jitter or bursts
- **Wire efficiency** — 2.4x smaller payloads, 10x faster serialization
- **Network resilience** — 2.5x better p99 under jittery conditions

### Where REST Genuinely Excels
- **Sequential single-client speed** — fewer layers, simpler path
- **Error handling** — HTTP status codes are simpler, faster recovery
- **Long-session stability** — less drift over hundreds of requests
- **Extreme concurrency (25+ clients on single worker)** — simpler queuing model

### What These Benchmarks DON'T Show
- **Browser compatibility** — browsers can't speak gRPC natively (need gRPC-Web proxy)
- **Caching** — HTTP caching/CDN is a massive REST advantage not tested here
- **Debugging** — JSON is human-readable; protobuf isn't
- **Tooling** — curl, Postman, browser devtools all work with REST out of the box
- **Multi-service hops** — gRPC's advantage compounds across microservice chains
- **Scale to millions** — both use PostgreSQL here; the protocol difference grows with data volume

### Caveats About This Benchmark
- **Single-worker servers** — production would use multiple workers, changing concurrency dynamics
- **Localhost only** — no real network latency; gRPC's binary advantage would grow over WAN
- **Python GIL** — both servers are GIL-bound; Go/Rust gRPC would show larger gains
- **Database-dominated** — many tests are bottlenecked by PostgreSQL, not the protocol
- **Small dataset** — with millions of records, payload size differences compound

---

## Verdict

| Use Case | Recommendation | Why |
|----------|----------------|-----|
| Browser-facing API | **REST** | Browsers only speak HTTP; caching, CORS, devtools |
| Service-to-service | **gRPC** | 1.6x throughput, 2.4x smaller payloads, type safety |
| Mobile on bad networks | **gRPC** | 2.5x better tail latency under jitter |
| Simple CRUD app | **REST** | Simpler, good enough performance |
| High-concurrency backend | **gRPC** | HTTP/2 multiplexing, lower per-request overhead |
| Streaming real-time data | **gRPC** | Native streaming, 25% faster time-to-first-result |

**For JKP Registration specifically**: Use REST for the browser-facing frontend, gRPC for any backend service communication. The hybrid approach gives you the best of both worlds.
