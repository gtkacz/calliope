# Findings & Decisions

## Requirements
- Implement Settings Profiles and Workspaces UX Revamp from the supplied plan.

## Research Findings
- `WorkspaceCreate`/`WorkspacePatch` and profile schemas currently accept names unchanged; validation belongs naturally in Pydantic schema validators.
- The scanner resolves the root, enumerates regular files using `rglob`, permanently ignores `.calliope`, applies custom segment-aware glob matching, then reads/hashes contents. Preview should reuse the matching helpers while using a no-read traversal.
- Workspace routes currently provide CRUD and reindex endpoints; the preview route should be added here and use the configured settings browse boundary.
- Both panels currently auto-present a new form and clear `editingId` after every save, which causes the planned POST-to-PATCH regression. State, baseline, and guard logic belong at the panel level; stores should expose save/test errors without forcing mode changes.
- SettingsDialog owns tab/close/backdrop model changes. A child-to-parent draft-guard registration interface is needed so it can defer tab and dialog dismissal.

## Technical Decisions
| Decision | Rationale |
|---|---|
| Add a preview-specific scanner helper | Reuses exact match logic while guaranteeing no file reads/hashes and enforcing caps. |
| Validate/normalize names in schemas | Applies uniformly to create and patch before services/repositories receive the payload. |
| Use a SettingsDialog-provided draft guard | Gives tab, close button, backdrop, and Escape one confirmation path without storing transient forms globally. |

## Codebase Walkthrough (2026-07-22)
- Survey started. Existing planning artifacts describe a completed settings/workspaces UX revamp and are being preserved.
- Goal: explain architecture, execution paths, data model, indexing/retrieval, agent orchestration, and frontend behavior for a CS Master's candidate with basic ML knowledge.
- Repository shape: Python backend under `src/backend/calliope`, Vue frontend under `src/frontend`, Alembic migrations, and unit/integration tests.
- Backend packages are split into API routes, services, repositories, SQLAlchemy DB models, ingestion, hybrid retrieval, prompts, and an OpenAI-compatible LLM client.
- Frontend is feature-sliced around chat, documents, editor, profiles, settings, and workspaces, with typed API wrappers and Pinia-style stores.
- The worktree contains substantial pre-existing modified/untracked files from the completed settings/workspaces work. Treat all of them as user-owned and do not modify application code.
- Product intent (`README.md`): Linux-first, local markdown knowledge system for worldbuilding canon. It indexes Markdown into PostgreSQL/pgvector and calls local or remote models through an OpenAI-compatible API.
- Runtime options: Docker Compose runs Postgres, migrations, backend, and frontend; host mode uses `uv`, Alembic, and `calliope serve`. The same Python package exposes a Typer CLI.
- Security/operational boundary: `CALLIOPE_BROWSE_ROOT` constrains what the containerized picker/indexer/editor can see; that tree is mounted read-write so editor changes persist to host files.
- Core backend dependencies are deliberately conventional: FastAPI/Pydantic, SQLAlchemy/Alembic/Postgres/pgvector, HTTPX, markdown-it/frontmatter, Typer/Uvicorn. There is no training framework—the ML work is inference-time embedding and text generation.
- Compose topology: pgvector/Postgres becomes healthy -> one-shot Alembic migration -> backend -> statically built Vue frontend served by nginx. The backend reaches host-side model servers through `host.docker.internal`.
- Frontend stack: Vue 3 + TypeScript + Vue Router + Pinia + Vuetify; markdown is rendered client-side with markdown-it and sanitized by DOMPurify; Vitest/jsdom cover component/store behavior.
- API entry point is an application factory that loads settings, warns about missing Git/empty browse roots, configures CORS, registers nine route groups, and installs uniform error handlers.
- CLI and HTTP are two thin interfaces over the same services/repositories. CLI commands manage workspaces/profiles, reindex, search, chat, and inspect sessions.
- Model selection is capability-based: the default profile for `embeddings` feeds indexing/search, and the default profile for `chat` feeds generation. Secrets are indirect references to environment-variable names, not stored raw in the profile.
- The LLM abstraction is OpenAI-compatible but recognizes Ollama/KoboldCPP profile kinds for protocol-specific behavior. Clients are explicitly closed, including around failures.
- Important ML/runtime constants: embeddings are fixed at 1024 dimensions; generation defaults to a 32,768-token assumed context, 4,096 max output tokens, 600 s timeout, and at most three continuation rounds. Token counts are estimated at ~4 chars/token with 10% safety slack rather than using model-specific tokenizers.
- FastAPI dependency injection creates a DB session per request and resolves clients from either the default capability profile or an explicitly selected chat profile. Sampling parameters are derived from the canon policy plus profile overrides.
- Changing embedding dimension is a schema/data migration, not a config-only tweak: the pgvector column width and every stored vector must match.
- Persistence model forms three clusters: (1) workspace -> documents -> chunks, (2) folders -> chat sessions -> messages/retrieval traces, and (3) standalone connection profiles.
- Documents are unique by `(workspace_id, path)` and store frontmatter, content hash, timestamps, and soft-deletion state. Chunks store heading context, text, estimated token count, metadata, a 1024-D embedding, and a PostgreSQL full-text vector.
- Retrieval has both a GIN index over `tsvector` and an HNSW pgvector index using L2 distance. Retrieval traces persist the query, canon policy, selected sources, and scoring details for inspectability.
- Conversations are workspace-scoped and optionally foldered. Write-mode sessions additionally persist a Markdown canvas; ordinary chat sessions do not.
- Three canon policies communicate desired grounding/creativity. Profile kinds are OpenAI-compatible, Ollama, or KoboldCPP; capabilities include chat, embeddings, rerank, and streaming, although implemented paths must be checked separately from enum declarations.
- HTTP surface is CRUD plus five main behaviors: reindex, hybrid search, grounded chat, long-form write, and editor proposal. Supporting endpoints expose document/source content, filesystem browsing/version history, chat sessions/folders, workspaces, and model profiles.
- Pydantic schemas separate create/patch/read contracts and make the API strongly typed. Chat requests can select workspace/session/profile/policy; write and editor requests add canvas/document-specific context.
- Ingestion starts with deterministic recursive file scanning. Include/exclude globs are segment-aware (`**` is recursive); Calliope's own hidden Git-version store is permanently excluded. Included files are SHA-256 hashed so unchanged content can be detected.
- Markdown parsing extracts YAML frontmatter, chooses title from `name` -> first H1 -> filename, and splits content into heading-aware sections. It correctly ignores apparent headings inside fenced code blocks.
- The settings glob preview deliberately traverses metadata only: it does not open files, follows no directory symlinks, and caps work by file count, time, and sample size.
- Chunking is simple and deterministic: preserve heading boundaries, then split on blank-line paragraphs/words to at most 1,800 characters. `token_count` is currently a whitespace word count, not a tokenizer count.
- Reindex flow: scan all matching files -> parse/chunk all -> embed every chunk -> upsert documents -> replace each document's chunks -> soft-delete missing documents -> commit one DB transaction.
- Embedding width is validated before persistence. On any error, the transaction rolls back and owned clients/runners are cleaned up.
- Important scalability caveat: despite storing content hashes, the current reindexer does not skip unchanged files and sends embeddings one chunk at a time rather than in batches. It is suitable for a local MVP, not yet an optimized large-corpus pipeline.
- Retrieval embeds the query once, independently pulls approximate-nearest-neighbor vector hits and PostgreSQL English full-text hits, over-fetches, then fuses ranks with reciprocal-rank fusion: each channel contributes `1/(60 + rank)`.
- Rank fusion uses order, not raw score calibration, which avoids comparing incomparable vector distances and lexical relevance values. The final threshold defaults near 0.005 and retains top-1 if candidates exist but all fall below threshold.
- An optional cross-encoder-like reranker protocol exists; it can rescore the fused pool and fails open to RRF ordering. Current API wiring must be checked to see whether any reranker profile is actually instantiated.
- The backend is mostly synchronous SQLAlchemy/service code. `_AsyncRunner` bridges async HTTP model calls through a dedicated event-loop thread and owns explicit shutdown semantics.
- Search maps fused chunk IDs back to rich source references. It is normally stateless, but `persist=true` stores a search turn in the same session/message model used by chat.
- Chat flow: validate session/workspace affinity -> load recent history -> hybrid-search the user's message -> add explicitly cited full documents -> inject optional workspace guidelines -> build policy prompt -> trim evidence/history to the context budget -> generate -> persist user/assistant messages and retrieval trace.
- A new conversation triggers a second small generation for its title, with deterministic user-message fallback if title generation fails. The core answer is persisted only after generation succeeds.
- Assistant message metadata records policy, chosen profile, sources, cited documents, model truncation/context-overflow flags, and prompt-trimming decisions. This makes degraded responses diagnosable.
- Grounding behavior is prompt-enforced, not a symbolic verifier: strict policy demands source-only answers/refusal; inference and creative policies require labels in chat. Write/edit use separate contracts so citation markers do not pollute the produced Markdown.
- Prompt assembly places the system policy/guidelines first, then retained conversation history, then the current question/canvas plus retrieved and explicitly cited evidence; a final reminder counters recency bias.
- Context budgeting reserves output tokens, estimates remaining prompt capacity in characters, and sheds context in this order: weakest retrieved sources -> truncate largest user-cited documents (keeping at least their lead) -> oldest history. It never trims the current canvas or instruction because generated output may replace that artifact.
- Long-document prompts contain strong completeness/no-placeholder contracts. These are pragmatic mitigations for local instruction-tuned models, not hard correctness guarantees.
- The model adapter supports standard `/embeddings` and `/chat/completions`, Ollama-native `/api/chat`, and KoboldCPP's compatible endpoint with native parameter names. HTTP/network/provider failures become uniform 502-style application errors.
- Generation reports two distinct failure signals: output truncation when finish reason is `length`, and inferred input-context overflow when provider token accounting is far below the sent prompt estimate. Ollama overflow inference is disabled because its cached-token accounting would create false positives.
- Sampling is policy-conditioned: temperature rises from strict (0.2) to inference (0.35) to creative (0.65). Local-style profiles default to min-p + repetition penalty; commercial-style profiles use top-p + frequency penalty; per-profile overrides are merged but cannot cross that invariant.
- A Cohere-compatible `/rerank` client is implemented separately. Need to confirm endpoint/service dependency wiring before calling reranking a user-visible feature.
- Reranking is wired for chat and write when the selected chat profile also declares the `rerank` capability; ordinary `/v1/search` does not wire one. A separate rerank-only default profile is not resolved in the current paths.
- `streaming` is currently a legacy/schema capability only. Generation is explicitly one non-streaming request; neither backend SSE/chunking nor frontend stream consumption exists.
- Write mode reuses chat's retrieval, citations, history, policy, guidelines, and budgeting, but the generated artifact replaces a DB-backed session canvas. The visible assistant timeline message is only “Updated the canvas”; the full Markdown lives separately on the session.
- If generation ends at the token ceiling, write mode makes up to three bounded continuation calls. Each receives the original instruction plus a budget-sized tail (minimum 4,000 chars), and responses are stitched with up to 500-character overlap deduplication.
- Continuation permits a document to exceed one completion's output cap, but the final truncation flag remains true if the last allowed continuation also hits its ceiling; context-overflow status is sticky across all rounds.
- Editor mode is deliberately two-phase: read an existing file and generate an append/rewrite proposal containing both original and proposed content; it does not apply the change itself. The frontend/user can review before invoking the filesystem write endpoint.
- Filesystem operations canonicalize paths and enforce `browse_root` after symlink resolution, preventing `..`/symlink escape. Editing is restricted to already-existing files; this API cannot create arbitrary new files.
- Optional versioning wraps writes with a per-workspace lock, baseline snapshot, actual write, then new snapshot. The write proceeds even though the history mechanism is designed as best-effort supporting infrastructure.
- Version history is a detached shadow Git repository at `<workspace>/.calliope-git`, with the workspace as work tree. It never uses the user's Git history/config/hooks; if the workspace is itself a repo, it adds the shadow directory to `.git/info/exclude`.
- Versioning requires the global feature flag, Git availability, an owning workspace, and no explicit workspace opt-out. History/restore operate only on UTF-8 text; restoring creates another snapshot rather than erasing history.
- There is no DB transaction coordinating filesystem writes and Git commits. This is intentional: Git snapshots may fail without blocking the user's requested file write.
- Chat/write route orchestration owns and closes all model clients around every request. Reranking is activated only for an explicitly selected chat profile that also advertises `rerank`; the default chat profile is not inspected for that capability.
- The frontend is currently a single routed application screen: `/` renders `ChatWorkspace` inside a Vuetify app/theme and globally honors reduced-motion preferences. Features appear as panels/dialogs within that workspace rather than separate pages.
- `ChatWorkspace` is the shell: conversation drawer at left, workspace/profile context header, chat timeline or write canvas/thread in the center, composer at bottom, plus settings/editor/source dialogs.
- Startup fetches workspaces and profiles in parallel, chooses the first available workspace/chat profile, then loads workspace-scoped conversations. Switching workspace clears the active session, canvas, citations, and mention cache to prevent cross-workspace leakage.
- The Pinia chat store is the primary UI state machine. Composer modes are `chat`, `write`, and `search`; all use one session timeline. Chat appends answer messages, write replaces the canvas and adds a terse timeline event, and search persists a structured search-result message.
- `@path` mentions are converted to explicit document IDs only if the token remains in the submitted text and the cached document belongs to the active workspace. Canvas autosave is best-effort; request errors are shown without corrupting current local state.
- The composer exposes the three operation modes and canon policies directly, along with workspace/model selection and per-surface guideline toggles. Search disables model selection because it only embeds/retrieves.
- The write canvas is an ordinary Markdown textarea with a sanitized preview. Manual edits update local state immediately and PATCH the active session after a 700 ms debounce guarded against cross-session races.
- File editor UX is review-first: pick an existing Markdown file from the active workspace, request append/rewrite, inspect current and proposed text side by side, then explicitly discard or save. Overflow/truncation warnings advise different remedies.
- Saving a proposal is a separate filesystem PUT, so generation cannot silently mutate the file. The current UI does not expose the backend's file-history/restore endpoints.
- Editor proposals always use `canon_plus_inference`. The backend finds the most specific workspace root containing the file, retrieves up to three sources using the instruction, and resolves that workspace's guidelines. Retrieval failure is non-fatal, so editing can continue without RAG context.
- Longest-containing-root lookup also determines which workspace owns a path for editor grounding and versioning, which handles nested/overlapping workspaces predictably.
- Workspace/profile Pinia stores are thin CRUD state layers; workspace store also owns reindex status/result, while profile getter exposes chat-capable profiles. The main chat store independently tracks its selected workspace/profile.
- Settings is a modal with profile, workspace, indexing, and appearance tabs. Profile/workspace forms register a draft guard so tab changes, backdrop/Escape, and close all confirm before discarding unsaved edits.
- Frontend caveat: chat and workspace stores maintain separate `selectedWorkspaceId` values with no synchronization. The composer changes the chat selection, while the file editor derives its initial root/guideline availability from the workspace-store selection (typically the first or last edited workspace), so these can drift.
- Profile settings simplify arbitrary capability arrays into chat vs embeddings roles, optionally adding reranking; legacy multi-role/streaming profiles are preserved until the user deliberately changes role. Provider presets prefill kind/URL/model/key-ref, and max output tokens are configurable per profile.
- Workspace settings define root, include/exclude globs, and standing guidelines. Glob previews debounce 400 ms, serialize in-flight requests, and reject stale results; a soft UI warning appears when guidelines exceed 2,000 chars because they consume prompt budget.
- Editing and saving a settings item stays in edit mode, so subsequent saves PATCH the same resource rather than accidentally creating duplicates.
- Default model resolution means “oldest stored profile advertising this capability,” not a named/default flag. The UI normally sends an explicit chat profile, while embeddings use the oldest embeddings-capable profile.
- Important caveat: `POST /v1/profiles/{id}/test` only verifies that the DB profile exists and returns its capabilities. It does not contact the configured provider/model, so the current “Profile test succeeded” message is not an end-to-end connectivity test.
- Only the most recent user/assistant history fitting within 8,000 characters is sent to the model; persisted search-role messages are excluded. Further context-budget trimming may drop oldest retained turns.
- Conversation folders support nesting, ordering, and cycle checks. Deleting sessions cascades their messages/traces; deleting/moving workspaces is enforced through database foreign keys and session/workspace validation.
- Document/source endpoints read reconstructed indexed chunk text, not the live filesystem. A file edit does not automatically reindex, so search/chat/@mentions can remain stale until the user runs the synchronous `/v1/reindex` operation.
- Reindex is an ordinary blocking HTTP request and returns only final document/chunk counts; there is no job queue, progress stream, filesystem watcher, or incremental background sync.
- SQLAlchemy engine/session factories are cached per database URL; repositories/services explicitly commit/rollback around mutations. Domain `AppError` exceptions are normalized as `{error: {code, message, details}}` JSON with intentional HTTP status codes.
- Frontend API access is one typed `fetch` wrapper with a build-time base URL and matching `ApiError` envelope. There is no authentication/session cookie layer; this is designed as a local single-user tool.
- Markdown rendering disables embedded HTML/linkification, adds custom citation/source-note markup, then sanitizes with DOMPurify. External links get `noopener noreferrer`, so model/file text is not inserted as arbitrary HTML.
- Every assistant/search turn shows structured source chips from backend metadata independently of whether the model formatted citations correctly. Clicking opens the reconstructed indexed document and attempts to locate/highlight the exact retrieved passage after Markdown rendering.
- The UI distinguishes prompt-context overflow from output truncation and gives targeted operator guidance; overflow takes precedence because raising output tokens would further reduce available prompt space.
- Test suite has roughly 147 backend tests split across pure unit behavior and PostgreSQL integration/API/service/repository flows. Each DB-backed test migrates a database up to head and back to base, with a hard guard refusing any database whose name is not `calliope_test` or `*_test`.
- Current verification: all 19 frontend Vitest tests pass. Full backend invocation ran 68 tests successfully, while 79 DB-backed tests errored at fixture setup because no PostgreSQL server is listening on localhost:5432; this is an environment failure, not an assertion failure.
- Focused backend unit suite passes 53/53, and frontend TypeScript checking passes.

## Walkthrough Synthesis
- Best mental model: Calliope is a local, single-user, retrieval-augmented Markdown knowledge/workbench application, not an ML training system or autonomous agent framework.
- Its essential loop is `files -> heading-aware chunks -> embeddings + full-text index -> reciprocal-rank-fused evidence -> policy/context-budgeted prompt -> external model -> persisted answer/canvas + provenance`.
- The main product distinction is three surfaces over shared infrastructure: search returns evidence only; chat returns a grounded answer; write/editor produce Markdown, with editor requiring explicit review before touching a real file.
- Most important operational facts: reindex is manual and synchronous; indexed content can lag filesystem content; generation is non-streaming; profile “test” is not a network test; PostgreSQL/pgvector and an external OpenAI-compatible model server are required.
