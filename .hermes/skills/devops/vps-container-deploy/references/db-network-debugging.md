# Docker Network Debugging — Database Not on Same Network

**Date:** 2026-07-05  
**Project:** Payntra  
**Environment:** Dev VPS (147.79.18.32)

---

## Symptom

```bash
docker exec payntra-app node -e "const { Pool } = require('pg'); new Pool({connectionString: process.env.DATABASE_URL}).query('SELECT 1')"
# Error: EAI_AGAIN getaddrinfo EAI_AGAIN db
```

The app container cannot resolve the database hostname `db`.

---

## Root Cause

In `docker-compose.yml`, the `db` service was missing the `networks:` directive:

```yaml
# PROBLEMATIC
services:
  db:
    image: postgres:16-alpine
    # NO networks: directive!
    
  app:
    networks:
      - payntra-net
      - web
```

This caused:
- `db` attached to default project network (`payntra_default`)
- `app` explicitly attached to `payntra-net` and `web`
- Different networks = no DNS resolution between them

---

## Fix

Add `networks:` to **every service that needs to communicate**:

```yaml
services:
  db:
    image: postgres:16-alpine
    networks:
      - payntra-net      # <-- ADD THIS
    # ...
    
  app:
    networks:
      - payntra-net
      - web
    # ...

networks:
  payntra-net:
    driver: bridge
    driver_opts:
      com.docker.network.driver.mtu: "1400"
  web:
    external: true
    name: web
```

---

## Verification

```bash
# Check which networks each container is on
docker inspect payntra-app --format '{{json .NetworkSettings.Networks}}'
docker inspect payntra-db --format '{{json .NetworkSettings.Networks}}'

# Test DNS resolution from app container
docker exec payntra-app getent hosts db
# Should return: 172.x.x.x  db
```

---

## Key Insight

**`depends_on` only controls startup order, NOT network connectivity.**

Many developers mistakenly believe `depends_on: db` makes the database reachable. It doesn't. You must explicitly declare the shared network on both services.

---

## Prevention Checklist

- [ ] Every service that needs to talk to another MUST declare the shared network
- [ ] Use consistent network names across all services in the compose file
- [ ] After compose changes, verify with `docker inspect <container> --format '{{json .NetworkSettings.Networks}}'`
- [ ] Test DNS resolution: `docker exec <app> getent hosts <service-name>`
- [ ] Don't assume `depends_on` implies network connectivity