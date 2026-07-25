# Competitors deploy runbook — Python fat images, tarball pipeline, multi-package PYTHONPATH

Added 2026-07-25 after the competitors deploy (`competitors.terrybot.top`,
FastAPI + Vite + Postgres + Whisper, on dev VPS 147.79.18.32). Lessons
in this runbook are about **Python** containerized apps, which the main
SKILL.md covers mostly from a Node/Vite angle (Payntra, SYNTRA). The
pitfalls are the same shape — Docker build slow, PYTHONPATH drift,
editable-install collisions — but the recipes here are Python-specific.

## Pitfalls

### AO. `docker save | rsync | docker load` is the **primary** build pipeline when SSH-to-dev-VPS bandwidth is constrained — not a fallback

**Symptom:** Building any non-trivial Python Docker image directly on the dev VPS over SSH is **painfully slow** even with MTU=1400 set correctly. A FastAPI image with `faster-whisper` + `ctranslate2` + `psycopg` + `bcrypt` + `uvicorn` takes ~7-10 minutes on the dev VPS (apt alone downloads gcc-14 + build-essential ~150 MB before pip starts, observed at 150-200 kB/s over SSH). For comparison, the SAME image builds in ~30-60 seconds locally on the Hermes host (1 Gbit link, no SSH bottleneck).

The "fallback" sentence at the end of pitfall AL ("the fallback is a slow workaround: pre-build images locally and `docker save | docker load` them onto the dev VPS") is misleading. **It's not a fallback — it's the right primary path for any image >200 MB on bandwidth-constrained VPSes.**

**Pattern that works:**

```bash
# 1. Build locally on the orchestrator (Hermes host)
cd /root/.hermes/projects/<project>
docker build -f apps/api/Dockerfile -t <project>-api:0.1.0 . > /tmp/api-build.log 2>&1

# 2. Save to tarball (≈ 1 GB for the api image, 70 MB for a Vite web bundle)
docker save <project>-api:0.1.0 > /tmp/<project>-api.tar

# 3. rsync to dev VPS (rsync is faster than scp for large single files)
rsync -a /tmp/<project>-api.tar dev-vps:/tmp/

# 4. Load on the dev VPS
ssh dev-vps 'docker load -i /tmp/<project>-api.tar && \
  docker tag <project>-api:0.1.0 <project>-api:0.1.0'  # tag is idempotent

# 5. Update docker-compose.yml to use `image:` instead of `build:`
#    so `docker compose up -d` doesn't try to rebuild
```

The `image:` directive is what makes this work end-to-end:

```yaml
# docker-compose.yml — pre-built image, no rebuild
services:
  api:
    image: <project>-api:0.1.0    # <-- USES the loaded image, no `build:`
    # ... (no `build:` block needed if you only deploy from a registry/local load)
```

**When to use which path:**

| Scenario | Path |
|---|---|
| Image < 200 MB, dev VPS has 1 Gbit | Build on dev VPS, simpler |
| Image > 200 MB, dev VPS is bandwidth-constrained (Hetzner, OVH, etc.) | Build local + `save | rsync | load` |
| Image has a 5 GB pip install step | **Always** build local + tarball |
| Multi-stage image with heavy builder stage (gcc-14 + ctranslate2 compile) | **Always** build local + tarball |
| Iterating on `docker-compose.yml` only (env vars, ports, networks) | No rebuild needed, just `docker compose up -d` |

**Costs:**
- Local build takes 30-60 s and uses Hermes CPU
- Tarball is ~1 GB for a fat API image — make sure `/tmp` has space (Hermes has 100+ GB)
- rsync over SSH to a nearby VPS takes 30-90 s at 30 MB/s
- `docker load` on dev VPS takes 30-60 s
- Total: 2-3 minutes end-to-end vs 7-10 minutes building on the dev VPS

**Diagnostic when "the tarball pipeline hangs":**

```bash
# Check rsync is actually making progress
rsync -a --progress /tmp/<project>-api.tar dev-vps:/tmp/  # add --progress
# Check disk space on Hermes for tarball
df -h /tmp
# Check disk space on dev VPS after load
ssh dev-vps 'df -h / && docker images | grep <project>'
```

**Pairs with:**
- Pitfall AL (MTU fix) in the parent SKILL.md — once MTU is right, the tarball path is the next optimization
- The `Background-process UX rule` in the parent SKILL.md — long docker builds go to background with `notify_on_complete=true`

Verified 2026-07-25 (competitors deploy — `competitors-api:test` is 1.97 GB with `faster-whisper` + `ctranslate2`. Direct `docker build` on dev VPS over SSH was making 150-200 kB/s of progress and projected to take 8-12 minutes for the apt + pip layers. Switched to local build (60 s) + `docker save` (492 MB tarball) + `rsync` (45 s) + `docker load` (90 s on dev VPS). Total wall time: ~3 minutes vs 8-12 minutes on the dev VPS directly.)

### AP. PYTHONPATH for multi-package Python Docker images — needs BOTH the workspace root and the package parent

**Symptom:** Python container boots, but uvicorn crashes with `ModuleNotFoundError: No module named 'pipeline'` (or any sibling package). The app's Dockerfile has a layout like:

```
/srv/competitors/
├── pipeline/                  # one Python package
├── apps/api/app/              # the FastAPI app package
└── scratch.py / scrape.py     # other scripts
```

And the API at `apps/api/app/main.py` does `from pipeline import bootstrap_session`.

**The trap:** Setting `ENV PYTHONPATH=/srv/competitors` makes `pipeline` importable but `app.main` (relative `from .routes import instagram_auth`) fails because `app` is at `/srv/competitors/apps/api/app/`, not `/srv/competitors/app/`. Setting `ENV PYTHONPATH=/srv/competitors/apps/api` makes `app.main` importable but `pipeline` fails.

**Fix — both paths, colon-separated:**

```dockerfile
ENV PYTHONPATH=/srv/competitors:/srv/competitors/apps/api
WORKDIR /srv/competitors/apps/api
```

The `WORKDIR` adds the empty string `''` to `sys.path` (current dir), which is what `python -m app.cli` needs. The PYTHONPATH makes `pipeline` and `app` both importable from any CWD.

**Verify inside the running container:**

```bash
docker exec <api-container> python -c "import sys; print('\n'.join(sys.path))"
# Should include both paths
docker exec <api-container> python -c "import pipeline, app; print(pipeline.__file__, app.__file__)"
```

**Pairs with pitfall AQ (editable-install collision) below** — the collision can mask whether PYTHONPATH is set correctly, so check both.

Verified 2026-07-25 (competitors deploy — first Dockerfile had only `ENV PYTHONPATH=/srv/competitors`, container crashed with `ModuleNotFoundError: No module named 'pipeline'`. Added `:apps/api` to PYTHONPATH, rebuilt image, uvicorn imported both `app.main` and `pipeline.bootstrap_session` cleanly.)

### AQ. Editable-install PYTHONPATH collision — `__editable__.<pkg>` finder shadows relative-path entries

**Symptom:** PYTHONPATH is set correctly inside the container (verified via `python -c "import sys; print(sys.path)"`), `import pipeline` works, `import app` works, but `python -m app.cli` fails with `Error while finding module specification for 'app.cli' (ModuleNotFoundError: No module named 'app')`.

**Root cause:** When a Python package is installed as **editable** (`pip install -e .`), the install creates a `__editable__.<pkg>-0.1.0.finder.__path_hook__` entry in `sys.path_hooks`. This finder hooks BEFORE the regular PYTHONPATH entries. If the editable install was done from a different directory layout than what's in the container (e.g. editable install happened during local venv setup on the Hermes host), the finder may map `app` to a different on-disk location than the container's `/srv/competitors/apps/api/app/`.

**The error message is misleading:** "No module named 'app'" suggests the package is missing, but `import app` works. The issue is specific to `python -m <module>` which uses the spec-finding machinery, not direct imports.

**Two fixes:**

1. **Quickest (avoid editable install in the container):** use `pip install -r requirements.txt` (non-editable) in the Dockerfile. The container image is built fresh and doesn't inherit the editable-install state.

2. **Right fix (match the editable install's view to the container's view):** the editable install's `*.pth` file (under `site-packages`) points at a directory. Ensure that directory layout matches what PYTHONPATH expects. For the competitors project, the editable install puts `app` at `<workspace_root>/apps/api/app/` — make sure `apps/api/` is in PYTHONPATH AND the editable `.pth` file points at the same path.

**Diagnostic:**

```bash
# 1. List the path hooks (editable installs are visible here)
docker exec <container> python -c "import sys; print('\n'.join(str(h) for h in sys.path_hooks))"

# 2. Find editable-install .pth files
docker exec <container> find /usr/local/lib/python3.12/site-packages -name '*.pth' -exec cat {} \;

# 3. Reproduce the exact failure
docker exec <container> python -c "import app.cli; print(app.cli.__file__)"
# If this raises the same error, the editable finder is the issue
```

**When you see "module-not-found on `python -m X` but `import X` works":** think editable-install collision before thinking PYTHONPATH. The latter is the obvious suspect but the former is the sneaky one.

**Pairs with pitfall AP (PYTHONPATH)** — AP covers the case where PYTHONPATH is genuinely wrong; AQ covers the case where PYTHONPATH looks right but the editable install shadows it.

Verified 2026-07-25 (competitors deploy — `pip install -e .` on the Hermes host installed `competitors` as an editable, mapping `app` to `<workspace>/apps/api/app/`. Inside the container, PYTHONPATH was correct (`/srv/competitors` + `/srv/competitors/apps/api`) and `import app` worked, but `python -m app.cli` failed because the editable finder installed by the same `pip install` on Hermes didn't propagate to the container. Fix was to either (a) rebuild the image with non-editable `pip install -r requirements.txt`, or (b) match the editable `.pth` paths to the container layout.)

## Companion: the `headless-vps-scraping-toolchain` `whoami` correction

OpenCLI 1.8.6 on a fresh Ubuntu 24.04 install does **not** ship `instagram whoami` as a built-in subcommand. The `whoami` binary is on `$PATH` (`/usr/bin/whoami`), and OpenCLI calls it via its `external` mechanism. The verify call needs:

```bash
# Once on the target VPS (registers /usr/bin/whoami as an OpenCLI external command):
opencli external register whoami /usr/bin/whoami

# Then the verify call:
opencli whoami
# Returns: { "ok": true, "result": { "username": "..." } }  (Instagram-authenticated)
# OR      { "ok": true, "result": { "username": "<unix-user>" } }  (default unix whoami)
```

If `opencli external register whoami /usr/bin/whoami` was never run, `opencli whoami` errors with:

```
error: unknown command 'whoami'
  Tip: 'whoami' exists on your PATH. Use 'opencli external register whoami' to add it as an external CLI.
```

The `headless-vps-scraping-toolchain` recipe needs to call this `register` step **once on the target VPS** as part of the install sequence. Verified 2026-07-25 (competitors deploy — first `opencli whoami` invocation failed with `unknown command 'whoami'` until `opencli external register whoami /usr/bin/whoami` was run on the dev VPS).
