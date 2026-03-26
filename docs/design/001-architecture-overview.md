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
│           │ (2) grpc-web Request                       │
│           ▼                                            │
│ ┌────────────────────────────────────────────────────┐ │
│ │ grpc-web Proxy (FastAPI Container)                 │ │
│ └─────────┬──────────────────────────────────────────┘ │
│           │                                            │
│           │ (3) Native gRPC                            │
│           ▼                                            │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Backend gRPC Server (Python/grpcio.aio, async)      │ │
│ │ - Validates Keycloak Auth JWT                      │ │
│ │ - Dispatches async jobs to Queue                   │ │
│ └─────────┬──────────────────────────────────────────┘ │
│           │                                            │
│ ┌─────────▼──────────────────────────────────────────┐ │
│ │ Background Worker (Python Process)                 │ │
│ │ - Executes heavy CSV exports offline               │ │
│ └─────────┬──────────────────────────────────────────┘ │
└───────────┼────────────────────────────────────────────┘
            │
            │ (4) SQL & HTTP (Cross-Server Internal Network)
            ▼
┌────────────────────────────────────────────────────────┐
│ SERVER B: STORAGE NODE (Stateful)                      │
│                                                        │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Primary Database (PostgreSQL Container)            │ │
│ │ - Persists ~200,000 Satsangi records               │ │
│ │ - Acts as Background Task Queue Broker             │ │
│ └────────────────────────────────────────────────────┘ │
│                                                        │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Object Storage (MinIO Container)                   │ │
│ │ - Stores ~400GB+ of Photos & ID Proofs             │ │
│ └────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

*Note: The **Keycloak SSO Identity Provider** can be hosted on either node, or a dedicated Auth server, depending on organizational load.*

## The Request Workflow Explained

When a staff member registers a new Satsangi or requests a large data export, the following workflow occurs across the Site-to-Site VPN:

1. **The Gateway (Compute Server):** The staff member types `registration.jkp.internal`. The Internal DNS resolves this locally. The request hits the Edge Web Server securely over the VPN. 
2. **The Authentication (Keycloak):** The user authenticates via the Keycloak SSO login page. Their browser receives a secure JWT (JSON Web Token) which is attached to all subsequent requests.
3. **The Translator (grpc-web Proxy):** Browsers can't speak native gRPC. The proxy catches the `grpc-web` formatted request, strips away the browser-specific wrappers, and extracts the raw binary protobuf payload.
4. **The Brain (Backend gRPC Server):** The native gRPC server deserializes the payload, validates the Keycloak JWT, applies business rules, and sends a cross-server SQL command to the Storage Node.
5. **Direct Media Upload (MinIO):** If the user uploads a photo, the Compute Node generates a Pre-Signed URL. The browser uses this URL to upload the 1MB photo *directly* to the MinIO container on the Storage Node, bypassing the Python backend entirely to save CPU cycles.
6. **Background Queuing:** If the request is a heavy task (e.g., "Export all users"), the gRPC Server writes a task note to PostgreSQL and instantly replies to the user. The Background Worker process picks up the note, generates the CSV, and saves it to MinIO for later download.
7. **The Backup:** Periodically, the database and MinIO volumes on the Storage Node are safely snapshotted/synced to a tertiary internal server to prevent data loss.

## Why This Architecture Wins

1. **Security:** Only port 443 (HTTPS) is exposed to the network. The Proxy, Backend, and Database are entirely hidden behind the Edge server.
2. **Performance:** The data contract between the proxy and backend uses native gRPC, which is ~10x faster and ~2.5x smaller than JSON. 
3. **Simplicity:** By serving the UI and the API from the exact same domain, we completely eliminate CORS errors and guarantee that the UI version perfectly matches the API version.
4. **Portability:** The database connection and backend endpoints are injected via Environment Variables. If the organization decides to move the PostgreSQL database to AWS RDS tomorrow, zero lines of Python code need to change.
