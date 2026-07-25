FROM python:3.12-slim

# System dependencies for bcrypt, psycopg, and Faster-Whisper.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        ffmpeg \
        libpq-dev \
        postgresql-client \
        && rm -rf /var/lib/apt/lists/*

# Create a non-root user.
RUN useradd --create-home --shell /bin/bash --uid 1001 app

WORKDIR /srv/competitors

# Install Python deps first for better layer caching.
COPY pyproject.toml /srv/competitors/pyproject.toml
COPY apps/api/requirements.txt /srv/competitors/requirements.txt
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir -r /srv/competitors/requirements.txt

# Copy the pipeline package and the API package.
COPY pipeline /srv/competitors/pipeline
COPY config /srv/competitors/config
COPY scrape.py /srv/competitors/scrape.py
COPY apps/api /srv/competitors/apps/api

# Make sure the app user can read / write to the bundle and audio dirs.
RUN mkdir -p /srv/competitors-private/audio /srv/competitors-private/bundles && \
    chown -R app:app /srv/competitors /srv/competitors-private

USER app
WORKDIR /srv/competitors/apps/api

ENV PYTHONPATH=/srv/competitors:/srv/competitors/apps/api
WORKDIR /srv/competitors/apps/api
EXPOSE 8000

# Health-check via the /api/healthz endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
