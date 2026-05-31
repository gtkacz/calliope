from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Native output width of the configured embedding model. This is the single
# source of truth for the pgvector column width: the ORM column reads it and
# the corresponding Alembic migration pins the same literal. Changing it
# requires a migration that alters the `chunks.embedding` column and re-embeds
# every document, because vectors of different widths are not comparable.
EMBEDDING_DIMENSIONS = 1024
DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS = 120

# Explicit completion ceiling sent on every generation request. OpenAI-compatible
# servers that receive no max_tokens fall back to their own default cap, which on
# common local backends is small (text-generation-webui ~200, KoboldCpp 512), so
# write-mode document rewrites silently truncate. 4096 holds a full character
# sheet or lore entry (rarely > 3000 tokens) while staying within the context
# window of every local model Calliope targets; operators raise it per deployment.
DEFAULT_MAX_TOKENS = 4096

# RRF scores top out ~0.033 for rank-1; 0.005 eliminates only true noise
# (rank >> 100 from both sources) while keeping at least one result unless
# the entire candidate set is empty.
RETRIEVAL_SCORE_THRESHOLD_DEFAULT: float = 0.005


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CALLIOPE_", env_file=".env", extra="ignore")

    api_title: str = "Calliope"
    database_url: str = "postgresql+psycopg://calliope:calliope@localhost:5432/calliope"
    # Host directory mounted into the container; the folder picker opens here by
    # default. Only paths under a mounted root are visible to the containerized
    # backend. None falls back to the user's home directory.
    browse_root: str | None = None
    # Feature flag (opt-in) for the per-workspace shadow-git file version history.
    # Off by default because enabling it writes a .calliope-git store into each
    # versioned workspace folder.
    versioning_enabled: bool = False
    embedding_dimensions: int = Field(default=EMBEDDING_DIMENSIONS, ge=1)
    llm_request_timeout_seconds: float = Field(
        default=DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS,
        gt=0,
    )
    default_max_tokens: int = Field(default=DEFAULT_MAX_TOKENS, gt=0)
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
    )
    retrieval_score_threshold: float = Field(default=RETRIEVAL_SCORE_THRESHOLD_DEFAULT, ge=0.0)
