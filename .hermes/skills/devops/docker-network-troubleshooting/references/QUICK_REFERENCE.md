# Docker Network MTU — Quick Reference

## The One-Liner Diagnosis

**If TLS hangs at `CONNECTED(00000003)` → MTU mismatch. Period.**

```bash
# From host - does it work?
openssl s_client -starttls smtp -connect mail.cyberslide.net:587 -servername mail.cyberslide.net < /dev/null

# From container - does it hang?
docker exec payntra-app openssl s_client -starttls smtp -connect mail.cyberslide.net:587 -servername mail.cyberslide.net < /dev/null
```

If host works but container hangs → **MTU mismatch**.

---

## Why We Missed It The First Time

| Assumption | Reality |
|------------|---------|
| "Docker networking just works" | Default bridge MTU = 1500; host MTU = 1400 on Hetzner/Cloud VPS |
| "SMTP works from host, so it works from container" | Container inherits Docker bridge MTU, not host MTU |
| "Postgres connection failed = DB down" | Actually `EAI_AGAIN` = DNS resolution failed because DB on different network |
| "Environment variables loaded" | `env_file: .env` was missing from docker-compose services |

---

## The Fix (Canonical)

```yaml
# docker-compose.yml
networks:
  payntra-net:
    driver: bridge
    driver_opts:
      com.docker.network.driver.mtu: "1400"  # MUST match host eth0 MTU

services:
  app:
    networks: [payntra-net]
    env_file: .env  # CRITICAL: was missing
  db:
    networks: [payntra-net]  # CRITICAL: was missing - DB on default network
    env_file: .env
```

Then force recreate:
```bash
docker compose down
docker network rm payntra_payntra-net
docker compose up -d
```

---

## Verification Script

```bash
# One command to rule them all
/root/.hermes/skills/devops/docker-network-troubleshooting/scripts/verify-network.sh payntra-net
```

Output should show:
- Host MTU: 1400
- Network MTU: 1400
- All container eth0 MTUs: 1400
- SMTP TLS handshake: COMPLETES (not hangs)
- DB connectivity: OK

---

## Add to Every New Project

1. **Day 0:** Run `ip link show eth0` on target VPS, record MTU
2. **Compose:** Add custom network with matching MTU
3. **Services:** Explicit `networks: [custom-net]` on EVERY service
4. **Env:** `env_file: .env` on EVERY service
5. **CI Gate:** Run `verify-network.sh` in pipeline before deploy
6. **Docs:** Add MTU to PROJECT_INDEX.md

---

## Related Files in This Repo

- `/root/projects/payntra/docker-compose.yml` — fixed version with MTU 1400
- `/root/projects/payntra/.env` — SMTP config (port 587, STARTTLS)
- `/root/projects/payntra/PROJECT_INDEX.md` — deployment metadata including MTU
- `/root/.hermes/skills/devops/deployment-checklist/scripts/deploy-smoke-test.sh` — post-deploy verification

---

## Memory Anchor

> **MTU mismatch is the #1 cause of "works on host, fails in container" for TLS/Postgres/SMTP.**
> 
> Check it FIRST. Not third. Not after debugging app code. FIRST.