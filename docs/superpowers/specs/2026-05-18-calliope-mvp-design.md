# Calliope MVP Backend Design

## Summary

Calliope MVP is a Linux-only, backend-first local knowledge server for markdown worldbuilding corpora. It indexes local markdown workspaces, retrieves relevant canon with hybrid search, and answers through a configured local or OpenAI-compatible model gateway with citations and retrieval traces.

The MVP is intentionally not a full writing studio, graph reasoning system, memory engine, or web app. It builds the backend foundation those features can sit on later.

## Goals

- Index one or more local markdown workspaces.
- Parse markdown, optional YAML frontmatter, headings, and source metadata.
- Chunk documents in a markdown-aware way.
- Store documents, chunks, metadata, embeddings, sessions, and retrieval traces in local Postgres.
- Use `pgvector` for vector similarity and Postgres full-text search for lexical retrieval.
- Provide hybrid search with inspectable scoring and source citations.
- Route all LLM, embedding, and reranker calls through configured OpenAI-compatible connection profiles, with LiteLLM as the recommended router.
- Support Ollama and LM Studio through OpenAI-compatible profiles or through LiteLLM.
- Expose an OpenAPI-documented FastAPI HTTP API.
- Provide a scriptable CLI for setup, indexing, search, chat, and session inspection.

## Non-Goals

- No direct calls from Calliope to OpenAI, Anthropic, Gemini, or other hosted LLM vendors.
- No web UI in the MVP.
- No Windows support in the MVP.
- No graph extraction or GraphRAG in the MVP.
- No automatic memory writes in the MVP.
- No programming-assistant backend in the MVP.
- No multi-user auth, billing, hosted deployment, or cloud dependency.
- No freeform ungrounded generation mode in the MVP.

## Recommended Stack

- Python for the application runtime.
- FastAPI for the HTTP API and OpenAPI documentation.
- Typer for the CLI.
- PostgreSQL for durable state.
- `pgvector` for vector storage and similarity search.
- Postgres full-text search for lexical retrieval.
- SQLAlchemy and Alembic for persistence and migrations.
- Pydantic for request, response, settings, and domain models.
- LiteLLM proxy as the recommended local model router.
- Docker Compose or Podman Compose for local infrastructure.
- Pytest for tests.

This choice keeps the MVP operationally simple: one primary database contains source metadata, chunks, embeddings, chat state, and traceability. Qdrant or another retrieval backend can be added later behind a retrieval interface if the corpus size or search requirements outgrow Postgres.

## Runtime Architecture

```txt
Markdown workspace(s)
  -> scanner / manual reindex / optional watcher
  -> markdown parser + frontmatter extractor
  -> markdown-aware chunker
  -> embedding client through configured OpenAI-compatible profile
  -> Postgres tables + pgvector + full-text indexes
  -> hybrid retriever
  -> optional reranker through configured OpenAI-compatible profile
  -> prompt builder with canon policy
  -> LLM client through configured OpenAI-compatible profile
  -> answer + citations + retrieval trace
```

The HTTP API and CLI share the same internal service layer. The CLI must not scrape HTTP responses from a locally running server for core behavior. It calls the same application services used by the API for local commands. Commands that target a remote running server can be added later as an explicit mode.

## Core Components

### Workspace Scanner

The scanner discovers markdown files under registered workspace roots. It respects include and exclude globs. It computes content hashes and modification timestamps so reindexing can skip unchanged files.

Manual reindexing is required for the MVP. A file watcher is optional only if it stays small and does not complicate the ingestion path.

### Markdown Parser

The parser extracts:

- Raw markdown content.
- YAML frontmatter when present.
- Title from frontmatter, H1, or filename.
- Heading hierarchy.
- Markdown sections.
- File path and workspace-relative path.

The parser must accept freeform markdown. Frontmatter is optional metadata, not a required schema.

### Chunker

Chunking is markdown-aware:

- Prefer H2 and H3 section boundaries.
- Preserve heading context on each chunk.
- Split oversized sections at paragraph, list, or table boundaries.
- Store chunk text with enough surrounding heading context to be useful after retrieval.
- Support small-to-big retrieval later by preserving document and heading relationships.

Each chunk stores:

- Document id.
- Chunk index.
- Heading path.
- Text.
- Token count or approximate token count.
- Metadata JSON.
- Embedding vector.
- Full-text search vector.

### Embedding Client

The embedding client talks to a configured OpenAI-compatible profile. It does not know whether the profile is backed by LiteLLM, Ollama, LM Studio, or another local service.

Embedding model dimensions are configuration-bound. The schema must make the chosen vector dimension explicit for the initial deployment.

### Retriever

The retriever searches the `chunks` table with two independent signals:

- Vector similarity through `pgvector`.
- Lexical search through Postgres full-text search.

Results are fused with reciprocal-rank-style scoring. The retrieval trace records vector hits, lexical hits, fused rankings, reranker output when present, and final selected sources.

### Reranker

Reranking is optional in the MVP. If configured, it is called through an OpenAI-compatible or simple HTTP profile abstraction. If not configured, fused retrieval results are used directly.

### Prompt Builder

The prompt builder assembles:

- System instructions for grounding and citation behavior.
- The active canon policy.
- Retrieved context blocks with source identifiers.
- The current user message.
- Recent session messages when a session id is provided.

The prompt builder is responsible for making unsupported-answer behavior explicit for strict canon mode.

### Model Client

The model client calls a configured OpenAI-compatible chat profile. LiteLLM is the recommended router, but Calliope only depends on the OpenAI-compatible API shape.

The MVP supports non-streaming responses and defines response model boundaries so streaming can be added without redesigning the API.

## Data Model

### `workspaces`

- `id`
- `name`
- `root_path`
- `include_globs`
- `exclude_globs`
- `created_at`

### `documents`

- `id`
- `workspace_id`
- `path`
- `title`
- `frontmatter_json`
- `content_hash`
- `modified_at`
- `indexed_at`
- `deleted_at`

### `chunks`

- `id`
- `document_id`
- `chunk_index`
- `heading_path`
- `text`
- `token_count`
- `metadata_json`
- `embedding`
- `search_vector`

### `chat_sessions`

- `id`
- `title`
- `created_at`
- `updated_at`

### `chat_messages`

- `id`
- `session_id`
- `role`
- `content`
- `created_at`
- `metadata_json`

### `retrieval_traces`

- `id`
- `session_id`
- `message_id`
- `query`
- `policy`
- `selected_sources_json`
- `scores_json`
- `created_at`

### `connection_profiles`

- `id`
- `name`
- `kind`
- `base_url`
- `model`
- `api_key_ref`
- `capabilities_json`

Connection profile capabilities identify whether a profile supports chat, embeddings, reranking, or streaming.

## Canon Policies

The MVP supports three policies:

### `strict_canon`

The answer must be grounded in retrieved sources. If the selected sources do not contain enough evidence, the assistant says that the indexed canon does not contain enough information.

### `canon_plus_inference`

The answer uses canon first and clearly separates cited facts from inference.

### `creative_but_consistent`

The answer may generate new material inspired by canon, but it must cite sources used and mark generated material as draft.

The MVP does not include a `freeform` policy because ungrounded generation is not the main product value.

## HTTP API

All endpoints are versioned under `/v1`.

```txt
POST /v1/workspaces
GET  /v1/workspaces
POST /v1/reindex
POST /v1/search
POST /v1/chat
POST /v1/profiles
GET  /v1/profiles
GET  /v1/profiles/{id}
POST /v1/profiles/{id}/test
GET  /v1/documents
GET  /v1/documents/{id}
GET  /v1/sources/{chunk_id}
GET  /v1/sessions/{id}
```

Responses that generate or retrieve answer context include source references:

```json
{
  "answer": "Ser Kaelen was exiled after...",
  "sources": [
    {
      "document_id": "doc_123",
      "chunk_id": "chunk_456",
      "path": "characters/kaelen.md",
      "heading": "Ser Kaelen Morcant > Biography > Exile",
      "excerpt": "After the Second Winter War...",
      "score": 0.87
    }
  ],
  "trace_id": "trace_789"
}
```

## CLI

The CLI mirrors common backend workflows:

```txt
calliope serve
calliope workspace add <path> --name <name>
calliope profiles add <name> --kind chat --base-url <url> --model <model>
calliope profiles list
calliope profiles test <name>
calliope reindex [workspace]
calliope search "query"
calliope chat "message" --policy strict_canon
calliope sessions show <id>
```

Commands that return structured data support `--json`. Human-readable output remains the default for interactive use.

## Error Handling

Application errors map to stable JSON responses:

```json
{
  "error": {
    "code": "workspace_not_found",
    "message": "Workspace not found.",
    "details": {
      "workspace_id": "workspace_123"
    }
  }
}
```

Error codes are stable API surface. Expected MVP codes include:

- `workspace_not_found`
- `document_not_found`
- `chunk_not_found`
- `connection_profile_not_found`
- `model_profile_missing_capability`
- `indexing_failed`
- `embedding_failed`
- `retrieval_failed`
- `generation_failed`
- `invalid_canon_policy`

## Testing Strategy

Tests are layered:

- Parser and chunker unit tests with markdown fixtures.
- Repository tests against local Postgres in Docker or Podman.
- Retrieval tests with deterministic fake embeddings.
- Prompt builder tests that verify canon policy instructions and citation formatting.
- API contract tests through FastAPI's test client.
- CLI smoke tests through Typer's test runner.
- Model adapter tests with fake OpenAI-compatible HTTP responses.

Tests must not require real calls to OpenAI, Anthropic, Gemini, Ollama, LM Studio, or LiteLLM. External model behavior is represented by local fake HTTP responses.

## Future Extension Points

### Memory

The MVP does not implement memory, but the architecture reserves room for future `memories` and `memory_events` tables. Future retrieval treats memory as another source class with explicit provenance.

Memory will support user-authored entries and model-proposed entries. Model-proposed memory must require a review path before becoming durable canon-like context.

### Graph Retrieval

Graph extraction is deferred. Future graph nodes may include characters, locations, factions, events, artifacts, religions, species, magic systems, and historical periods. Graph retrieval augments hybrid text retrieval only for relationship-heavy questions.

### Retrieval Backends

The MVP uses Postgres and `pgvector`. The retriever boundary must allow Qdrant or another retrieval engine to be added later without changing the API contract.

### Additional Backends

The backend keeps domain-specific behavior modular so a future programming assistant backend can reuse connection profiles, sessions, retrieval traces, and model routing without inheriting worldbuilding-only assumptions.

## Acceptance Criteria

- A user can register a local markdown workspace.
- A user can register, list, and test local model connection profiles.
- A user can reindex that workspace.
- Markdown documents are parsed with optional frontmatter and heading metadata.
- Chunks are stored with embeddings and full-text search vectors.
- A user can search indexed canon and receive source references.
- A user can chat with strict canon, canon plus inference, or creative but consistent policy.
- Chat answers return citations and a retrieval trace id.
- The service exposes OpenAPI documentation.
- The CLI supports serving, workspace registration, profile management, reindexing, search, chat, and session inspection.
- Tests do not require external model providers.
