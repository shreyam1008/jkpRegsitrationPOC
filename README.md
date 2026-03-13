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

### Run REST Version

```bash
# Terminal 1: Server (:8001)
cd jkpRegsitrationPOC/server && uv sync && uv run python -m uvicorn app.main:app --port 8001

# Terminal 2: Client (:5173)
cd jkpRegsitrationPOC/client && bun install && bun run dev
```

Open **http://localhost:5173**

### Run gRPC Version

```bash
# Terminal 1: gRPC Server (:50051) + grpc-web Proxy (:8080)
cd jkpRegistrationFULLGRPC/server && uv sync && uv run python -m uvicorn app.main:app --port 8080

# Terminal 2: Client (:5174)
cd jkpRegistrationFULLGRPC/client && bun install && bun run dev
```

Open **http://localhost:5174**

### Run Benchmarks

```bash
# Start REST server (:8001) and gRPC server (:50051) first, then:
cd jkpRegistrationFULLGRPC/server && uv run python ../../benchmarks/bench_standalone.py
```

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
│   └── client/
│       ├── src/
│       │   ├── api.ts           ← fetch() calls to REST API
│       │   ├── App.tsx          ← React routing
│       │   └── pages/           ← CreatePage, SearchPage
│       ├── vite.config.ts       ← Port 5173, proxy → :8001
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
│   └── bench_standalone.py      ← 10-category benchmark suite
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

The benchmark suite (`benchmarks/bench_standalone.py`) tests **10 categories**:

| # | Category | Description |
|---|----------|-------------|
| 1 | **Latency** | Single-request round-trip (create + search), p50/p95/p99 |
| 2 | **Throughput** | Sustained requests/sec for reads and writes |
| 3 | **Payload Size** | Wire bytes for 1, 10, 100, 1000 records |
| 4 | **Serialization** | Encode/decode speed for 10,000 messages |
| 5 | **Concurrency** | 5 / 10 / 25 / 50 / 100 simultaneous clients |
| 6 | **Streaming** | gRPC server-streaming vs REST batch |
| 7 | **Connection** | New connection vs reused connection overhead |
| 8 | **Memory** | Client-side RAM consumption per request |
| 9 | **Slow Network** | Simulated 10 / 50 / 100 / 200ms added latency |
| 10 | **Mixed Workload** | Realistic 70% read / 30% write pattern |

### Expected Results

| Metric | REST | gRPC | Winner |
|--------|------|------|--------|
| Latency (p50) | ~2-5ms | ~0.5-2ms | **gRPC** (2-4x) |
| Throughput | ~1-3K rps | ~5-15K rps | **gRPC** (3-5x) |
| Payload (1 record) | ~800-1200B | ~200-400B | **gRPC** (3-5x smaller) |
| Serialization (10K) | ~50-100ms | ~5-15ms | **gRPC** (5-10x) |
| 100 clients | Degrades | Stable | **gRPC** |
| Human readable | Excellent | Poor | **REST** |
| Browser native | Yes | Needs proxy | **REST** |
| Debugging | Easy (devtools) | Hard (binary) | **REST** |

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
