# Tests — JKP Registration gRPC

## Architecture

```
Pytest    → backend brain     (Python: gRPC server + proxy + DB)
Vitest    → frontend brain    (TypeScript: api.ts integration via ConnectRPC)
Playwright → full body        (real browser, UI rendering + navigation)
```

## Folder Structure

```
tests/
├── README.md                        ← you are here
├── requirements.txt                 ← pytest + httpx + grpcio
├── package.json                     ← vitest + playwright (bun)
├── backend/                         ← pytest
│   ├── conftest.py                  ← fixtures: grpc stub, proxy url, cleanup
│   ├── test_health.py               ← /healthz + Health RPC
│   ├── test_create.py               ← CreateSatsangi (gRPC direct + grpc-web proxy)
│   └── test_search.py               ← SearchSatsangis + ListSatsangis
├── frontend/                        ← vitest
│   ├── vitest.config.ts             ← config (points to this dir)
│   ├── tsconfig.json                ← TS config for tests
│   └── api.test.ts                  ← integration tests for api.ts via real server
└── e2e/                             ← playwright
    ├── playwright.config.ts         ← config (auto-starts Vite on :5175)
    └── registration.spec.ts         ← search results, create form, navigation
```

## How gRPC Testing Works

This project has 3 testable boundaries:

```
                 ┌─── Frontend tests (vitest) test the full TS→proxy chain
                 │
Browser ──grpc-web──▶ FastAPI Proxy :8080 ──gRPC──▶ gRPC Server :50051 ──▶ PostgreSQL
                     │                              │
                     └── Backend proxy tests        └── Backend gRPC tests
                         (httpx, raw frames)            (grpcio stub)
```

- **gRPC direct tests** — use `grpcio` Python client to call `:50051` directly.
  Tests the actual business logic without the proxy layer.
- **Proxy tests** — use `httpx` to POST raw grpc-web frames to `:8080`.
  Tests the framing, base64 encoding, error handling.
- **Frontend tests** — import the real `api.ts` and call the server through
  ConnectRPC's grpc-web transport. Verifies the entire TS→proxy→gRPC chain.
- **E2E tests** — Playwright opens a real browser, verifies pages render,
  data loads from the backend, navigation works, and forms render correctly.

## Running

### Prerequisites

```bash
# Server must be running for backend + e2e tests
cd server && uv run task dev

# E2E tests auto-start their own Vite server (port 5175)
# No need to start the client manually
```

### Backend (pytest)

```bash
cd tests
../server/.venv/bin/python -m pytest backend/ -v
```

### Frontend (vitest)

```bash
cd tests
bun run test:unit
```

### E2E (playwright)

```bash
cd tests
bun run test:e2e
```

### All at once

```bash
cd tests
bun run test:all
```

## Long-Term Test Plan

### Current Coverage

| Layer | Tool | What's Tested | Count |
|-------|------|---------------|-------|
| Backend gRPC | pytest + grpcio | All 4 RPCs directly | 8 |
| Backend proxy | pytest + httpx | grpc-web framing, health, errors | 6 |
| Frontend API | vitest | api.ts integration: health, create, list, search | 7 |
| E2E | playwright | Search results, create form rendering, navigation | 7 |

### What to Add Next (when scaling)

| Priority | What | Why |
|----------|------|-----|
| **P0** | Auth tests | When JWT/session auth is added — test protected routes |
| **P1** | DB migration tests | When schema changes — verify migrations run clean |
| **P1** | Concurrent load tests | Verify connection pool under 50+ concurrent requests |
| **P2** | Error boundary tests | Frontend error states, network failures, timeouts |
| **P2** | Proto compatibility tests | Ensure old clients work with new protos (backward compat) |
| **P3** | Performance regression | Track p95 latency over time, alert on regression |
| **P3** | Visual regression | Screenshot comparison for UI changes |

### Test Principles

1. **Tests don't touch other folders** — all test code lives in `tests/`
2. **Tests talk to running servers** — no mocking the DB, no faking gRPC, no brittle mocks
3. **Each layer tests its boundary** — pytest for Python, vitest for TS, playwright for the whole thing
4. **Fast feedback** — unit tests < 5s, integration < 15s, e2e < 30s
5. **Dockerignored** — `tests/` never ships in production images
