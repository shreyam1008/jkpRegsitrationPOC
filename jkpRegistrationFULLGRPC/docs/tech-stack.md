# JKP Registration — Tech Stack & Architecture (Dev Reference)

Last updated: 26 March 2026
Status: Living document — add decisions as they're made.
POC reference: `jkpRegistrationFULLGRPC/`

---

## Summary

Internal web app for satsangi (devotee) registration at JKP ashrams. Self-hosted on internal network behind site-to-site VPN. Two-server topology — stateless compute node + stateful storage node. Target scale: ~200k–500k records, 50–60 concurrent staff, 4–5 geographies.

The POC validates the full vertical slice: React SPA → gRPC-web → FastAPI proxy → async gRPC server → PostgreSQL. Everything async end-to-end. No threads.

---

## Architecture (Request Flow)

```
Browser (React SPA, ConnectRPC)
    │  grpc-web-text (base64, HTTP/1.1 POST)
    ▼
Caddy (TLS termination, static files, compression, HTTP/3)
    │  reverse_proxy (keepalive, health-check)
    ▼
FastAPI grpc-web Proxy (:8080, uvicorn, async)
    │  HTTP/2 multiplexed, singleton grpc.aio channel
    │  identity serializers — raw bytes pass-through, zero deser
    ▼
gRPC Server (:50051, grpc.aio.server, in-process, fully async)
    │  async pooled connections (psycopg v3 AsyncConnectionPool)
    ▼
PostgreSQL 17
```

Target production adds: Keycloak (auth), MinIO (photos/docs), background workers (PG-backed queue), and separates proxy from gRPC server into independent containers.

---

## Frontend

| What | Choice | Version | Notes |
|------|--------|---------|-------|
| Framework | React | 19.2 | |
| Language | TypeScript | 5.9+ | Strict. No `any`. Explicit interfaces everywhere. |
| Build | Vite | 8.x | |
| Package manager | Bun | latest | Replaces npm/yarn everywhere. Lockfile: `bun.lock` |
| Styling | TailwindCSS | 4.2 | Vite plugin (`@tailwindcss/vite`). No CSS-in-JS. |
| Routing | React Router | 7.x | |
| Forms | react-hook-form + zod + @hookform/resolvers | 7.x / 4.x / 5.x | Zod for schema validation, resolver bridges it to RHF |
| Icons | lucide-react | latest | Tree-shakeable, consistent icon set |
| Utility | clsx | 2.x | Conditional class merging |
| gRPC client | @connectrpc/connect + connect-web | 2.x | grpc-web transport. Typed client from generated code. |
| Proto types | @bufbuild/protobuf | 2.x | Auto-generated from `.proto`. Never hand-write proto types. |
| Linting | ESLint 9 + typescript-eslint + react-hooks plugin | latest | |
| Type checking | `tsc -b` (build mode) | — | Part of `bun run build` |

### Frontend rules
- **No `any`.** Use `unknown` + type narrowing if truly unknown.
- **No manual `fetch()` or `axios` to gRPC backend.** All comms via ConnectRPC generated client.
- **Exception:** media uploads use native `fetch` with pre-signed MinIO URLs (future).
- **Server state:** plan to use `@tanstack/react-query` for caching/retries/loading states.
- **Local UI state:** `useState` / React Context. No Redux unless complexity demands it.
- **UI primitives** live in `src/components/ui/`. Reusable, accessible (`useId` for labels).
- **Design system:** Inter font, brand indigo palette (`--color-brand-*`), custom scrollbar, CSS grid animations.

---

## Proto / API Contract

| What | Choice | Notes |
|------|--------|-------|
| IDL | Protocol Buffers 3 (`proto3`) | Single source of truth for data shape |
| Package | `jkp.registration.v1` | Versioned package for future evolution |
| TS codegen | `buf` CLI + remote plugin (`buf.build/bufbuild/es`) | Outputs to `client/src/generated/` |
| Python codegen | `grpcio-tools` (via `uv run python -m grpc_tools.protoc`) | Outputs to `server/app/generated/` |
| Generation script | `./proto/generate` | Single bash script, generates both languages, fixes Python imports via `sed` |

### Why proto / gRPC
- Strict compile-time contract between frontend and backend. No type drift.
- ~10x faster serialization, ~2.5x smaller payloads vs JSON.
- Schema evolution via numbered field tags — add/remove fields without breaking old clients.
- AI tooling makes debugging binary payloads easy.

### Current RPCs

| RPC | What it does |
|-----|-------------|
| `CreateSatsangi` | Register new devotee → returns full record with generated ID |
| `SearchSatsangis` | ILIKE search across 12 fields |
| `ListSatsangis` | Paginated list (limit/offset), returns total_count |
| `Health` | Service liveness + DB connectivity check |

---

## Backend

| What | Choice | Version | Notes |
|------|--------|---------|-------|
| Language | Python | ≥3.12 | |
| gRPC server | grpcio (`grpc.aio`) | 1.78 | Fully async. No ThreadPoolExecutor. |
| gRPC reflection | grpcio-reflection | 1.78 | Enables grpcurl/grpcui/Postman discovery |
| Protobuf runtime | protobuf | 6.33 | |
| HTTP proxy | FastAPI | 0.135 | **Only** for grpc-web proxy + webhooks. No business logic here. |
| ASGI server | uvicorn | 0.41 | Single worker (in-process gRPC binds :50051) |
| DB driver | psycopg v3 (async, binary) | ≥3.2 | `psycopg[binary]` |
| DB pool | psycopg-pool (`AsyncConnectionPool`) | ≥3.2 | 2–20 conns, auto-recovery, retry on boot (5 attempts, 2s backoff) |
| Validation | Pydantic | 2.12 | Models for internal data, proto conversion in servicer |
| Linting | Ruff | 0.15 | Rules: E, F, I, UP. Line length 100. |
| Type checking | Pyright (strict) | — | `exclude: app/generated` |
| Task runner | taskipy | ≥1.14 | `uv run task dev` |
| Package manager | uv | latest | Lockfile: `uv.lock`. No pip/poetry. |

### Backend rules
- **FastAPI is a dumb proxy.** Core logic lives in gRPC servicers. FastAPI's job: translate grpc-web frames ↔ native gRPC. Period.
- **Generated code is isolated.** `app/generated/` — never edit, never put logic here.
- **All functions are async.** Proxy, servicer, store, DB pool — zero blocking calls on the event loop.
- **Identity serializers in proxy.** Raw protobuf bytes pass through without deserialize/re-serialize. Proxy only handles framing.
- **Strict type hints.** All function args and return types. `typing` module, `from __future__ import annotations`.
- **Connection pooling mandatory.** Every DB call goes through `get_conn()` → `AsyncConnectionPool`. Never raw `psycopg.connect()`.
- **Streaming for large datasets.** Don't load 50k rows into RAM. Use cursors + generators.
- **Background tasks >1–2s** must be decoupled from the request cycle (PG-backed queue, Phase 1).

### How the grpc-web proxy works (POC, in-process)
1. Browser sends ConnectRPC grpc-web-text (base64, 5-byte framed protobuf) via POST
2. FastAPI catch-all decodes frame, extracts raw protobuf bytes
3. Forwards to in-process gRPC server via async `channel.unary_unary()` with identity serializers
4. Wraps response in grpc-web DATA + TRAILER frames, base64-encodes, returns

Production plan: separate proxy and gRPC server into independent containers.

---

## Database

| What | Choice | Notes |
|------|--------|-------|
| Engine | PostgreSQL | 17 (Alpine image in Docker) |
| Schema management | `CREATE TABLE IF NOT EXISTS` at app startup + `init.sql` for Docker | Alembic deferred to when first migration is needed |
| Search | ILIKE across 12 columns (POC). Target: `pg_trgm` + full-text search for fuzzy matching at scale |
| Indexes | name (lower), phone, email (partial) | |
| Connection | Env vars: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | App is DB-location-agnostic. Can swap to RDS with zero code changes. |
| Backups (target) | Automated `pg_dump` to secondary in-house server. WAL archiving as stretch goal. | |

---

## Infrastructure & Deployment

| What | Choice | Notes |
|------|--------|-------|
| Containers | Docker Compose | Separate compose files: app server vs DB server |
| Web server / TLS | Caddy 2 | Auto-TLS (internal CA for LAN, Let's Encrypt option). HTTP/3. Zstd+Gzip. Security headers (HSTS, CSP, X-Frame, etc). |
| Tunnel (POC) | Cloudflare Tunnel | For internet access during POC. Production uses site-to-site VPN instead. |
| Client image | Multi-stage: `oven/bun:1-alpine` → build → `caddy:2-alpine` (serves static) | |
| Server image | Multi-stage: `python:3.12-slim` + uv → build → `python:3.12-slim` + libpq5 | Runs as non-root `appuser` |
| CI/CD (target) | GitHub Actions → build images → push to registry. Deploy: manual pull on VPN server. | Hybrid: automated build, manual deploy. |

### Production topology (target)
- **Server A (Compute, stateless):** Caddy + grpc-web proxy + gRPC backend + Keycloak + background workers
- **Server B (Storage, stateful):** PostgreSQL + MinIO
- **Staging:** Single machine running the full stack. Not backed up.
- **Network:** Site-to-site VPN across 4–5 offices. App is invisible to public internet.

### Caddy responsibilities
- TLS termination (self-signed on LAN, Cloudflare on internet)
- Serve static React SPA from `/srv` with immutable cache headers on hashed assets
- Reverse proxy API traffic to backend with keepalive + health polling
- SPA fallback (`try_files {path} /index.html`)
- Security headers, rate limiting, body size limits

---

## Auth

| What | Choice | Notes |
|------|--------|-------|
| POC | Hardcoded client-side (`admin`/`admin123`, localStorage) | Not for production |
| Production | Keycloak (self-hosted, OIDC) | Free, no user limits, SSO hub for future apps |
| JWT validation | gRPC interceptor on backend | Proxy passes token through, backend validates |
| Public self-reg (Phase 2) | Firebase OTP | SMS verification, no Keycloak account needed |

---

## File Storage (Target)

| What | Choice | Notes |
|------|--------|-------|
| Engine | MinIO (self-hosted, S3-compatible) | On storage node |
| Upload path | Browser → pre-signed URL → direct PUT to MinIO | Bypasses Python backend entirely |
| URL generation | gRPC RPC returns pre-signed URL | Backend generates, client uploads directly |
| Backup | MinIO built-in mirroring to secondary server | |
| Budget | <200GB total for photos + ID proofs + Form C docs | |

---

## Testing

| Layer | Tool | What it covers |
|-------|------|----------------|
| Backend gRPC | pytest + grpcio | All RPCs directly against :50051 |
| Backend proxy | pytest + httpx | grpc-web framing, base64 encoding, error codes |
| Frontend API | vitest | `api.ts` integration through real running server |
| E2E | Playwright | Real browser — pages render, data loads, nav works, forms work |

### Test principles
- **No mocking.** Tests talk to running test servers. No fake DB, no fake gRPC.
- **Each layer tests its boundary.** pytest for Python, vitest for TS, Playwright for everything.
- **Fast.** Unit <5s, integration <15s, e2e <30s.
- **Isolated.** `tests/` dir never ships in production images (dockerignored).

---

## Dev Tooling

| Tool | What it does |
|------|-------------|
| `bun` | JS package manager + script runner. Replaces npm everywhere. |
| `uv` | Python package manager. Replaces pip/poetry. |
| `buf` | Protobuf codegen (TS). Remote plugin, no local protoc needed for TS. |
| `grpcio-tools` | Protobuf codegen (Python). Guarantees protobuf version compatibility. |
| `ruff` | Python lint + format + import sort. Single tool. |
| `pyright` | Python type checker. Strict mode. |
| `grpcui` | Browser GUI for gRPC. Like Swagger UI for gRPC. |
| `taskipy` | Python task runner (`uv run task dev`). |

---

## Dev Commands

```bash
# Frontend
cd client && bun run dev          # Vite dev server (:5174)
cd client && bun run build        # Production build

# Backend
cd server && uv run task dev      # FastAPI + gRPC (:8080 / :50051)

# Proto generation (both languages)
cd proto && ./generate

# Database (local dev)
docker compose -f docker-compose.db.yml up -d

# Full deploy
docker compose up -d --build

# Tests
cd tests && ../server/.venv/bin/python -m pytest backend/ -v
cd tests && bun run test:unit
cd tests && bun run test:e2e
cd tests && bun run test:all

# gRPC debugging
grpcurl -plaintext localhost:50051 list
```


## What's Not Built Yet (Production Gaps)

- [ ] Real auth (Keycloak integration, JWT validation)
- [ ] Role-based access control (5 roles)
- [ ] Photo upload (MinIO + pre-signed URLs)
- [ ] Background job queue (PG-backed)
- [ ] pg_trgm / full-text search indexes
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Database migrations tooling (Alembic)
- [ ] Audit log
- [ ] Bulk import/export (CSV)
- [ ] Printer setup for ID card printing
- [ ] Sentry integration (frontend + backend)
