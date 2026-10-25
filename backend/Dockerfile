# Sonar: one image serving the API and the built web app.
# Build from the repository root:   docker build -f backend/Dockerfile -t sonar .

# ---- stage 1: build the web app -------------------------------------------------------------
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- stage 2: the API, serving the built web app ----------------------------------------------
FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

# a non-root user: the app never needs to write outside its own logs
RUN useradd --create-home --uid 10001 sonar

COPY backend/pyproject.toml ./backend/pyproject.toml
COPY backend/app ./backend/app
COPY backend/alembic.ini ./backend/alembic.ini
COPY backend/alembic ./backend/alembic
COPY config ./config
COPY scripts ./scripts
COPY data/businesses.example.yaml ./data/businesses.example.yaml
# editable, so `app` stays under /app/backend and finds /app/config
RUN pip install -e ./backend
COPY --from=web /web/dist /app/frontend_dist

ENV FRONTEND_DIST=/app/frontend_dist \
    SONAR_ENV=prod
USER sonar
WORKDIR /app/backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=4).status == 200 else 1)"

# One worker on purpose: the orchestrator holds the call-concurrency limit in-process (D-006).
# Migrations are a separate step (see docker-compose.prod.example.yml), never run implicitly here.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
