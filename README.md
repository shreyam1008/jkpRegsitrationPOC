# JKP Satsangi Registration — REST vs gRPC Proof of Concept

A side-by-side comparison of **REST** and **gRPC** architectures for the same application: a satsangi (devotee) registration system for JKP ashrams.

Both implementations are **functionally identical** — create and search satsangis — but use completely different communication protocols and data formats.

---

## Quick Start

### Prerequisites

- Python 3.12+ with [`uv`](https://docs.astral.sh/uv/)
- [Bun](https://bun.sh/) (or Node.js) for the frontend
- PostgreSQL running on localhost:5432

### Create Databases

```bash
PGPASSWORD=postgres psql -h localhost -U postgres -c "CREATE DATABASE jkp_reg_poc_rest;"
PGPASSWORD=postgres psql -h localhost -U postgres -c "CREATE DATABASE jkp_reg_poc_grpc;"
```

### Run REST Version (2 terminals)

```bash
# Terminal 1: FastAPI server (:8001)
cd jkpRegsitrationPOC/server
uv sync
uv run python -m uvicorn app.main:app --port 8001

# Terminal 2: React client (:5173)
cd jkpRegsitrationPOC/client
bun install
bun run dev
```

Open **http://localhost:5173** — browser talks directly to FastAPI via `fetch()`

### Run gRPC Version (3 terminals)

```bash
# Terminal 1: Native gRPC server (:50051) — the real backend
cd jkpRegistrationFULLGRPC/server
uv sync
uv run python -m app.grpc_server

# Terminal 2: grpc-web proxy (:8080) — translates browser HTTP → gRPC
cd jkpRegistrationFULLGRPC/server
uv run python -m uvicorn app.main:app --port 8080

# Terminal 3: React client (:5174)
cd jkpRegistrationFULLGRPC/client
bun install
bun run dev
```

Open **http://localhost:5174** — browser sends grpc-web to proxy (:8080) which forwards to gRPC server (:50051)

> **Why 3 terminals?** Browsers can't speak native gRPC. The proxy translates grpc-web frames into real gRPC calls. Without Terminal 1 (gRPC server), the proxy has nothing to forward to.

### Run Tests (REST version)

Tests live in `jkpRegsitrationPOC/tests/` — **21 unit tests** (Vitest) + **9 e2e tests** (Playwright).

```bash
# Install test dependencies (first time only)
cd jkpRegsitrationPOC/tests
bun install

# Unit tests (no servers needed)
bun run test:unit

# E2E tests — headless (auto-starts server :8001 + client :5174)
bun run test:e2e

# E2E tests — headed (see the browser)
bunx playwright test --headed

# E2E tests — step-by-step debug mode
bunx playwright test --debug
```

> **Note:** Playwright auto-starts both the FastAPI server (`:8001`) and the Vite client (`:5174`) via `webServer` config. If they're already running, it reuses them (`reuseExistingServer: true`).

### Run Benchmarks (16-test suite)

```bash
# Start REST server (:8001) and gRPC server (:50051) first (no proxy/client needed), then:
cd jkpRegistrationFULLGRPC/server
uv run python ../../benchmarks/bench_robust.py
```

Results are written to `benchmarks/results.json` and reported in [`benchmarks/RESULTS.md`](benchmarks/RESULTS.md).

---

## Architecture Overview

### 1. REST Version (`jkpRegsitrationPOC/`)

```
┌─────────────────┐    HTTP/1.1 + JSON     ┌─────────────────┐       SQL       ┌──────────────────┐
│   React Client   │ ────────────────────► │  FastAPI :8001   │ ──────────────► │   PostgreSQL      │
│   :5173          │ ◄──────────────────── │  (REST server)   │ ◄────────────── │   jkp_reg_poc_rest│
└─────────────────┘                        └─────────────────┘                  └──────────────────┘
```

- **Protocol**: HTTP/1.1
- **Data format**: JSON (text, human-readable)
- **API**: `POST /api/satsangis` (create), `GET /api/satsangis?q=...` (search)
- **Browser integration**: Native `fetch()` — no special libraries needed

### 2. gRPC Version (`jkpRegistrationFULLGRPC/`) — Pure gRPC, Zero REST

```
┌─────────────────┐   grpc-web (protobuf)  ┌──────────────────┐   gRPC/HTTP2   ┌─────────────────┐       SQL       ┌──────────────────┐
│   React Client   │ ───────────────────► │  grpc-web Proxy   │ ─────────────► │  gRPC Server     │ ──────────────► │   PostgreSQL      │
│   :5174          │ ◄───────────────────  │  :8080             │ ◄───────────── │  :50051          │ ◄────────────── │   jkp_reg_poc_grpc│
│   (grpc-web)     │                      │  (frame translate) │                │  (grpcio)        │                 │                   │
└─────────────────┘                       └──────────────────┘                 └─────────────────┘                  └──────────────────┘
```

- **Protocol**: gRPC over HTTP/2 (server), gRPC-web over HTTP/1.1 (browser)
- **Data format**: Protocol Buffers (binary, schema-enforced)
- **API**: RPC methods defined in `.proto` file (`CreateSatsangi`, `SearchSatsangis`, `ListSatsangis`)
- **Browser integration**: `grpc-web` npm package + proxy (no REST anywhere)

---

## Project Structure

```
jkpRegsitrationPOC/
├── jkpRegsitrationPOC/          ← REST implementation
│   ├── server/
│   │   ├── app/
│   │   │   ├── db.py            ← PostgreSQL connection (jkp_reg_poc_rest)
│   │   │   ├── main.py          ← FastAPI REST endpoints
│   │   │   ├── models.py        ← Pydantic data models
│   │   │   └── store.py         ← PostgreSQL CRUD operations
│   │   └── pyproject.toml
│   ├── client/
│   │   ├── src/
│   │   │   ├── api.ts           ← fetch() calls to REST API
│   │   │   ├── App.tsx          ← React routing
│   │   │   └── pages/           ← CreatePage, SearchPage
│   │   ├── vite.config.ts       ← Port 5173, proxy → :8001
│   │   └── package.json
│   └── tests/
│       ├── e2e/
│       │   └── registration.spec.ts  ← 9 Playwright e2e tests
│       ├── unit/
│       │   ├── api.test.ts           ← API function tests
│       │   ├── CreatePage.test.tsx   ← Create form tests
│       │   └── SearchPage.test.tsx   ← Search page tests
│       ├── playwright.config.ts      ← E2E config (server :8001, client :5174)
│       ├── vitest.config.ts          ← Unit test config (jsdom)
│       └── package.json
│
├── jkpRegistrationFULLGRPC/     ← gRPC implementation (no REST)
│   ├── server/
│   │   ├── proto/
│   │   │   └── satsangi.proto   ← gRPC service contract
│   │   ├── app/
│   │   │   ├── generated/       ← protoc-generated Python code
│   │   │   ├── db.py            ← PostgreSQL connection (jkp_reg_poc_grpc)
│   │   │   ├── grpc_server.py   ← Pure gRPC server (:50051)
│   │   │   ├── main.py          ← grpc-web proxy (:8080)
│   │   │   ├── models.py        ← Pydantic data models
│   │   │   └── store.py         ← PostgreSQL CRUD operations
│   │   └── pyproject.toml
│   └── client/
│       ├── src/
│       │   ├── generated/       ← TypeScript protobuf + gRPC-web client
│       │   ├── api.ts           ← gRPC-web calls (no fetch!)
│       │   ├── App.tsx          ← React routing
│       │   └── pages/           ← CreatePage, SearchPage (same UI)
│       ├── vite.config.ts       ← Port 5174
│       └── package.json         ← grpc-web, google-protobuf
│
├── benchmarks/
│   ├── bench_robust.py          ← 16-category benchmark suite
│   ├── bench_standalone.py      ← Standalone benchmark
│   └── RESULTS.md               ← Benchmark results
│
├── grpc_instruction.md          ← Detailed gRPC vs REST guide + grpc-web docs
└── README.md                    ← This file
```

---

## Port Configuration

| Component | REST Version | gRPC Version |
|-----------|-------------|--------------|
| **Client (React)** | `:5173` | `:5174` |
| **Server** | `:8001` (FastAPI) | `:50051` (gRPC) |
| **Proxy** | — | `:8080` (grpc-web) |
| **Database** | `jkp_reg_poc_rest` | `jkp_reg_poc_grpc` |
| **PostgreSQL** | `:5432` | `:5432` |

---

## Technology Stack

| Layer | REST | gRPC |
|-------|------|------|
| **Frontend** | React 19 + Vite + TypeScript + TailwindCSS | Same |
| **API Layer** | `fetch()` + JSON | `grpc-web` + Protobuf |
| **Backend** | FastAPI (Python 3.12) | grpcio (Python 3.12) |
| **Database** | PostgreSQL via psycopg2 | PostgreSQL via psycopg2 |
| **Package Mgr** | uv (Python), Bun (JS) | Same |
| **Serialization** | JSON | Protocol Buffers |
| **Transport** | HTTP/1.1 | HTTP/2 |

---

## How gRPC-web Works

Browsers cannot make native gRPC calls (no HTTP/2 framing control, no trailers). **gRPC-web** solves this:

```
Standard gRPC:     HTTP/2 + binary protobuf + HTTP/2 trailers
gRPC-web:          HTTP/1.1 + binary protobuf frames + trailers-in-body
```

Every message is wrapped in a **5-byte frame**:

```
[Flag: 1 byte] [Length: 4 bytes big-endian] [Payload: N bytes]

Flag 0x00 = Data frame (protobuf)
Flag 0x80 = Trailer frame (grpc-status + grpc-message)
```

Our grpc-web proxy (`main.py`) handles this translation:
1. Browser sends `application/grpc-web-text` POST with base64-encoded protobuf frame
2. Proxy decodes frame, extracts protobuf payload
3. Forwards raw bytes to gRPC server via `grpc.insecure_channel`
4. Wraps response in grpc-web frame (data + trailers)
5. Returns to browser

See [grpc_instruction.md](grpc_instruction.md) for the full technical deep-dive.

---

## Benchmark Categories

The benchmark suite (`benchmarks/bench_robust.py`) tests **16 categories** — 8 synthetic + 8 real-life:

| # | Category | Type | Description |
|---|----------|------|-------------|
| A1 | **Latency** | Synthetic | Single-request (create/search/list), p50/p95/p99 |
| A2 | **Throughput** | Synthetic | Sustained requests/sec for reads and writes |
| A3 | **Payload Size** | Synthetic | Wire bytes for 1–1,000 records |
| A4 | **Serialization** | Synthetic | Encode/decode speed for 10,000 messages |
| A5 | **Concurrency** | Synthetic | 5 / 10 / 25 simultaneous clients |
| A6 | **Streaming** | Synthetic | gRPC server-streaming vs REST batch |
| A7 | **Connection** | Synthetic | New connection vs reused connection overhead |
| A8 | **Memory** | Synthetic | Client-side RAM consumption per request |
| B9 | **Page Load** | Real-life | 3 sequential calls per page (search + create + re-fetch) |
| B10 | **Bursty Traffic** | Real-life | Idle → sudden burst (registration desk waves) |
| B11 | **Variable Payload** | Real-life | Minimal (3 fields) vs full (30+ fields) |
| B12 | **Network Jitter** | Real-life | Random 0–200ms delays (bad WiFi/mobile) |
| B13 | **Long Session** | Real-life | 300+ requests, check for latency drift |
| B14 | **Error Recovery** | Real-life | Bad requests → good requests, measure recovery |
| B15 | **Concurrent Mixed** | Real-life | 10 users, 80/20 read/write |
| B16 | **Cold Start** | Real-life | First request after idle vs warmed-up connection |

### Actual Results (measured 2026-03-13)

| Metric | REST | gRPC | Winner |
|--------|------|------|--------|
| Payload (1 record) | 927 B | 389 B | **gRPC** (2.4x smaller) |
| Serialization (10K enc+dec) | 383 ms | 39 ms | **gRPC** (9.9x faster) |
| Concurrent throughput (10 clients) | 6.9 rps | 11.7 rps | **gRPC** (1.7x) |
| Bursty traffic p99 | 347 ms | 120 ms | **gRPC** (2.9x) |
| Network jitter consistency (stdev) | 82 ms | 38 ms | **gRPC** (2.2x) |
| Sequential throughput | 20 rps | 11.6 rps | **REST** (1.7x) |
| Error recovery | 25 ms | 64 ms | **REST** (2.6x) |
| Long-session stability (drift) | +4.6 ms | +54 ms | **REST** |

Full results with all 16 benchmarks: [`benchmarks/RESULTS.md`](benchmarks/RESULTS.md)

---

## Key Differences Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                        REST                                      │
│                                                                  │
│  Browser  ──fetch(JSON)──►  FastAPI  ──SQL──►  PostgreSQL       │
│                                                                  │
│  ✓ Simple, readable, browser-native                             │
│  ✓ curl/Postman/devtools friendly                               │
│  ✗ Larger payloads, slower serialization                        │
│  ✗ No streaming, new connections per request                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        gRPC                                      │
│                                                                  │
│  Browser  ──grpc-web(protobuf)──►  Proxy  ──gRPC──►  Server    │
│                                                ──SQL──►  PG     │
│                                                                  │
│  ✓ 3-5x smaller payloads, 5-10x faster serialization           │
│  ✓ HTTP/2 multiplexing, native streaming                        │
│  ✓ Compile-time type safety (.proto contract)                   │
│  ✗ Requires proxy for browsers                                  │
│  ✗ Binary format, harder to debug                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## When to Use Which

| Scenario | Recommendation |
|----------|---------------|
| Public browser API | **REST** |
| Mobile app API | REST or gRPC |
| Microservice ↔ Microservice | **gRPC** |
| Real-time streaming | **gRPC** |
| High-throughput internal | **gRPC** |
| Third-party integrations | **REST** |
| Need HTTP caching / CDN | **REST** |
| Polyglot services (Go + Python + Java) | **gRPC** |
| End-to-end type safety | **gRPC** (with grpc-web) |

---

## Further Reading

- [grpc_instruction.md](grpc_instruction.md) — Full technical guide with grpc-web deep-dive
- [gRPC official docs](https://grpc.io/docs/)
- [gRPC-web docs](https://grpc.io/docs/platforms/web/basics/)
- [Protocol Buffers guide](https://protobuf.dev/programming-guides/proto3/)
- [grpc-web GitHub](https://github.com/grpc/grpc-web)
