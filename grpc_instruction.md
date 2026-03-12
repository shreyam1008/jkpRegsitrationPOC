# gRPC vs REST — Complete Guide for JKP Registration POC

## Table of Contents

1. [What is gRPC?](#1-what-is-grpc)
2. [What is REST? (Current Implementation)](#2-what-is-rest-current-implementation)
3. [Key Differences: gRPC vs REST](#3-key-differences-grpc-vs-rest)
4. [Architecture of This Project](#4-architecture-of-this-project)
5. [How gRPC Works Under the Hood](#5-how-grpc-works-under-the-hood)
6. [Protocol Buffers (Protobuf)](#6-protocol-buffers-protobuf)
7. [File-by-File Walkthrough](#7-file-by-file-walkthrough)
8. [How to Run](#8-how-to-run)
9. [How to Use / Test Manually](#9-how-to-use--test-manually)
10. [gRPC Communication Patterns](#10-grpc-communication-patterns)
11. [When to Use gRPC vs REST](#11-when-to-use-grpc-vs-rest)
12. [Benchmark Results](#12-benchmark-results)

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
// You write this:
stub.CreateSatsangi(request)

// Instead of this:
fetch('/api/satsangis', { method: 'POST', body: JSON.stringify(data) })
```

---

## 2. What is REST? (Current Implementation)

The `jkpRegsitrationPOC/` folder uses a standard REST architecture:

```
Browser (React)  ---HTTP/1.1 + JSON--->  FastAPI server (:8000)  --->  JSON file store
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
| Frontend  | React + Vite + TypeScript |
| Transport | HTTP/1.1 + JSON |
| Backend   | FastAPI (Python) |
| Storage   | `data/satsangis.json` |

---

## 3. Key Differences: gRPC vs REST

| Feature | REST (jkpRegsitrationPOC) | gRPC (jkpRegsitrationPOCgrpc) |
|---------|--------------------------|-------------------------------|
| **Protocol** | HTTP/1.1 | HTTP/2 |
| **Data Format** | JSON (text, ~1KB per record) | Protobuf (binary, ~300B per record) |
| **Schema** | Optional (OpenAPI) | Required (.proto file, compile-time) |
| **Type Safety** | Runtime validation (Pydantic) | Compile-time (protoc generates typed code) |
| **Streaming** | Not native (SSE/WebSocket needed) | Native (server, client, bidirectional) |
| **Browser Support** | Native (fetch API) | Needs proxy (gRPC-web) |
| **Tooling** | curl, Postman, browser | grpcurl, grpcui, Postman (gRPC tab) |
| **Connection** | New TCP connection per request | Persistent multiplexed connection |
| **Latency** | Higher (JSON parse + new connection) | Lower (binary + persistent connection) |
| **Payload Size** | Larger (~3-10x) | Smaller (binary encoding) |
| **Human Readable** | Yes (JSON) | No (binary, need tools to inspect) |
| **Code Generation** | Optional | Required (protoc compiler) |
| **Error Handling** | HTTP status codes (200, 404, 500) | gRPC status codes (OK, NOT_FOUND, INTERNAL) |
| **Caching** | Easy (HTTP caching, CDNs) | Hard (binary, no URL-based caching) |

### The Trade-off

```
REST  = Simple + Human-readable + Browser-native + Widely understood
gRPC  = Fast + Compact + Type-safe + Streaming + Better for microservices
```

---

## 4. Architecture of This Project

### REST Architecture (jkpRegsitrationPOC)

```
┌─────────────┐     HTTP/1.1 + JSON     ┌─────────────────┐     File I/O     ┌──────────┐
│   Browser    │ ──────────────────────► │  FastAPI :8000   │ ──────────────► │ JSON DB  │
│  (React)     │ ◄────────────────────── │  (REST server)   │ ◄────────────── │          │
└─────────────┘                          └─────────────────┘                  └──────────┘
```

### gRPC Architecture (jkpRegsitrationPOCgrpc)

```
┌─────────────┐   HTTP/1.1+JSON   ┌──────────────────┐   gRPC/Protobuf   ┌─────────────────┐   File I/O   ┌──────────┐
│   Browser    │ ───────────────► │  FastAPI Gateway   │ ────────────────► │  gRPC Server     │ ──────────► │ JSON DB  │
│  (React)     │ ◄─────────────── │  :8000 (BFF)       │ ◄──────────────── │  :50051          │ ◄────────── │          │
└─────────────┘                   └──────────────────┘                    └─────────────────┘              └──────────┘
                                         │
                                         │  This gateway translates
                                         │  REST ↔ gRPC automatically
                                         │
                                  ┌──────────────────┐   gRPC/Protobuf   ┌─────────────────┐
                                  │  Python client    │ ────────────────► │  gRPC Server     │
                                  │  (benchmarks)     │ ◄──────────────── │  :50051          │
                                  └──────────────────┘                    └─────────────────┘
                                         │
                                         │  Direct gRPC — no REST overhead
                                         │  This is where the speed lives
```

**Key insight**: The FastAPI gateway exists ONLY so the browser can interact. For service-to-service or benchmark communication, you call gRPC directly — bypassing JSON serialization entirely.

---

## 5. How gRPC Works Under the Hood

### Step-by-step: What happens when you call `stub.CreateSatsangi(request)`

```
1. CLIENT: Python creates a SatsangiCreate protobuf message object
2. CLIENT: Protobuf serializes it to binary (~300 bytes vs ~1KB JSON)
3. CLIENT: grpcio sends it over HTTP/2 to the server
   - Uses existing persistent connection (no TCP handshake)
   - HTTP/2 multiplexing: multiple requests on same connection
   - Header compression via HPACK
4. NETWORK: Binary payload travels over the wire
5. SERVER: grpcio receives the HTTP/2 frame
6. SERVER: Protobuf deserializes binary → SatsangiCreate message
7. SERVER: Calls SatsangiServiceServicer.CreateSatsangi() method
8. SERVER: Business logic runs (store.create_satsangi)
9. SERVER: Result serialized to binary Satsangi protobuf message
10. SERVER: Sent back over same HTTP/2 connection
11. CLIENT: Receives and deserializes → usable Satsangi object
```

### Why is this faster than REST?

| Step | REST | gRPC |
|------|------|------|
| Connection | New TCP + TLS handshake (or keep-alive) | Persistent HTTP/2 connection |
| Serialization | `json.dumps()` → text string | `msg.SerializeToString()` → binary bytes |
| Payload size | ~1000 bytes | ~300 bytes |
| Deserialization | `json.loads()` → dict → Pydantic validation | `msg.FromString()` → typed object |
| Schema validation | Runtime (Pydantic parses JSON) | Compile-time (protoc already enforced types) |

---

## 6. Protocol Buffers (Protobuf)

### The .proto file

Located at `server/proto/satsangi.proto`:

```protobuf
syntax = "proto3";
package jkp.registration.v1;

// Messages define data structures (like TypeScript interfaces or Pydantic models)
message SatsangiCreate {
  string first_name           = 1;   // Field number 1 — used in binary encoding
  string last_name            = 2;
  string phone_number         = 3;
  optional int32 age          = 4;   // "optional" means field can be absent
  // ... more fields
}

message Satsangi {
  string satsangi_id  = 1;
  string created_at   = 2;
  // ... all fields from SatsangiCreate plus ID and timestamp
}

// Service defines the RPC methods (like REST endpoints)
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
# This command reads the .proto file and generates Python code
python -m grpc_tools.protoc \
  -I proto \
  --python_out=app/generated \
  --grpc_python_out=app/generated \
  proto/satsangi.proto

# Generates:
#   satsangi_pb2.py      — Message classes (SatsangiCreate, Satsangi, etc.)
#   satsangi_pb2_grpc.py — Service stubs and servicer base classes
#   satsangi_pb2.pyi     — Type stubs for IDE autocomplete
```

---

## 7. File-by-File Walkthrough

### `jkpRegsitrationPOCgrpc/server/` structure

```
server/
├── proto/
│   └── satsangi.proto              ← The contract (shared between client & server)
├── app/
│   ├── generated/
│   │   ├── __init__.py
│   │   ├── satsangi_pb2.py         ← Generated: protobuf message classes
│   │   ├── satsangi_pb2.pyi        ← Generated: type stubs
│   │   └── satsangi_pb2_grpc.py    ← Generated: gRPC service stubs
│   ├── __init__.py
│   ├── grpc_server.py              ← The gRPC server (port 50051)
│   ├── main.py                     ← FastAPI gateway (port 8000, proxies to gRPC)
│   ├── models.py                   ← Pydantic models (shared)
│   └── store.py                    ← JSON file data store (shared)
├── data/
│   └── satsangis.json              ← Data file
└── pyproject.toml                  ← Dependencies (grpcio, grpcio-tools, etc.)
```

### `grpc_server.py` — The core gRPC server

This file:
1. Implements `SatsangiServiceServicer` — the class that handles incoming gRPC calls
2. Converts between protobuf messages ↔ Pydantic models
3. Uses the same `store.py` data layer as the REST version
4. Enables server reflection (so tools like grpcurl can discover the API)
5. Starts a thread pool executor (10 workers) for concurrent requests

### `main.py` — The FastAPI gateway

This file:
1. Starts the gRPC server in-process on startup (lifespan event)
2. Exposes the same REST endpoints as the original (`POST /api/satsangis`, `GET /api/satsangis`)
3. Internally creates a gRPC stub and forwards requests to the gRPC server
4. Converts protobuf responses back to JSON for the browser

This means **the browser doesn't need to know about gRPC at all** — it sees the same REST API. But internally, all communication goes through gRPC.

---

## 8. How to Run

### Prerequisites

- Python 3.12+ with `uv` package manager
- Node.js / Bun for the frontend

### Server Setup

```bash
cd jkpRegsitrationPOCgrpc/server

# Install Python dependencies
uv sync

# (Re)generate protobuf code (only needed if .proto changes)
uv run python -m grpc_tools.protoc \
  -I proto \
  --python_out=app/generated \
  --grpc_python_out=app/generated \
  proto/satsangi.proto

# Start the server (starts both gRPC:50051 and FastAPI:8000)
uv run uvicorn app.main:app --reload --port 8000

# OR start ONLY the gRPC server (for benchmarks)
uv run python -m app.grpc_server
```

### Client Setup

```bash
cd jkpRegsitrationPOCgrpc/client

# Install frontend dependencies
bun install

# Start dev server
bun run dev
```

### Standalone gRPC server (for benchmarking)

```bash
cd jkpRegsitrationPOCgrpc/server

# Start gRPC server only (no gateway)
uv run python -m app.grpc_server
# Server starts on port 50051
```

---

## 9. How to Use / Test Manually

### Using grpcurl (CLI tool for gRPC)

```bash
# Install grpcurl
# Linux: go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest
# Mac:   brew install grpcurl

# List available services (reflection must be enabled)
grpcurl -plaintext localhost:50051 list

# Describe a service
grpcurl -plaintext localhost:50051 describe jkp.registration.v1.SatsangiService

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

# Stream search results
grpcurl -plaintext -d '{"query": "Ravi"}' \
  localhost:50051 jkp.registration.v1.SatsangiService/StreamSearchResults
```

### Using Python client directly

```python
import grpc
from app.generated import satsangi_pb2, satsangi_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)

# Create
result = stub.CreateSatsangi(satsangi_pb2.SatsangiCreate(
    first_name="Ravi",
    last_name="Sharma",
    phone_number="9876543210",
))
print(f"Created: {result.satsangi_id}")

# Search
results = stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Ravi"))
for s in results.satsangis:
    print(f"  {s.first_name} {s.last_name}")

# Server streaming
for s in stub.StreamSearchResults(satsangi_pb2.SearchRequest(query="Ravi")):
    print(f"  Streamed: {s.first_name}")
```

---

## 10. gRPC Communication Patterns

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

**Advantage**: Client can start processing results BEFORE the server finishes. Great for large result sets.

### 3. Client Streaming (not used here)

```
Client ──── Message #1 ─────► Server
Client ──── Message #2 ─────► Server
Client ──── (end) ──────────► Server
Client ◄─── Response ──────── Server
```

### 4. Bidirectional Streaming (not used here)

```
Client ──── Message ────► Server
Client ◄─── Message ◄─── Server
Client ──── Message ────► Server
Client ◄─── Message ◄─── Server
```

---

## 11. When to Use gRPC vs REST

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
- **Strong contracts** — .proto file enforces types at compile time across all languages
- **High throughput** — thousands of requests/sec between services

### Hybrid approach (what this project does):

```
Browser  ──REST──►  Gateway  ──gRPC──►  Backend Services
```

This is the **industry standard**: REST for external clients, gRPC for internal communication.

---

## 12. Benchmark Results

Run the benchmarks yourself:

```bash
cd jkpRegsitrationPOCgrpc/server

# Make sure both REST and gRPC servers are running first
# Then run the benchmark suite from the project root:
uv run python ../../benchmarks/run_all_benchmarks.py
```

### What the benchmarks test:

| Test | What it measures |
|------|-----------------|
| **Latency** | Round-trip time for a single request (p50, p95, p99) |
| **Throughput** | Requests per second under load |
| **Payload Size** | Bytes on the wire for identical data |
| **Serialization** | Time to encode/decode 10,000 messages |
| **Concurrent Load** | Performance under 10/50/100 concurrent clients |
| **Streaming vs Batch** | gRPC streaming vs REST batch fetch for large datasets |
| **Connection Overhead** | Cost of creating new connections |
| **Memory Usage** | RAM consumed by server under load |

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
| Browser support | Native | Needs proxy | REST |

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

### Python (server/pyproject.toml)

| Package | Purpose |
|---------|---------|
| `grpcio` | Core gRPC runtime for Python |
| `grpcio-tools` | Protobuf compiler + Python code generator |
| `grpcio-reflection` | Enables service discovery (grpcurl, Postman) |
| `protobuf` | Protobuf message runtime library |
| `fastapi` | REST gateway for browser clients |
| `uvicorn` | ASGI server for FastAPI |
| `pydantic` | Data validation models |

### Frontend (client/package.json)

The frontend remains unchanged — it talks to the FastAPI gateway via REST.
The gateway internally translates REST → gRPC → REST.
