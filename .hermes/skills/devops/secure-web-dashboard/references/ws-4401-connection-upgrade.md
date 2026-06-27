# WebSocket 4401 / Auth Failed — Root Cause: nginx `auth_basic` Intercepts Upgrade

## Symptoms

- TUI (Chat) page WebSocket fails to connect
- Browser console shows WebSocket `close` event with code `4401`
- Access log: `GET /api/ws?token=<valid> HTTP/1.1" 401 25`
- Same token works for direct WebSocket (no nginx), returns `101 Switching Protocols`
- Backend returns `{"detail":"Unauthorized"}` — same error as invalid token

## Original Misdiagnosis

The first fix attempted was adding `proxy_set_header Connection "upgrade";` because the previous config had `proxy_set_header Connection "";` which stripped the header. That was indeed necessary but **not sufficient**.

Even with `Connection: upgrade` forwarded correctly, the WebSocket still returned 401 through nginx.

## Actual Root Cause

Nginx's `auth_basic` module runs at the **access phase** — before `proxy_pass` is evaluated. The access phase is where nginx checks:

- Is the IP allowed/disallowed?
- Does the request have valid HTTP Basic Auth credentials?

The browser's WebSocket handshake does NOT include `Authorization: Basic` — it only has:
- `Upgrade: websocket`
- `Connection: Upgrade`
- `Sec-WebSocket-Key: ...`
- `?token=<session>` (in query string)

When nginx sees no `Authorization` header on a request to a location protected by `auth_basic`, it returns its own `401 Authorization Required` HTML response immediately — **before forwarding anything to the backend**.

This is why the 401 looked identical to a token validation failure: nginx returns a 401 response with `WWW-Authenticate: Basic realm="Hermes"` as plain HTML, not a WebSocket upgrade rejection.

## Diagnosis

The smoking gun: the 401 response body contains nginx's HTML login prompt, not uvicorn's JSON `{"detail":"Unauthorized"}`:

```
HTTP/1.1 401 Authorization Required
Server: nginx/1.24.0 (Ubuntu)
WWW-Authenticate: Basic realm="Hermes"
Content-Type: text/html

<html><head><title>401 Authorization Required</title></head>...
```

vs. a backend token rejection:

```
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{"detail":"Unauthorized"}
```

Also note: when using `Connection: upgrade` alone (without the `auth_basic` fix), the 401 comes from nginx **before** the backend is involved — you can confirm by checking that the response has `Server: nginx` not `Server: uvicorn`.

## Fix

Add a regex `location` block that matches WebSocket paths and disables `auth_basic`:

```nginx
# Main location — still protected by auth_basic
location / {
    proxy_pass http://127.0.0.1:9119;
    proxy_http_version 1.1;
    proxy_set_header Host 127.0.0.1;          # NOT 127.0.0.1:9119
    proxy_set_header Origin "http://127.0.0.1"; # NOT http://127.0.0.1:9119
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Authorization "";
    proxy_set_header Connection "upgrade";
    proxy_set_header Proxy-Connection "keep-alive";
}

# WebSocket routes — auth_basic DISABLED
# Backend validates token via ?token= query param (HMAC), not nginx
location ~ ^/api/(ws|pty|events|pub)$ {
    proxy_pass http://127.0.0.1:9119;
    proxy_http_version 1.1;
    proxy_set_header Host 127.0.0.1:9119;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Authorization "";
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Proxy-Connection "keep-alive";

    auth_basic off;  # <— critical: bypass nginx Basic Auth for WS routes
}
```

The regex location uses nginx's `~` modifier, which has priority over the prefix `/` location, so requests to `/api/ws?token=...` match the WS location and skip `auth_basic`.

Then reload nginx:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

## Verification

```bash
python3 << 'EOF'
import socket, ssl, base64, re, subprocess

result = subprocess.run(['curl', '-s', 'http://127.0.0.1:9119/'], capture_output=True, text=True)
m = re.search(r'window\.__HERMES_SESSION_TOKEN__=([^;]+)', result.stdout)
token = m.group(1).strip().strip('"').strip("'")

host = 'dashboard.terrybot.top'
key = base64.b64encode(b'test1234test1234').decode()

request = f'GET /api/ws?token={token} HTTP/1.1\r\n'
request += f'Host: {host}\r\n'
request += 'Upgrade: websocket\r\n'
request += 'Connection: Upgrade\r\n'
request += f'Sec-WebSocket-Key: {key}\r\n'
request += 'Sec-WebSocket-Version: 13\r\n'
request += '\r\n'

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with socket.create_connection((host, 443)) as sock:
    with ctx.wrap_socket(sock, server_hostname=host) as ssock:
        ssock.send(request.encode())
        resp = ssock.recv(4096).decode()
        print(resp[:200])
        # Expected: HTTP/1.1 101 Switching Protocols
EOF
```

Expected output: `HTTP/1.1 101 Switching Protocols` — not `401 Authorization Required`.

## Why the 401 Looks the Same

Both the token-mismatch 401 and the nginx auth_basic 401 return `{"detail":"Unauthorized"}` (or nginx's HTML login page) with status 401, making them indistinguishable by code alone. The actual differentiator is:
- `Server: nginx` header in the response → nginx's `auth_basic` rejected it
- `Server: uvicorn` header → backend rejected the token
- `WWW-Authenticate: Basic` header → definitely nginx (backend never sets this for a rejected token)

## Note on Two-Layer Auth

Both layers still serve a purpose even after this fix:
- **Nginx auth_basic**: protects the initial page load and prevents unauthenticated users from even reaching the SPA. It also prevents random internet scanners from probing the dashboard.
- **Backend token (HMAC)**: validates that the SPA talking to the API is the legitimate dashboard session, not a CSRF'd request or a replay from a different context.

Disabling `auth_basic` only for WS routes does not weaken security because the WS endpoints are protected by the backend's own HMAC token validation. The browser must first authenticate via Basic Auth to load the SPA (which injects the session token into `window.__HERMES_SESSION_TOKEN__`), then use that token to establish the WebSocket connection.
