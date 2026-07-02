# syntax=docker/dockerfile:1
# ─── Stage 1: install dependencies ──────────────────────────────────────────
# Python 3.13.14 confirmed from venv (no .python-version file in repo).
FROM python:3.13-slim AS builder

WORKDIR /build

# Copy lockfile only — separate layer from app code.
# Docker cache reuses this layer on code-only changes (deps change less often).
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

# ─── Stage 2: production image ───────────────────────────────────────────────
# Copies only installed packages from builder — no pip, no build toolchain.
# Result: smaller image with no unnecessary attack surface.
FROM python:3.13-slim

WORKDIR /app

# Installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# App code — separate layer; changes more often than deps
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Cloud Run injects $PORT at runtime — container MUST listen on it.
# exec replaces the shell so uvicorn is PID 1 and receives SIGTERM directly.
# No --reload (dev-only flag).
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}"]

EXPOSE 8001

# Docker-level health check (Cloud Run uses its own HTTP probe, but this
# enables local `docker run` health status and validates the /health endpoint).
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c \
  "import urllib.request, os; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT','8001') + '/health')"
