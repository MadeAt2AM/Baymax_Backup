# Docker Image Cache Pitfall — Quick Reference

## The Problem
`docker compose build` with cached layers serves stale code even after source changes.

## Symptoms
- Code changes appear in local build but not in running container
- `docker exec <app> cat /app/dist/routes/auth.js` shows old code
- `--no-cache` sometimes still uses cached intermediate layers

## Root Cause
Docker layer caching skips `COPY server/ ./` if file timestamps/metadata appear unchanged, or intermediate builder stages are reused.

## Fix Pattern
```bash
# 1. Full clean rebuild
docker compose build --no-cache --pull app

# 2. Verify artifact BEFORE restart
docker exec <app> cat /app/dist/routes/auth.js | grep -A 10 "logout"

# 3. Only then restart
docker compose up -d --force-recreate app
```

## Prevention
- Always verify the built artifact inside the container before declaring deploy done
- Add verification step to CI/CD pipeline
- Use `docker compose build --pull` to ensure base images are fresh