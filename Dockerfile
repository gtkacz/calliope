# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

COPY pyproject.toml uv.lock README.md ./
# sharing=locked serializes the cache mount: compose builds the `migrate` and
# `backend` services from this same Dockerfile concurrently, and without the lock
# both writers collide on the shared uv cache (Permission denied under rootless
# podman). Locking makes the second build wait rather than race.
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic ./alembic
COPY src/backend ./src/backend
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-dev


FROM docker.io/library/python:3.12-slim AS runtime
WORKDIR /app

# git powers the optional per-workspace file version history feature.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 calliope

COPY --from=builder --chown=calliope:calliope /app /app

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER calliope
EXPOSE 8000

ENTRYPOINT ["uvicorn", "calliope.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
