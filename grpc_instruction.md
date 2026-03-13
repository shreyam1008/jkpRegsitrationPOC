# gRPC vs REST — Complete Guide for JKP Registration POC

## Table of Contents

1. [What is gRPC?](#1-what-is-grpc)
2. [What is REST?](#2-what-is-rest)
3. [Key Differences: gRPC vs REST](#3-key-differences-grpc-vs-rest)
4. [Architecture of This Project](#4-architecture-of-this-project)
5. [gRPC-web: gRPC in the Browser](#5-grpc-web-grpc-in-the-browser)
6. [How gRPC Works Under the Hood](#6-how-grpc-works-under-the-hood)
7. [Protocol Buffers (Protobuf)](#7-protocol-buffers-protobuf)
8. [File-by-File Walkthrough](#8-file-by-file-walkthrough)
9. [How to Run](#9-how-to-run)
10. [How to Use / Test Manually](#10-how-to-use--test-manually)
11. [gRPC Communication Patterns](#11-grpc-communication-patterns)
12. [When to Use gRPC vs REST](#12-when-to-use-grpc-vs-rest)
13. [Benchmark Results](#13-benchmark-results)

---

## 1. What is gRPC?

**gRPC** (gRPC Remote Procedure Call) is a high-performance, open-source RPC framework created by Google.

- **Transport**: HTTP/2 (multiplexed streams, header compression, persistent connections)
- **Serialization**: Protocol Buffers (binary, schema-enforced, ~3-10x smaller than JSON)
- **Contract**: `.proto` files define services and message schemas at compile time
- **Language**: Polyglot — generate client/server code for Python, Go, Java, TypeScript, C++, etc.
- **Streaming**: Native support for server-streaming, client-streaming, and bidirectional streaming

### Core Idea

Instead of making HTTP requests with JSON payloads to URL endpoints (REST), you **call remote functions directly** as if they were local functions. The `.proto` file is the shared contract between client and server.

```
// You write this (gRPC):
client.createSatsangi(request)

// Instead of this (REST):
fetch('/api/satsangis', { method: 'POST', body: JSON.stringify(data) })
```

---

## 2. What is REST?

The `jkpRegsitrationPOC/` folder uses a standard REST architecture:

```
Browser (React :5173)  --HTTP/1.1 + JSON-->  FastAPI (:8001)  --SQL-->  PostgreSQL (jkp_reg_poc_rest)
```

- **Transport**: HTTP/1.1
- **Serialization**: JSON (text-based, human-readable, larger payloads)
- **Contract**: OpenAPI/Swagger spec (generated at runtime, optional)
- **Endpoints**:
  - `POST /api/satsangis` — Create a satsangi
  - `GET /api/satsangis?q=...` — List/search satsangis

### REST Stack

| Layer     | Technology     |
|-----------|---------------|
| Frontend  | React + Vite + TypeScript (:5173) |
| Transport | HTTP/1.1 + JSON |
| Backend   | FastAPI (Python) (:8001) |
| Storage   | PostgreSQL (`jkp_reg_poc_rest`) |

---

## 3. Key Differences: gRPC vs REST

| Feature | REST (jkpRegsitrationPOC) | gRPC (jkpRegistrationFULLGRPC) |
|---------|--------------------------|-------------------------------|
| **Protocol** | HTTP/1.1 | HTTP/2 (server) + gRPC-web (browser) |
| **Data Format** | JSON (text, ~1KB per record) | Protobuf (binary, ~300B per record) |
| **Schema** | Optional (OpenAPI) | Required (.proto file, compile-time) |
| **Type Safety** | Runtime validation (Pydantic) | Compile-time (protoc generates typed code) |
| **Streaming** | Not native (SSE/WebSocket needed) | Native (server, client, bidirectional) |
| **Browser Support** | Native (fetch API) | Via gRPC-web + proxy |
| **Tooling** | curl, Postman, browser | grpcurl, grpcui, Postman (gRPC tab) |
| **Connection** | New TCP connection per request | Persistent multiplexed connection |
| **Latency** | Higher (JSON parse + new connection) | Lower (binary + persistent connection) |
| **Payload Size** | Larger (~3-5x) | Smaller (binary encoding) |
| **Human Readable** | Yes (JSON) | No (binary, need tools to inspect) |
| **Code Generation** | Optional | Required (protoc compiler) |
| **Error Handling** | HTTP status codes (200, 404, 500) | gRPC status codes (OK, NOT_FOUND, INTERNAL) |
| **Caching** | Easy (HTTP caching, CDNs) | Hard (binary, no URL-based caching) |
| **Database** | PostgreSQL (`jkp_reg_poc_rest`) | PostgreSQL (`jkp_reg_poc_grpc`) |
| **Server Port** | 8001 | 50051 (gRPC) + 8080 (grpc-web proxy) |
| **Client Port** | 5173 | 5174 |

### The Trade-off

```
REST  = Simple + Human-readable + Browser-native + Widely understood
gRPC  = Fast + Compact + Type-safe + Streaming + Better for microservices
```

---

## 4. Architecture of This Project

This project implements the **same application** (satsangi registration) in two completely different architectures:

### REST Architecture (jkpRegsitrationPOC)

```
┌─────────────────┐    HTTP/1.1 + JSON     ┌─────────────────┐       SQL       ┌──────────────────┐
│   React Client   │ ────────────────────► │  FastAPI :8001   │ ──────────────► │   PostgreSQL      │
│   :5173          │ ◄──────────────────── │  (REST server)   │ ◄────────────── │   jkp_reg_poc_rest│
└─────────────────┘                        └─────────────────┘                  └──────────────────┘
```

**Simple, direct, browser-native.**

### gRPC Architecture (jkpRegistrationFULLGRPC) — Pure gRPC, No REST

```
┌─────────────────┐   grpc-web/HTTP1.1   ┌──────────────────┐   gRPC/HTTP2   ┌─────────────────┐       SQL       ┌──────────────────┐
│   React Client   │ ──────────────────► │  grpc-web Proxy   │ ─────────────► │  gRPC Server     │ ──────────────► │   PostgreSQL      │
│   :5174          │ ◄────────────────── │  :8080             │ ◄───────────── │  :50051          │ ◄────────────── │   jkp_reg_poc_grpc│
│   (grpc-web)     │                     │  (frame translate) │                │  (grpcio)        │                 │                   │
└─────────────────┘                      └──────────────────┘                 └─────────────────┘                  └──────────────────┘
```

**No REST anywhere.** The browser speaks gRPC-web protocol (binary protobuf frames). The proxy translates the grpc-web wire format to native gRPC/HTTP2.

### Benchmark Direct Path (no browser)

```
┌──────────────────┐   gRPC/HTTP2 (native)   ┌─────────────────┐       SQL       ┌──────────────────┐
│  Python client    │ ─────────────────────► │  gRPC Server     │ ──────────────► │   PostgreSQL      │
│  (benchmarks)     │ ◄───────────────────── │  :50051          │ ◄────────────── │   jkp_reg_poc_grpc│
└──────────────────┘                         └─────────────────┘                  └──────────────────┘
```

**Key insight**: For service-to-service communication, gRPC is called directly without any web proxy overhead.

---

## 5. gRPC-web: gRPC in the Browser

### The Problem

Browsers cannot make native gRPC calls because:
1. **No HTTP/2 framing control** — browsers don't expose low-level HTTP/2 APIs
2. **No trailer support** — gRPC uses HTTP/2 trailers for status codes; browsers can't read them
3. **No bidirectional streaming** — browser `fetch()` doesn't support it

### The Solution: gRPC-web

[gRPC-web](https://grpc.io/docs/platforms/web/basics/) is a JavaScript client library that implements a **subset of the gRPC protocol** adapted for browsers:

```
Standard gRPC:     HTTP/2 + binary protobuf + trailers
gRPC-web:          HTTP/1.1 + binary protobuf frames + trailers-in-body
gRPC-web-text:     HTTP/1.1 + base64-encoded protobuf + trailers-in-body
```

### gRPC-web Wire Format

Every gRPC-web message is wrapped in a **5-byte frame header**:

```
┌────────────────┬──────────────────────┬────────────────────┐
│  Flag (1 byte) │  Length (4 bytes BE) │  Payload (N bytes) │
└────────────────┴──────────────────────┴────────────────────┘

Flag = 0x00: Data frame (protobuf payload)
Flag = 0x80: Trailer frame (status codes as text)
```

#### Example: CreateSatsangi Request

```
Browser sends:
  Content-Type: application/grpc-web-text
  Body: base64(
    0x00                          ← data frame flag
    0x00 0x00 0x01 0x2B          ← payload length (299 bytes)
    [protobuf binary payload]     ← SatsangiCreate message
  )

Proxy receives, base64-decodes, extracts payload, forwards to gRPC server via HTTP/2.

Server responds with Satsangi protobuf message.

Proxy wraps in grpc-web frame:
  0x00 [length] [protobuf data]   ← data frame
  0x80 [length] "grpc-status:0\r\ngrpc-message:OK\r\n"  ← trailer frame

Browser decodes, deserializes protobuf → typed JavaScript object.
```

### Our Implementation

Instead of using Envoy proxy (the "official" gRPC-web proxy), we built a **lightweight Python proxy** using FastAPI:

```python
# server/app/main.py — grpc-web proxy (NOT a REST server!)
@app.post("/{service_path:path}")
async def grpc_web_proxy(service_path, request):
    body = await request.body()
    if "grpc-web-text" in content_type:
        body = base64.b64decode(body)
    payload = decode_grpc_web_frame(body)
    result = channel.unary_unary(f"/{service_path}")(payload)
    return encode_grpc_web_response(result)
```

This proxy:
- Accepts `application/grpc-web` or `application/grpc-web-text`
- Decodes the grpc-web frame (strips 5-byte header)
- Forwards raw protobuf bytes to the gRPC server via `grpc.insecure_channel`
- Wraps the response in grpc-web frames with trailer metadata
- Handles CORS headers for browser cross-origin requests

### Client-Side gRPC-web

The React client uses the [`grpc-web`](https://github.com/grpc/grpc-web) npm package:

```typescript
// client/src/api.ts
import { SatsangiServiceClient } from './generated/SatsangiServiceClientPb'
import { SatsangiCreate, SearchRequest, Empty } from './generated/satsangi_pb'

const client = new SatsangiServiceClient('http://localhost:8080')

// This sends a REAL gRPC call (protobuf binary) — NOT a REST call
export async function createSatsangi(data) {
  const req = new SatsangiCreate()
  req.setFirstName(data.first_name)
  req.setLastName(data.last_name)
  // ...
  return client.createSatsangi(req)  // ← gRPC call, not fetch()
}
```

### gRPC-web vs REST Gateway: Key Differences

| Aspect | REST Gateway (old) | gRPC-web (new) |
|--------|-------------------|----------------|
| Browser sends | JSON text | Protobuf binary |
| Content-Type | `application/json` | `application/grpc-web-text` |
| Schema enforcement | Runtime (JSON → Pydantic) | Compile-time (protobuf) |
| Payload size | ~1KB per record | ~300B per record |
| Type safety | None (JSON is untyped) | Full (generated classes) |
| REST involved? | Yes (entire browser layer) | **No** — pure gRPC end-to-end |

### References

- [gRPC-web official docs](https://grpc.io/docs/platforms/web/basics/)
- [grpc-web GitHub repo](https://github.com/grpc/grpc-web)
- [gRPC-web protocol spec](https://github.com/grpc/grpc/blob/master/doc/PROTOCOL-WEB.md)
- [google-protobuf npm](https://www.npmjs.com/package/google-protobuf)

---

## 6. How gRPC Works Under the Hood

### Step-by-step: What happens when the browser calls `client.createSatsangi(request)`

```
1. BROWSER: React creates a SatsangiCreate protobuf message object
2. BROWSER: grpc-web serializes it to binary via google-protobuf
3. BROWSER: Wraps in grpc-web frame (5-byte header + payload)
4. BROWSER: Base64-encodes and sends POST to proxy :8080
   - Content-Type: application/grpc-web-text
   - URL: /jkp.registration.v1.SatsangiService/CreateSatsangi
5. PROXY: Receives HTTP/1.1 request, base64-decodes, strips frame header
6. PROXY: Forwards raw protobuf bytes to gRPC server via HTTP/2
7. SERVER: grpcio receives the HTTP/2 frame
8. SERVER: Protobuf deserializes binary → SatsangiCreate message
9. SERVER: Calls SatsangiServiceServicer.CreateSatsangi() method
10. SERVER: Business logic runs (store.create_satsangi → PostgreSQL)
11. SERVER: Result serialized to binary Satsangi protobuf message
12. SERVER: Sent back over HTTP/2 to proxy
13. PROXY: Wraps in grpc-web frame (data frame + trailer frame)
14. PROXY: Base64-encodes, returns to browser
15. BROWSER: grpc-web decodes frame, deserializes protobuf
16. BROWSER: Returns typed SatsangiMsg object to React component
```

### Why is this faster than REST?

| Step | REST | gRPC (with grpc-web) |
|------|------|------|
| Browser serialization | `JSON.stringify()` → text string | `msg.serializeBinary()` → binary bytes |
| Payload size (request) | ~1000 bytes | ~300 bytes |
| Server deserialization | `json.loads()` → dict → Pydantic | `msg.FromString()` → typed object |
| Payload size (response) | ~1000 bytes | ~300 bytes |
| Schema validation | Runtime (Pydantic parses JSON) | Compile-time (protoc enforced types) |
| Connection (backend) | HTTP/1.1 | HTTP/2 persistent multiplexed |

---

## 7. Protocol Buffers (Protobuf)

### The .proto file

Located at `jkpRegistrationFULLGRPC/server/proto/satsangi.proto`:

```protobuf
syntax = "proto3";
package jkp.registration.v1;

message SatsangiCreate {
  string first_name           = 1;   // Field number 1 — used in binary encoding
  string last_name            = 2;
  string phone_number         = 3;
  optional int32 age          = 4;   // "optional" means field can be absent
  // ... 31 fields total
}

message Satsangi {
  string satsangi_id  = 1;
  string created_at   = 2;
  // ... all fields from SatsangiCreate plus ID and timestamp (33 fields)
}

service SatsangiService {
  rpc CreateSatsangi(SatsangiCreate) returns (Satsangi);           // Unary
  rpc SearchSatsangis(SearchRequest) returns (SatsangiList);       // Unary
  rpc ListSatsangis(Empty) returns (SatsangiList);                 // Unary
  rpc StreamSearchResults(SearchRequest) returns (stream Satsangi); // Server streaming
}
```

### How field numbers work

In JSON: `{"first_name": "Ravi"}` → field name is repeated in every message (wastes bytes)

In Protobuf: `[field 1 = "Ravi"]` → only the field NUMBER is encoded (1 byte), not the name. This is why protobuf is so much smaller.

### Code generation

```bash
# Python (server-side) — generates from .proto
python -m grpc_tools.protoc \
  -I proto \
  --python_out=app/generated \
  --grpc_python_out=app/generated \
  proto/satsangi.proto

# TypeScript (client-side) — hand-written using google-protobuf
# See client/src/generated/satsangi_pb.ts
# Uses jspb.BinaryWriter/BinaryReader for wire-format serialization
```

---

## 8. File-by-File Walkthrough

### REST version: `jkpRegsitrationPOC/`

```
jkpRegsitrationPOC/
├── server/
│   ├── app/
│   │   ├── db.py          ← PostgreSQL connection (jkp_reg_poc_rest)
│   │   ├── main.py        ← FastAPI REST endpoints (:8001)
│   │   ├── models.py      ← Pydantic models
│   │   └── store.py       ← PostgreSQL CRUD operations
│   └── pyproject.toml     ← fastapi, uvicorn, psycopg2-binary
├── client/
│   ├── src/
│   │   ├── api.ts         ← fetch() calls to REST API
│   │   ├── App.tsx        ← React routing
│   │   └── pages/         ← CreatePage, SearchPage
│   ├── vite.config.ts     ← Port 5173, proxy /api → :8001
│   └── package.json       ← React, Vite, TailwindCSS
```

### gRPC version: `jkpRegistrationFULLGRPC/`

```
jkpRegistrationFULLGRPC/
├── server/
│   ├── proto/
│   │   └── satsangi.proto       ← The gRPC contract
│   ├── app/
│   │   ├── generated/
│   │   │   ├── satsangi_pb2.py      ← Generated protobuf classes
│   │   │   └── satsangi_pb2_grpc.py ← Generated gRPC stubs
│   │   ├── db.py                ← PostgreSQL connection (jkp_reg_poc_grpc)
│   │   ├── grpc_server.py      ← Pure gRPC server (:50051)
│   │   ├── main.py             ← grpc-web proxy (:8080) — NOT REST!
│   │   ├── models.py           ← Pydantic models
│   │   └── store.py            ← PostgreSQL CRUD operations
│   └── pyproject.toml          ← grpcio, psycopg2-binary (no fastapi for gRPC)
├── client/
│   ├── src/
│   │   ├── generated/
│   │   │   ├── satsangi_pb.ts           ← Protobuf message classes (TypeScript)
│   │   │   └── SatsangiServiceClientPb.ts ← gRPC-web service client
│   │   ├── api.ts              ← gRPC-web calls (no fetch!)
│   │   ├── App.tsx             ← React routing
│   │   └── pages/              ← CreatePage, SearchPage (identical UI)
│   ├── vite.config.ts          ← Port 5174 (no proxy needed)
│   └── package.json            ← grpc-web, google-protobuf
```

### Key files in the gRPC version

| File | Purpose |
|------|---------|
| `grpc_server.py` | Pure gRPC server: implements `SatsangiServiceServicer`, handles protobuf ↔ Pydantic conversion, starts on :50051 |
| `main.py` | grpc-web proxy: translates grpc-web wire format from browsers into native gRPC calls. **Not a REST server.** |
| `satsangi_pb.ts` | Hand-written TypeScript protobuf classes using `google-protobuf` BinaryWriter/BinaryReader |
| `SatsangiServiceClientPb.ts` | gRPC-web client using `grpc-web` MethodDescriptor pattern |
| `api.ts` | Public API: converts TypeScript interfaces ↔ protobuf messages, calls gRPC-web client |

---

## 9. How to Run

### Prerequisites

- Python 3.12+ with `uv` package manager
- Node.js / Bun for the frontend
- PostgreSQL with databases `jkp_reg_poc_rest` and `jkp_reg_poc_grpc`

### Create databases

```bash
PGPASSWORD=postgres psql -h localhost -U postgres -c "CREATE DATABASE jkp_reg_poc_rest;"
PGPASSWORD=postgres psql -h localhost -U postgres -c "CREATE DATABASE jkp_reg_poc_grpc;"
```

### REST version

```bash
# Terminal 1: Server
cd jkpRegsitrationPOC/server
uv sync
uv run python -m uvicorn app.main:app --port 8001

# Terminal 2: Client
cd jkpRegsitrationPOC/client
bun install && bun run dev
# → http://localhost:5173
```

### gRPC version

```bash
# Terminal 1: Server (starts gRPC :50051 + grpc-web proxy :8080)
cd jkpRegistrationFULLGRPC/server
uv sync
uv run python -m uvicorn app.main:app --port 8080

# Terminal 2: Client
cd jkpRegistrationFULLGRPC/client
bun install && bun run dev
# → http://localhost:5174
```

### Standalone gRPC server (for benchmarking)

```bash
cd jkpRegistrationFULLGRPC/server
uv run python -m app.grpc_server
# Server starts on port 50051 (no web proxy)
```

---

## 10. How to Use / Test Manually

### Using grpcurl (CLI tool for gRPC)

```bash
# List available services (reflection must be enabled)
grpcurl -plaintext localhost:50051 list

# Create a satsangi
grpcurl -plaintext -d '{
  "first_name": "Ravi",
  "last_name": "Sharma",
  "phone_number": "9876543210",
  "nationality": "Indian",
  "country": "India"
}' localhost:50051 jkp.registration.v1.SatsangiService/CreateSatsangi

# List all satsangis
grpcurl -plaintext localhost:50051 jkp.registration.v1.SatsangiService/ListSatsangis

# Search satsangis
grpcurl -plaintext -d '{"query": "Ravi"}' \
  localhost:50051 jkp.registration.v1.SatsangiService/SearchSatsangis
```

### Using Python client directly

```python
import grpc
from app.generated import satsangi_pb2, satsangi_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)

# Create
result = stub.CreateSatsangi(satsangi_pb2.SatsangiCreate(
    first_name="Ravi", last_name="Sharma", phone_number="9876543210",
))
print(f"Created: {result.satsangi_id}")

# Search
results = stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Ravi"))
for s in results.satsangis:
    print(f"  {s.first_name} {s.last_name}")
```

### Using curl to test REST

```bash
# Create
curl -X POST http://localhost:8001/api/satsangis \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Ravi","last_name":"Sharma","phone_number":"9876543210"}'

# Search
curl http://localhost:8001/api/satsangis?q=Ravi
```

---

## 11. gRPC Communication Patterns

gRPC supports 4 communication patterns. Our implementation uses 2 of them:

### 1. Unary RPC (Request → Response)

Like a normal REST call. Client sends one message, server returns one message.

```protobuf
rpc CreateSatsangi(SatsangiCreate) returns (Satsangi);
```

```
Client ──── SatsangiCreate ────► Server
Client ◄─── Satsangi ─────────── Server
```

**Used for**: CreateSatsangi, SearchSatsangis, ListSatsangis

### 2. Server Streaming RPC (Request → Stream of Responses)

Client sends one message, server returns a stream of messages one by one.

```protobuf
rpc StreamSearchResults(SearchRequest) returns (stream Satsangi);
```

```
Client ──── SearchRequest ─────► Server
Client ◄─── Satsangi #1 ──────── Server
Client ◄─── Satsangi #2 ──────── Server
Client ◄─── Satsangi #3 ──────── Server
Client ◄─── (stream end) ──────── Server
```

**Advantage**: Client can start processing results BEFORE the server finishes.

### 3. Client Streaming (not used here)
### 4. Bidirectional Streaming (not used here)

> **Note**: gRPC-web currently only supports Unary and Server Streaming. Client streaming and bidirectional streaming require native gRPC (not available in browsers).

---

## 12. When to Use gRPC vs REST

### Use REST when:

- **Public-facing APIs** — browsers, mobile apps, third-party integrations
- **Simple CRUD** — standard create/read/update/delete with no streaming
- **Caching is important** — REST integrates with HTTP caches and CDNs
- **Team familiarity** — everyone knows REST; gRPC has a learning curve
- **Human-readable debugging** — you can read JSON in browser devtools

### Use gRPC when:

- **Microservice-to-microservice** — internal service communication
- **Low latency required** — binary serialization + HTTP/2 multiplexing
- **Streaming needed** — real-time data feeds, live updates, large datasets
- **Polyglot systems** — services in Python, Go, Java, etc. share .proto files
- **Strong contracts** — .proto file enforces types at compile time
- **High throughput** — thousands of requests/sec between services

### Use gRPC-web when:

- You want **end-to-end gRPC** including the browser
- You need **protobuf type safety** all the way to the UI
- You want to **eliminate the REST layer** entirely
- You're building a **microservices frontend** (micro-frontends)

---

## 13. Benchmark Results

Run the benchmarks yourself:

```bash
# Start both servers first:
# Terminal 1: REST
cd jkpRegsitrationPOC/server && uv run python -m uvicorn app.main:app --port 8001
# Terminal 2: gRPC
cd jkpRegistrationFULLGRPC/server && uv run python -m app.grpc_server

# Terminal 3: Run benchmarks
cd benchmarks
uv run python bench_standalone.py
```

### What the benchmarks test (10 categories):

| # | Test | What it measures |
|---|------|-----------------|
| 1 | **Latency** | Round-trip time (create + search, p50/p95/p99) |
| 2 | **Throughput** | Sustained requests/sec (read + write) |
| 3 | **Payload Size** | Wire bytes for 1, 10, 100, 1000 records |
| 4 | **Serialization** | Encode/decode speed for 10,000 messages |
| 5 | **Concurrent Load** | 5/10/25/50/100 simultaneous clients |
| 6 | **Streaming** | gRPC server-streaming vs REST batch |
| 7 | **Connection Overhead** | New vs reused connection cost |
| 8 | **Memory** | Client-side RAM consumption |
| 9 | **Slow Network** | Added 10/50/100/200ms latency simulation |
| 10 | **Mixed Workload** | 70% read / 30% write realistic pattern |

### Expected results (typical):

| Metric | REST | gRPC | Winner |
|--------|------|------|--------|
| Single request latency | ~2-5ms | ~0.5-2ms | gRPC (2-4x faster) |
| Throughput (req/s) | ~1,000-3,000 | ~5,000-15,000 | gRPC (3-5x faster) |
| Payload size (1 record) | ~800-1200 bytes | ~200-400 bytes | gRPC (3-5x smaller) |
| Serialization (10K msgs) | ~50-100ms | ~5-15ms | gRPC (5-10x faster) |
| 100 concurrent clients | Degrades | Stable | gRPC |
| Connection setup | ~1-3ms each | ~0.1ms (reused) | gRPC |
| Human readability | Excellent | Poor | REST |
| Browser support | Native | Via proxy | REST |

---

## Appendix: gRPC Status Codes vs HTTP Status Codes

| gRPC Status | HTTP Equivalent | Meaning |
|-------------|----------------|---------|
| OK (0) | 200 | Success |
| CANCELLED (1) | 499 | Client cancelled |
| INVALID_ARGUMENT (3) | 400 | Bad request |
| NOT_FOUND (5) | 404 | Resource not found |
| ALREADY_EXISTS (6) | 409 | Conflict |
| PERMISSION_DENIED (7) | 403 | Forbidden |
| UNAUTHENTICATED (16) | 401 | Unauthorized |
| INTERNAL (13) | 500 | Server error |
| UNAVAILABLE (14) | 503 | Service unavailable |

## Appendix: Dependencies

### REST Server (jkpRegsitrationPOC/server/pyproject.toml)

| Package | Purpose |
|---------|---------|
| `fastapi` | REST API framework |
| `uvicorn` | ASGI server |
| `pydantic` | Data validation models |
| `psycopg2-binary` | PostgreSQL driver |

### gRPC Server (jkpRegistrationFULLGRPC/server/pyproject.toml)

| Package | Purpose |
|---------|---------|
| `grpcio` | Core gRPC runtime for Python |
| `grpcio-tools` | Protobuf compiler + Python code generator |
| `grpcio-reflection` | Service discovery (grpcurl, Postman) |
| `protobuf` | Protobuf message runtime library |
| `psycopg2-binary` | PostgreSQL driver |
| `fastapi` + `uvicorn` | grpc-web proxy only (NOT for REST) |

### gRPC Client (jkpRegistrationFULLGRPC/client/package.json)

| Package | Purpose |
|---------|---------|
| `grpc-web` | gRPC-web client library for browsers |
| `google-protobuf` | Protobuf runtime (BinaryWriter/BinaryReader) |
| `@types/google-protobuf` | TypeScript type definitions |

### REST Client (jkpRegsitrationPOC/client/package.json)

Standard React + Vite + TypeScript. Uses native `fetch()` — no gRPC dependencies.
