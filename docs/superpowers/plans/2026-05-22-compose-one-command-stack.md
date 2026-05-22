---
title: One-command compose stack for db, backend, and frontend
type: feat
status: active
date: 2026-05-22
---

# One-command compose stack for db, backend, and frontend

## Overview

Add Dockerfiles for the FastAPI backend and the Vue frontend, expand the existing `docker-compose.yml` to orchestrate Postgres + backend + frontend + migrations, and document a single command (`docker compose up --build`) that stands the whole app up. The stack must be portable across `docker compose` and `podman compose` on Linux, with explicit handling of the two architectural quirks that bite Calliope specifically: the browser-side API client and the backend's outbound calls to host-side Ollama.

## Problem Statement / Motivation

Today, running Calliope locally is a multi-step ritual that lives only in the README (`README.md:7-34`):

1. `docker compose up -d postgres` (DB only)
2. `uv sync --extra dev` (host Python env)
3. `uv run alembic upgrade head` (migrations)
4. `uv run calliope serve` (backend)
5. `cd src/frontend && bun install && bun run dev` (frontend, separate terminal)

This is painful for: (a) onboarding contributors, (b) sanity-checking the stack on a fresh machine, (c) running the app on a workstation that doesn't have `uv`/`bun` installed, and (d) reproducible bug reports. A single `docker compose up --build` should produce a working Calliope at `http://localhost:5173` with the backend reachable at `http://localhost:8000`, schema migrated, and ready to accept workspace and profile configuration.

## Proposed Solution

Ship three artifacts:

1. **`Dockerfile`** (backend) — multi-stage build using `uv`, installs the `calliope` package, runs `uvicorn calliope.api.app:create_app --factory` as PID 1.
2. **`src/frontend/Dockerfile`** — multi-stage build using `bun` to install + `vite build`, served by `nginx:1.27-alpine` from `dist/`. Build-time `VITE_CALLIOPE_API_BASE_URL` arg.
3. **Expanded `docker-compose.yml`** — adds `migrate` (one-shot), `backend`, and `frontend` services on top of the existing `postgres` service. Wires healthchecks, depends_on, env vars, named volumes, and host-gateway aliases. Updates README with the new single command.

The compose file stays in the project root (matches existing layout) and uses Compose Spec v2 features that both Docker Compose v2 and `podman compose` honor. No `version:` key (deprecated/ignored on both).

## Technical Considerations

### Architectural quirks to handle explicitly

**1. Browser-side API client.** `src/frontend/src/shared/api/client.ts:5-9` reads `import.meta.env.VITE_CALLIOPE_API_BASE_URL` and falls back to `http://127.0.0.1:8000`. Vite bakes this at build time. The frontend container does not proxy API traffic — the browser fetches the backend directly. Therefore the backend MUST be published on a host port the user's browser can reach. Default: `8000:8000`. The build arg `VITE_CALLIOPE_API_BASE_URL=http://localhost:8000` is injected into the frontend image build.

**2. Backend → Ollama (or any OpenAI-compatible host service).** Calliope profiles point to `http://127.0.0.1:11434/v1` (README workflow example). Inside the backend container, `127.0.0.1` is the container, not the host. Fix with:
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```
This works for Docker (Linux/macOS/Windows). Podman additionally exposes `host.containers.internal` natively; the explicit `extra_hosts` line is still required for portable profile URLs. Document that users should configure profiles with `http://host.docker.internal:11434/v1` when running under compose.

**3. Alembic migrations need the compose-internal DB URL.** `alembic/env.py:8-13` falls back to `Settings()` which defaults to `localhost:5432`. The `migrate` one-shot service must set `CALLIOPE_DATABASE_URL=postgresql+psycopg://calliope:calliope@postgres:5432/calliope`.

**4. Service startup ordering.** Postgres healthcheck already exists (`docker-compose.yml:10-14`). Use `depends_on: condition: service_healthy` for `migrate`, and `depends_on: condition: service_completed_successfully` for `backend → migrate`. This is supported by Docker Compose v2 and `podman compose` (provider-backed); `podman-compose` (pip package) is historically weaker here — call out in the README.

**5. Fedora SELinux.** Bind mounts of source code or workspace markdown directories require the `:Z` suffix on Fedora to relabel for container access. Document this. Named volumes (Postgres data) are unaffected.

### Build choices

- **Backend image**: `python:3.12-slim` base + `uv` copied from `ghcr.io/astral-sh/uv:latest`. Multi-stage: builder installs deps with `uv sync --frozen --no-dev` against a frozen `uv.lock`; runtime stage copies `/app/.venv` and source. `ENTRYPOINT ["uvicorn", "calliope.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]`. Non-root user.
- **Frontend image**: `oven/bun:1-alpine` builder runs `bun install --frozen-lockfile && bun run build`; `nginx:1.27-alpine` runtime serves `dist/` with a minimal nginx config (single-page app fallback to `/index.html`, no API proxy in MVP).
- **No HMR in this design** — explicit tradeoff. A `dev` profile that runs `vite --host 0.0.0.0` with a bind mount of `src/frontend/src` is a known followup if active frontend development inside containers is ever needed.

### Single-command UX

`docker compose up --build` is technically two flags but is the canonical one-command compose invocation. Document it as the entry point. For subsequent runs without source changes, `docker compose up` suffices. Use `pull_policy: build` on the custom services so `docker compose up` builds when the image is missing without requiring `--build`.

## System-Wide Impact

- **Interaction graph**: `docker compose up` → builds `backend` and `frontend` images if missing → starts `postgres` → waits for `postgres` healthcheck → runs `migrate` to completion → starts `backend` (uvicorn) → starts `frontend` (nginx). User's browser hits `localhost:5173`, frontend serves static SPA, SPA fetches `localhost:8000` for API. Backend reads/writes Postgres at `postgres:5432`, and calls external OpenAI-compatible endpoints via `host.docker.internal:11434` (or whatever the profile points to).
- **Error propagation**: A failing `migrate` blocks the backend (correct). A failing backend leaves the frontend serving static assets with API calls returning network errors — the existing frontend startup error state (`src/frontend/src/features/...`) already handles this gracefully per session memory 1934-1937. Postgres restart restarts dependent services.
- **State lifecycle risks**: Named volume `calliope_pgdata` persists Postgres data across `docker compose down` (only wiped by `docker compose down -v`). Migrations are idempotent (`alembic upgrade head` is a no-op on a current schema). Frontend nginx serves a baked-in API URL — changing it requires a rebuild.
- **API surface parity**: No code changes to the FastAPI app or the Vue app. Only orchestration and packaging. Existing `uv run calliope serve` and host-side `bun run dev` paths continue to work for developers who prefer them.
- **Integration test scenarios**:
  1. Fresh clone → `docker compose up --build` → workspace add via CLI inside backend container (`docker compose exec backend calliope workspace add /workspaces/notes --name demo`) → frontend at `localhost:5173` lists the workspace.
  2. Stop stack, restart without `--build` → Postgres state persists (workspace still listed), images are cached.
  3. Wipe with `docker compose down -v` → next `up` re-runs migrations from scratch.
  4. Backend points at host-side Ollama → profile created with `http://host.docker.internal:11434/v1` → `calliope chat` succeeds end-to-end.
  5. Run the same compose file under `podman compose up --build` on Fedora → all four scenarios above still pass.

## Acceptance Criteria

- [ ] `docker compose up --build` from a clean checkout produces a healthy stack: Postgres ready, schema migrated, backend responding `200` at `http://localhost:8000/openapi.json`, frontend serving the Vue SPA at `http://localhost:5173`.
- [ ] `podman compose up --build` produces the same healthy stack on Fedora (the development host).
- [ ] `docker compose down` stops the stack cleanly. A subsequent `docker compose up` (no `--build`) restarts it without re-running migrations against an already-migrated DB (idempotent).
- [ ] `docker compose down -v` followed by `docker compose up --build` rebuilds from scratch, including re-running all migrations.
- [ ] The Vue SPA, when loaded in a browser, successfully calls the backend (verifiable: settings dialog loads workspaces and profiles without surfacing the startup-error alert added in 1ff131b/25a68c0).
- [ ] A profile configured with `base_url: http://host.docker.internal:11434/v1` allows the backend to reach a host-side Ollama instance (manual verification, since CI won't have Ollama).
- [ ] README's "Local Development" section is updated to feature the new single command as the primary path, with the existing `uv`/`bun` path preserved as "Run without containers".
- [ ] `.dockerignore` files exist for backend and frontend that exclude `.venv`, `node_modules`, `dist`, `__pycache__`, `.git`, `.pytest_cache`, `.ruff_cache`, and IDE noise.
- [ ] A `.env.example` documents `CALLIOPE_DATABASE_URL` and the build-arg-controlled `VITE_CALLIOPE_API_BASE_URL` for users who want to override defaults.

## Success Metrics

- **Time-to-first-request** on a fresh machine drops from ~5 manual steps to a single `docker compose up --build`.
- The README's "Local Development" section shrinks to fewer lines while covering more environments.
- Zero new code changes to the FastAPI app or Vue app — purely additive packaging.

## Dependencies & Risks

- **Risk: `podman-compose` (pip) divergence.** The pip-installed `podman-compose` (an alternative to `podman compose`) has historically had patchy `condition: service_healthy` and `extra_hosts: host-gateway` support. Mitigation: document that `podman compose` (the v5+ provider) is the supported entry point; `podman-compose` is best-effort.
- **Risk: SELinux on Fedora denying bind mounts.** If a future change mounts source for hot-reload or mounts workspace markdown dirs, the `:Z` suffix is required. Mitigation: documented in the README, not silently broken because MVP avoids host bind mounts entirely.
- **Risk: port collisions.** `5432` is the default Postgres port, often already in use on developer machines. Mitigation: expose Postgres on `127.0.0.1:5432:5432` (loopback-only on host) and let users override via a `.env` value like `POSTGRES_HOST_PORT=5433`.
- **Risk: stale frontend image after backend URL change.** If a user wants to point the frontend at a different backend, they must rebuild the frontend image (`docker compose build frontend`). Mitigation: document this; a runtime-config injection scheme is a followup, not MVP.
- **Risk: backend image bloat.** Naive `uv sync` ships dev deps. Mitigation: multi-stage build with `uv sync --no-dev` against `uv.lock`.
- **Dependency: workspace markdown directories.** Out of scope for this plan. Documented as a known limitation: workspace ingestion requires either CLI inside the container with a mounted host dir or a future "workspace upload" API.

## Implementation Sketch

### `Dockerfile` (project root, backend)

```dockerfile
# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
COPY alembic.ini ./
COPY alembic ./alembic
COPY src/backend ./src/backend
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime
WORKDIR /app
RUN useradd --create-home --uid 10001 calliope
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
USER calliope
EXPOSE 8000
ENTRYPOINT ["uvicorn", "calliope.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

### `src/frontend/Dockerfile`

```dockerfile
# syntax=docker/dockerfile:1.7

FROM oven/bun:1-alpine AS builder
WORKDIR /app
ARG VITE_CALLIOPE_API_BASE_URL=http://localhost:8000
ENV VITE_CALLIOPE_API_BASE_URL=${VITE_CALLIOPE_API_BASE_URL}
COPY package.json bun.lockb* ./
RUN bun install --frozen-lockfile
COPY . .
RUN bun run build

FROM nginx:1.27-alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### `src/frontend/nginx.conf`

```nginx
server {
  listen 80;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;
  location / {
    try_files $uri $uri/ /index.html;
  }
}
```

### Expanded `docker-compose.yml`

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: calliope
      POSTGRES_PASSWORD: calliope
      POSTGRES_DB: calliope
    ports:
      - "127.0.0.1:${POSTGRES_HOST_PORT:-5432}:5432"
    volumes:
      - calliope_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U calliope -d calliope"]
      interval: 5s
      timeout: 5s
      retries: 10

  migrate:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      CALLIOPE_DATABASE_URL: postgresql+psycopg://calliope:calliope@postgres:5432/calliope
    entrypoint: ["alembic", "upgrade", "head"]
    depends_on:
      postgres:
        condition: service_healthy
    restart: "no"

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      CALLIOPE_DATABASE_URL: postgresql+psycopg://calliope:calliope@postgres:5432/calliope
    ports:
      - "8000:8000"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      migrate:
        condition: service_completed_successfully

  frontend:
    build:
      context: ./src/frontend
      args:
        VITE_CALLIOPE_API_BASE_URL: ${VITE_CALLIOPE_API_BASE_URL:-http://localhost:8000}
    ports:
      - "5173:80"
    depends_on:
      - backend

volumes:
  calliope_pgdata:
```

### `.dockerignore` (project root)

```
.git
.venv
**/__pycache__
**/*.pyc
.pytest_cache
.ruff_cache
.worktrees
.claude
.codex
.agents
docs
src/frontend/node_modules
src/frontend/dist
tests
```

### `src/frontend/.dockerignore`

```
node_modules
dist
.vite
*.log
```

### `.env.example` (project root)

```
# Override the host port Postgres is published on if 5432 is already taken
POSTGRES_HOST_PORT=5432

# The browser-facing URL the Vue app will use to reach the backend.
# Baked into the frontend image at build time.
VITE_CALLIOPE_API_BASE_URL=http://localhost:8000

# Optional: override the backend's DB URL. Defaults are set in docker-compose.yml.
# CALLIOPE_DATABASE_URL=postgresql+psycopg://calliope:calliope@postgres:5432/calliope
```

### README update (sketch)

Replace the current "Local Development" section with:

```markdown
## Local Development

Stand up the full stack with one command:

​```bash
docker compose up --build
​```

Podman users on Fedora can substitute `podman compose up --build`. Frontend is at <http://localhost:5173>, backend OpenAPI at <http://127.0.0.1:8000/docs>.

To configure profiles pointing at a host-side Ollama, use `http://host.docker.internal:11434/v1` as the base URL. Run CLI commands inside the running backend container:

​```bash
docker compose exec backend calliope workspace add /path/inside/container --name my-world
​```

### Without containers

(Existing instructions retained as a fallback.)
```

## Verification Loop

1. `docker compose down -v && docker compose up --build` → wait for all services healthy → curl `http://localhost:8000/openapi.json` returns `200` → curl `http://localhost:5173/` returns the Vue index → run `docker compose exec backend alembic current` and confirm the head revision is applied.
2. Open `http://localhost:5173` in a browser → settings dialog opens without the startup-error alert → workspaces and profiles list endpoints return cleanly (DevTools Network tab).
3. Repeat steps 1–2 with `podman compose` on Fedora.
4. `docker compose down` then `docker compose up` (no `--build`, no `-v`) → stack comes back, no migration noise on a current schema.

## Sources & References

- Existing partial compose: `docker-compose.yml:1-15`
- Backend entry point: `src/backend/calliope/cli.py:103-105` (uvicorn factory)
- Backend settings + DB URL: `src/backend/calliope/config.py:5-10`
- Alembic env: `alembic/env.py:8-13`
- Frontend API client (browser-side): `src/frontend/src/shared/api/client.ts:5-9`
- Frontend env type: `src/frontend/src/vite-env.d.ts:3-9`
- README local-dev workflow: `README.md:7-45`
- Prior Calliope plans: `docs/superpowers/plans/2026-05-19-calliope-mvp.md`, `docs/superpowers/plans/2026-05-20-calliope-fe-mvp.md`
- Compose Spec (current): https://github.com/compose-spec/compose-spec/blob/main/spec.md
- Astral `uv` Docker guide: https://docs.astral.sh/uv/guides/integration/docker/
- Bun Dockerfile guide: https://bun.sh/guides/ecosystem/docker
- pgvector image: https://hub.docker.com/r/pgvector/pgvector
- Podman host-gateway behavior: `man podman-run` (extra_hosts mapping)

## Out of Scope (Followups)

- **Dev profile with HMR**: a `compose.dev.yaml` override that runs `vite --host 0.0.0.0` with `src/frontend/src` bind-mounted. Adds value only if frontend work moves into containers.
- **Workspace markdown mounting**: a documented `WORKSPACE_DIR` env + bind mount so `calliope reindex` can see host files. Currently the operator must `docker cp` files in or use a manually-added bind mount.
- **Runtime API base URL**: nginx envsubst on a `window.RUNTIME_CONFIG` snippet so the same frontend image can target multiple backends without rebuild. Unnecessary for a single-machine dev tool.
- **CI smoke test**: a GitHub Actions job that runs `docker compose up --wait` and curls the health endpoints. Cheap to add later.
- **Production image hardening**: rootless nginx, distroless backend, scanned with `trivy`. Not a goal for a local dev tool.
