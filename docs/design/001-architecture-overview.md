# Architecture Overview

This document provides a high-level overview of the target production architecture for the JKP Registration system. It maps out the request workflow – the path a user's request takes from their browser all the way to the database and back.

---

## The Target Topology (Split Server)

The system is designed to be self-hosted securely on an internal network using a Two-Server topology to separate stateless compute from stateful storage.

```text
User's Browser (React App)
       │
       │ (1) HTTPS Request (to registration.jkp.internal)
       ▼
┌────────────────────────────────────────────────────────┐
│ SERVER A: COMPUTE NODE (Stateless)                     │
│                                                        │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Edge Web Server (Caddy / Nginx)                    │ │
│ │ - Port 443 (HTTPS Termination)                     │ │
│ │ - Serves static React files for `/`                │ │
│ └─────────┬──────────────────────────────────────────┘ │
│           │                                            │
│           │ (2) REST / JSON Request (gRPC optional)    │
│           ▼                                            │
│ ┌────────────────────────────────────────────────────┐ │
│ │ ASP.NET Core Application (.NET 8+)                 │ │
│ │ - REST API (Minimal APIs / Controllers)            │ │
│ │ - gRPC available for perf-critical endpoints       │ │
│ │ - Validates Auth JWT (ASP.NET Identity)            │ │
│ │ - BackgroundService workers (in-process)           │ │
│ │   - Executes heavy CSV exports, image processing   │ │
│ └─────────┬──────────────────────────────────────────┘ │
└───────────┼────────────────────────────────────────────┘
            │
            │ (3) SQL & HTTP (Cross-Server Internal Network)
            ▼
┌────────────────────────────────────────────────────────┐
│ SERVER B: STORAGE NODE (Stateful)                      │
│                                                        │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Primary Database (PostgreSQL Container)            │ │
│ │ - Persists ~500,000 Satsangi records               │ │
│ │ - EF Core migrations & data access                 │ │
│ └────────────────────────────────────────────────────┘ │
│                                                        │
│ ┌────────────────────────────────────────────────────┐ │
│ │ SeaweedFS Object Storage (Container)                │ │
│ │ - Stores ~500GB of Photos & ID Proofs              │ │
│ │ - Pre-signed URL uploads (browser-direct)          │ │
│ └────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

*Note: Authentication is handled by **ASP.NET Identity** in Phase 1 (single app). When additional org apps require SSO, the architecture can be extended with **OpenIddict** or migrated to **Keycloak** — see `008-dotnet-architectural-choices.md` §7.*

## The Request Workflow Explained

When a staff member registers a new Satsangi or requests a large data export, the following workflow occurs across the Site-to-Site VPN:

1. **The Gateway (Compute Server):** The staff member types `registration.jkp.internal`. The Internal DNS resolves this locally. The request hits the Edge Web Server securely over the VPN.
2. **The Authentication (ASP.NET Identity):** The user authenticates via the application's login page. Their browser receives a secure JWT (JSON Web Token) which is attached to all subsequent requests. JWT validation is handled by ASP.NET Core's built-in `JwtBearer` middleware.
3. **The API (ASP.NET Core REST):** The browser sends a standard JSON request to the REST API. The controller validates the JWT, applies business rules via the service layer, and sends a cross-server SQL command (via Entity Framework Core) to the Storage Node. For specific performance-critical operations (e.g., bulk data sync), gRPC endpoints can be added alongside REST without any infrastructure changes.
4. **Direct Media Upload (Object Storage):** If the user uploads a photo, the ASP.NET Core backend generates a Pre-Signed URL. The browser uses this URL to upload the file *directly* to the S3-compatible object storage container on the Storage Node, bypassing the .NET backend entirely to save CPU cycles.
5. **Background Processing:** If the request is a heavy task (e.g., "Export all users"), the API pushes the task to an in-process `Channel<T>` queue and instantly replies to the user. A `BackgroundService` worker picks up the task, generates the CSV, and saves it to object storage for later download. For durable/scheduled tasks, Hangfire (PostgreSQL-backed) can be used.
6. **The Backup:** Periodically, the database and object storage volumes on the Storage Node are safely snapshotted/synced to a tertiary internal server to prevent data loss.

## Why This Architecture Wins

1. **Security:** Only port 443 (HTTPS) is exposed to the network. The Backend and Database are entirely hidden behind the Edge server.
2. **Performance:** REST with JSON is more than sufficient for 50-60 concurrent users. gRPC endpoints can be added alongside REST for bulk operations or server-to-server calls if performance demands it.
3. **Simplicity:** The ASP.NET Core server handles REST API, background workers, and optional gRPC services in a single process — only 2 containers on the Compute Node. Serving the UI and API from the same domain eliminates CORS errors entirely.
4. **Portability:** The database connection, object storage endpoint, and backend configuration are injected via Environment Variables. Migrating PostgreSQL to AWS RDS or object storage to AWS S3 requires zero code changes.
5. **Type Safety:** Compile-time enforcement from browser (TypeScript) through the API (C# DTOs) to the database (EF Core) — bugs are caught before code runs.
6. **Debuggability:** REST with JSON means every request/response is inspectable in browser DevTools, testable with `curl`, and auto-documented via Swagger/OpenAPI.
