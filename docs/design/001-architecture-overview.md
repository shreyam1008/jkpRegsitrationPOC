# Architecture Overview

This document provides a high-level overview of the target production architecture for the JKP Registration system. It maps out the request workflow – the path a user's request takes from their browser all the way to the database and back.

---

## The Target Topology

The system is designed to be self-hosted securely on an internal network, but entirely cloud-ready. We enforce strict boundaries between the UI delivery, browser-to-gRPC translation, business logic, and data storage.

```text
User's Browser (React App)
       │
       │ (1) HTTPS Request (to registration.jkp.internal)
       ▼
┌────────────────────────────────────────────────────────┐
│ Edge Web Server (Caddy / Nginx)                        │
│ - Port 443 (HTTPS Termination)                         │
│ - Resolved via Internal DNS (No public internet)       │
│ - Serves static React files for `/`                    │
│ - Routes `/grpc/` traffic to the proxy                 │
└──────────────────────────┬─────────────────────────────┘
                           │
                           │ (2) grpc-web Request (Internal HTTP/1.1)
                           ▼
┌────────────────────────────────────────────────────────┐
│ grpc-web Proxy (FastAPI Container)                     │
│ - Port 8080 (Internal only)                            │
│ - Translates browser HTTP/1.1 frames to native gRPC    │
└──────────────────────────┬─────────────────────────────┘
                           │
                           │ (3) Native gRPC (Internal HTTP/2 + Protobuf)
                           ▼
┌────────────────────────────────────────────────────────┐
│ Backend gRPC Server (Python/grpcio Container)          │
│ - Port 50051 (Internal only)                           │
│ - Validates SuperTokens Auth JWT                       │
│ - Executes business logic                              │
└──────────────────────────┬─────────────────────────────┘
                           │
                           │ (4) SQL via asyncpg/psycopg
                           ▼
┌────────────────────────────────────────────────────────┐
│ Primary Database (PostgreSQL Container)                │
│ - Port 5432 (Strictly Private)                         │
│ - Persists Satsangi registration data                  │
│ - Backed up via automated scheduled snapshots          │
└────────────────────────────────────────────────────────┘
```

## The Request Workflow Explained

When a staff member registers a new Satsangi, the following workflow occurs across the Site-to-Site VPN:

1. **The Gateway (Edge Web Server):** The staff member types `registration.jkp.internal`. The Internal DNS resolves this locally. The request hits the Edge Web Server securely over the VPN. Because the React app and the API share the same domain, the browser sends the request cleanly without triggering complex CORS security blocks. 
2. **The Authentication (SuperTokens):** The user authenticates via the application-specific SuperTokens UI. Their browser receives a secure JWT (JSON Web Token) which is attached to all subsequent gRPC requests.
3. **The Translator (grpc-web Proxy):** Browsers can't speak native gRPC. The proxy catches the `grpc-web` formatted request, strips away the browser-specific wrappers, and extracts the raw, highly-compressed binary protobuf payload along with the auth headers.
4. **The Brain (Backend gRPC Server):** The native gRPC server receives the binary payload. It instantly deserializes it into a Python object with guaranteed type safety, validates the SuperTokens JWT, applies business rules, and commits the data to PostgreSQL.
5. **The Backup:** Periodically, the database state is safely snapshotted and stored on a secondary internal server to prevent data loss. (Continuous WAL streaming may also run in the background).

## Why This Architecture Wins

1. **Security:** Only port 443 (HTTPS) is exposed to the network. The Proxy, Backend, and Database are entirely hidden behind the Edge server.
2. **Performance:** The data contract between the proxy and backend uses native gRPC, which is ~10x faster and ~2.5x smaller than JSON. 
3. **Simplicity:** By serving the UI and the API from the exact same domain, we completely eliminate CORS errors and guarantee that the UI version perfectly matches the API version.
4. **Portability:** The database connection and backend endpoints are injected via Environment Variables. If the organization decides to move the PostgreSQL database to AWS RDS tomorrow, zero lines of Python code need to change.
