# calliope

Calliope is a Linux-first local markdown knowledge backend for worldbuilding canon. The MVP exposes a FastAPI service and Typer CLI, indexes markdown into Postgres with pgvector, and talks to models through OpenAI-compatible local profiles.

## Local Development

Start local Postgres with pgvector:

```bash
docker compose up -d postgres
```

Podman users can run the same compose file:

```bash
podman-compose up -d postgres
```

Install the application with development dependencies and apply migrations:

```bash
uv sync --extra dev
uv run alembic upgrade head
```

Run the API:

```bash
uv run calliope serve
```

OpenAPI docs are available at <http://127.0.0.1:8000/docs>. The raw schema is available at <http://127.0.0.1:8000/openapi.json>.

Common CLI workflow:

```bash
uv run calliope workspace add /path/to/world-notes --name my-world
uv run calliope profiles add default-embeddings openai_compatible http://127.0.0.1:11434/v1 nomic-embed-text --capability embeddings
uv run calliope profiles add default-chat openai_compatible http://127.0.0.1:11434/v1 llama3.1 --capability chat
uv run calliope reindex my-world
uv run calliope search "ancient city beneath the lake"
uv run calliope chat "What does canon say about the lake city?"
```
