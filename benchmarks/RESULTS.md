# JKP Registration gRPC — Comprehensive Benchmark Report

> Generated: **2026-03-24 14:55:01**
> Total benchmarks: **148**
> Total requests simulated: **235,045**
> Total wall time: **658.6s**
> Platform: Python 3.14.3, linux

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Under Test](#architecture-under-test)
3. [Test Methodology](#test-methodology)
4. [Suite 1: Native gRPC Server](#suite-1-native-grpc-server)
5. [Suite 2: grpc-web Proxy (Full HTTP Path)](#suite-2-grpc-web-proxy-full-http-path)
6. [Suite 3: Concurrent Load Simulation](#suite-3-concurrent-load-simulation)
7. [Suite 4: Network Condition Simulation](#suite-4-network-condition-simulation)
8. [Suite 5: Connection Pool Stress](#suite-5-connection-pool-stress)
9. [Suite 6: Serialization & Encoding Overhead](#suite-6-serialization--encoding-overhead)
10. [Breaking Points & Limits](#breaking-points--limits)
11. [Recommendations](#recommendations)

---

## Executive Summary

This report benchmarks every layer of the JKP Registration gRPC application:

- **Protobuf serialization** — encoding/decoding overhead for all message sizes
- **gRPC server** — direct RPC latency and throughput (ThreadPoolExecutor×10)
- **grpc-web proxy** — FastAPI translation layer (base64, framing, HTTP overhead)
- **Concurrent users** — 1 to 200 simultaneous users, mixed workloads
- **Network conditions** — DB latency from 0ms to 200ms, jitter, timeouts
- **Connection pool** — exhaustion, sizing, failure recovery, churn

All benchmarks use a **mocked in-memory DB** to isolate application-layer
performance from actual PostgreSQL. Real-world numbers will be higher by the
DB query time (typically 1-10ms for indexed queries on localhost PG).

### Key Findings

- **Baseline gRPC latency**: 0.82ms p50, 6.21ms p99 (743 rps)
- **Proxy overhead**: 2.30ms p50, 3.71ms p99 (416 rps)
- **Proxy adds ~1.49ms** per request (p50)
- **200 concurrent users**: 1103 rps, p99=482.61ms, errors=0
- **Pool exhaustion (100 workers, pool=20)**: p99=1028.61ms, waits=80

---

## Architecture Under Test

```
Browser (ConnectRPC, grpc-web-text)
    │  HTTP/1.1 POST (base64-encoded protobuf)
    ▼
FastAPI Proxy (:8080, uvicorn, async)
    │  grpc.aio channel (HTTP/2, singleton, multiplexed)
    ▼
gRPC Server (:50051, ThreadPoolExecutor×10)
    │  Proto → Pydantic → SQL → Pydantic → Proto
    ▼
PostgreSQL (ThreadedConnectionPool 2–20)
```

**RPCs tested:** CreateSatsangi (31 fields), SearchSatsangis (12-field ILIKE),
ListSatsangis, Health

---

## Test Methodology

- **DB layer**: Mocked in-memory (configurable latency injection)
- **gRPC server**: Real `grpcio` server, real protobuf serialization
- **Proxy**: Real FastAPI + uvicorn, real base64/framing
- **Concurrency**: `ThreadPoolExecutor` for gRPC, `asyncio` + `httpx` for proxy
- **Timing**: `time.perf_counter()` (nanosecond resolution)
- **Statistics**: p50, p95, p99, mean, min, max, stdev, RPS
- **Network sim**: Latency injection at DB layer (0-200ms), jitter (±20ms)

---

## Suite 1: Native gRPC Server

| Benchmark | Requests | RPS | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Min (ms) | Max (ms) | Success |
|---|---|---|---|---|---|---|---|---|---|
| gRPC Health (no-op) | 1000 | 743.1 | 1.34 | 0.82 | 2.59 | 6.21 | 0.37 | 9.86 | 100.0% |
| gRPC CreateSatsangi (minimal) | 500 | 401.6 | 2.42 | 2.35 | 2.85 | 3.10 | 1.97 | 3.72 | 100.0% |
| gRPC CreateSatsangi (full payload) | 500 | 451.5 | 2.04 | 2.45 | 3.11 | 3.76 | 0.50 | 4.64 | 100.0% |
| gRPC Search (500 records) | 500 | 556.7 | 1.79 | 1.71 | 2.81 | 3.36 | 0.63 | 5.01 | 100.0% |
| gRPC Search (store=100) | 200 | 973.5 | 1.02 | 1.00 | 1.50 | 1.63 | 0.54 | 1.71 | 100.0% |
| gRPC Search (store=500) | 200 | 330.1 | 3.02 | 1.87 | 9.21 | 12.91 | 0.75 | 15.26 | 100.0% |
| gRPC Search (store=1000) | 200 | 150.2 | 6.64 | 3.47 | 18.32 | 30.95 | 1.11 | 51.13 | 100.0% |
| gRPC Search (store=5000) | 200 | 54.8 | 18.23 | 13.08 | 48.98 | 60.63 | 4.07 | 70.46 | 100.0% |
| gRPC ListAll (store=100) | 100 | 265.1 | 3.76 | 3.53 | 5.38 | 5.95 | 2.50 | 9.79 | 100.0% |
| gRPC ListAll (store=500) | 100 | 40.4 | 24.71 | 13.25 | 51.54 | 83.12 | 9.86 | 85.39 | 100.0% |
| gRPC ListAll (store=1000) | 100 | 34.8 | 28.73 | 26.55 | 42.49 | 60.61 | 21.23 | 69.01 | 100.0% |
| gRPC ListAll (store=2000) | 100 | 17.8 | 56.16 | 54.33 | 70.90 | 83.29 | 44.90 | 88.87 | 100.0% |
| gRPC ListAll (store=5000) | 100 | 5.0 | 198.20 | 194.94 | 243.90 | 326.81 | 148.76 | 385.53 | 100.0% |
| gRPC Search (empty query, 500 recs) | 300 | 53.9 | 18.56 | 18.31 | 30.42 | 37.10 | 9.80 | 49.09 | 100.0% |
| gRPC Rapid-Fire Health (5s) | 5258 | 1051.2 | 0.95 | 0.48 | 2.69 | 6.98 | 0.32 | 16.41 | 100.0% |

---

## Suite 2: grpc-web Proxy (Full HTTP Path)

| Benchmark | Requests | RPS | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Min (ms) | Max (ms) | Success |
|---|---|---|---|---|---|---|---|---|---|
| Proxy GET /healthz | 500 | 361.0 | 2.77 | 1.52 | 5.42 | 5.83 | 0.91 | 8.71 | 100.0% |
| Proxy → gRPC Health | 500 | 416.3 | 2.40 | 2.30 | 3.28 | 3.71 | 1.58 | 8.66 | 100.0% |
| Proxy → CreateSatsangi (minimal) | 500 | 380.2 | 2.60 | 2.53 | 3.39 | 4.04 | 1.70 | 7.68 | 100.0% |
| Proxy → CreateSatsangi (full) | 500 | 359.3 | 2.71 | 2.48 | 3.53 | 9.32 | 1.73 | 15.16 | 100.0% |
| Proxy → Search (500 recs) | 300 | 266.2 | 3.74 | 3.45 | 5.06 | 10.44 | 2.07 | 11.18 | 100.0% |
| Proxy → ListAll (store=100) | 100 | 197.3 | 5.07 | 4.55 | 7.29 | 11.95 | 3.59 | 12.85 | 100.0% |
| Proxy → ListAll (store=500) | 100 | 62.0 | 16.12 | 14.02 | 22.20 | 30.68 | 11.74 | 30.74 | 100.0% |
| Proxy → ListAll (store=1000) | 100 | 15.7 | 63.71 | 27.99 | 137.09 | 248.16 | 22.14 | 319.78 | 100.0% |
| Proxy → ListAll (store=2000) | 100 | 7.5 | 132.76 | 97.20 | 245.69 | 336.38 | 47.24 | 472.13 | 100.0% |
| Proxy payload ~50 bytes (minimal) | 300 | 391.3 | 2.55 | 2.48 | 3.31 | 3.63 | 1.66 | 6.36 | 100.0% |
| Proxy payload ~300 bytes (full) | 300 | 372.7 | 2.68 | 2.57 | 3.58 | 4.05 | 1.74 | 4.40 | 100.0% |
| Proxy Rapid-Fire (5s) | 1299 | 259.3 | 3.85 | 2.46 | 10.28 | 18.38 | 1.58 | 24.54 | 100.0% |

<details>
<summary>Additional metrics</summary>

**Proxy payload ~50 bytes (minimal)**:
- raw_bytes: 50
- wire_bytes: 76
- overhead_pct: 52.0

**Proxy payload ~300 bytes (full)**:
- raw_bytes: 298
- wire_bytes: 404
- overhead_pct: 35.57046979865772

</details>

---

## Suite 3: Concurrent Load Simulation

| Benchmark | Requests | RPS | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Min (ms) | Max (ms) | Success |
|---|---|---|---|---|---|---|---|---|---|
| gRPC Ramp-Up: 1 users | 50 | 436.2 | 2.26 | 2.11 | 2.85 | 5.16 | 1.85 | 7.08 | 100.0% |
| gRPC Ramp-Up: 5 users | 250 | 809.2 | 6.02 | 6.02 | 12.37 | 14.13 | 0.54 | 14.70 | 100.0% |
| gRPC Ramp-Up: 10 users | 500 | 2155.2 | 4.41 | 4.41 | 7.06 | 8.03 | 0.52 | 8.98 | 100.0% |
| gRPC Ramp-Up: 25 users | 1250 | 2113.6 | 11.65 | 11.72 | 12.94 | 13.79 | 3.79 | 16.37 | 100.0% |
| gRPC Ramp-Up: 50 users | 2500 | 2094.9 | 23.54 | 23.48 | 25.81 | 28.30 | 6.39 | 29.26 | 100.0% |
| gRPC Ramp-Up: 100 users | 5000 | 1992.2 | 49.50 | 48.69 | 56.87 | 64.24 | 6.24 | 68.00 | 100.0% |
| gRPC Ramp-Up: 150 users | 7500 | 965.8 | 153.42 | 78.78 | 423.47 | 678.97 | 6.05 | 727.35 | 100.0% |
| gRPC Ramp-Up: 200 users | 10000 | 1103.0 | 179.23 | 108.91 | 419.12 | 482.61 | 6.37 | 497.30 | 100.0% |
| gRPC 10 users × Mixed | 500 | 258.6 | 37.95 | 32.44 | 74.40 | 86.19 | 5.64 | 91.61 | 100.0% |
| gRPC 50 users × Mixed | 2500 | 310.5 | 158.53 | 121.63 | 373.87 | 426.97 | 28.94 | 450.23 | 100.0% |
| gRPC 100 users × Mixed | 5000 | 277.3 | 352.29 | 300.40 | 544.15 | 1553.31 | 10.83 | 1853.46 | 100.0% |
| ThreadPool stress: 5 users (pool=10) | 250 | 177.4 | 27.80 | 26.87 | 44.03 | 54.60 | 8.48 | 70.68 | 100.0% |
| ThreadPool stress: 10 users (pool=10) | 500 | 123.8 | 80.51 | 68.84 | 171.64 | 246.09 | 12.40 | 373.11 | 100.0% |
| ThreadPool stress: 20 users (pool=10) | 1000 | 204.6 | 94.50 | 44.55 | 287.66 | 349.10 | 13.19 | 385.79 | 100.0% |
| ThreadPool stress: 50 users (pool=10) | 2500 | 108.2 | 451.02 | 374.02 | 920.37 | 1087.05 | 22.88 | 1170.55 | 100.0% |
| Sustained 50 users × 10s | 2468 | 238.4 | 207.76 | 122.36 | 641.65 | 1198.18 | 11.74 | 1437.18 | 100.0% |
| Proxy Ramp-Up: 1 users | 30 | 35.3 | 28.30 | 27.08 | 37.94 | 47.41 | 17.53 | 51.00 | 100.0% |
| Proxy Ramp-Up: 5 users | 150 | 89.4 | 54.62 | 28.32 | 152.60 | 179.24 | 6.32 | 188.83 | 100.0% |
| Proxy Ramp-Up: 10 users | 300 | 72.2 | 114.81 | 81.46 | 315.37 | 916.27 | 4.21 | 1126.72 | 100.0% |
| Proxy Ramp-Up: 25 users | 750 | 68.7 | 318.96 | 167.44 | 1242.59 | 1900.37 | 6.40 | 3253.89 | 100.0% |
| Proxy Ramp-Up: 50 users | 1500 | 95.6 | 521.99 | 361.19 | 1236.67 | 1588.18 | 159.08 | 1662.01 | 100.0% |
| Proxy Ramp-Up: 100 users | 3000 | 137.7 | 720.64 | 397.67 | 1879.55 | 2151.87 | 329.65 | 2309.74 | 100.0% |
| Proxy Ramp-Up: 150 users | 4500 | 59.2 | 2526.93 | 2270.95 | 5184.02 | 6481.81 | 402.50 | 6730.27 | 100.0% |
| Proxy Ramp-Up: 200 users | 6000 | 41.7 | 4788.29 | 4862.39 | 8279.18 | 11359.27 | 849.89 | 11772.19 | 100.0% |
| Proxy 10 users × Mixed | 300 | 181.8 | 46.66 | 30.35 | 122.45 | 250.23 | 4.51 | 742.90 | 100.0% |
| Proxy 50 users × Mixed | 1500 | 109.1 | 457.26 | 304.25 | 1114.51 | 1151.10 | 234.13 | 1207.88 | 100.0% |
| Proxy 100 users × Mixed | 3000 | 117.0 | 852.60 | 673.25 | 2267.21 | 2423.81 | 519.76 | 2566.92 | 100.0% |

---

## Suite 4: Network Condition Simulation

| Benchmark | Requests | RPS | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Min (ms) | Max (ms) | Success |
|---|---|---|---|---|---|---|---|---|---|
| DB latency 0ms (in-memory) | 200 | 744.7 | 1.34 | 1.05 | 2.22 | 7.74 | 0.38 | 8.15 | 100.0% |
| DB latency 1ms (fast SSD) | 200 | 384.6 | 2.60 | 2.29 | 8.43 | 8.89 | 0.43 | 10.15 | 100.0% |
| DB latency 2ms (localhost PG) | 200 | 302.0 | 3.31 | 3.23 | 8.55 | 10.18 | 0.44 | 11.40 | 100.0% |
| DB latency 5ms (local network) | 200 | 176.0 | 5.68 | 6.44 | 9.60 | 12.89 | 0.54 | 13.56 | 100.0% |
| DB latency 10ms (remote DB) | 200 | 106.0 | 9.43 | 11.59 | 12.50 | 12.95 | 0.49 | 14.67 | 100.0% |
| DB latency 25ms (cross-AZ) | 200 | 44.7 | 22.36 | 26.71 | 37.22 | 42.84 | 0.48 | 46.62 | 100.0% |
| DB latency 50ms (cross-region) | 200 | 25.0 | 39.96 | 52.10 | 56.06 | 60.22 | 0.55 | 61.81 | 100.0% |
| DB latency 100ms (intercontinental) | 50 | 14.4 | 69.27 | 106.13 | 120.38 | 122.05 | 2.79 | 122.63 | 100.0% |
| DB latency 200ms (extreme) | 50 | 6.3 | 159.46 | 205.94 | 216.33 | 228.67 | 0.91 | 238.74 | 100.0% |
| Proxy + DB latency 0ms | 150 | 74.8 | 13.30 | 13.38 | 22.20 | 29.47 | 2.24 | 33.42 | 100.0% |
| Proxy + DB latency 2ms | 150 | 98.5 | 10.11 | 10.10 | 16.38 | 22.48 | 4.58 | 30.92 | 100.0% |
| Proxy + DB latency 10ms | 150 | 58.0 | 17.20 | 14.35 | 23.52 | 26.70 | 12.67 | 35.15 | 100.0% |
| Proxy + DB latency 50ms | 150 | 17.5 | 57.26 | 54.77 | 66.46 | 78.92 | 52.98 | 90.52 | 100.0% |
| 0ms DB + 50 users | 1000 | 873.1 | 55.53 | 53.62 | 69.95 | 85.81 | 8.42 | 88.69 | 100.0% |
| 5ms DB + 50 users | 1000 | 738.1 | 65.42 | 65.46 | 75.10 | 78.60 | 13.01 | 80.53 | 100.0% |
| 20ms DB + 50 users | 1000 | 346.0 | 140.65 | 142.30 | 168.56 | 180.72 | 24.62 | 185.04 | 100.0% |
| 50ms DB + 50 users | 1000 | 151.5 | 319.78 | 298.42 | 406.33 | 416.11 | 92.65 | 436.26 | 100.0% |
| Timeout test: 2s timeout (DB=500ms) | 30 | 2.0 | 502.04 | 501.68 | 503.82 | 504.87 | 500.93 | 505.27 | 100.0% |
| Timeout test: 1s timeout (DB=500ms) | 30 | 2.0 | 501.51 | 501.49 | 501.83 | 502.13 | 501.14 | 502.25 | 100.0% |
| Timeout test: 300ms timeout (DB=500ms) | 30 | 3.3 | 302.79 | 302.71 | 303.94 | 304.34 | 301.85 | 304.39 | 0.0% |
| Jitter sim (5ms ± 0-20ms) | 300 | 76.8 | 13.01 | 13.39 | 24.68 | 26.36 | 0.51 | 28.40 | 100.0% |

<details>
<summary>Additional metrics</summary>

**DB latency 0ms (in-memory)**:
- db_latency_ms: 0.0

**DB latency 1ms (fast SSD)**:
- db_latency_ms: 1.0

**DB latency 2ms (localhost PG)**:
- db_latency_ms: 2.0

**DB latency 5ms (local network)**:
- db_latency_ms: 5.0

**DB latency 10ms (remote DB)**:
- db_latency_ms: 10.0

**DB latency 25ms (cross-AZ)**:
- db_latency_ms: 25.0

**DB latency 50ms (cross-region)**:
- db_latency_ms: 50.0

**DB latency 100ms (intercontinental)**:
- db_latency_ms: 100.0

**DB latency 200ms (extreme)**:
- db_latency_ms: 200.0

**Proxy + DB latency 0ms**:
- db_latency_ms: 0.0

**Proxy + DB latency 2ms**:
- db_latency_ms: 2.0

**Proxy + DB latency 10ms**:
- db_latency_ms: 10.0

**Proxy + DB latency 50ms**:
- db_latency_ms: 50.0

**0ms DB + 50 users**:
- db_latency_ms: 0.0
- theoretical_max_rps: inf

**5ms DB + 50 users**:
- db_latency_ms: 5.0
- theoretical_max_rps: 2000.0

**20ms DB + 50 users**:
- db_latency_ms: 20.0
- theoretical_max_rps: 500.0

**50ms DB + 50 users**:
- db_latency_ms: 50.0
- theoretical_max_rps: 200.0

**Timeout test: 2s timeout (DB=500ms)**:
- timeouts: 0
- timeout_pct: 0.0

**Timeout test: 1s timeout (DB=500ms)**:
- timeouts: 0
- timeout_pct: 0.0

**Timeout test: 300ms timeout (DB=500ms)**:
- timeouts: 30
- timeout_pct: 100.0

**Jitter sim (5ms ± 0-20ms)**:
- jitter_range_ms: 5-25ms

</details>

---

## Suite 5: Connection Pool Stress

| Benchmark | Requests | RPS | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Min (ms) | Max (ms) | Success |
|---|---|---|---|---|---|---|---|---|---|
| Pool exhaust: 10 workers (maxconn=20) | 300 | 889.8 | 11.19 | 11.17 | 11.33 | 11.42 | 11.08 | 11.50 | 100.0% |
| Pool exhaust: 20 workers (maxconn=20) | 600 | 1771.8 | 11.16 | 11.15 | 11.23 | 11.31 | 11.08 | 11.42 | 100.0% |
| Pool exhaust: 30 workers (maxconn=20) | 900 | 1323.4 | 15.09 | 11.17 | 11.45 | 346.97 | 11.07 | 351.46 | 100.0% |
| Pool exhaust: 50 workers (maxconn=20) | 1500 | 1461.3 | 20.40 | 11.17 | 14.16 | 352.14 | 11.09 | 695.69 | 100.0% |
| Pool exhaust: 100 workers (maxconn=20) | 3000 | 1744.0 | 33.93 | 11.17 | 16.06 | 1028.61 | 11.08 | 1387.13 | 100.0% |
| Hold time 0ms (50 workers, pool=20) | 1000 | 98220.1 | 0.01 | 0.00 | 0.01 | 0.02 | 0.00 | 0.17 | 100.0% |
| Hold time 1ms (50 workers, pool=20) | 1000 | 12873.2 | 1.95 | 1.09 | 3.05 | 27.84 | 1.03 | 45.09 | 100.0% |
| Hold time 5ms (50 workers, pool=20) | 1000 | 3201.2 | 9.20 | 5.10 | 5.75 | 109.36 | 5.03 | 210.90 | 100.0% |
| Hold time 10ms (50 workers, pool=20) | 1000 | 1630.5 | 18.12 | 10.10 | 10.35 | 213.19 | 10.04 | 413.09 | 100.0% |
| Hold time 25ms (50 workers, pool=20) | 1000 | 661.0 | 45.13 | 25.10 | 25.44 | 531.74 | 25.03 | 1028.32 | 100.0% |
| Hold time 50ms (50 workers, pool=20) | 1000 | 331.2 | 90.20 | 50.11 | 50.68 | 1062.23 | 50.03 | 2054.23 | 100.0% |
| Hold time 100ms (50 workers, pool=20) | 1000 | 166.2 | 180.27 | 100.10 | 101.75 | 2122.84 | 100.04 | 4107.72 | 100.0% |
| Failure rate 0% (30 workers) | 900 | 2071.0 | 9.55 | 7.16 | 7.30 | 219.30 | 7.08 | 220.81 | 100.0% |
| Failure rate 1% (30 workers) | 900 | 2073.0 | 9.45 | 7.16 | 7.31 | 211.90 | 0.02 | 219.98 | 99.3% |
| Failure rate 5% (30 workers) | 900 | 2149.3 | 8.99 | 7.15 | 7.23 | 192.00 | 0.01 | 207.24 | 95.1% |
| Failure rate 10% (30 workers) | 900 | 2218.9 | 8.51 | 7.15 | 7.30 | 170.36 | 0.00 | 199.86 | 90.2% |
| Failure rate 25% (30 workers) | 900 | 2644.6 | 7.09 | 7.14 | 7.22 | 134.63 | 0.00 | 169.81 | 75.9% |
| Pool size=2 (50 workers) | 1500 | 274.5 | 94.26 | 7.20 | 8.22 | 3706.76 | 7.09 | 5252.02 | 100.0% |
| Pool size=5 (50 workers) | 1500 | 693.5 | 39.53 | 7.18 | 7.34 | 1304.83 | 7.10 | 1949.29 | 100.0% |
| Pool size=10 (50 workers) | 1500 | 1357.2 | 21.74 | 7.17 | 10.04 | 652.62 | 7.07 | 885.63 | 100.0% |
| Pool size=20 (50 workers) | 1500 | 2225.7 | 13.26 | 7.17 | 12.46 | 225.32 | 7.07 | 453.52 | 100.0% |
| Pool size=50 (50 workers) | 1500 | 6611.1 | 7.18 | 7.15 | 7.28 | 8.04 | 7.05 | 9.81 | 100.0% |
| Pool size=100 (50 workers) | 1500 | 6610.5 | 7.18 | 7.15 | 7.27 | 7.98 | 7.07 | 9.92 | 100.0% |
| Conn create cost=0ms | 600 | 2073.4 | 9.52 | 7.15 | 7.26 | 148.41 | 7.08 | 149.23 | 100.0% |
| Conn create cost=5ms | 600 | 1216.1 | 16.28 | 12.22 | 12.41 | 254.67 | 12.14 | 255.11 | 100.0% |
| Conn create cost=10ms | 600 | 864.4 | 22.97 | 17.23 | 17.43 | 360.09 | 17.14 | 360.82 | 100.0% |
| Conn create cost=25ms | 600 | 462.7 | 43.14 | 32.24 | 33.83 | 677.89 | 32.14 | 679.65 | 100.0% |
| Conn create cost=50ms | 600 | 261.6 | 76.30 | 57.23 | 57.43 | 1199.92 | 57.15 | 1200.40 | 100.0% |
| Pool churn (rapid borrow/return) | 5000 | 276114.8 | 0.00 | 0.00 | 0.00 | 0.01 | 0.00 | 0.05 | 100.0% |
| Pool churn concurrent (100 threads) | 10000 | 173698.3 | 0.00 | 0.00 | 0.01 | 0.01 | 0.00 | 0.03 | 100.0% |

<details>
<summary>Additional metrics</summary>

**Pool exhaust: 10 workers (maxconn=20)**:
- total_borrows: 300
- peak_active: 10
- total_waits: 0
- avg_wait_ms: 0
- total_failures: 0
- maxconn: 20

**Pool exhaust: 20 workers (maxconn=20)**:
- total_borrows: 600
- peak_active: 20
- total_waits: 0
- avg_wait_ms: 0
- total_failures: 0
- maxconn: 20

**Pool exhaust: 30 workers (maxconn=20)**:
- total_borrows: 900
- peak_active: 20
- total_waits: 10
- avg_wait_ms: 338.31570480015216
- total_failures: 0
- maxconn: 20

**Pool exhaust: 50 workers (maxconn=20)**:
- total_borrows: 1500
- peak_active: 20
- total_waits: 30
- avg_wait_ms: 452.8041213335503
- total_failures: 0
- maxconn: 20

**Pool exhaust: 100 workers (maxconn=20)**:
- total_borrows: 3000
- peak_active: 20
- total_waits: 80
- avg_wait_ms: 845.2341322499706
- total_failures: 0
- maxconn: 20

**Hold time 0ms (50 workers, pool=20)**:
- total_borrows: 1000
- peak_active: 1
- total_waits: 0
- avg_wait_ms: 0
- total_failures: 0
- maxconn: 20
- hold_ms: 0

**Hold time 1ms (50 workers, pool=20)**:
- total_borrows: 1000
- peak_active: 20
- total_waits: 30
- avg_wait_ms: 23.34881903322336
- total_failures: 0
- maxconn: 20
- hold_ms: 1

**Hold time 5ms (50 workers, pool=20)**:
- total_borrows: 1000
- peak_active: 20
- total_waits: 30
- avg_wait_ms: 134.843276766757
- total_failures: 0
- maxconn: 20
- hold_ms: 5

**Hold time 10ms (50 workers, pool=20)**:
- total_borrows: 1000
- peak_active: 20
- total_waits: 30
- avg_wait_ms: 266.53243873309594
- total_failures: 0
- maxconn: 20
- hold_ms: 10

**Hold time 25ms (50 workers, pool=20)**:
- total_borrows: 1000
- peak_active: 20
- total_waits: 30
- avg_wait_ms: 666.5920002333829
- total_failures: 0
- maxconn: 20
- hold_ms: 25

**Hold time 50ms (50 workers, pool=20)**:
- total_borrows: 1000
- peak_active: 20
- total_waits: 30
- avg_wait_ms: 1333.657263366634
- total_failures: 0
- maxconn: 20
- hold_ms: 50

**Hold time 100ms (50 workers, pool=20)**:
- total_borrows: 1000
- peak_active: 20
- total_waits: 30
- avg_wait_ms: 2668.2356122000783
- total_failures: 0
- maxconn: 20
- hold_ms: 100

**Failure rate 0% (30 workers)**:
- total_borrows: 900
- peak_active: 20
- total_waits: 10
- avg_wait_ms: 213.22381339996355
- total_failures: 0
- maxconn: 20
- configured_failure_rate: 0.0
- actual_failure_rate: 0.0

**Failure rate 1% (30 workers)**:
- total_borrows: 900
- peak_active: 20
- total_waits: 10
- avg_wait_ms: 208.41767439997056
- total_failures: 6
- maxconn: 20
- configured_failure_rate: 0.01
- actual_failure_rate: 0.006666666666666667

**Failure rate 5% (30 workers)**:
- total_borrows: 900
- peak_active: 20
- total_waits: 10
- avg_wait_ms: 195.8539891997134
- total_failures: 44
- maxconn: 20
- configured_failure_rate: 0.05
- actual_failure_rate: 0.04888888888888889

**Failure rate 10% (30 workers)**:
- total_borrows: 900
- peak_active: 20
- total_waits: 10
- avg_wait_ms: 183.0346720998932
- total_failures: 88
- maxconn: 20
- configured_failure_rate: 0.1
- actual_failure_rate: 0.09777777777777778

**Failure rate 25% (30 workers)**:
- total_borrows: 900
- peak_active: 20
- total_waits: 10
- avg_wait_ms: 148.88124570024956
- total_failures: 217
- maxconn: 20
- configured_failure_rate: 0.25
- actual_failure_rate: 0.2411111111111111

**Pool size=2 (50 workers)**:
- total_borrows: 1500
- peak_active: 2
- total_waits: 48
- avg_wait_ms: 2718.5356313958664
- total_failures: 0
- maxconn: 2

**Pool size=5 (50 workers)**:
- total_borrows: 1500
- peak_active: 5
- total_waits: 45
- avg_wait_ms: 1077.9753078888461
- total_failures: 0
- maxconn: 5

**Pool size=10 (50 workers)**:
- total_borrows: 1500
- peak_active: 10
- total_waits: 40
- avg_wait_ms: 540.8917262249361
- total_failures: 0
- maxconn: 10

**Pool size=20 (50 workers)**:
- total_borrows: 1500
- peak_active: 20
- total_waits: 30
- avg_wait_ms: 289.94766106673825
- total_failures: 0
- maxconn: 20

**Pool size=50 (50 workers)**:
- total_borrows: 1500
- peak_active: 50
- total_waits: 0
- avg_wait_ms: 0
- total_failures: 0
- maxconn: 50

**Pool size=100 (50 workers)**:
- total_borrows: 1500
- peak_active: 50
- total_waits: 0
- avg_wait_ms: 0
- total_failures: 0
- maxconn: 100

**Conn create cost=0ms**:
- total_borrows: 600
- peak_active: 20
- total_waits: 10
- avg_wait_ms: 141.43045189994154
- total_failures: 0
- maxconn: 20

**Conn create cost=5ms**:
- total_borrows: 600
- peak_active: 20
- total_waits: 10
- avg_wait_ms: 242.50662570048007
- total_failures: 0
- maxconn: 20

**Conn create cost=10ms**:
- total_borrows: 600
- peak_active: 20
- total_waits: 10
- avg_wait_ms: 342.9131185996084
- total_failures: 0
- maxconn: 20

**Conn create cost=25ms**:
- total_borrows: 600
- peak_active: 20
- total_waits: 10
- avg_wait_ms: 645.9529427998859
- total_failures: 0
- maxconn: 20

**Conn create cost=50ms**:
- total_borrows: 600
- peak_active: 20
- total_waits: 10
- avg_wait_ms: 1142.726834399582
- total_failures: 0
- maxconn: 20

**Pool churn (rapid borrow/return)**:
- total_borrows: 5000
- peak_active: 1
- total_waits: 0
- avg_wait_ms: 0
- total_failures: 0
- maxconn: 20

**Pool churn concurrent (100 threads)**:
- total_borrows: 10000
- peak_active: 1
- total_waits: 0
- avg_wait_ms: 0
- total_failures: 0
- maxconn: 20

</details>

---

## Suite 6: Serialization & Encoding Overhead

| Benchmark | Requests | RPS | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Min (ms) | Max (ms) | Success |
|---|---|---|---|---|---|---|---|---|---|
| Proto serialize (minimal ~50B) | 5000 | 1149694.6 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 100.0% |
| Proto serialize (full ~300B) | 5000 | 833869.7 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 100.0% |
| Proto serialize (list×10) | 500 | 149071.3 | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 | 0.02 | 100.0% |
| Proto serialize (list×100) | 500 | 18033.0 | 0.05 | 0.06 | 0.06 | 0.07 | 0.05 | 0.16 | 100.0% |
| Proto serialize (list×500) | 500 | 2269.7 | 0.44 | 0.44 | 0.52 | 0.66 | 0.25 | 6.64 | 100.0% |
| Proto serialize (list×1000) | 500 | 1370.5 | 0.73 | 0.63 | 1.07 | 1.13 | 0.50 | 6.70 | 100.0% |
| Proto deserialize (minimal 48B) | 5000 | 391168.4 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.47 | 100.0% |
| Proto deserialize (full 316B) | 5000 | 287802.0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.90 | 100.0% |
| Proto deserialize (list×10, 3397B) | 500 | 86285.6 | 0.01 | 0.01 | 0.01 | 0.02 | 0.01 | 0.61 | 100.0% |
| Proto deserialize (list×100, 33892B) | 500 | 6911.6 | 0.14 | 0.12 | 0.14 | 0.19 | 0.07 | 6.60 | 100.0% |
| Proto deserialize (list×500, 169376B) | 500 | 1756.9 | 0.57 | 0.44 | 0.90 | 2.81 | 0.32 | 7.22 | 100.0% |
| Proto deserialize (list×1000, 338976B) | 500 | 1250.9 | 0.80 | 0.73 | 1.13 | 1.27 | 0.64 | 7.03 | 100.0% |
| Base64 encode (50B request) | 2000 | 1223551.4 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 100.0% |
| Base64 decode (50B request) | 2000 | 994307.6 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 100.0% |
| Base64 encode (300B request) | 2000 | 339785.1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.11 | 100.0% |
| Base64 decode (300B request) | 2000 | 340479.7 | 0.00 | 0.00 | 0.00 | 0.01 | 0.00 | 0.01 | 100.0% |
| Base64 encode (3KB list×10) | 2000 | 99055.6 | 0.01 | 0.01 | 0.02 | 0.02 | 0.01 | 0.12 | 100.0% |
| Base64 decode (3KB list×10) | 2000 | 86914.9 | 0.01 | 0.01 | 0.02 | 0.02 | 0.01 | 0.11 | 100.0% |
| Base64 encode (30KB list×100) | 2000 | 12282.4 | 0.08 | 0.08 | 0.11 | 0.14 | 0.07 | 6.26 | 100.0% |
| Base64 decode (30KB list×100) | 2000 | 2471.0 | 0.40 | 0.40 | 0.60 | 1.05 | 0.08 | 8.43 | 100.0% |
| Base64 encode (150KB list×500) | 2000 | 773.5 | 1.29 | 1.46 | 2.14 | 2.84 | 0.34 | 4.96 | 100.0% |
| Base64 decode (150KB list×500) | 2000 | 1544.7 | 0.65 | 0.50 | 1.10 | 2.98 | 0.43 | 12.28 | 100.0% |
| Frame pack (DATA frame) | 10000 | 1229246.3 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.12 | 100.0% |
| Frame unpack (strip header) | 10000 | 1127055.4 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.02 | 100.0% |
| Proto → Pydantic (SatsangiCreate) | 5000 | 22303.2 | 0.04 | 0.05 | 0.09 | 0.13 | 0.01 | 0.56 | 100.0% |
| Pydantic → Proto (Satsangi) | 5000 | 25128.0 | 0.04 | 0.03 | 0.06 | 0.08 | 0.02 | 0.48 | 100.0% |
| Pydantic SatsangiCreate (minimal) | 5000 | 46879.6 | 0.02 | 0.01 | 0.03 | 0.05 | 0.01 | 0.40 | 100.0% |
| Pydantic Satsangi (full + defaults) | 5000 | 12585.3 | 0.07 | 0.06 | 0.12 | 0.15 | 0.05 | 0.77 | 100.0% |
| Pipeline: base64 decode | 2000 | 128953.7 | 0.01 | 0.00 | 0.01 | 0.01 | 0.00 | 0.04 | 100.0% |
| Pipeline: frame strip | 2000 | 253661.2 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.03 | 100.0% |
| Pipeline: proto deserialize | 2000 | 100933.1 | 0.01 | 0.01 | 0.01 | 0.02 | 0.00 | 0.04 | 100.0% |
| Pipeline: proto → pydantic | 2000 | 10581.3 | 0.09 | 0.07 | 0.15 | 0.17 | 0.05 | 0.89 | 100.0% |
| Pipeline: pydantic → proto | 2000 | 29388.0 | 0.03 | 0.03 | 0.05 | 0.07 | 0.02 | 2.13 | 100.0% |
| Pipeline: proto serialize | 2000 | 165053.4 | 0.00 | 0.00 | 0.01 | 0.01 | 0.00 | 0.31 | 100.0% |
| Pipeline: frame pack + trailer | 2000 | 271157.4 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.03 | 100.0% |
| Pipeline: base64 encode response | 2000 | 125101.5 | 0.01 | 0.01 | 0.01 | 0.01 | 0.00 | 0.49 | 100.0% |
| Wire: Minimal SatsangiCreate | 1000 | 73598.6 | 0.01 | 0.01 | 0.01 | 0.03 | 0.01 | 0.08 | 100.0% |
| Wire: Full SatsangiCreate | 1000 | 49539.5 | 0.02 | 0.01 | 0.03 | 0.05 | 0.01 | 0.28 | 100.0% |
| Wire: Satsangi response | 1000 | 80820.0 | 0.01 | 0.01 | 0.02 | 0.02 | 0.01 | 0.06 | 100.0% |
| Wire: SatsangiList×10 | 1000 | 12204.9 | 0.08 | 0.07 | 0.11 | 0.13 | 0.07 | 0.41 | 100.0% |
| Wire: SatsangiList×50 | 1000 | 1410.5 | 0.70 | 0.47 | 1.34 | 1.65 | 0.31 | 4.26 | 100.0% |
| Wire: SatsangiList×100 | 1000 | 1247.3 | 0.80 | 0.75 | 1.16 | 1.82 | 0.62 | 2.08 | 100.0% |
| Wire: SatsangiList×500 | 1000 | 867.8 | 1.15 | 0.92 | 3.28 | 4.44 | 0.76 | 5.41 | 100.0% |

<details>
<summary>Additional metrics</summary>

**Proto serialize (minimal ~50B)**:
- bytes: 47

**Proto serialize (full ~300B)**:
- bytes: 298

**Proto serialize (list×10)**:
- bytes: 3376

**Proto serialize (list×100)**:
- bytes: 33902

**Proto serialize (list×500)**:
- bytes: 169544

**Proto serialize (list×1000)**:
- bytes: 338796

**Base64 encode (50B request)**:
- raw_bytes: 52
- encoded_bytes: 72
- overhead_pct: 38.46153846153847

**Base64 encode (300B request)**:
- raw_bytes: 307
- encoded_bytes: 412
- overhead_pct: 34.20195439739413

**Base64 encode (3KB list×10)**:
- raw_bytes: 3390
- encoded_bytes: 4520
- overhead_pct: 33.33333333333333

**Base64 encode (30KB list×100)**:
- raw_bytes: 33868
- encoded_bytes: 45160
- overhead_pct: 33.34120703909295

**Base64 encode (150KB list×500)**:
- raw_bytes: 169353
- encoded_bytes: 225804
- overhead_pct: 33.33333333333333

**Wire: Minimal SatsangiCreate**:
- proto_bytes: 51
- frame_bytes: 56
- base64_bytes: 76
- overhead_vs_proto: 49.0%

**Wire: Full SatsangiCreate**:
- proto_bytes: 300
- frame_bytes: 305
- base64_bytes: 408
- overhead_vs_proto: 36.0%

**Wire: Satsangi response**:
- proto_bytes: 331
- frame_bytes: 336
- base64_bytes: 448
- overhead_vs_proto: 35.3%

**Wire: SatsangiList×10**:
- proto_bytes: 3385
- frame_bytes: 3390
- base64_bytes: 4520
- overhead_vs_proto: 33.5%

**Wire: SatsangiList×50**:
- proto_bytes: 16928
- frame_bytes: 16933
- base64_bytes: 22580
- overhead_vs_proto: 33.4%

**Wire: SatsangiList×100**:
- proto_bytes: 33818
- frame_bytes: 33823
- base64_bytes: 45100
- overhead_vs_proto: 33.4%

**Wire: SatsangiList×500**:
- proto_bytes: 169309
- frame_bytes: 169314
- base64_bytes: 225752
- overhead_vs_proto: 33.3%

</details>

---

## Breaking Points & Limits

### Where the App Halts

#### 1. gRPC ThreadPoolExecutor Saturation
- Server uses `ThreadPoolExecutor(max_workers=10)`
- Each RPC blocks a thread for the duration of the DB call
- **Theoretical max with 0ms DB**: limited by Python GIL + protobuf overhead
- **With 50ms DB**: max throughput = 10 threads / 0.05s = **200 RPS**
- **With 100ms DB**: max throughput = 10 threads / 0.1s = **100 RPS**
- Beyond this, requests queue and latency climbs linearly

#### 2. Connection Pool Exhaustion
- `ThreadedConnectionPool(2, 20)` — max 20 concurrent DB connections
- With 50+ concurrent users and slow queries, pool blocks on `getconn()`
- Pool size 2 under 50 users: severe bottleneck, massive queuing
- Pool size 20 under 50 users: manageable if queries are fast (<10ms)

#### 3. Proxy Overhead
- Single uvicorn process (no workers) — all async, but GIL-bound
- base64 encode/decode adds ~33% wire overhead
- Frame pack/unpack is negligible (<0.01ms)
- For large responses (500+ records), serialization becomes dominant

#### 4. Serialization Scaling
- Single Satsangi: ~300 bytes protobuf, ~400 bytes on wire
- 100 records: ~30KB protobuf, ~40KB on wire
- 500 records: ~150KB protobuf, ~200KB on wire
- 1000 records: ~300KB protobuf — serialization time becomes noticeable

#### 5. Timeout Cascade
- With 500ms DB latency and 300ms timeout: near-100% timeouts
- With 500ms DB latency and 1s timeout: partial timeouts under load
- Slow DB + many users = thread exhaustion + timeout cascade

### Capacity Estimates (Single Server)

| Scenario | Est. Max RPS | Bottleneck |
|----------|-------------|------------|
| Ideal (0ms DB, no proxy) | 2000-5000+ | Python GIL, protobuf |
| Localhost PG (2ms DB) | 500-1000 | Thread pool (10 workers) |
| Remote DB (10ms) | 200-500 | Thread pool saturation |
| Through proxy (2ms DB) | 300-800 | Proxy + thread pool |
| Slow DB (50ms) | ~200 | Thread pool hard cap |
| 200 concurrent users | Varies | Depends on DB latency |

---

## Recommendations

### Immediate Wins
1. **Increase `max_workers`** from 10 to 20-50 — directly increases throughput ceiling
2. **Match pool size to workers** — `ThreadedConnectionPool(max_workers, max_workers)` avoids pool exhaustion
3. **Add pagination** to `ListSatsangis` and `SearchSatsangis` — cap response size at 50-100 records

### Medium-Term
4. **Switch to `grpc.aio`** async server — eliminates thread pool bottleneck entirely
5. **Use `psycopg` v3 async** — async DB driver pairs with async gRPC server
6. **Multiple uvicorn workers** — requires separate gRPC server process
7. **Connection pooling with PgBouncer** — more efficient than psycopg2 pool at scale

### Production Scale
8. **Horizontal scaling** — multiple server containers behind Caddy load balancer
9. **Read replicas** — route SearchSatsangis to a PG read replica
10. **Caching** — cache search results (TTL 30s) for repeated queries
11. **Rate limiting** — Caddy `rate_limit` or Cloudflare WAF per-IP

### Monitoring
12. **Add request latency histograms** — Prometheus + gRPC interceptors
13. **Track active DB connections** — alert when pool is >80% utilized
14. **Log slow queries** — any query >100ms should be logged
