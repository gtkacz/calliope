# calliope

Calliope is the goddess of epic poetry.

Calliope is a Linux-first local knowledge tool for tabletop roleplaying games. Keep campaign notes, setting material, rules references, NPCs, locations, session recaps, encounter ideas, and other game documents in ordinary Markdown. You can search and work with those files through a web UI, FastAPI service, or Typer CLI.

Calliope indexes Markdown into Postgres with pgvector and connects to models through OpenAI-compatible local profiles. Use it to prepare a campaign, look things up during a session, keep track of continuity, brainstorm with an assistant, or edit notes against your existing material. Your source files stay on your machine.

## Local Development

Start the full stack, including Postgres, the backend, the frontend, and applied migrations, with one command.

```bash
docker compose up --build
```

If you use Podman on Fedora, run `podman compose up --build` instead. The frontend is available at <http://localhost:5173>. The backend API documentation is at <http://127.0.0.1:8000/docs>, and the raw schema is at <http://127.0.0.1:8000/openapi.json>.

Copy `.env.example` to `.env` if you need to change the default host ports or the backend URL used by the frontend.

Calliope needs access to the files you want to browse. A container can only see directories that are bind-mounted into it. By default, `CALLIOPE_BROWSE_ROOT` points to an empty scratch directory, so the folder picker, indexer, and file editor will not show any files. Set it in `.env` to the directory you want to browse and edit. This can be your whole home directory or one notes tree.

```bash
CALLIOPE_BROWSE_ROOT=/home/youruser          # browse anything under your home
# CALLIOPE_BROWSE_ROOT=/home/youruser/notes  # or restrict to a single tree
```

You can also set it for one run with `CALLIOPE_BROWSE_ROOT="$HOME" docker compose up`. The directory is mounted read-write at the same absolute path inside the container. Absolute paths pasted into the app will resolve as expected, and edits made in the app will be saved on the host. If the picker shows only one empty folder, this variable is unset or points to an empty directory.

Once the stack is running, run CLI commands inside the backend container.

```bash
docker compose exec backend calliope workspace add /path/inside/container --name my-campaign
docker compose exec backend calliope profiles add default-embeddings openai_compatible http://host.docker.internal:11434/v1 nomic-embed-text --capability embeddings
docker compose exec backend calliope profiles add default-chat openai_compatible http://host.docker.internal:11434/v1 llama3.1 --capability chat
docker compose exec backend calliope reindex my-campaign
docker compose exec backend calliope search "What happened to the missing caravan?"
docker compose exec backend calliope chat "Summarize what we know about the missing caravan and cite the relevant notes."
```

Use `host.docker.internal` as the base URL when your OpenAI-compatible service, such as Ollama, is running on the host. `docker-compose.yml` maps this name to `host-gateway`. On Fedora, add the `:Z` suffix to bind-mounted workspace directories so SELinux relabels them for container access.

If a local model takes a long time to load or generate a response, increase `CALLIOPE_LLM_REQUEST_TIMEOUT_SECONDS` in `.env` and restart the backend. The default is 120 seconds.

### Without containers

To run the services directly on your host, start the database first.

```bash
docker compose up -d postgres
```

Install the application with its development dependencies, then apply the migrations.

```bash
uv sync --extra dev
uv run alembic upgrade head
```

Start the API.

```bash
uv run calliope serve
```

When you run the CLI on the host, use `127.0.0.1` as the model base URL.

```bash
uv run calliope workspace add /path/to/campaign-notes --name my-campaign
uv run calliope profiles add default-embeddings openai_compatible http://127.0.0.1:11434/v1 nomic-embed-text --capability embeddings
uv run calliope profiles add default-chat openai_compatible http://127.0.0.1:11434/v1 llama3.1 --capability chat
uv run calliope reindex my-campaign
uv run calliope search "What happened to the missing caravan?"
uv run calliope chat "Summarize what we know about the missing caravan and cite the relevant notes."
```
