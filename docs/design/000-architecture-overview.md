# Architecture Overview

This document provides a high-level overview of the target production architecture for the JKP Registration system. It maps out the request workflow – the path a user's request takes from their browser all the way to the database and back.

---

## The Target Topology

The system is designed to be self-hosted securely on an internal network, but entirely cloud-ready. We enforce strict boundaries between the UI delivery, browser-to-gRPC translation, business logic, and data storage.

```text
User's Browser (React App)
       │
       │ (1) HTTPS Request (to registration.yourorg.org)
       ▼
┌────────────────────────────────────────────────────────┐
│ Cloudflare (WAF & Zero Trust Tunnel)                   │
│ - Port 443 (HTTPS)                                     │
│ - Absorbs malicious bots / DDoS                        │
│ - Enforces Email OTP login for staff                   │
└──────────────────────────┬─────────────────────────────┘
                           │
                           │ (2) Secure Internal Tunnel (No open router ports)
                           ▼
┌────────────────────────────────────────────────────────┐
│ Edge Web Server (Caddy / Nginx)                        │
│ - Port 443 (HTTPS Termination)                         │
│ - Serves static React files for `/`                    │
│ - Routes `/grpc/` traffic to the proxy                 │
└──────────────────────────┬─────────────────────────────┘
                           │
                           │ (3) grpc-web Request (Internal HTTP/1.1)
                           ▼
┌────────────────────────────────────────────────────────┐
│ grpc-web Proxy (FastAPI Container)                     │
│ - Port 8080 (Internal only)                            │
│ - Translates browser HTTP/1.1 frames to native gRPC    │
└──────────────────────────┬─────────────────────────────┘
                           │
                           │ (4) Native gRPC (Internal HTTP/2 + Protobuf)
                           ▼
┌────────────────────────────────────────────────────────┐
│ Backend gRPC Server (Python/grpcio Container)          │
│ - Port 50051 (Internal only)                           │
│ - Executes business logic                              │
│ - Validates data using Pydantic                        │
└──────────────────────────┬─────────────────────────────┘
                           │
                           │ (5) SQL via asyncpg/psycopg
                           ▼
┌────────────────────────────────────────────────────────┐
│ Database (PostgreSQL Container / Managed DB)           │
│ - Port 5432 (Strictly Private)                         │
│ - Persists Satsangi registration data                  │
│ - Backed up every 3 hours to secondary server          │
└────────────────────────────────────────────────────────┘
```

## The Request Workflow Explained

When a staff member registers a new Satsangi, the following workflow occurs:

1. **The Shield (Cloudflare):** The staff member accesses the URL. Cloudflare intercepts the request, verifies their Email OTP, and securely tunnels them to the office network.
2. **The UI (React):** The staff member fills out the form. The React app creates a strongly-typed `SatsangiCreate` object and calls the generated gRPC client.
3. **The Gateway (Edge Web Server):** The request hits the Edge Web Server. Because the React app and the API share the same domain (`registration.yourorg.org`), the browser sends the request cleanly without triggering complex CORS security blocks. The Edge server sees the `/grpc/` path and forwards it internally.
4. **The Translator (grpc-web Proxy):** Browsers can't speak native gRPC. The proxy catches the `grpc-web` formatted request, strips away the browser-specific wrappers, and extracts the raw, highly-compressed binary protobuf payload.
5. **The Brain (Backend gRPC Server):** The native gRPC server receives the binary payload. It instantly deserializes it into a Python object with guaranteed type safety. It applies business rules and commits the data to PostgreSQL.
6. **The Return Trip:** The database confirms the write. The backend serializes the new `Satsangi` object back to binary. The proxy wraps it in a browser-friendly `grpc-web` frame. The Edge server passes it back through the secure HTTPS tunnel to the React app, which instantly updates the UI.

## Why This Architecture Wins

1. **Security:** Only port 443 (HTTPS) is exposed to the network. The Proxy, Backend, and Database are entirely hidden behind the Edge server.
2. **Performance:** The data contract between the proxy and backend uses native gRPC, which is ~10x faster and ~2.5x smaller than JSON. 
3. **Simplicity:** By serving the UI and the API from the exact same domain, we completely eliminate CORS errors and guarantee that the UI version perfectly matches the API version.
4. **Portability:** The database connection and backend endpoints are injected via Environment Variables. If the organization decides to move the PostgreSQL database to AWS RDS tomorrow, zero lines of Python code need to change.
