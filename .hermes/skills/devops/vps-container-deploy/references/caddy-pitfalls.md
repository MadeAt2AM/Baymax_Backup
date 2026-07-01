# Caddy v2 — config pitfalls

Quick reference for the traps that produced silent restart loops or useless containers this session. Each entry has the trigger, what shows up, and the fix.

## Trap 1 — `auto_https on` is invalid syntax

**Trigger:** Copying Caddy examples from older blog posts that show `auto_https on` in global options.

**Symptom (docker logs):**
```
{"level":"info","msg":"using config from file","file":"/etc/caddy/Caddyfile"}
Error: adapting config using caddyfile: parsing caddyfile tokens for 'auto_https':
  auto_https must be one of 'off', 'disable_redirects', 'disable_certs', or 'ignore_loaded_certs',
  at /etc/caddy/Caddyfile:<line>
```

Container restart-loops every 2-3 seconds.

**Why:** `auto_https` is a top-level directive that takes an enum, not a bool. It's enabled by default — setting it does nothing useful.

**Fix:** Drop the line entirely. To disable per-site:
```caddy
my-site.example.com {
    auto_https off
    reverse_proxy ...
}
```

## Trap 2 — empty `import` glob → Caddy resets every request

**Trigger:** Deploy Caddy without any per-site blocks yet.

**Symptom (curl):**
```
curl: (35) Recv failure: Connection reset by peer
```

Caddy's HTTP log shows nothing useful — the daemon is fine, no listener error. `docker logs caddy` shows the config adopted successfully with:
```
{"level":"warn","msg":"No files matching import glob pattern","pattern":"/etc/caddy/sites/*.caddy"}
```

**Why:** With zero site blocks, Caddy doesn't know what to do with HTTP traffic on port 80/443. It accepts the connection then resets.

**Fix:** Drop a placeholder site block when smoke-testing:
```bash
echo 'smoketest.example.com { respond "Caddy OK" }' \
  > /srv/caddy/sites/_smoketest.caddy
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
curl --resolve smoketest.example.com:80:$VPS_IP http://smoketest.example.com/
# Expect 308 redirect to HTTPS (Caddy enforcing TLS)
```

## Trap 3 — `systemctl reload` doesn't propagate to socket-activated listeners

**Trigger:** Updating Caddy config on Ubuntu 24.04 (or any systemd socket-activated service).

**Symptom:** New config in `/srv/caddy/Caddyfile` and per-site files, but Caddy serves the old behaviour. `caddy reload` inside the container seemingly succeeds, no errors.

**Why:** On socket-activated services, the **service** unit is just a no-op wrapping the socket. The actual `sshd` / `caddy` process is the listener. `systemctl reload ssh.service` doesn't restart the listener — only `systemctl restart ssh.socket` re-evaluates the socket (and starts a fresh listener if needed).

**Fix:**
```bash
docker exec caddy caddy reload --config /etc/caddy/Caddyfile   # reload config inside container
systemctl restart caddy.socket                                  # for host-level services: bounce the socket
```

For Caddy in Docker (our setup), the docker-level `docker exec caddy caddy reload --config /etc/caddy/Caddyfile` IS the equivalent — but also `docker compose restart caddy` works. Both reload semantically.

## Trap 4 — per-site block needs the cert name match

**Trigger:** Setting up `<name>.example.com` but the A record points to the wrong IP, or the wildcard cert doesn't apply.

**Symptom:** Caddy logs say `obtaining new certificate` repeatedly, eventually times out.

**Why:** Let's Encrypt HTTP-01 challenge requires reaching your server on the requested hostname. If DNS doesn't resolve, the challenge fails.

**Fix:** Before deploying, verify DNS propagated:
```bash
dig +short myapp.example.com      # should match VPS IP
curl http://myapp.example.com/.well-known/acme-challenge/test  # should reach Caddy
```

## Trap 5 — reloading with active TLS handshake in progress

**Trigger:** Reloading Caddy config immediately after the previous deploy's cert acquisition.

**Symptom:** Caddy logs say `loading cert from storage failed` or `previous certificate still being processed`.

**Why:** ACME state machine in Caddy has cooldown periods. Reloading mid-flight drops in-flight requests.

**Fix:** Add a small sleep before reload:
```bash
sleep 2
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

## Useful debug commands

```bash
docker logs caddy 2>&1 | tail -30               # recent log lines
docker exec caddy caddy adapt --config /etc/caddy/Caddyfile   # validate WITHOUT deploying
docker exec caddy caddy list-certificates       # cert inventory
curl -v --resolve myapp.example.com:443:$VPS_IP https://myapp.example.com/   # bypass DNS, test direct
curl -fsSL https://myapp.example.com/ 2>&1 | grep -i "subject\|issuer"
openssl s_client -connect myapp.example.com:443 -servername myapp.example.com < /dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
```