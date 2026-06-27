---
name: google-workspace-auth
description: "Google Workspace OAuth2 setup, re-authentication, and token refresh for madeat2am.ai@gmail.com. All services: Gmail, Calendar, Drive, Sheets, Docs, Contacts. Companion to bundled google-workspace skill."
version: 1.0.0
author: baymax
platforms: [linux]
tags: [google, oauth, gmail, calendar, drive, sheets, docs, contacts]
---

# Google Workspace — Session Reference (madeat2am.ai@gmail.com)

This skill is a session-specific reference companion to the bundled `google-workspace` skill.
It captures the actual working commands, pitfalls, and credentials for this specific account.

---

## Current Status

✅ **Authenticated** — token valid at `/root/.hermes/google_token.json`

- **Client ID:** `315512698311-gup8nnkd8b7va0q7q5itjbvgtplnct6d.apps.googleusercontent.com`
- **Client Secret:** `/root/.hermes/google_client_secret.json`
- **Token:** `/root/.hermes/google_token.json` (auto-refreshes)
- **venv:** `/root/.hermes/.venv` (Python 3.12, `google-api-python-client` + deps installed)
- **Scopes:** gmail.readonly, gmail.send, gmail.modify, calendar, drive, contacts.readonly, spreadsheets, documents (all Sensitive — requires OAuth review to publish as Production)
- **App status:** Published as Production (Jun 2026) — privacy policy URL required for this

---

## Quick Commands

**Activate venv + set shorthand:**
```bash
cd /root/.hermes && . .venv/bin/activate
GAPI="python3 /root/.hermes/skills/productivity/google-workspace/scripts/google_api.py"
```

**Check auth:**
```bash
cd /root/.hermes && . .venv/bin/activate && python3 /root/.hermes/skills/productivity/google-workspace/scripts/setup.py --check
```

**Generate fresh auth URL:**
```bash
cd /root/.hermes && . .venv/bin/activate && python3 /root/.hermes/skills/productivity/google-workspace/scripts/setup.py --auth-url
```

**Exchange auth code (after user pastes redirect URL):**
```bash
cd /root/.hermes && . .venv/bin/activate && python3 /root/.hermes/skills/productivity/google-workspace/scripts/setup.py --auth-code "PASTE_FULL_REDIRECT_URL"
```

---

## Pitfalls Discovered

### Python deps fail with "externally-managed-environment"
**Symptom:** `setup.py --auth-url` fails with `externally-managed-environment` when using system Python.
**Fix:** Create a venv first:
```bash
cd /root/.hermes && uv venv .venv --python 3.12 && uv pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
```
Always use `. .venv/bin/activate` before running `setup.py` or `google_api.py`.

### OAuth hangs on "Continue with all selected"
**Symptom:** Browser hangs on consent screen, never redirects.
**Fix (in order):**
1. Use **Chrome incognito** — no extensions, no cached sessions
2. Check `chrome://settings/people` — remove extra Google accounts or use Guest mode
3. Confirm test user is added: https://console.cloud.google.com/auth/audience → Test users → Add
4. Generate a **fresh auth URL** — old URLs expire and can't be reused

### Writing client secret from raw strings (no JSON file)
If user provides raw Client ID + Client Secret strings instead of a JSON file, write the JSON manually:
```json
{
  "installed": {
    "client_id": "CLIENT_ID_STRING",
    "client_secret": "CLIENT_SECRET_STRING",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "redirect_uris": ["http://localhost:1"]
  }
}
```
Save to `/root/.hermes/google_client_secret.json`.

### All scopes are Sensitive — no workaround
All 8 scopes (gmail, calendar, drive, sheets, docs, contacts) are classified Sensitive by Google.
No alternative non-sensitive scopes exist for these APIs.
To publish permanently without 7-day re-auth: add privacy policy URL + publish as Production in Google Cloud Console.

---

## Re-authentication Flow (when token expires)

1. Generate URL: `setup.py --auth-url`
2. User opens URL in Chrome incognito (only target account logged in)
3. User approves → browser redirects to `http://localhost:1/?code=...`
4. User copies full URL from address bar and pastes it back
5. Exchange: `setup.py --auth-code "PASTE_URL_HERE"`
6. Verify: `setup.py --check`

---

## Google Cloud Console Links (for reference)

- OAuth consent: https://console.cloud.google.com/apis/credentials/consent
- Test users: https://console.cloud.google.com/auth/audience
- APIs to enable: https://console.cloud.google.com/apis/library
  (Gmail API, Calendar API, Drive API, Sheets API, Docs API, People API)

---

## Files

- Token: `/root/.hermes/google_token.json`
- Client secret: `/root/.hermes/google_client_secret.json`
- venv Python: `/root/.hermes/.venv/bin/python3`
- Setup script: `/root/.hermes/skills/productivity/google-workspace/scripts/setup.py`
- API wrapper: `/root/.hermes/skills/productivity/google-workspace/scripts/google_api.py`
