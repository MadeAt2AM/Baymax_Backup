# OpenCLI Browser Bridge — Cookie Extraction

The OpenCLI daemon (port 19825) exposes a CDP bridge via its Node.js client. This lets you extract **plaintext cookies** directly from the browser's live session — bypassing Chrome's encrypted `Cookies` SQLite blob entirely.

## The Problem with Encrypted SQLite

Chrome 80+ stores cookies in an `encrypted_value` (AES-GCM) column. Decrypting requires:
- The DPAPI key on Windows, or
- Chrome's `Local State` → `os_crypt` → `encrypted_key` (base64 DPAPI on Linux) → DPAPI decrypt → AES-GCM decrypt

`browser_cookie3` tries this path but fails on some cookie types (e.g. Instagram's `sessionid` is HttpOnly and set via subrequest — never written to the SQLite `value` column by Chrome).

## The CDP Bridge Solution

OpenCLI's daemon-client.js exposes `Network.getCookies` via CDP. Since this runs inside the browser process, cookies come back **already decrypted** — including HttpOnly ones.

```javascript
// Node.js ESM — call from anywhere the opencli daemon is reachable
import { sendCommand } from '/usr/local/lib/node_modules/@jackwener/opencli/dist/src/browser/daemon-client.js';

async function getCookies(url, session = 'default') {
  const res = await sendCommand('cookies', {
    session,
    url   // e.g. 'https://www.facebook.com' or 'https://www.instagram.com'
  });
  return Array.isArray(res) ? res : [];
}

// Usage
const fb = await getCookies('https://facebook.com', 'vnc_session');
console.log(fb.map(c => ({ name: c.name, value: c.value.substring(0,20), httpOnly: c.httpOnly })));
```

## Cookie Keys for Each Platform

| Platform | Key cookies | Notes |
|---|---|---|
| Facebook | `c_user`, `xs`, `fr`, `datr`, `sb` | `c_user` = numeric user ID; `xs` = session token |
| Instagram | `sessionid`, `csrftoken`, `ds_user_id`, `mid`, `ig_did` | `sessionid` is HttpOnly; missing = not logged in |
| Twitter | `auth_token`, `ct0` | Already in config.yaml from `agent-reach configure --from-browser` |

## Finding the Right Session Name

OpenCLI session names are arbitrary strings you pass on first `open` command. To find what's active:

```bash
opencli browser list          # list all sessions (active tabs)
opencli browser <session> state  # confirm a session is alive
```

Common pattern — create a named session:
```bash
opencli browser vnc_session open "https://facebook.com"
# All subsequent commands use 'vnc_session'
opencli browser vnc_session state
opencli browser vnc_session cookies ...
```

## OpenCLI Daemon Port

- **Port:** 19825 (hardcoded in `DEFAULT_DAEMON_PORT`)
- **Transport:** HTTP + WebSocket (extension ↔ daemon)
- **Health check:** `curl -s http://127.0.0.1:19825/status`
- **Daemon must be running:** `opencli daemon start` or it's started automatically by the first browser command

## Manual Cookie Verification via eval

If `sendCommand('cookies', ...)` isn't available, use JavaScript evaluation in the page context:

```bash
opencli browser <session> eval "document.cookie"
```

Limitations: **only non-HttpOnly cookies** appear in `document.cookie`. HttpOnly cookies (like Facebook `xs`, Instagram `sessionid`) are invisible here — you need the CDP bridge approach.
