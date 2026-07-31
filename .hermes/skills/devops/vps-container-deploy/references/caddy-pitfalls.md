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

## Trap 6 — host-systemd Caddy can't resolve Docker container hostnames

**Trigger:** Caddy is running as a host systemd service (`/usr/bin/caddy run --environ --config /etc/caddy/Caddyfile`), not as a Docker container. The Caddy site blocks were written assuming Caddy was on the shared `web` Docker network, where Docker's embedded DNS would resolve bare hostnames like `payntra-app`, `syntra-web`, `baymax-pipeline-probe-app` automatically. They don't.

**Symptom (curl):**
```
HTTP/2 502
server: Caddy
```

**Symptom (caddy logs, `journalctl -u caddy`):**
```
"dial tcp: lookup payntra-app on 127.0.0.53:53: server misbehaving"
```
Fired for every request to every site block whose `reverse_proxy` uses a bare container hostname. All sites on the host break at once.

**Why:** systemd-resolved at `127.0.0.53` is the host's DNS resolver. It knows nothing about Docker container names — those only resolve via Docker's embedded DNS at `127.0.0.11`, which only listens on the docker bridge interfaces (NOT on the host's loopback). `dig @127.0.0.11 payntra-app` from the host returns `connection refused`. So Caddy, running as a host process, gets NXDOMAIN-equivalent for every container name and returns 502.

**Why this is the inverse of Trap L:** Trap L says "Caddy-as-container needs the app on the `web` network." This trap says "Caddy-as-host-service needs the app reachable via a host port, period." Same DNS limitation, opposite resolution paths.

**Diagnostic sequence:**

```bash
# 1. Confirm it's the host systemd Caddy that's running, not the docker-compose one
systemctl status caddy --no-pager | grep -E 'Active|Main PID'
ls /etc/caddy/Caddyfile /srv/caddy/docker-compose.yml   # both usually exist
docker ps -a --filter name=caddy                        # empty = Caddy isn't in Docker

# 2. Confirm the symptom is the DNS lookup, not a port or backend issue
journalctl -u caddy -n 50 --no-pager | grep "server misbehaving"
# ^ If you see this, Trap 6 is firing

# 3. Confirm the upstream is fine
docker exec payntra-app sh -c "wget -qO- http://127.0.0.1:3000/"   # 200 = app is healthy

# 4. Try to reach the upstream via a host port (if one is mapped)
docker port payntra-app
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:32769/
# 200 = port mapping works → just need to point Caddy at 127.0.0.1:PORT
# 000 / connection refused = docker-proxy is missing OR no host port mapping at all
```

**Fix — the openreply pattern. Every site gets a host port + a Caddy rewrite:**

1. In each project's `docker-compose.yml`, pin a stable host port (don't rely on Docker randomising one — it picks a different port every restart and breaks Caddy):

   ```yaml
   services:
     app:
       ports:
         - 127.0.0.1:32769:3000   # host_port:container_port, pinned
   ```

   For containers that currently use `expose:` (which only documents, doesn't publish), replace with `ports:`. For containers that already have `ports: - 3000` (randomised), pin to a specific `127.0.0.1:HOST:CONTAINER` mapping.

2. In the Caddy site block, point `reverse_proxy` at the loopback, not the container name:

   ```caddy
   # WRONG — Caddy on host can't resolve this:
   payntra.terrybot.top {
       reverse_proxy payntra-app:3000
   }

   # RIGHT — matches the host port from step 1:
   payntra.terrybot.top {
       reverse_proxy 127.0.0.1:32769
   }
   ```

3. Reload and verify:

   ```bash
   /usr/bin/caddy validate --config /etc/caddy/Caddyfile   # must say "Valid configuration"
   systemctl reload caddy
   curl -sI -m 10 https://payntra.terrybot.top/             # expect HTTP 200
   ```

**Pin every project's host port.** The pattern across the dev VPS (147.79.18.32) as of 2026-07-31:

| Project | Host port | Container port |
|---|---|---|
| openreply-web | 32770 | 3000 |
| payntra-app | 32769 | 3000 |
| syntra_web | 8081 | 80 |
| baymax-pipeline-probe-app | 8082 | 8080 |

**Why `127.0.0.1:` not `0.0.0.0:` in the host port mapping:** binding to `0.0.0.0` exposes the container on the public interface. The Caddy reverse proxy is the only legitimate ingress path. Loopback-only keeps the attack surface to processes on the host. ufw doesn't need to allow these ports because loopback traffic bypasses the INPUT chain's filtered rules.

**Smell test for an existing project — check `HostConfig.PortBindings`:**
```bash
docker inspect payntra-app --format '{{.HostConfig.PortBindings}}'
# Healthy: map[3000/tcp:[{HostIp:127.0.0.1 HostPort:32769}]]
# Broken:  map[3000/tcp:[{invalid IP }]]     ← docker-proxy died, no listener
```
If you see `{invalid IP}`, the docker-proxy for that mapping has died. Recreate the container (`docker compose up -d --force-recreate <service>`) and the proxy comes back. Also fix the compose file to use a properly-pinned `127.0.0.1:PORT:containerPort` so it doesn't regress.

**If you'd rather not live with this:** convert Caddy back to a Docker container. The `/srv/caddy/docker-compose.yml` template already exists (binds 80/443, joins the `web` network, imports `/etc/caddy/sites/*.caddy`). Run `docker compose up -d` from `/srv/caddy/` and `systemctl disable --now caddy`. Then re-point the site blocks at bare container hostnames and remove the host port mappings from each project. Single change, eliminates the host-port pin dance, but you trade a different set of concerns (cert storage location, container restart on Caddy config changes, etc.). Verify the cert store works from the new location before deleting the host one.

**Lesson carved from this session:** on 2026-07-31, three sites on 147.79.18.32 went 502 simultaneously. Root cause was docker-proxy dying for payntra's port mapping (manifesting as `HostConfig.PortBindings: [{invalid IP }]`), combined with Caddy being a host service that can't resolve container names. Recovery: restart payntra-app to restore the proxy, add `127.0.0.1:8081:80` to syntra_web and `127.0.0.1:8082:8080` to baymax-pipeline-probe-app (neither had host port mappings at all), pin payntra's mapping to `127.0.0.1:32769:3000`, rewrite three Caddy site blocks, validate, reload. Total downtime ~12 minutes.

## Useful debug commands

```bash
docker logs caddy 2>&1 | tail -30               # recent log lines
docker exec caddy caddy adapt --config /etc/caddy/Caddyfile   # validate WITHOUT deploying
docker exec caddy caddy list-certificates       # cert inventory
curl -v --resolve myapp.example.com:443:$VPS_IP https://myapp.example.com/   # bypass DNS, test direct
curl -fsSL https://myapp.example.com/ 2>&1 | grep -i "subject\|issuer"
openssl s_client -connect myapp.example.com:443 -servername myapp.example.com < /dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
# Host Caddy trap-6 diagnostics
journalctl -u caddy -n 50 --no-pager | grep "server misbehaving"   # the smoking gun
docker inspect <container> --format '{{.HostConfig.PortBindings}}' # look for "invalid IP"
docker port <container>                                            # what Docker thinks is published
ss -tlnp 4all 2>&1 | grep <host_port>                              # is anything actually listening?
```