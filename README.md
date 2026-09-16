# calliope

Calliope is the goddess of epic poetry.

Calliope is a Linux-first local knowledge tool for tabletop roleplaying games. Keep campaign notes, setting material, rules references, NPCs, locations, session recaps, encounter ideas, and other game documents in ordinary Markdown, then search and work with them through a web UI, FastAPI service, and Typer CLI.

Calliope indexes Markdown into Postgres with pgvector and connects to models through OpenAI-compatible local profiles. Use it for campaign preparation, in-session lookup, continuity and canon tracking, brainstorming with an assistant, or grounded editing of your notes—while keeping the source files on your own machine.

## Local Development

Stand up the full stack (Postgres + backend + frontend, with migrations applied) with one command:

```bash
docker compose up --build
```

Podman users on Fedora can substitute `podman compose up --build`. The frontend is served at <http://localhost:5173>, the backend OpenAPI at <http://127.0.0.1:8000/docs>, and the raw schema at <http://127.0.0.1:8000/openapi.json>.

Copy `.env.example` to `.env` to override any of the default host ports or the frontend's baked-in backend URL.

**Point Calliope at your files.** A container can only see directories that are bind-mounted into it. By default `CALLIOPE_BROWSE_ROOT` is an empty scratch directory, so the in-app folder picker, indexer, and file editor start out seeing *nothing*. Set it to the host directory you want to browse and edit — your whole home, or a single notes tree — in `.env`:

```bash
CALLIOPE_BROWSE_ROOT=/home/youruser          # browse anything under your home
# CALLIOPE_BROWSE_ROOT=/home/youruser/notes  # or restrict to a single tree
```

or inline for a one-off run: `CALLIOPE_BROWSE_ROOT="$HOME" docker compose up`. The directory is bind-mounted read-write at the same absolute path inside the container, so pasted absolute paths resolve verbatim and in-app edits persist back to the host. If the picker reports that it can only see one empty folder, this variable is unset or points at an empty directory.

Run CLI commands inside the running backend container:

```bash
docker compose exec backend calliope workspace add /path/inside/container --name my-campaign
docker compose exec backend calliope profiles add default-embeddings openai_compatible http://host.docker.internal:11434/v1 nomic-embed-text --capability embeddings
docker compose exec backend calliope profiles add default-chat openai_compatible http://host.docker.internal:11434/v1 llama3.1 --capability chat
docker compose exec backend calliope reindex my-campaign
docker compose exec backend calliope search "What happened to the missing caravan?"
docker compose exec backend calliope chat "Summarize what we know about the missing caravan and cite the relevant notes."
```

Use `host.docker.internal` (mapped to `host-gateway` in `docker-compose.yml`) as the base URL when your OpenAI-compatible service (for example, Ollama) runs on the host. On Fedora, bind-mounting workspace markdown directories into the backend container requires the `:Z` suffix on the volume so SELinux relabels the directory for container access.

If a local model is slow to load or generate, increase `CALLIOPE_LLM_REQUEST_TIMEOUT_SECONDS` in `.env` and restart the backend. The default is 120 seconds.

### Without containers

If you prefer to run services directly on your host, start just the database:

```bash
docker compose up -d postgres
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

The host-side CLI workflow uses `127.0.0.1` as the model base URL:

```bash
uv run calliope workspace add /path/to/campaign-notes --name my-campaign
uv run calliope profiles add default-embeddings openai_compatible http://127.0.0.1:11434/v1 nomic-embed-text --capability embeddings
uv run calliope profiles add default-chat openai_compatible http://127.0.0.1:11434/v1 llama3.1 --capability chat
uv run calliope reindex my-campaign
uv run calliope search "What happened to the missing caravan?"
uv run calliope chat "Summarize what we know about the missing caravan and cite the relevant notes."
```
