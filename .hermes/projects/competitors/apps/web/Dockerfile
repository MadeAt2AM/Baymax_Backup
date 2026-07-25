FROM node:22-bookworm-slim AS build

WORKDIR /srv/competitors/web

# Install deps first for better layer caching.
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm install --no-audit --no-fund

# Build the Vite bundle.
COPY apps/web /srv/competitors/web
RUN npm run build

# Runtime: Caddy static-serves the bundle.
FROM caddy:2.8-alpine

COPY --from=build /srv/competitors/web/dist /srv/web
COPY apps/web/Caddyfile /etc/caddy/Caddyfile

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
