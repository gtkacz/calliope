# Calliope MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Linux-only Python backend and CLI that indexes local markdown workspaces, performs hybrid Postgres/pgvector retrieval, and answers through OpenAI-compatible local model profiles with citations.

**Architecture:** FastAPI and Typer call the same application services. Postgres stores workspaces, documents, chunks, embeddings, sessions, traces, and connection profiles; pgvector handles vector search and Postgres full-text search handles lexical search. Model, embedding, and reranker traffic goes only through configured OpenAI-compatible profiles.

**Tech Stack:** Python 3.12, FastAPI, Typer, Pydantic, SQLAlchemy, Alembic, PostgreSQL, pgvector, httpx, markdown-it-py, python-frontmatter, pytest, pytest-httpx, ruff, pyright, Docker Compose or Podman Compose.

---

## Scope Check

The approved design covers one MVP backend. It includes multiple layers, but they are sequentially dependent and form one testable product. Keep them in one implementation plan and land frequent commits after each layer.

## File Structure

Create this structure:

```txt
pyproject.toml
README.md
docker-compose.yml
alembic.ini
src/calliope/__init__.py
src/calliope/api/app.py
src/calliope/api/errors.py
src/calliope/api/routes/chat.py
src/calliope/api/routes/documents.py
src/calliope/api/routes/profiles.py
src/calliope/api/routes/search.py
src/calliope/api/routes/sessions.py
src/calliope/api/routes/workspaces.py
src/calliope/api/dependencies.py
src/calliope/cli.py
src/calliope/config.py
src/calliope/db/base.py
src/calliope/db/models.py
src/calliope/db/session.py
src/calliope/db/types.py
src/calliope/domain/enums.py
src/calliope/domain/errors.py
src/calliope/domain/schemas.py
src/calliope/ingest/chunker.py
src/calliope/ingest/indexer.py
src/calliope/ingest/parser.py
src/calliope/ingest/scanner.py
src/calliope/llm/openai_compatible.py
src/calliope/prompts/builder.py
src/calliope/repositories/chats.py
src/calliope/repositories/chunks.py
src/calliope/repositories/documents.py
src/calliope/repositories/profiles.py
src/calliope/repositories/workspaces.py
src/calliope/retrieval/hybrid.py
src/calliope/services/chat.py
src/calliope/services/profiles.py
src/calliope/services/search.py
src/calliope/services/workspaces.py
alembic/env.py
alembic/versions/0001_initial.py
tests/conftest.py
tests/fixtures/world/characters/kaelen.md
tests/unit/test_chunker.py
tests/unit/test_errors.py
tests/unit/test_parser.py
tests/unit/test_prompt_builder.py
tests/unit/test_scanner.py
tests/unit/test_schemas.py
tests/unit/test_settings.py
tests/unit/test_hybrid_retriever.py
tests/unit/test_openai_compatible_client.py
tests/integration/test_api_contract.py
tests/integration/test_indexer.py
tests/integration/test_profiles.py
tests/integration/test_repositories.py
tests/integration/test_search_service.py
tests/integration/test_chat_service.py
tests/integration/test_cli.py
```

Keep module responsibilities narrow:

- `domain/`: public enums, schemas, and typed errors.
- `db/`: SQLAlchemy setup, models, and custom database types.
- `repositories/`: database reads and writes only.
- `ingest/`: filesystem scanning, markdown parsing, chunking, and reindex orchestration.
- `retrieval/`: hybrid search and score fusion.
- `llm/`: OpenAI-compatible HTTP client only.
- `prompts/`: prompt assembly and canon policy text.
- `services/`: use cases consumed by API and CLI.
- `api/`: FastAPI app, route wiring, and error translation.
- `cli.py`: Typer command wiring.

## Task 1: Project Scaffold And Settings

**Files:**
- Create: `pyproject.toml`
- Create: `src/calliope/__init__.py`
- Create: `src/calliope/config.py`
- Create: `src/calliope/cli.py`
- Create: `src/calliope/api/app.py`
- Create: `tests/unit/test_settings.py`
- Create: `tests/integration/test_api_contract.py`
- Modify: `README.md`

- [ ] **Step 1: Write the failing settings test**

Create `tests/unit/test_settings.py`:

```python
from calliope.config import Settings


def test_settings_defaults_are_local() -> None:
    settings = Settings()

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.api_title == "Calliope"
    assert settings.embedding_dimensions == 384
```

- [ ] **Step 2: Write the failing API smoke test**

Create `tests/integration/test_api_contract.py`:

```python
from fastapi.testclient import TestClient

from calliope.api.app import create_app


def test_openapi_document_exists() -> None:
    client = TestClient(create_app())

    response = client.get("/openapi.json")

    assert response.status_code == 200
    body = response.json()
    assert body["info"]["title"] == "Calliope"
```

- [ ] **Step 3: Run tests to verify scaffold is missing**

Run: `uv run pytest tests/unit/test_settings.py tests/integration/test_api_contract.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'calliope'`.

- [ ] **Step 4: Create Python project configuration**

Create `pyproject.toml`:

```toml
[project]
name = "calliope"
version = "0.1.0"
description = "Local markdown knowledge backend for worldbuilding canon"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
  "alembic>=1.13",
  "fastapi>=0.115",
  "httpx>=0.27",
  "markdown-it-py>=3.0",
  "pgvector>=0.3",
  "psycopg[binary]>=3.2",
  "pydantic>=2.8",
  "pydantic-settings>=2.4",
  "python-frontmatter>=1.1",
  "sqlalchemy>=2.0",
  "typer>=0.12",
  "uvicorn>=0.30",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3",
  "pytest-asyncio>=0.24",
  "pytest-httpx>=0.30",
  "pyright>=1.1",
  "ruff>=0.6",
  "testcontainers[postgres]>=4.8",
]

[project.scripts]
calliope = "calliope.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/calliope"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pyright]
include = ["src", "tests"]
pythonVersion = "3.12"
typeCheckingMode = "basic"
```

- [ ] **Step 5: Add minimal package files**

Create `src/calliope/__init__.py`:

```python
__all__ = ["__version__"]

__version__ = "0.1.0"
```

Create `src/calliope/config.py`:

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CALLIOPE_", env_file=".env", extra="ignore")

    api_title: str = "Calliope"
    database_url: str = "postgresql+psycopg://calliope:calliope@localhost:5432/calliope"
    embedding_dimensions: int = Field(default=384, ge=1)
```

Create `src/calliope/api/app.py`:

```python
from fastapi import FastAPI

from calliope.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    return FastAPI(title=resolved_settings.api_title)
```

Create `src/calliope/cli.py`:

```python
import typer
import uvicorn

from calliope.config import Settings

app = typer.Typer(help="Calliope local markdown knowledge backend.")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the HTTP API."""
    Settings()
    uvicorn.run("calliope.api.app:create_app", factory=True, host=host, port=port)
```

- [ ] **Step 6: Update README with local-first direction**

Modify `README.md` to keep the existing sentence and add:

```markdown

Calliope is a Linux-first local markdown knowledge backend for worldbuilding canon. The MVP exposes a FastAPI service and Typer CLI, indexes markdown into Postgres with pgvector, and talks to models through OpenAI-compatible local profiles.
```

- [ ] **Step 7: Run scaffold tests**

Run: `uv run pytest tests/unit/test_settings.py tests/integration/test_api_contract.py -v`

Expected: PASS.

- [ ] **Step 8: Run lint**

Run: `uv run ruff check src tests`

Expected: PASS.

- [ ] **Step 9: Commit scaffold**

```bash
git add pyproject.toml README.md src/calliope tests/unit/test_settings.py tests/integration/test_api_contract.py
git commit -m "feat: scaffold calliope backend"
```

## Task 2: Domain Contracts And Error Mapping

**Files:**
- Create: `src/calliope/domain/enums.py`
- Create: `src/calliope/domain/errors.py`
- Create: `src/calliope/domain/schemas.py`
- Create: `src/calliope/api/errors.py`
- Modify: `src/calliope/api/app.py`
- Create: `tests/unit/test_schemas.py`
- Create: `tests/unit/test_errors.py`

- [ ] **Step 1: Write schema tests**

Create `tests/unit/test_schemas.py`:

```python
from calliope.domain.enums import CanonPolicy, ProfileCapability, ProfileKind
from calliope.domain.schemas import SourceReference, WorkspaceCreate


def test_workspace_create_defaults_globs() -> None:
    payload = WorkspaceCreate(name="World", root_path="/tmp/world")

    assert payload.include_globs == ["**/*.md", "**/*.markdown"]
    assert payload.exclude_globs == [".git/**", ".venv/**", "node_modules/**"]


def test_source_reference_contains_citation_fields() -> None:
    source = SourceReference(
        document_id="doc_1",
        chunk_id="chunk_1",
        path="characters/kaelen.md",
        heading="Biography > Exile",
        excerpt="After the Second Winter War",
        score=0.87,
    )

    assert source.score == 0.87
    assert "Exile" in source.heading


def test_enums_cover_mvp_values() -> None:
    assert CanonPolicy.STRICT_CANON == "strict_canon"
    assert CanonPolicy.CANON_PLUS_INFERENCE == "canon_plus_inference"
    assert CanonPolicy.CREATIVE_BUT_CONSISTENT == "creative_but_consistent"
    assert ProfileKind.OPENAI_COMPATIBLE == "openai_compatible"
    assert ProfileCapability.CHAT == "chat"
```

- [ ] **Step 2: Write error mapping tests**

Create `tests/unit/test_errors.py`:

```python
from fastapi.testclient import TestClient

from calliope.api.app import create_app
from calliope.domain.errors import AppError


def test_app_error_maps_to_stable_json() -> None:
    app = create_app()

    @app.get("/raise-test-error")
    def raise_error() -> None:
        raise AppError(
            code="workspace_not_found",
            message="Workspace not found.",
            status_code=404,
            details={"workspace_id": "workspace_123"},
        )

    response = TestClient(app).get("/raise-test-error")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "workspace_not_found",
            "message": "Workspace not found.",
            "details": {"workspace_id": "workspace_123"},
        }
    }
```

- [ ] **Step 3: Run domain tests to verify failure**

Run: `uv run pytest tests/unit/test_schemas.py tests/unit/test_errors.py -v`

Expected: FAIL with missing `calliope.domain` modules.

- [ ] **Step 4: Implement domain enums**

Create `src/calliope/domain/enums.py`:

```python
from enum import StrEnum


class CanonPolicy(StrEnum):
    STRICT_CANON = "strict_canon"
    CANON_PLUS_INFERENCE = "canon_plus_inference"
    CREATIVE_BUT_CONSISTENT = "creative_but_consistent"


class ProfileKind(StrEnum):
    OPENAI_COMPATIBLE = "openai_compatible"


class ProfileCapability(StrEnum):
    CHAT = "chat"
    EMBEDDINGS = "embeddings"
    RERANK = "rerank"
    STREAMING = "streaming"
```

- [ ] **Step 5: Implement schemas**

Create `src/calliope/domain/schemas.py` with Pydantic models for the API and services:

```python
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from calliope.domain.enums import CanonPolicy, ProfileCapability, ProfileKind


class WorkspaceCreate(BaseModel):
    name: str
    root_path: str
    include_globs: list[str] = Field(default_factory=lambda: ["**/*.md", "**/*.markdown"])
    exclude_globs: list[str] = Field(
        default_factory=lambda: [".git/**", ".venv/**", "node_modules/**"]
    )


class WorkspaceRead(WorkspaceCreate):
    id: str
    created_at: datetime


class ProfileCreate(BaseModel):
    name: str
    kind: ProfileKind = ProfileKind.OPENAI_COMPATIBLE
    base_url: str
    model: str
    api_key_ref: str | None = None
    capabilities: list[ProfileCapability]


class ProfileRead(ProfileCreate):
    id: str
    created_at: datetime


class SourceReference(BaseModel):
    document_id: str
    chunk_id: str
    path: str
    heading: str
    excerpt: str
    score: float


class SearchRequest(BaseModel):
    query: str
    workspace_id: str | None = None
    limit: int = Field(default=8, ge=1, le=50)


class SearchResponse(BaseModel):
    sources: list[SourceReference]


class ReindexRequest(BaseModel):
    workspace_id: str


class ReindexResponse(BaseModel):
    documents_indexed: int
    chunks_indexed: int


class ChatRequest(BaseModel):
    message: str
    policy: CanonPolicy = CanonPolicy.STRICT_CANON
    session_id: str | None = None
    workspace_id: str | None = None
    limit: int = Field(default=8, ge=1, le=50)


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
    trace_id: str


class DocumentRead(BaseModel):
    id: str
    workspace_id: str
    path: str
    title: str
    frontmatter: dict[str, Any]
    modified_at: datetime
    indexed_at: datetime | None


class SessionRead(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 6: Implement typed application errors**

Create `src/calliope/domain/errors.py`:

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AppError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: dict[str, Any] = field(default_factory=dict)
```

Create `src/calliope/api/errors.py`:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from calliope.domain.errors import AppError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )
```

- [ ] **Step 7: Register error handlers**

Modify `src/calliope/api/app.py`:

```python
from fastapi import FastAPI

from calliope.api.errors import register_error_handlers
from calliope.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    app = FastAPI(title=resolved_settings.api_title)
    register_error_handlers(app)
    return app
```

- [ ] **Step 8: Run domain tests**

Run: `uv run pytest tests/unit/test_schemas.py tests/unit/test_errors.py -v`

Expected: PASS.

- [ ] **Step 9: Run current suite**

Run: `uv run pytest -v`

Expected: PASS.

- [ ] **Step 10: Commit domain contracts**

```bash
git add src/calliope/domain src/calliope/api tests/unit/test_schemas.py tests/unit/test_errors.py
git commit -m "feat: add domain contracts and errors"
```

## Task 3: Database Models, Migrations, And Test Database

**Files:**
- Create: `docker-compose.yml`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/0001_initial.py`
- Create: `src/calliope/db/base.py`
- Create: `src/calliope/db/models.py`
- Create: `src/calliope/db/session.py`
- Create: `src/calliope/db/types.py`
- Create: `tests/conftest.py`
- Create: `tests/integration/test_repositories.py`

- [ ] **Step 1: Write repository schema integration test**

Create `tests/integration/test_repositories.py`:

```python
from sqlalchemy import inspect, text

from calliope.db.models import Base


def test_metadata_contains_mvp_tables() -> None:
    assert {
        "workspaces",
        "documents",
        "chunks",
        "chat_sessions",
        "chat_messages",
        "retrieval_traces",
        "connection_profiles",
    }.issubset(Base.metadata.tables)


def test_database_has_vector_extension(db_session) -> None:
    version = db_session.execute(text("select extname from pg_extension where extname='vector'"))

    assert version.scalar_one() == "vector"


def test_database_tables_are_created(db_engine) -> None:
    inspector = inspect(db_engine)

    assert "chunks" in inspector.get_table_names()
```

- [ ] **Step 2: Run schema tests to verify failure**

Run: `uv run pytest tests/integration/test_repositories.py -v`

Expected: FAIL with missing `calliope.db` module.

- [ ] **Step 3: Add local infrastructure**

Create `docker-compose.yml`:

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: calliope
      POSTGRES_PASSWORD: calliope
      POSTGRES_DB: calliope
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U calliope -d calliope"]
      interval: 5s
      timeout: 5s
      retries: 10
```

- [ ] **Step 4: Implement SQLAlchemy base and vector type**

Create `src/calliope/db/base.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

Create `src/calliope/db/types.py`:

```python
from pgvector.sqlalchemy import Vector

EmbeddingVector = Vector
```

- [ ] **Step 5: Implement database models**

Create `src/calliope/db/models.py` with all MVP tables:

```python
from datetime import datetime
from typing import Any
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from calliope.db.base import Base


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("workspace"))
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    root_path: Mapped[str] = mapped_column(Text, nullable=False)
    include_globs: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    exclude_globs: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    documents: Mapped[list["Document"]] = relationship(back_populates="workspace")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("document"))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    frontmatter_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workspace: Mapped[Workspace] = relationship(back_populates="documents")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_documents_workspace_path", "workspace_id", "path", unique=True),)


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("chunk"))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    heading_path: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    search_vector = mapped_column(TSVECTOR)

    document: Mapped[Document] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_document_index", "document_id", "chunk_index", unique=True),
        Index("ix_chunks_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_chunks_embedding", "embedding", postgresql_using="hnsw"),
    )


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("session"))
    title: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("message"))
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class RetrievalTrace(Base):
    __tablename__ = "retrieval_traces"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("trace"))
    session_id: Mapped[str | None] = mapped_column(ForeignKey("chat_sessions.id"))
    message_id: Mapped[str | None] = mapped_column(ForeignKey("chat_messages.id"))
    query: Mapped[str] = mapped_column(Text, nullable=False)
    policy: Mapped[str] = mapped_column(String, nullable=False)
    selected_sources_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    scores_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConnectionProfile(Base):
    __tablename__ = "connection_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("profile"))
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_ref: Mapped[str | None] = mapped_column(Text)
    capabilities_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 6: Add session factory**

Create `src/calliope/db/session.py`:

```python
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from calliope.config import Settings


def create_db_engine(database_url: str):
    return create_engine(database_url, future=True)


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=create_db_engine(database_url), expire_on_commit=False)


def get_session(settings: Settings | None = None) -> Iterator[Session]:
    factory = create_session_factory((settings or Settings()).database_url)
    with factory() as session:
        yield session
```

- [ ] **Step 7: Add Alembic configuration**

Create `alembic.ini`:

```ini
[alembic]
script_location = alembic
prepend_sys_path = .

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

Create `alembic/env.py`:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from calliope.config import Settings
from calliope.db.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", Settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 8: Add initial migration**

Create `alembic/versions/0001_initial.py` with `CREATE EXTENSION vector`, all tables, GIN index on `search_vector`, and HNSW index on `embedding`. Use the SQLAlchemy metadata from `src/calliope/db/models.py` as the table source when generating. Verify the migration contains:

```python
op.execute("CREATE EXTENSION IF NOT EXISTS vector")
```

- [ ] **Step 9: Add database fixtures**

Create `tests/conftest.py`:

```python
import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from calliope.db.models import Base


@pytest.fixture(scope="session")
def database_url() -> str:
    return os.environ.get(
        "CALLIOPE_TEST_DATABASE_URL",
        "postgresql+psycopg://calliope:calliope@localhost:5432/calliope",
    )


@pytest.fixture()
def db_engine(database_url: str):
    engine = create_engine(database_url, future=True)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.drop_all(connection)
        Base.metadata.create_all(connection)
    try:
        yield engine
    finally:
        with engine.begin() as connection:
            Base.metadata.drop_all(connection)


@pytest.fixture()
def db_session(db_engine) -> Iterator[Session]:
    factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    with factory() as session:
        yield session
```

- [ ] **Step 10: Start Postgres and run schema tests**

Run: `docker compose up -d postgres`

Expected: Postgres starts and healthcheck becomes healthy.

Run: `uv run pytest tests/integration/test_repositories.py -v`

Expected: PASS.

- [ ] **Step 11: Commit persistence foundation**

```bash
git add docker-compose.yml alembic.ini alembic src/calliope/db tests/conftest.py tests/integration/test_repositories.py
git commit -m "feat: add postgres persistence schema"
```

## Task 4: Workspace And Profile Repositories

**Files:**
- Create: `src/calliope/repositories/workspaces.py`
- Create: `src/calliope/repositories/profiles.py`
- Create: `src/calliope/services/workspaces.py`
- Create: `src/calliope/services/profiles.py`
- Create: `tests/integration/test_profiles.py`
- Modify: `tests/integration/test_repositories.py`

- [ ] **Step 1: Write repository and service tests**

Append to `tests/integration/test_repositories.py`:

```python
from calliope.domain.schemas import WorkspaceCreate
from calliope.repositories.workspaces import WorkspaceRepository


def test_workspace_repository_creates_and_lists(db_session) -> None:
    repo = WorkspaceRepository(db_session)
    created = repo.create(WorkspaceCreate(name="World", root_path="/tmp/world"))

    listed = repo.list()

    assert created.id.startswith("workspace_")
    assert [workspace.name for workspace in listed] == ["World"]
```

Create `tests/integration/test_profiles.py`:

```python
from calliope.domain.enums import ProfileCapability, ProfileKind
from calliope.domain.errors import AppError
from calliope.domain.schemas import ProfileCreate
from calliope.services.profiles import ProfileService


def test_profile_service_creates_lists_and_requires_capability(db_session) -> None:
    service = ProfileService(db_session)
    created = service.create(
        ProfileCreate(
            name="local-chat",
            kind=ProfileKind.OPENAI_COMPATIBLE,
            base_url="http://localhost:4000/v1",
            model="local-model",
            capabilities=[ProfileCapability.CHAT],
        )
    )

    assert created.name == "local-chat"
    assert service.list()[0].capabilities == [ProfileCapability.CHAT]

    try:
        service.require_capability("local-chat", ProfileCapability.EMBEDDINGS)
    except AppError as exc:
        assert exc.code == "model_profile_missing_capability"
    else:
        raise AssertionError("expected AppError")
```

- [ ] **Step 2: Run repository tests to verify failure**

Run: `uv run pytest tests/integration/test_repositories.py tests/integration/test_profiles.py -v`

Expected: FAIL with missing repository modules.

- [ ] **Step 3: Implement workspace repository and service**

Create `src/calliope/repositories/workspaces.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from calliope.db.models import Workspace
from calliope.domain.errors import AppError
from calliope.domain.schemas import WorkspaceCreate, WorkspaceRead


class WorkspaceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, payload: WorkspaceCreate) -> WorkspaceRead:
        workspace = Workspace(
            name=payload.name,
            root_path=payload.root_path,
            include_globs=payload.include_globs,
            exclude_globs=payload.exclude_globs,
        )
        self.session.add(workspace)
        self.session.commit()
        self.session.refresh(workspace)
        return self._to_read(workspace)

    def list(self) -> list[WorkspaceRead]:
        rows = self.session.scalars(select(Workspace).order_by(Workspace.name)).all()
        return [self._to_read(row) for row in rows]

    def get(self, workspace_id: str) -> WorkspaceRead:
        workspace = self.session.get(Workspace, workspace_id)
        if workspace is None:
            raise AppError(
                code="workspace_not_found",
                message="Workspace not found.",
                status_code=404,
                details={"workspace_id": workspace_id},
            )
        return self._to_read(workspace)

    @staticmethod
    def _to_read(workspace: Workspace) -> WorkspaceRead:
        return WorkspaceRead(
            id=workspace.id,
            name=workspace.name,
            root_path=workspace.root_path,
            include_globs=workspace.include_globs,
            exclude_globs=workspace.exclude_globs,
            created_at=workspace.created_at,
        )
```

Create `src/calliope/services/workspaces.py`:

```python
from sqlalchemy.orm import Session

from calliope.domain.schemas import WorkspaceCreate, WorkspaceRead
from calliope.repositories.workspaces import WorkspaceRepository


class WorkspaceService:
    def __init__(self, session: Session) -> None:
        self.repository = WorkspaceRepository(session)

    def create(self, payload: WorkspaceCreate) -> WorkspaceRead:
        return self.repository.create(payload)

    def list(self) -> list[WorkspaceRead]:
        return self.repository.list()
```

- [ ] **Step 4: Implement profile repository and service**

Create `src/calliope/repositories/profiles.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from calliope.db.models import ConnectionProfile
from calliope.domain.enums import ProfileCapability
from calliope.domain.errors import AppError
from calliope.domain.schemas import ProfileCreate, ProfileRead


class ProfileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, payload: ProfileCreate) -> ProfileRead:
        profile = ConnectionProfile(
            name=payload.name,
            kind=payload.kind.value,
            base_url=payload.base_url,
            model=payload.model,
            api_key_ref=payload.api_key_ref,
            capabilities_json=[capability.value for capability in payload.capabilities],
        )
        self.session.add(profile)
        self.session.commit()
        self.session.refresh(profile)
        return self._to_read(profile)

    def list(self) -> list[ProfileRead]:
        rows = self.session.scalars(select(ConnectionProfile).order_by(ConnectionProfile.name)).all()
        return [self._to_read(row) for row in rows]

    def get_by_name(self, name: str) -> ProfileRead:
        profile = self.session.scalar(select(ConnectionProfile).where(ConnectionProfile.name == name))
        if profile is None:
            raise AppError(
                code="connection_profile_not_found",
                message="Connection profile not found.",
                status_code=404,
                details={"name": name},
            )
        return self._to_read(profile)

    @staticmethod
    def _to_read(profile: ConnectionProfile) -> ProfileRead:
        return ProfileRead(
            id=profile.id,
            name=profile.name,
            kind=profile.kind,
            base_url=profile.base_url,
            model=profile.model,
            api_key_ref=profile.api_key_ref,
            capabilities=[ProfileCapability(value) for value in profile.capabilities_json],
            created_at=profile.created_at,
        )
```

Create `src/calliope/services/profiles.py`:

```python
from sqlalchemy.orm import Session

from calliope.domain.enums import ProfileCapability
from calliope.domain.errors import AppError
from calliope.domain.schemas import ProfileCreate, ProfileRead
from calliope.repositories.profiles import ProfileRepository


class ProfileService:
    def __init__(self, session: Session) -> None:
        self.repository = ProfileRepository(session)

    def create(self, payload: ProfileCreate) -> ProfileRead:
        return self.repository.create(payload)

    def list(self) -> list[ProfileRead]:
        return self.repository.list()

    def require_capability(self, name: str, capability: ProfileCapability) -> ProfileRead:
        profile = self.repository.get_by_name(name)
        if capability not in profile.capabilities:
            raise AppError(
                code="model_profile_missing_capability",
                message="Connection profile does not support the requested capability.",
                status_code=400,
                details={"name": name, "capability": capability.value},
            )
        return profile
```

- [ ] **Step 5: Run repository and profile tests**

Run: `uv run pytest tests/integration/test_repositories.py tests/integration/test_profiles.py -v`

Expected: PASS.

- [ ] **Step 6: Commit repositories**

```bash
git add src/calliope/repositories src/calliope/services tests/integration/test_repositories.py tests/integration/test_profiles.py
git commit -m "feat: add workspace and profile repositories"
```

## Task 5: Markdown Scanner, Parser, And Chunker

**Files:**
- Create: `tests/fixtures/world/characters/kaelen.md`
- Create: `src/calliope/ingest/scanner.py`
- Create: `src/calliope/ingest/parser.py`
- Create: `src/calliope/ingest/chunker.py`
- Create: `tests/unit/test_scanner.py`
- Create: `tests/unit/test_parser.py`
- Create: `tests/unit/test_chunker.py`

- [ ] **Step 1: Add markdown fixture**

Create `tests/fixtures/world/characters/kaelen.md`:

```markdown
---
type: character
name: Ser Kaelen Morcant
aliases:
  - The Black Hart
canon: true
---

# Ser Kaelen Morcant

Ser Kaelen is a knight of House Morcant.

## Biography

### Exile

After the Second Winter War, Kaelen was exiled from Velmora.

### Return

Kaelen returned under a moonless sky.
```

- [ ] **Step 2: Write scanner test**

Create `tests/unit/test_scanner.py`:

```python
from pathlib import Path

from calliope.ingest.scanner import scan_workspace


def test_scan_workspace_finds_markdown_files() -> None:
    root = Path("tests/fixtures/world")

    files = scan_workspace(root, include_globs=["**/*.md"], exclude_globs=["drafts/**"])

    assert [file.relative_path for file in files] == ["characters/kaelen.md"]
    assert files[0].content_hash
```

- [ ] **Step 3: Write parser test**

Create `tests/unit/test_parser.py`:

```python
from pathlib import Path

from calliope.ingest.parser import parse_markdown_file


def test_parse_markdown_extracts_frontmatter_and_headings() -> None:
    parsed = parse_markdown_file(Path("tests/fixtures/world/characters/kaelen.md"), "characters/kaelen.md")

    assert parsed.title == "Ser Kaelen Morcant"
    assert parsed.frontmatter["type"] == "character"
    assert parsed.sections[0].heading_path == "Ser Kaelen Morcant"
    assert parsed.sections[1].heading_path == "Ser Kaelen Morcant > Biography"
    assert parsed.sections[2].heading_path == "Ser Kaelen Morcant > Biography > Exile"
```

- [ ] **Step 4: Write chunker test**

Create `tests/unit/test_chunker.py`:

```python
from pathlib import Path

from calliope.ingest.chunker import chunk_document
from calliope.ingest.parser import parse_markdown_file


def test_chunk_document_preserves_heading_context() -> None:
    parsed = parse_markdown_file(Path("tests/fixtures/world/characters/kaelen.md"), "characters/kaelen.md")

    chunks = chunk_document(parsed, max_chars=120)

    exile = [chunk for chunk in chunks if chunk.heading_path.endswith("Exile")][0]
    assert "Second Winter War" in exile.text
    assert exile.metadata["path"] == "characters/kaelen.md"
```

- [ ] **Step 5: Run ingestion tests to verify failure**

Run: `uv run pytest tests/unit/test_scanner.py tests/unit/test_parser.py tests/unit/test_chunker.py -v`

Expected: FAIL with missing `calliope.ingest` modules.

- [ ] **Step 6: Implement scanner**

Create `src/calliope/ingest/scanner.py`:

```python
from dataclasses import dataclass
from fnmatch import fnmatch
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True)
class ScannedFile:
    absolute_path: Path
    relative_path: str
    content_hash: str
    modified_at_ns: int


def scan_workspace(root: Path, include_globs: list[str], exclude_globs: list[str]) -> list[ScannedFile]:
    results: list[ScannedFile] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if not any(fnmatch(relative, pattern) for pattern in include_globs):
            continue
        if any(fnmatch(relative, pattern) for pattern in exclude_globs):
            continue
        content = path.read_bytes()
        results.append(
            ScannedFile(
                absolute_path=path,
                relative_path=relative,
                content_hash=sha256(content).hexdigest(),
                modified_at_ns=path.stat().st_mtime_ns,
            )
        )
    return results
```

- [ ] **Step 7: Implement parser**

Create `src/calliope/ingest/parser.py`:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import frontmatter


@dataclass(frozen=True)
class MarkdownSection:
    heading_path: str
    text: str


@dataclass(frozen=True)
class ParsedDocument:
    path: str
    title: str
    frontmatter: dict[str, Any]
    raw_markdown: str
    sections: list[MarkdownSection]


def parse_markdown_file(path: Path, relative_path: str) -> ParsedDocument:
    post = frontmatter.loads(path.read_text(encoding="utf-8"))
    frontmatter_data = dict(post.metadata)
    content = post.content
    sections = _split_sections(content)
    title = str(frontmatter_data.get("name") or _first_h1(content) or Path(relative_path).stem)
    return ParsedDocument(
        path=relative_path,
        title=title,
        frontmatter=frontmatter_data,
        raw_markdown=content,
        sections=sections,
    )


def _first_h1(content: str) -> str | None:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _split_sections(content: str) -> list[MarkdownSection]:
    heading_stack: list[tuple[int, str]] = []
    current_lines: list[str] = []
    current_heading = ""
    sections: list[MarkdownSection] = []

    def flush() -> None:
        nonlocal current_lines, current_heading
        text = "\n".join(line for line in current_lines).strip()
        if text:
            sections.append(MarkdownSection(heading_path=current_heading, text=text))
        current_lines = []

    for line in content.splitlines():
        if line.startswith("#"):
            marker, _, title = line.partition(" ")
            if set(marker) == {"#"} and title:
                flush()
                level = len(marker)
                heading_stack[:] = [(existing, name) for existing, name in heading_stack if existing < level]
                heading_stack.append((level, title.strip()))
                current_heading = " > ".join(name for _, name in heading_stack)
                continue
        current_lines.append(line)
    flush()
    return sections
```

- [ ] **Step 8: Implement chunker**

Create `src/calliope/ingest/chunker.py`:

```python
from dataclasses import dataclass
from typing import Any

from calliope.ingest.parser import ParsedDocument


@dataclass(frozen=True)
class MarkdownChunk:
    chunk_index: int
    heading_path: str
    text: str
    token_count: int
    metadata: dict[str, Any]


def chunk_document(document: ParsedDocument, max_chars: int = 1800) -> list[MarkdownChunk]:
    chunks: list[MarkdownChunk] = []
    for section in document.sections:
        pieces = _split_text(section.text, max_chars=max_chars)
        for piece in pieces:
            chunks.append(
                MarkdownChunk(
                    chunk_index=len(chunks),
                    heading_path=section.heading_path,
                    text=piece,
                    token_count=max(1, len(piece.split())),
                    metadata={
                        "path": document.path,
                        "title": document.title,
                        "frontmatter": document.frontmatter,
                    },
                )
            )
    return chunks


def _split_text(text: str, max_chars: int) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    pieces: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip()
        if current and len(candidate) > max_chars:
            pieces.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces
```

- [ ] **Step 9: Run ingestion tests**

Run: `uv run pytest tests/unit/test_scanner.py tests/unit/test_parser.py tests/unit/test_chunker.py -v`

Expected: PASS.

- [ ] **Step 10: Commit ingestion primitives**

```bash
git add src/calliope/ingest tests/fixtures tests/unit/test_scanner.py tests/unit/test_parser.py tests/unit/test_chunker.py
git commit -m "feat: add markdown ingestion primitives"
```

## Task 6: OpenAI-Compatible Client

**Files:**
- Create: `src/calliope/llm/openai_compatible.py`
- Create: `tests/unit/test_openai_compatible_client.py`

- [ ] **Step 1: Write client tests with fake HTTP responses**

Create `tests/unit/test_openai_compatible_client.py`:

```python
import httpx
import pytest

from calliope.llm.openai_compatible import OpenAICompatibleClient


@pytest.mark.asyncio
async def test_create_embedding_calls_openai_compatible_endpoint() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"data": [{"embedding": [0.1, 0.2, 0.3]}]},
        )
    )
    client = OpenAICompatibleClient(
        base_url="http://local/v1",
        model="embed-model",
        api_key="test",
        http_client=httpx.AsyncClient(transport=transport),
    )

    embedding = await client.embed("Kaelen")

    assert embedding == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_chat_returns_message_content() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Grounded answer"}}]},
        )
    )
    client = OpenAICompatibleClient(
        base_url="http://local/v1",
        model="chat-model",
        api_key="test",
        http_client=httpx.AsyncClient(transport=transport),
    )

    answer = await client.chat([{"role": "user", "content": "Who is Kaelen?"}])

    assert answer == "Grounded answer"
```

- [ ] **Step 2: Run client tests to verify failure**

Run: `uv run pytest tests/unit/test_openai_compatible_client.py -v`

Expected: FAIL with missing `calliope.llm` module.

- [ ] **Step 3: Implement OpenAI-compatible client**

Create `src/calliope/llm/openai_compatible.py`:

```python
from collections.abc import Sequence
from typing import Any

import httpx

from calliope.domain.errors import AppError


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or "not-needed"
        self.http_client = http_client or httpx.AsyncClient(timeout=30)

    async def embed(self, text: str) -> list[float]:
        response = await self.http_client.post(
            f"{self.base_url}/embeddings",
            headers=self._headers(),
            json={"model": self.model, "input": text},
        )
        self._raise_for_status(response, code="embedding_failed")
        data = response.json()
        return [float(value) for value in data["data"][0]["embedding"]]

    async def chat(self, messages: Sequence[dict[str, str]]) -> str:
        response = await self.http_client.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json={"model": self.model, "messages": list(messages)},
        )
        self._raise_for_status(response, code="generation_failed")
        data = response.json()
        return str(data["choices"][0]["message"]["content"])

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    @staticmethod
    def _raise_for_status(response: httpx.Response, *, code: str) -> None:
        if response.status_code >= 400:
            raise AppError(
                code=code,
                message="OpenAI-compatible request failed.",
                status_code=502,
                details={"status_code": response.status_code, "body": response.text},
            )
```

- [ ] **Step 4: Run client tests**

Run: `uv run pytest tests/unit/test_openai_compatible_client.py -v`

Expected: PASS.

- [ ] **Step 5: Commit client**

```bash
git add src/calliope/llm tests/unit/test_openai_compatible_client.py
git commit -m "feat: add openai compatible client"
```

## Task 7: Indexer And Document Persistence

**Files:**
- Create: `src/calliope/repositories/documents.py`
- Create: `src/calliope/repositories/chunks.py`
- Create: `src/calliope/ingest/indexer.py`
- Create: `tests/integration/test_indexer.py`

- [ ] **Step 1: Write indexer integration test**

Create `tests/integration/test_indexer.py`:

```python
from pathlib import Path

from calliope.domain.schemas import WorkspaceCreate
from calliope.ingest.indexer import Reindexer
from calliope.repositories.workspaces import WorkspaceRepository


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        return [float(len(text) % 7)] * 384


def test_reindexer_stores_documents_chunks_and_search_vectors(db_session) -> None:
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(name="World", root_path=str(Path("tests/fixtures/world").resolve()))
    )
    reindexer = Reindexer(db_session, embedding_client=FakeEmbeddingClient())

    result = reindexer.reindex_workspace(workspace.id)

    assert result.documents_indexed == 1
    assert result.chunks_indexed >= 3
```

- [ ] **Step 2: Run indexer test to verify failure**

Run: `uv run pytest tests/integration/test_indexer.py -v`

Expected: FAIL with missing `Reindexer`.

- [ ] **Step 3: Implement document repository**

Create `src/calliope/repositories/documents.py`:

```python
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from calliope.db.models import Document
from calliope.domain.errors import AppError
from calliope.domain.schemas import DocumentRead


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(
        self,
        *,
        workspace_id: str,
        path: str,
        title: str,
        frontmatter: dict[str, Any],
        content_hash: str,
        modified_at_ns: int,
    ) -> Document:
        modified_at = datetime.fromtimestamp(modified_at_ns / 1_000_000_000, tz=UTC)
        document = self.session.scalar(
            select(Document).where(Document.workspace_id == workspace_id, Document.path == path)
        )
        if document is None:
            document = Document(
                workspace_id=workspace_id,
                path=path,
                title=title,
                frontmatter_json=frontmatter,
                content_hash=content_hash,
                modified_at=modified_at,
                indexed_at=datetime.now(UTC),
            )
            self.session.add(document)
        else:
            document.title = title
            document.frontmatter_json = frontmatter
            document.content_hash = content_hash
            document.modified_at = modified_at
            document.indexed_at = datetime.now(UTC)
            document.deleted_at = None
        self.session.flush()
        return document

    def list(self) -> list[DocumentRead]:
        rows = self.session.scalars(select(Document).order_by(Document.path)).all()
        return [self._to_read(row) for row in rows]

    def get(self, document_id: str) -> DocumentRead:
        document = self.session.get(Document, document_id)
        if document is None:
            raise AppError(
                code="document_not_found",
                message="Document not found.",
                status_code=404,
                details={"document_id": document_id},
            )
        return self._to_read(document)

    @staticmethod
    def _to_read(document: Document) -> DocumentRead:
        return DocumentRead(
            id=document.id,
            workspace_id=document.workspace_id,
            path=document.path,
            title=document.title,
            frontmatter=document.frontmatter_json,
            modified_at=document.modified_at,
            indexed_at=document.indexed_at,
        )
```

- [ ] **Step 4: Implement chunk repository**

Create `src/calliope/repositories/chunks.py`:

```python
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from calliope.db.models import Chunk
from calliope.domain.errors import AppError
from calliope.domain.schemas import SourceReference
from calliope.ingest.chunker import MarkdownChunk


class ChunkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def replace_for_document(
        self,
        *,
        document_id: str,
        chunks: list[MarkdownChunk],
        embeddings: list[list[float]],
    ) -> None:
        self.session.execute(delete(Chunk).where(Chunk.document_id == document_id))
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            self.session.add(
                Chunk(
                    document_id=document_id,
                    chunk_index=chunk.chunk_index,
                    heading_path=chunk.heading_path,
                    text=chunk.text,
                    token_count=chunk.token_count,
                    metadata_json=chunk.metadata,
                    embedding=embedding,
                    search_vector=func.to_tsvector("english", chunk.text),
                )
            )

    def source_for_chunk(self, chunk_id: str, score: float = 1.0) -> SourceReference:
        chunk = self.session.get(Chunk, chunk_id)
        if chunk is None:
            raise AppError(
                code="chunk_not_found",
                message="Chunk not found.",
                status_code=404,
                details={"chunk_id": chunk_id},
            )
        return SourceReference(
            document_id=chunk.document_id,
            chunk_id=chunk.id,
            path=str(chunk.metadata_json.get("path", "")),
            heading=chunk.heading_path,
            excerpt=chunk.text[:300],
            score=score,
        )

    def count(self) -> int:
        return int(self.session.scalar(select(func.count()).select_from(Chunk)) or 0)
```

- [ ] **Step 5: Implement reindexer**

Create `src/calliope/ingest/indexer.py`:

```python
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sqlalchemy.orm import Session

from calliope.ingest.chunker import chunk_document
from calliope.ingest.parser import parse_markdown_file
from calliope.ingest.scanner import scan_workspace
from calliope.repositories.chunks import ChunkRepository
from calliope.repositories.documents import DocumentRepository
from calliope.repositories.workspaces import WorkspaceRepository


class EmbeddingClient(Protocol):
    async def embed(self, text: str) -> list[float]:
        pass


@dataclass(frozen=True)
class ReindexResult:
    documents_indexed: int
    chunks_indexed: int


class Reindexer:
    def __init__(self, session: Session, embedding_client: EmbeddingClient) -> None:
        self.session = session
        self.embedding_client = embedding_client

    def reindex_workspace(self, workspace_id: str) -> ReindexResult:
        workspace = WorkspaceRepository(self.session).get(workspace_id)
        document_repo = DocumentRepository(self.session)
        chunk_repo = ChunkRepository(self.session)
        documents_indexed = 0
        chunks_indexed = 0

        for scanned in scan_workspace(
            Path(workspace.root_path), workspace.include_globs, workspace.exclude_globs
        ):
            parsed = parse_markdown_file(scanned.absolute_path, scanned.relative_path)
            chunks = chunk_document(parsed)
            embeddings = [asyncio.run(self.embedding_client.embed(chunk.text)) for chunk in chunks]
            document = document_repo.upsert(
                workspace_id=workspace.id,
                path=parsed.path,
                title=parsed.title,
                frontmatter=parsed.frontmatter,
                content_hash=scanned.content_hash,
                modified_at_ns=scanned.modified_at_ns,
            )
            chunk_repo.replace_for_document(document_id=document.id, chunks=chunks, embeddings=embeddings)
            documents_indexed += 1
            chunks_indexed += len(chunks)

        self.session.commit()
        return ReindexResult(documents_indexed=documents_indexed, chunks_indexed=chunks_indexed)
```

- [ ] **Step 6: Run indexer test**

Run: `uv run pytest tests/integration/test_indexer.py -v`

Expected: PASS.

- [ ] **Step 7: Commit indexing persistence**

```bash
git add src/calliope/repositories/documents.py src/calliope/repositories/chunks.py src/calliope/ingest/indexer.py tests/integration/test_indexer.py
git commit -m "feat: persist indexed markdown chunks"
```

## Task 8: Hybrid Retrieval And Search Service

**Files:**
- Create: `src/calliope/retrieval/hybrid.py`
- Create: `src/calliope/services/search.py`
- Create: `tests/unit/test_hybrid_retriever.py`
- Create: `tests/integration/test_search_service.py`

- [ ] **Step 1: Write reciprocal-rank fusion unit test**

Create `tests/unit/test_hybrid_retriever.py`:

```python
from calliope.retrieval.hybrid import fuse_ranked_results


def test_fuse_ranked_results_prefers_items_seen_by_both_searches() -> None:
    fused = fuse_ranked_results(
        vector_ids=["chunk_a", "chunk_b", "chunk_c"],
        lexical_ids=["chunk_c", "chunk_a"],
        k=60,
    )

    assert fused[0].chunk_id == "chunk_a"
    assert fused[0].score > fused[-1].score
```

- [ ] **Step 2: Write search service integration test**

Create `tests/integration/test_search_service.py`:

```python
from pathlib import Path

from calliope.domain.schemas import SearchRequest, WorkspaceCreate
from calliope.ingest.indexer import Reindexer
from calliope.repositories.workspaces import WorkspaceRepository
from calliope.services.search import SearchService


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        value = 1.0 if "Kaelen" in text or "Kaelen" in text else 0.1
        return [value] * 384


def test_search_service_returns_cited_sources(db_session) -> None:
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(name="World", root_path=str(Path("tests/fixtures/world").resolve()))
    )
    embedder = FakeEmbeddingClient()
    Reindexer(db_session, embedding_client=embedder).reindex_workspace(workspace.id)

    response = SearchService(db_session, embedding_client=embedder).search(
        SearchRequest(query="Kaelen exile", workspace_id=workspace.id, limit=3)
    )

    assert response.sources
    assert response.sources[0].path == "characters/kaelen.md"
```

- [ ] **Step 3: Run search tests to verify failure**

Run: `uv run pytest tests/unit/test_hybrid_retriever.py tests/integration/test_search_service.py -v`

Expected: FAIL with missing `calliope.retrieval`.

- [ ] **Step 4: Implement score fusion and retriever**

Create `src/calliope/retrieval/hybrid.py`:

```python
import asyncio
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from calliope.db.models import Chunk, Document


class EmbeddingClient(Protocol):
    async def embed(self, text: str) -> list[float]:
        pass


@dataclass(frozen=True)
class FusedHit:
    chunk_id: str
    score: float


def fuse_ranked_results(vector_ids: list[str], lexical_ids: list[str], k: int = 60) -> list[FusedHit]:
    scores: dict[str, float] = {}
    for rank, chunk_id in enumerate(vector_ids, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    for rank, chunk_id in enumerate(lexical_ids, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return [
        FusedHit(chunk_id=chunk_id, score=score)
        for chunk_id, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
    ]


class HybridRetriever:
    def __init__(self, session: Session, embedding_client: EmbeddingClient) -> None:
        self.session = session
        self.embedding_client = embedding_client

    def retrieve(self, query: str, *, workspace_id: str | None, limit: int) -> list[FusedHit]:
        embedding = asyncio.run(self.embedding_client.embed(query))
        vector_ids = self._vector_search(embedding, workspace_id=workspace_id, limit=limit * 2)
        lexical_ids = self._lexical_search(query, workspace_id=workspace_id, limit=limit * 2)
        return fuse_ranked_results(vector_ids, lexical_ids)[:limit]

    def _vector_search(self, embedding: list[float], *, workspace_id: str | None, limit: int) -> list[str]:
        statement = select(Chunk.id).join(Document).order_by(Chunk.embedding.l2_distance(embedding)).limit(limit)
        if workspace_id:
            statement = statement.where(Document.workspace_id == workspace_id)
        return list(self.session.scalars(statement))

    def _lexical_search(self, query: str, *, workspace_id: str | None, limit: int) -> list[str]:
        statement = (
            select(Chunk.id)
            .join(Document)
            .where(Chunk.search_vector.op("@@")(text("plainto_tsquery('english', :query)")))
            .params(query=query)
            .limit(limit)
        )
        if workspace_id:
            statement = statement.where(Document.workspace_id == workspace_id)
        return list(self.session.scalars(statement))
```

- [ ] **Step 5: Implement search service**

Create `src/calliope/services/search.py`:

```python
from sqlalchemy.orm import Session

from calliope.domain.schemas import SearchRequest, SearchResponse
from calliope.repositories.chunks import ChunkRepository
from calliope.retrieval.hybrid import EmbeddingClient, HybridRetriever


class SearchService:
    def __init__(self, session: Session, embedding_client: EmbeddingClient) -> None:
        self.session = session
        self.embedding_client = embedding_client

    def search(self, request: SearchRequest) -> SearchResponse:
        retriever = HybridRetriever(self.session, self.embedding_client)
        chunk_repo = ChunkRepository(self.session)
        hits = retriever.retrieve(request.query, workspace_id=request.workspace_id, limit=request.limit)
        sources = [chunk_repo.source_for_chunk(hit.chunk_id, score=hit.score) for hit in hits]
        return SearchResponse(sources=sources)
```

- [ ] **Step 6: Run search tests**

Run: `uv run pytest tests/unit/test_hybrid_retriever.py tests/integration/test_search_service.py -v`

Expected: PASS.

- [ ] **Step 7: Commit search**

```bash
git add src/calliope/retrieval src/calliope/services/search.py tests/unit/test_hybrid_retriever.py tests/integration/test_search_service.py
git commit -m "feat: add hybrid search service"
```

## Task 9: Prompt Builder, Chat Service, Sessions, And Traces

**Files:**
- Create: `src/calliope/prompts/builder.py`
- Create: `src/calliope/repositories/chats.py`
- Create: `src/calliope/services/chat.py`
- Create: `tests/unit/test_prompt_builder.py`
- Create: `tests/integration/test_chat_service.py`

- [ ] **Step 1: Write prompt builder tests**

Create `tests/unit/test_prompt_builder.py`:

```python
from calliope.domain.enums import CanonPolicy
from calliope.domain.schemas import SourceReference
from calliope.prompts.builder import build_chat_messages


def test_strict_canon_prompt_requires_insufficient_evidence_answer() -> None:
    messages = build_chat_messages(
        message="Who exiled Kaelen?",
        policy=CanonPolicy.STRICT_CANON,
        sources=[
            SourceReference(
                document_id="doc_1",
                chunk_id="chunk_1",
                path="characters/kaelen.md",
                heading="Biography > Exile",
                excerpt="Kaelen was exiled from Velmora.",
                score=0.9,
            )
        ],
    )

    assert messages[0]["role"] == "system"
    assert "indexed canon does not contain enough information" in messages[0]["content"]
    assert "characters/kaelen.md" in messages[1]["content"]
```

- [ ] **Step 2: Write chat service integration test**

Create `tests/integration/test_chat_service.py`:

```python
from pathlib import Path

from calliope.domain.enums import CanonPolicy
from calliope.domain.schemas import ChatRequest, WorkspaceCreate
from calliope.ingest.indexer import Reindexer
from calliope.repositories.workspaces import WorkspaceRepository
from calliope.services.chat import ChatService


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        return [1.0 if "Kaelen" in text else 0.1] * 384


class FakeChatClient:
    async def chat(self, messages):
        return "Kaelen was exiled from Velmora. [characters/kaelen.md]"


def test_chat_service_returns_answer_sources_and_trace(db_session) -> None:
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(name="World", root_path=str(Path("tests/fixtures/world").resolve()))
    )
    embedder = FakeEmbeddingClient()
    Reindexer(db_session, embedding_client=embedder).reindex_workspace(workspace.id)

    response = ChatService(db_session, embedding_client=embedder, chat_client=FakeChatClient()).chat(
        ChatRequest(
            message="Where was Kaelen exiled from?",
            policy=CanonPolicy.STRICT_CANON,
            workspace_id=workspace.id,
        )
    )

    assert "Velmora" in response.answer
    assert response.sources
    assert response.trace_id.startswith("trace_")
```

- [ ] **Step 3: Run chat tests to verify failure**

Run: `uv run pytest tests/unit/test_prompt_builder.py tests/integration/test_chat_service.py -v`

Expected: FAIL with missing prompt and chat modules.

- [ ] **Step 4: Implement prompt builder**

Create `src/calliope/prompts/builder.py`:

```python
from calliope.domain.enums import CanonPolicy
from calliope.domain.schemas import SourceReference


POLICY_TEXT = {
    CanonPolicy.STRICT_CANON: (
        "Answer only from the provided canon sources. If the sources do not contain enough "
        "evidence, say: The indexed canon does not contain enough information."
    ),
    CanonPolicy.CANON_PLUS_INFERENCE: (
        "Use canon sources first. Separate cited facts from inference with clear wording."
    ),
    CanonPolicy.CREATIVE_BUT_CONSISTENT: (
        "Generate draft material inspired by canon. Mark generated material as draft and cite sources used."
    ),
}


def build_chat_messages(
    *, message: str, policy: CanonPolicy, sources: list[SourceReference]
) -> list[dict[str, str]]:
    context = "\n\n".join(
        f"[{index}] {source.path} :: {source.heading}\n{source.excerpt}"
        for index, source in enumerate(sources, start=1)
    )
    return [
        {
            "role": "system",
            "content": (
                "You are Calliope, a grounded worldbuilding assistant.\n"
                f"{POLICY_TEXT[policy]}\n"
                "Cite sources by path when making factual claims."
            ),
        },
        {"role": "user", "content": f"Sources:\n{context}\n\nQuestion:\n{message}"},
    ]
```

- [ ] **Step 5: Implement chat repository**

Create `src/calliope/repositories/chats.py`:

```python
from typing import Any

from sqlalchemy.orm import Session

from calliope.db.models import ChatMessage, ChatSession, RetrievalTrace
from calliope.domain.enums import CanonPolicy
from calliope.domain.schemas import SourceReference


class ChatRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_session(self, title: str | None = None) -> ChatSession:
        session = ChatSession(title=title)
        self.session.add(session)
        self.session.flush()
        return session

    def add_message(self, *, session_id: str, role: str, content: str, metadata: dict[str, Any]) -> ChatMessage:
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            metadata_json=metadata,
        )
        self.session.add(message)
        self.session.flush()
        return message

    def add_trace(
        self,
        *,
        session_id: str,
        message_id: str,
        query: str,
        policy: CanonPolicy,
        sources: list[SourceReference],
        scores: dict[str, Any],
    ) -> RetrievalTrace:
        trace = RetrievalTrace(
            session_id=session_id,
            message_id=message_id,
            query=query,
            policy=policy.value,
            selected_sources_json=[source.model_dump() for source in sources],
            scores_json=scores,
        )
        self.session.add(trace)
        self.session.flush()
        return trace

    def get_session(self, session_id: str):
        session = self.session.get(ChatSession, session_id)
        if session is None:
            from calliope.domain.errors import AppError

            raise AppError(
                code="session_not_found",
                message="Chat session not found.",
                status_code=404,
                details={"session_id": session_id},
            )
        from calliope.domain.schemas import SessionRead

        return SessionRead(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
```

- [ ] **Step 6: Implement chat service**

Create `src/calliope/services/chat.py`:

```python
import asyncio
from typing import Protocol

from sqlalchemy.orm import Session

from calliope.domain.schemas import ChatRequest, ChatResponse, SearchRequest
from calliope.prompts.builder import build_chat_messages
from calliope.repositories.chats import ChatRepository
from calliope.retrieval.hybrid import EmbeddingClient
from calliope.services.search import SearchService


class ChatClient(Protocol):
    async def chat(self, messages: list[dict[str, str]]) -> str:
        pass


class ChatService:
    def __init__(
        self,
        session: Session,
        *,
        embedding_client: EmbeddingClient,
        chat_client: ChatClient,
    ) -> None:
        self.session = session
        self.embedding_client = embedding_client
        self.chat_client = chat_client

    def chat(self, request: ChatRequest) -> ChatResponse:
        search_response = SearchService(self.session, self.embedding_client).search(
            SearchRequest(query=request.message, workspace_id=request.workspace_id, limit=request.limit)
        )
        messages = build_chat_messages(
            message=request.message,
            policy=request.policy,
            sources=search_response.sources,
        )
        answer = asyncio.run(self.chat_client.chat(messages))
        repo = ChatRepository(self.session)
        session = repo.create_session(title=request.message[:80]) if request.session_id is None else repo.create_session()
        user_message = repo.add_message(
            session_id=session.id,
            role="user",
            content=request.message,
            metadata={"policy": request.policy.value},
        )
        repo.add_message(session_id=session.id, role="assistant", content=answer, metadata={})
        trace = repo.add_trace(
            session_id=session.id,
            message_id=user_message.id,
            query=request.message,
            policy=request.policy,
            sources=search_response.sources,
            scores={"source_count": len(search_response.sources)},
        )
        self.session.commit()
        return ChatResponse(answer=answer, sources=search_response.sources, trace_id=trace.id)
```

- [ ] **Step 7: Run chat tests**

Run: `uv run pytest tests/unit/test_prompt_builder.py tests/integration/test_chat_service.py -v`

Expected: PASS.

- [ ] **Step 8: Commit chat service**

```bash
git add src/calliope/prompts src/calliope/repositories/chats.py src/calliope/services/chat.py tests/unit/test_prompt_builder.py tests/integration/test_chat_service.py
git commit -m "feat: add grounded chat service"
```

## Task 10: FastAPI Routes

**Files:**
- Create: `src/calliope/api/dependencies.py`
- Create: `src/calliope/api/routes/workspaces.py`
- Create: `src/calliope/api/routes/profiles.py`
- Create: `src/calliope/api/routes/search.py`
- Create: `src/calliope/api/routes/chat.py`
- Create: `src/calliope/api/routes/documents.py`
- Create: `src/calliope/api/routes/sessions.py`
- Modify: `src/calliope/api/app.py`
- Modify: `tests/integration/test_api_contract.py`

- [ ] **Step 1: Extend API contract tests**

Append to `tests/integration/test_api_contract.py`:

```python
def test_openapi_contains_mvp_routes() -> None:
    client = TestClient(create_app())

    paths = client.get("/openapi.json").json()["paths"]

    assert "/v1/workspaces" in paths
    assert "/v1/reindex" in paths
    assert "/v1/search" in paths
    assert "/v1/chat" in paths
    assert "/v1/profiles" in paths
    assert "/v1/documents" in paths
    assert "/v1/sessions/{session_id}" in paths
```

- [ ] **Step 2: Run API route test to verify failure**

Run: `uv run pytest tests/integration/test_api_contract.py::test_openapi_contains_mvp_routes -v`

Expected: FAIL because route paths are missing.

- [ ] **Step 3: Add API dependencies and model client factories**

Create `src/calliope/api/dependencies.py`:

```python
import os
from collections.abc import Iterator

from sqlalchemy.orm import Session

from calliope.config import Settings
from calliope.db.session import create_session_factory
from calliope.domain.enums import ProfileCapability
from calliope.domain.schemas import ProfileRead
from calliope.llm.openai_compatible import OpenAICompatibleClient
from calliope.services.profiles import ProfileService


def get_db_session() -> Iterator[Session]:
    factory = create_session_factory(Settings().database_url)
    with factory() as session:
        yield session


def api_key_for(profile: ProfileRead) -> str | None:
    if profile.api_key_ref is None:
        return None
    return os.environ.get(profile.api_key_ref)


def get_embedding_client(session: Session) -> OpenAICompatibleClient:
    profile = ProfileService(session).require_capability(
        "default-embeddings", ProfileCapability.EMBEDDINGS
    )
    return OpenAICompatibleClient(
        base_url=profile.base_url,
        model=profile.model,
        api_key=api_key_for(profile),
    )


def get_chat_client(session: Session) -> OpenAICompatibleClient:
    profile = ProfileService(session).require_capability("default-chat", ProfileCapability.CHAT)
    return OpenAICompatibleClient(
        base_url=profile.base_url,
        model=profile.model,
        api_key=api_key_for(profile),
    )
```

- [ ] **Step 4: Add workspace and reindex routes**

Create `src/calliope/api/routes/workspaces.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from calliope.api.dependencies import get_db_session, get_embedding_client
from calliope.domain.schemas import ReindexRequest, ReindexResponse, WorkspaceCreate, WorkspaceRead
from calliope.ingest.indexer import Reindexer
from calliope.services.workspaces import WorkspaceService

router = APIRouter(tags=["workspaces"])


@router.post("/v1/workspaces", response_model=WorkspaceRead)
def create_workspace(
    payload: WorkspaceCreate, session: Session = Depends(get_db_session)
) -> WorkspaceRead:
    return WorkspaceService(session).create(payload)


@router.get("/v1/workspaces", response_model=list[WorkspaceRead])
def list_workspaces(session: Session = Depends(get_db_session)) -> list[WorkspaceRead]:
    return WorkspaceService(session).list()


@router.post("/v1/reindex", response_model=ReindexResponse)
def reindex_workspace(
    payload: ReindexRequest, session: Session = Depends(get_db_session)
) -> ReindexResponse:
    result = Reindexer(session, embedding_client=get_embedding_client(session)).reindex_workspace(
        payload.workspace_id
    )
    return ReindexResponse(
        documents_indexed=result.documents_indexed,
        chunks_indexed=result.chunks_indexed,
    )
```

- [ ] **Step 5: Add profile routes**

Create `src/calliope/api/routes/profiles.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from calliope.api.dependencies import get_db_session
from calliope.domain.schemas import ProfileCreate, ProfileRead
from calliope.services.profiles import ProfileService

router = APIRouter(prefix="/v1/profiles", tags=["profiles"])


@router.post("", response_model=ProfileRead)
def create_profile(payload: ProfileCreate, session: Session = Depends(get_db_session)) -> ProfileRead:
    return ProfileService(session).create(payload)


@router.get("", response_model=list[ProfileRead])
def list_profiles(session: Session = Depends(get_db_session)) -> list[ProfileRead]:
    return ProfileService(session).list()


@router.get("/{profile_id}", response_model=ProfileRead)
def get_profile(profile_id: str, session: Session = Depends(get_db_session)) -> ProfileRead:
    for profile in ProfileService(session).list():
        if profile.id == profile_id:
            return profile
    from calliope.domain.errors import AppError

    raise AppError(
        code="connection_profile_not_found",
        message="Connection profile not found.",
        status_code=404,
        details={"profile_id": profile_id},
    )


@router.post("/{profile_id}/test")
def test_profile(profile_id: str, session: Session = Depends(get_db_session)) -> dict[str, object]:
    profile = get_profile(profile_id, session)
    return {"ok": True, "id": profile.id, "capabilities": [value.value for value in profile.capabilities]}
```

- [ ] **Step 6: Add search and chat routes**

Create `src/calliope/api/routes/search.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from calliope.api.dependencies import get_db_session, get_embedding_client
from calliope.domain.schemas import SearchRequest, SearchResponse
from calliope.services.search import SearchService

router = APIRouter(tags=["search"])


@router.post("/v1/search", response_model=SearchResponse)
def search(request: SearchRequest, session: Session = Depends(get_db_session)) -> SearchResponse:
    return SearchService(session, embedding_client=get_embedding_client(session)).search(request)
```

Create `src/calliope/api/routes/chat.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from calliope.api.dependencies import get_chat_client, get_db_session, get_embedding_client
from calliope.domain.schemas import ChatRequest, ChatResponse
from calliope.services.chat import ChatService

router = APIRouter(tags=["chat"])


@router.post("/v1/chat", response_model=ChatResponse)
def chat(request: ChatRequest, session: Session = Depends(get_db_session)) -> ChatResponse:
    return ChatService(
        session,
        embedding_client=get_embedding_client(session),
        chat_client=get_chat_client(session),
    ).chat(request)
```

- [ ] **Step 7: Add document and session routes**

Create `src/calliope/api/routes/documents.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from calliope.api.dependencies import get_db_session
from calliope.domain.schemas import DocumentRead, SourceReference
from calliope.repositories.chunks import ChunkRepository
from calliope.repositories.documents import DocumentRepository

router = APIRouter(tags=["documents"])


@router.get("/v1/documents", response_model=list[DocumentRead])
def list_documents(session: Session = Depends(get_db_session)) -> list[DocumentRead]:
    return DocumentRepository(session).list()


@router.get("/v1/documents/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, session: Session = Depends(get_db_session)) -> DocumentRead:
    return DocumentRepository(session).get(document_id)


@router.get("/v1/sources/{chunk_id}", response_model=SourceReference)
def get_source(chunk_id: str, session: Session = Depends(get_db_session)) -> SourceReference:
    return ChunkRepository(session).source_for_chunk(chunk_id)
```

Create `src/calliope/api/routes/sessions.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from calliope.api.dependencies import get_db_session
from calliope.domain.schemas import SessionRead
from calliope.repositories.chats import ChatRepository

router = APIRouter(tags=["sessions"])


@router.get("/v1/sessions/{session_id}", response_model=SessionRead)
def get_session(session_id: str, session: Session = Depends(get_db_session)) -> SessionRead:
    return ChatRepository(session).get_session(session_id)
```

- [ ] **Step 8: Wire routers into app**

Modify `src/calliope/api/app.py`:

```python
from fastapi import FastAPI

from calliope.api.errors import register_error_handlers
from calliope.api.routes import chat, documents, profiles, search, sessions, workspaces
from calliope.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    app = FastAPI(title=resolved_settings.api_title)
    register_error_handlers(app)
    app.include_router(workspaces.router)
    app.include_router(profiles.router)
    app.include_router(search.router)
    app.include_router(chat.router)
    app.include_router(documents.router)
    app.include_router(sessions.router)
    return app
```

- [ ] **Step 9: Run OpenAPI route test**

Run: `uv run pytest tests/integration/test_api_contract.py::test_openapi_contains_mvp_routes -v`

Expected: PASS.

- [ ] **Step 10: Commit API routes**

```bash
git add src/calliope/api tests/integration/test_api_contract.py
git commit -m "feat: wire mvp api routes"
```

## Task 11: CLI Commands

**Files:**
- Modify: `src/calliope/cli.py`
- Create: `tests/integration/test_cli.py`

- [ ] **Step 1: Write CLI smoke tests**

Create `tests/integration/test_cli.py`:

```python
from typer.testing import CliRunner

from calliope.cli import app


def test_cli_lists_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "workspace" in result.output
    assert "profiles" in result.output
    assert "search" in result.output
    assert "chat" in result.output


def test_workspace_add_command_persists_workspace(db_session, database_url: str) -> None:
    result = CliRunner().invoke(
        app,
        ["workspace", "add", "/tmp/world", "--name", "World"],
        env={"CALLIOPE_DATABASE_URL": database_url},
    )

    assert result.exit_code == 0
    assert "World" in result.output
```

- [ ] **Step 2: Run CLI test to verify failure**

Run: `uv run pytest tests/integration/test_cli.py -v`

Expected: FAIL because CLI commands are missing.

- [ ] **Step 3: Implement CLI command groups**

Modify `src/calliope/cli.py`:

```python
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager

import typer
import uvicorn
from sqlalchemy.orm import Session

from calliope.config import Settings
from calliope.db.session import create_session_factory
from calliope.domain.enums import CanonPolicy, ProfileCapability, ProfileKind
from calliope.domain.schemas import ChatRequest, ProfileCreate, SearchRequest, WorkspaceCreate
from calliope.ingest.indexer import Reindexer
from calliope.llm.openai_compatible import OpenAICompatibleClient
from calliope.repositories.chats import ChatRepository
from calliope.services.chat import ChatService
from calliope.services.profiles import ProfileService
from calliope.services.search import SearchService
from calliope.services.workspaces import WorkspaceService

app = typer.Typer(help="Calliope local markdown knowledge backend.")
workspace_app = typer.Typer(help="Manage markdown workspaces.")
profiles_app = typer.Typer(help="Manage model connection profiles.")
sessions_app = typer.Typer(help="Inspect chat sessions.")

app.add_typer(workspace_app, name="workspace")
app.add_typer(profiles_app, name="profiles")
app.add_typer(sessions_app, name="sessions")


@contextmanager
def session_scope() -> Iterator[Session]:
    factory = create_session_factory(Settings().database_url)
    with factory() as session:
        yield session


def profile_client(session: Session, name: str, capability: ProfileCapability) -> OpenAICompatibleClient:
    profile = ProfileService(session).require_capability(name, capability)
    api_key = os.environ.get(profile.api_key_ref) if profile.api_key_ref else None
    return OpenAICompatibleClient(base_url=profile.base_url, model=profile.model, api_key=api_key)


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the HTTP API."""
    uvicorn.run("calliope.api.app:create_app", factory=True, host=host, port=port)


@workspace_app.command("add")
def workspace_add(path: str, name: str) -> None:
    with session_scope() as session:
        workspace = WorkspaceService(session).create(WorkspaceCreate(name=name, root_path=path))
    typer.echo(f"{workspace.id} {workspace.name} {workspace.root_path}")


@profiles_app.command("add")
def profile_add(
    name: str,
    kind: ProfileKind,
    base_url: str,
    model: str,
    capability: list[ProfileCapability] = typer.Option([ProfileCapability.CHAT], "--capability"),
    api_key_ref: str | None = None,
) -> None:
    with session_scope() as session:
        profile = ProfileService(session).create(
            ProfileCreate(
                name=name,
                kind=kind,
                base_url=base_url,
                model=model,
                api_key_ref=api_key_ref,
                capabilities=capability,
            )
        )
    typer.echo(f"{profile.id} {profile.name} {profile.model}")


@profiles_app.command("list")
def profile_list(json_output: bool = typer.Option(False, "--json")) -> None:
    with session_scope() as session:
        profiles = ProfileService(session).list()
    if json_output:
        typer.echo(json.dumps([profile.model_dump(mode="json") for profile in profiles]))
        return
    for profile in profiles:
        typer.echo(f"{profile.id} {profile.name} {profile.model}")


@profiles_app.command("test")
def profile_test(name: str) -> None:
    with session_scope() as session:
        profile = ProfileService(session).require_capability(name, ProfileCapability.CHAT)
    typer.echo(f"{profile.name} ok")


@app.command()
def reindex(workspace: str | None = None) -> None:
    with session_scope() as session:
        workspaces = WorkspaceService(session).list()
        workspace_id = workspace or workspaces[0].id
        result = Reindexer(
            session,
            embedding_client=profile_client(
                session, "default-embeddings", ProfileCapability.EMBEDDINGS
            ),
        ).reindex_workspace(workspace_id)
    typer.echo(f"documents={result.documents_indexed} chunks={result.chunks_indexed}")


@app.command()
def search(query: str, json_output: bool = typer.Option(False, "--json")) -> None:
    with session_scope() as session:
        response = SearchService(
            session,
            embedding_client=profile_client(
                session, "default-embeddings", ProfileCapability.EMBEDDINGS
            ),
        ).search(SearchRequest(query=query))
    if json_output:
        typer.echo(response.model_dump_json())
        return
    for source in response.sources:
        typer.echo(f"{source.score:.4f} {source.path} :: {source.heading}")


@app.command()
def chat(message: str, policy: CanonPolicy = CanonPolicy.STRICT_CANON) -> None:
    with session_scope() as session:
        response = ChatService(
            session,
            embedding_client=profile_client(
                session, "default-embeddings", ProfileCapability.EMBEDDINGS
            ),
            chat_client=profile_client(session, "default-chat", ProfileCapability.CHAT),
        ).chat(ChatRequest(message=message, policy=policy))
    typer.echo(response.answer)
    typer.echo(f"trace={response.trace_id}")


@sessions_app.command("show")
def session_show(session_id: str) -> None:
    with session_scope() as session:
        session_read = ChatRepository(session).get_session(session_id)
    typer.echo(session_read.model_dump_json())
```

- [ ] **Step 4: Run CLI tests**

Run: `uv run pytest tests/integration/test_cli.py -v`

Expected: PASS.

- [ ] **Step 5: Commit CLI entrypoints**

```bash
git add src/calliope/cli.py tests/integration/test_cli.py
git commit -m "feat: add mvp cli commands"
```

## Task 12: End-To-End Verification And Documentation

**Files:**
- Modify: `README.md`
- Modify: `tests/integration/test_api_contract.py`

- [ ] **Step 1: Add final acceptance test for OpenAPI and core route names**

Append to `tests/integration/test_api_contract.py`:

```python
def test_openapi_declares_calliope_contract() -> None:
    client = TestClient(create_app())

    schema = client.get("/openapi.json").json()

    assert schema["info"]["title"] == "Calliope"
    assert sorted(path for path in schema["paths"] if path.startswith("/v1/"))
```

- [ ] **Step 2: Update README with run commands**

Add:

```markdown
## Local Development

```bash
docker compose up -d postgres
uv sync --extra dev
uv run alembic upgrade head
uv run calliope serve
```

OpenAPI is available at `http://127.0.0.1:8000/docs`.

```bash
uv run calliope workspace add ./world --name world
uv run calliope profiles add local-chat --kind openai_compatible --base-url http://localhost:4000/v1 --model local-model
uv run calliope reindex world
uv run calliope search "Kaelen exile"
uv run calliope chat "Where was Kaelen exiled from?" --policy strict_canon
```
```

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest -v`

Expected: PASS.

- [ ] **Step 4: Run lint**

Run: `uv run ruff check src tests`

Expected: PASS.

- [ ] **Step 5: Run type check**

Run: `uv run pyright`

Expected: PASS.

- [ ] **Step 6: Inspect git status**

Run: `git status --short`

Expected: only intentional implementation files are modified. The pre-existing user README edit may still appear if it was never committed separately.

- [ ] **Step 7: Commit final docs and verification**

```bash
git add README.md tests/integration/test_api_contract.py
git commit -m "docs: add mvp development workflow"
```

## Self-Review Checklist

- Spec coverage:
  - Workspace registration: Tasks 4, 10, 11.
  - Profile registration, listing, and testing: Tasks 4, 10, 11.
  - Reindexing: Tasks 5, 7, 11.
  - Markdown parsing and frontmatter: Task 5.
  - Chunk storage with embeddings and full-text vectors: Tasks 3 and 7.
  - Hybrid search and citations: Task 8.
  - Chat with canon policies, citations, and trace id: Task 9.
  - OpenAPI documentation: Tasks 1, 10, 12.
  - CLI surface: Tasks 1, 11, 12.
  - No external model-provider tests: Tasks 6, 8, 9 use fake clients.
- Placeholder scan: the plan avoids incomplete sections and names concrete files, commands, and tests.
- Type consistency: public names used across tasks are `WorkspaceCreate`, `ProfileCreate`, `SearchRequest`, `SearchResponse`, `ChatRequest`, `ChatResponse`, `SourceReference`, `CanonPolicy`, `ProfileKind`, `ProfileCapability`, `OpenAICompatibleClient`, `Reindexer`, `HybridRetriever`, `SearchService`, and `ChatService`.
