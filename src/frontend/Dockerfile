# syntax=docker/dockerfile:1.7

FROM docker.io/oven/bun:1 AS builder
WORKDIR /app

# Baked into the SPA at build time. Override with --build-arg or via compose.
ARG VITE_CALLIOPE_API_BASE_URL=http://localhost:8000
ENV VITE_CALLIOPE_API_BASE_URL=${VITE_CALLIOPE_API_BASE_URL}

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .
# Skip vue-tsc typecheck in the container build; CI/host runs `bun run build`
# which includes it. The image only needs the static bundle.
RUN bun x vite build


FROM docker.io/library/nginx:1.27-alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
