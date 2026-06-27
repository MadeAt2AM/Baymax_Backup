# Hermes Dashboard Auth Architecture

## Overview

The Hermes dashboard uses a **two-layer auth** architecture:
1. **Layer 1 — Nginx HTTP Basic Auth**: Protects the initial page load. The browser caches credentials and sends them on every subsequent request to the domain automatically.
2. **Layer 2 — Hermes Session Token**: The SPA validates API calls using a per-session HMAC token injected into `window.__HERMES_SESSION_TOKEN__` by the backend.

## Auth Flow

```
Browser                    Nginx                    Backend (127.0.0.1:9119)
  |                           |                              |
  |-- GET / ---------------→ |                              |
  |   (no auth header)       |-- GET / -------------------→ |
  |                           |   (Host: 127.0.0.1:9119)     |
  |←─ 401 Basic Auth -------- |←─ 200 HTML ----------------- |
  |   (nginx serves its      |   (backend returns SPA)       |
  |    login dialog)         |                              |
  |                           |                              |
  |-- GET / (Basic Auth) --→ |                              |
  |   Authorization: Basic   |-- (nginx validates Basic)    |
  |                           |-- GET / -------------------→ |
  |                           |   (Authorization: "" stripped|
  |                           |    by proxy_set_header)      |
  |←─ 200 HTML + JS --------- |←─ 200 HTML ----------------- |
  |   + window.__HERMES_SESSION_TOKEN__                     |
  |   = "abc123..."          |                              |
  |                           |                              |
  | [Browser JS runs, extracts token, makes XHR calls]       |
  |                           |                              |
  |-- GET /api/sessions ----→ |                              |
  |   Authorization: Basic   |-- (nginx validates Basic)    |
  |   X-Hermes-Session-Token:|   (Authorization stripped)   |
  |     "abc123..."          |-- GET /api/sessions ------→ |
  |                           |   X-Hermes-Session-Token:  |
  |                           |     "abc123..."             |
  |                           |   (no Authorization header) |
  |←─ 200 JSON -------------- |←─ 200 JSON ---------------- |
```

## Hermes Session Token

- Generated on each dashboard startup: `secrets.token_urlsafe(32)` → HMAC-SHA256 signed
- Injected into page HTML: `window.__HERMES_SESSION_TOKEN__ = "hex_token"`
- Read by the SPA's `lh()` function from `window.__HERMES_SESSION_TOKEN__`
- Sent by the SPA on all API XHR calls via `X-Hermes-Session-Token` header
- For WebSocket upgrades: appended as `?token=<session>` query param

## Nginx `auth_basic` + Header Stripping

Nginx's `auth_basic` module intercepts the request BEFORE proxying. It:
1. Receives the request with `Authorization: Basic <base64>`
2. Validates credentials against `htpasswd` file
3. **Consumes** the header — backend never sees it (unless explicitly forwarded)

If you forward it with `proxy_set_header Authorization $http_authorization`, the backend receives `Authorization: Basic ...` which conflicts with its own session-token auth mechanism.

**The fix:** `proxy_set_header Authorization "";` — nginx strips the consumed Basic Auth header before proxying.

## WebSocket Authentication

WebSocket endpoints (`/api/ws`, `/api/events`, `/api/pty`) use a different path:
- Token passed via query param: `wss://domain/api/ws?token=<session>`
- Backend validates using `hmac.compare_digest(token, _SESSION_TOKEN)`
- **Connection header is critical**: uvicorn requires `Connection: Upgrade` to be present. Setting `proxy_set_header Connection ""` removes it and causes 401 on WS upgrade.

### Host / Origin Port-Stripping for Hermes

Hermes's uvicorn server has a `_is_accepted_host` check that validates the `Host` header against `bound_host` (configured as `127.0.0.1`). It compares **without the port** — `127.0.0.1:9119` does NOT match `127.0.0.1`. The same applies to the `Origin` header for WebSocket validation.

**All three headers must be port-free when forwarded by nginx:**

```nginx
# Correct — port stripped
proxy_set_header Host 127.0.0.1;          # NOT 127.0.0.1:9119
proxy_set_header Origin "http://127.0.0.1"; # NOT http://127.0.0.1:9119

# Wrong — causes 403 on all requests through nginx
proxy_set_header Host 127.0.0.1:9119;       # uvicorn rejects this
```

The `_is_accepted_host` check causes Hermes to return `403 Forbidden` or `400 Bad Request` (depending on whether the port mismatch triggers the HTTP rejection path or the WebSocket rejection path), and the request never reaches the actual auth logic.

### The `auth_basic` Interception Problem

**This is why `Connection: Upgrade` alone was insufficient to fix WebSocket 401 through nginx.**

Even with `proxy_set_header Connection "upgrade"` set on the main `/` location block, nginx's `auth_basic` module runs at the **access phase** — before `proxy_pass` is ever reached. When the browser initiates a WebSocket upgrade (e.g. `wss://dashboard.terrybot.top/api/ws?token=...`):

1. Nginx receives the HTTP/1.1 upgrade request
2. `auth_basic` checks the request **before** routing to `proxy_pass`
3. The browser's WebSocket handshake does NOT carry `Authorization: Basic` — it only carries the WebSocket upgrade headers plus `?token=` in the query string
4. Nginx sees no Basic Auth credentials and returns its own `401 Authorization Required` HTML response
5. Uvicorn never sees the request — the 401 comes from nginx itself

The fix is to disable `auth_basic` for WebSocket routes using a regex `location` block that matches `/api/ws`, `/api/pty`, `/api/events`, and `/api/pub`. The backend itself validates the `?token=` param via HMAC — nginx does not need to (and should not) authenticate these requests.

```nginx
# Disable auth_basic for WebSocket endpoints — backend owns WS auth via ?token=
location ~ ^/api/(ws|pty|events|pub)$ {
    auth_basic off;
    proxy_pass http://127.0.0.1:9119;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    # ... other headers
}
```

## Key nginx directives

```nginx
# Strip Authorization after auth_basic consumes it
proxy_set_header Authorization "";

# Preserve WebSocket upgrade header
proxy_set_header Connection "upgrade";
```

## htpasswd Pitfall

If `htpasswd` has **duplicate entries** for the same user (different hashes), nginx checks them in order and any wrong one causes intermittent 401s. Always ensure only ONE entry per user:

```bash
# Check for duplicates
sudo cat /etc/nginx/.htpasswd

# Regenerate cleanly
sudo htpasswd -c -b /etc/nginx/.htpasswd chrisspeaks Cris0037
```