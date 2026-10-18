# syntax=docker/dockerfile:1
# backend/Dockerfile: the API image. Build from the repository root:
#   docker build -f backend/Dockerfile -t devorchestrator-api:local .
# At start it applies the migrations (alembic upgrade head), then serves on 8000.
# Runtime environment: DATABASE_URL (required), CORS_ORIGINS, GIT_SHA (optional).
#
# Base images are pinned by tag. TODO(devops): pin them by digest too
# (image@sha256:...) once the digests can be resolved and kept up to date.
ARG PYTHON_IMAGE=python:3.14-slim-trixie
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13.1

FROM ${UV_IMAGE} AS uv

# ---- build: resolve the locked dependencies into /app/.venv ----
FROM ${PYTHON_IMAGE} AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app

# dependencies first, so the layer is reused while only the code changes
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# then the project itself: the API reads its version from the package metadata
COPY backend/ ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ---- runtime: no uv, no build cache, non-root ----
FROM ${PYTHON_IMAGE} AS runtime
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
# owned by root and not writable by the app user: works with a read-only filesystem
COPY --from=build /app /app
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
USER 10001:10001
EXPOSE 8000

# liveness only: readiness (database) is /api/v1/health/ready
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2)"]

CMD ["sh", "-c", "alembic upgrade head && exec fastapi run --host 0.0.0.0 --port 8000"]
