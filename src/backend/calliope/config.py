from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Native output width of the configured embedding model. This is the single
# source of truth for the pgvector column width: the ORM column reads it and
# the corresponding Alembic migration pins the same literal. Changing it
# requires a migration that alters the `chunks.embedding` column and re-embeds
# every document, because vectors of different widths are not comparable.
EMBEDDING_DIMENSIONS = 1024

# Generation is a single non-streaming POST, so the read timeout must outlive an
# entire completion. A full DEFAULT_MAX_TOKENS document on a local model at
# 10-30 tok/s takes several minutes; the previous 120s produced 502s
# (httpx.ReadTimeout) precisely on the long write-mode generations that matter.
DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS = 600

# Explicit completion ceiling sent on every generation request. OpenAI-compatible
# servers that receive no max_tokens fall back to their own default cap, which on
# common local backends is small (text-generation-webui ~200, KoboldCpp 512), so
# write-mode document rewrites silently truncate. 4096 holds a full character
# sheet or lore entry (rarely > 3000 tokens) while staying within the context
# window of every local model Calliope targets; operators raise it per deployment.
DEFAULT_MAX_TOKENS = 4096

# Context window (in tokens) Calliope assumes the model server provides. Local
# backends SILENTLY front-truncate any prompt exceeding their window (Ollama's
# default num_ctx is 2048-4096; KoboldCpp's default --contextsize is 8192),
# discarding the system prompt — and its grounding/format contract — before
# generation begins, which is why overflowing output comes back short,
# hallucinated, and off-format. The value is sent as options.num_ctx on
# Ollama-native profiles and as max_context_length on KoboldCpp profiles (its
# /v1 route passes native genparams through), and every profile kind uses it to
# budget prompt assembly (see prompts/budget.py). It can only shrink a server's
# window, never grow it, so operators must set this to match the server's real
# launched context size.
DEFAULT_NUM_CTX = 32768

# English prose averages ~4 characters per token on the tokenizers Calliope
# targets. Used for prompt budgeting and context-overflow detection, which need
# order-of-magnitude accuracy without shipping a per-model tokenizer.
ESTIMATED_CHARS_PER_TOKEN = 4

# Fraction of the nominal prompt window the budgeter actually fills. The slack
# absorbs what the char-ratio estimate cannot see: chat-template tags, message
# framing, and tokenizer variance across models.
PROMPT_BUDGET_SAFETY = 0.9

# Upper bound on how many continuation requests one write/edit generation may
# chain after a response ends at the token ceiling (finish_reason=length). Each
# round adds up to max_tokens of output from a fresh bounded-context request, so
# documents can grow ~4x the per-request ceiling even on a small context window,
# while a model that never emits a natural stop cannot loop forever. 0 disables
# continuation entirely.
DEFAULT_MAX_CONTINUATION_ROUNDS = 3

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
    default_num_ctx: int = Field(default=DEFAULT_NUM_CTX, gt=0)
    max_continuation_rounds: int = Field(default=DEFAULT_MAX_CONTINUATION_ROUNDS, ge=0)
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
    )
    retrieval_score_threshold: float = Field(default=RETRIEVAL_SCORE_THRESHOLD_DEFAULT, ge=0.0)
