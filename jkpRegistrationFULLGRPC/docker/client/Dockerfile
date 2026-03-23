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
# Stage 2 — Serve with nginx:alpine (~75 MB final image)
# ============================================================
FROM nginx:1.27-alpine AS runtime

RUN rm /etc/nginx/conf.d/default.conf

COPY docker/client/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html

RUN chown -R nginx:nginx /usr/share/nginx/html \
    && chown -R nginx:nginx /var/cache/nginx \
    && chown -R nginx:nginx /var/log/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid

USER nginx

EXPOSE 3000

ENTRYPOINT ["nginx", "-g", "daemon off;"]
