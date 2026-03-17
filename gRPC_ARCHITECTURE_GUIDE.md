# gRPC Architecture Guide - JKP Registration POC

## Why gRPC in This Project?

This project demonstrates **gRPC vs REST** for the same business application (satsangi registration). The gRPC version shows how modern microservices communicate efficiently.

## The Core Problem gRPC Solves

**REST (HTTP/1.1 + JSON)**:
- Text-based payloads (~3-5x larger)
- One request per TCP connection
- No streaming support
- Runtime type validation

**gRPC (HTTP/2 + Protocol Buffers)**:
- Binary payloads (compact, fast)
- Multiplexed connections
- Native streaming
- Compile-time type safety

## Architecture Overview

```
┌─────────────────┐    HTTP/1.1     ┌──────────────────┐    HTTP/2     ┌─────────────────┐
│   React Client  │ ──────────────► │  Proxy Server    │ ────────────► │  gRPC Server    │
│   :5174         │                 │  :8080           │               │  :50051         │
│   (Browser)     │ ◀────────────── │  (FastAPI)       │ ◀─────────── │  (grpcio)       │
└─────────────────┘   grpc-web      └──────────────────┘   gRPC       └─────────────────┘
```

## Why the Proxy? Browser Limitations

Browsers cannot speak native gRPC because:
- No HTTP/2 framing control
- No trailer support (gRPC uses these for status codes)
- No bidirectional streaming

**Solution**: gRPC-web protocol (in browser) + proxy translation (on application server)

## Data Flow: CreateSatsangi Example

### 1. Browser (React)
```typescript
// Create protobuf object
const req = new SatsangiCreate()
req.setFirstName("Ravi")
req.setLastName("Sharma")

// gRPC-web library handles:
// - Object → binary protobuf
// - Wrap in 5-byte frame: [Flag:1][Length:4][Data:N]
// - Base64 encode for HTTP/1.1
// - POST to proxy
```

### 2. Proxy (Port 8080)
```python
# Extracts protobuf from gRPC-web frame
proto_payload = _decode_grpc_web_frame(body)

# Forwards to gRPC server via HTTP/2
channel = grpc.insecure_channel("localhost:50051")
response = channel.unary_unary(method)(proto_payload)
```

### 3. gRPC Server (Port 50051)
```python
# gRPC framework automatically:
# - Receives HTTP/2 stream
# - Deserializes binary → SatsangiCreate object
# - Calls your service method
def CreateSatsangi(self, request, context):
    # request is typed object, not binary!
    create_data = _proto_to_create(request)
    return store.create_satsangi(create_data)
```

## Protocol Buffers: The Type System

### Contract (.proto file)
```protobuf
message SatsangiCreate {
  string first_name = 1;    // Field numbers = efficient encoding
  string last_name = 2;
  string phone_number = 3;
}

service SatsangiService {
  rpc CreateSatsangi(SatsangiCreate) returns (Satsangi);
}
```

### Generated Code (What you use)

#### Server-Side (Python) - Auto-generated
```bash
# Generated at build time
python -m grpc_tools.protoc \
  -I proto \
  --python_out=app/generated \
  --grpc_python_out=app/generated \
  proto/satsangi.proto
```

```python
# Auto-generated classes
request = satsangi_pb2.SatsangiCreate()
request.first_name = "Ravi"  # Typed access!
request.last_name = "Sharma"

# Binary serialization handled automatically
binary = request.SerializeToString()
```

#### Client-Side (TypeScript) - Manual Implementation
```typescript
// Hand-written classes using google-protobuf
export class SatsangiCreate extends jspb.Message {
  getFirstName(): string { return _get(this, 1, '') as string }
  setFirstName(v: string) { _set(this, 1, v) }
  // ... 29 more fields
}

// Usage in React
const req = new SatsangiCreate()
req.setFirstName("Ravi")
req.setLastName("Sharma")
```

## Performance Benefits

| Metric | REST | gRPC | Improvement |
|--------|------|------|-------------|
| Payload size | ~950 bytes | ~390 bytes | 2.4x smaller |
| Serialization | 383ms (10K msgs) | 39ms (10K msgs) | 9.9x faster |
| Concurrent throughput | 6.9 rps | 11.7 rps | 1.7x higher |

## What You Write vs What Libraries Do

### You Write (Business Logic)
- ✅ `.proto` file (data contract)
- ✅ Service implementation (business rules)
- ✅ Database operations
- ✅ Protobuf ↔ Pydantic conversions
- ✅ Frontend API wrappers

### Libraries Handle (Protocol Details)
- ✅ Binary serialization/deserialization
- ✅ HTTP/2 frame management
- ✅ gRPC-web frame wrapping
- ✅ Code generation from `.proto`
- ✅ Network transport

## When to Use gRPC vs REST

### Use REST when:
- Public-facing APIs
- Simple CRUD operations
- Human-readable debugging needed
- Team unfamiliar with gRPC

### Use gRPC when:
- Microservice-to-microservice communication
- High throughput requirements
- Real-time streaming needed
- Strong type safety required
- Polyglot systems (different languages)

## Key Files in This Project

```
jkpRegistrationFULLGRPC/
├── server/
│   ├── proto/satsangi.proto          # Contract
│   ├── app/grpc_server.py            # gRPC service implementation
│   ├── app/main.py                   # gRPC-web proxy
│   └── app/generated/                # Auto-generated code
└── client/src/generated/              # TypeScript protobuf classes
```

## Running the gRPC Version

```bash
# Terminal 1: Start both proxy and gRPC server
cd jkpRegistrationFULLGRPC/server
uv run python -m uvicorn app.main:app --port 8080

# Terminal 2: Start React client
cd jkpRegistrationFULLGRPC/client
bun run dev
# Open http://localhost:5174
```

## Summary

gRPC in this project demonstrates:
- **End-to-end type safety** from browser to database
- **High-performance binary communication** vs JSON
- **Modern microservice patterns** with protocol translation
- **Real-world browser limitations** and how gRPC-web solves them

The proxy is the bridge that makes gRPC work in browsers while maintaining all its benefits for server-to-server communication.
