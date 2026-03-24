# ============================================================
# Stage 1 — Build the React app with Bun (thrown away)
# ============================================================
FROM oven/bun:1-alpine AS builder

WORKDIR /build

COPY client/package.json client/bun.lock ./
RUN bun install --frozen-lockfile

COPY client/ .

# Reads VITE_GRPC_URL from client/.env at build time
RUN bunx vite build

# ============================================================
# Stage 2 — Caddy serves static files + reverse-proxies API
# ============================================================
FROM caddy:2-alpine

COPY --from=builder /build/dist /srv

EXPOSE 80 443
