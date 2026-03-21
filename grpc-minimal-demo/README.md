# gRPC Minimal Demo

A stripped-down gRPC example: **one proto, one RPC, one table**.  
Reads devotees from the same PostgreSQL database the REST POC uses.

## Architecture

```
┌─────────────┐   HTTP/1.1    ┌──────────────┐   HTTP/2     ┌──────────────┐
│ React Client │ ──grpc-web──► │ Proxy (FastAPI)│ ──gRPC────► │ gRPC Server  │ ──SQL──► PostgreSQL
│ :5175        │ ◄──────────── │ :8080          │ ◄────────── │ :50051       │         (devotees)
└──────────────┘               └────────────────┘             └──────────────┘
```

## Files (read in this order)

1. **`server/proto/devotee.proto`** — The contract. Defines `Devotee` message + `ListDevotees` RPC.
2. **`server/app/grpc_server.py`** — gRPC server. Queries PostgreSQL, returns protobuf.
3. **`server/app/main.py`** — grpc-web proxy. Translates browser requests → real gRPC.
4. **`client/src/generated/devotee_pb.ts`** — TypeScript protobuf classes (match the proto).
5. **`client/src/generated/DevoteeServiceClientPb.ts`** — grpc-web client (calls the proxy).
6. **`client/src/api.ts`** — API layer. Converts protobuf → plain TypeScript objects.
7. **`client/src/App.tsx`** — React component. Calls `listDevotees()`, renders table.

## Running

```bash
# Terminal 1: Start server (proxy + gRPC server both start)
cd server
uv run python -m uvicorn app.main:app --port 8080

# Terminal 2: Start React client
cd client
bun install
bun run dev
# Open http://localhost:5175
```

## Key Concepts

- **Proto file** = the contract between client and server
- **gRPC server** = serves data as binary protobuf over HTTP/2
- **grpc-web proxy** = bridges browser (HTTP/1.1) to gRPC (HTTP/2)
- **Protobuf classes** = typed objects that serialize to/from binary
- The browser never sends JSON — it sends **real protobuf binary**
