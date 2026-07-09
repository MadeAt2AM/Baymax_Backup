---
name: caddy-service-dns-aliases
description: Compose-to-Caddy reverse-proxy gotchas — DNS labels on user-defined networks, MTU=1400 for Hetzner, and Caddy bind-mount sites/ directory.
---

# Caddy + Compose reverse-proxy DNS gotchas

This captures the non-obvious failures I hit bringing SYNTRA up on the dev VPS
behind the existing Caddy container (also used by Payntra / baymax-pipeline-probe).

## Symptom: Caddy returns 502 right after the deploy

The web container is up, nginx listens on `:80`, but Caddy logs show
"looking up host" / "no such host". Doing `docker exec caddy wget syntra-web`
inside the Caddy container says "bad address".

## Cause

On a **user-defined Docker network** (the `web` external network shared by
Caddy), only the container's `container_name` is auto-registered as a DNS
label. The compose *service* name (and any alias with hyphens) is NOT added
unless explicitly declared via `networks.<net>.aliases`.

So if your compose has:

```yaml
services:
  web:
    container_name: syntra_web
    networks:
      web: { ... }
```

…then `syntra_web` resolves, but `syntra-web` (the Caddy file uses hyphens
because that's the convention everywhere else) does NOT.

## Fix

Always alias the canonical "Caddy-facing" name on the shared network:

```yaml
services:
  web:
    container_name: syntra_web
    networks:
      web:
        aliases:
          - syntra-web     # what /srv/caddy/sites/<name>.caddy uses
          - syntra-app     # backwards compat with project_dev.sh patterns
      private:
        aliases:
          - syntra-app
```

Then write `/srv/caddy/sites/<name>.caddy`:

```
<name>.<domain> {
    reverse_proxy <name>-web:80
}
```

`docker exec caddy caddy reload --config /etc/caddy/Caddyfile` picks it up.

## Other pitfalls seen on this VPS

### 1. Hetzner eth0 MTU is 1400; Docker default bridge is 1500

Builds that hit `apt-get update` or `npm/pnpm install` from a clean cache time
out with "Some index files failed to download" because the response fragments
on MTU mismatch. Set globally:

```json
// /etc/docker/daemon.json
{
  "mtu": 1400,
  "default-network-opts": { "bridge": { "com.docker.network.driver.mtu": "1400" } }
}
```

`systemctl restart docker` causes ~5s downtime for ALL containers. Bake this
in on first contact with any Hetzner VPS — see notes from 2026-07-05.

### 2. Compose file with `web: external: true` requires the network to exist

```yaml
networks:
  web:
    name: web
    external: true
```

If the network isn't there the deploy fails with "network not found".
On the dev VPS, `web` already exists and contains Caddy + payntra + probe.

### 3. The Caddyfile mounts `/srv/caddy/sites` from the host

It's a `bind` mount, NOT a volume. Files you write to the host's
`/srv/caddy/sites/*.caddy` are visible to Caddy immediately; reload picks them
up. Hot reload is via `docker exec caddy caddy reload`. Do NOT bounce the
Caddy container for config changes — it disturbs all peer sites.

### 4. For first-time subdomain: Let's Encrypt needs ~30s

On the very first request, Caddy's HTTP-01 challenge fires and the cert gets
provisioned. During this window `curl https://<host>/` may return
`tlsv1 alert internal error` for ~30s before settling to 200.

## Verification checklist

After `docker compose up -d`:

```bash
# 1. Inside the web container
docker exec <name>-web wget -qO- http://127.0.0.1/ | head -c 200

# 2. Inside the Caddy container — CRITICAL alias resolution test
docker exec caddy sh -c "wget -qO- http://<name>-web/ | head -c 200"

# 3. From the host via Caddy
curl -sS -o /dev/null -w "%{http_code}\n" https://<name>.<domain>/api/healthz
```

Step 2 is what catches the alias problem early.
