# SMTP TLS Timeout Debugging — MTU Mismatch Case Study

**Date:** 2026-07-05  
**Project:** Payntra  
**Environment:** Dev VPS (147.79.18.32) — host eth0 MTU 1400, Docker bridge default MTU 1500  
**Symptom:** `nodemailer` in container times out on SMTP STARTTLS to `mail.cyberslide.net:587` with `ETIMEDOUT`

---

## The Debugging Path (5 minutes from symptom to root cause)

### 1. Confirm the symptom is container-specific
```bash
# Host works
nc -zv mail.cyberslide.net 587
# Connection to mail.cyberslide.net (157.173.106.6) 587 port [tcp/submission] succeeded!

openssl s_client -connect mail.cyberslide.net:587 -starttls smtp
# CONNECTED(00000003)
# TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384
```

### 2. Container TCP connectivity works, TLS doesn't
```bash
docker exec payntra-app nc -zv mail.cyberslide.net 587
# mail.cyberslide.net (157.173.106.6:587) open

docker exec payntra-app node -e "const tls = require('tls'); tls.connect(587, 'mail.cyberslide.net', ...)"
# Hangs after "220 Go ahead" — TLS handshake never completes
```

### 3. Key insight: `--network host` works
```bash
docker run --rm --network host node:20-alpine node -e "tls.connect(...)"
# SUCCESS: TLS_AES_256_GCM_SHA384 (TLSv1.3)
```
**This proves:** The container's network stack is the problem, not the application code or the mail server.

### 4. Compare MTUs
```bash
# Host
ip link show eth0
# mtu 1400

# Container
docker exec payntra-app ip link show eth0
# mtu 1500
```

**Found it:** Host MTU 1400, Docker bridge default 1500.

---

## The Fix

### docker-compose.yml
```yaml
networks:
  payntra-net:
    driver: bridge
    driver_opts:
      com.docker.network.driver.mtu: "1400"  # Match host
```

### Must recreate network (can't hot-patch)
```bash
docker compose down
docker network rm payntra_payntra-net   # or whatever the project-prefixed name is
docker compose up -d
```

### Verify
```bash
docker exec payntra-app ip link show eth0 | grep mtu
# mtu 1400

# Test SMTP
docker exec payntra-app node -e "nodemailer test..."
# Success: true
```

---

## Why This Matters

- **Environment-specific:** Only happens on VPS where host MTU < 1500 (common with VPN/tunneling overhead)
- **Protocol-specific:** Affects TLS handshakes (large certs/keys) more than plain TCP
- **Silent failure:** TCP handshake succeeds, `nc -zv` shows "open", but TLS hangs
- **Easy to miss:** Works fine on dev machine (MTU 1500 everywhere)

---

## Prevention Checklist for Future Deploys

- [ ] Check host MTU: `ip link show | grep -E 'mtu|eth' | head -5`
- [ ] Set `driver_opts.com.docker.network.driver.mtu` in docker-compose.yml to match
- [ ] Verify container MTU after deploy: `docker exec <app> ip link show eth0 | grep mtu`
- [ ] Test outbound TLS (SMTP/HTTPS) from container as part of smoke test