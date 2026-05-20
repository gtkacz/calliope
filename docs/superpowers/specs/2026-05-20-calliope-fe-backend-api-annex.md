# Calliope Frontend MVP Backend API Annex

## Summary

This annex defines backend changes required by the Calliope Frontend MVP. The frontend design lives in `docs/superpowers/specs/2026-05-20-calliope-fe-mvp-design.md`.

The annex is intentionally narrow. It adds frontend-facing API and persistence support while preserving the existing Python/FastAPI backend architecture.

## Goals

- Move the existing Python package under `src/backend/calliope`.
- Preserve existing backend CLI, API, tests, and import behavior.
- Add endpoints for listing sessions and loading session messages.
- Persist conversation folder organization in the database.
- Support nested, nameable conversation folders.
- Support assigning and unassigning sessions from folders.
- Support profile and workspace update/delete operations needed by settings.
- Let chat requests specify a chat-capable profile id.
- Persist search-result turns in chat history.
- Keep reindex behavior usable from a settings dialog.

## Non-Goals

- No streaming chat endpoint.
- No background reindex job system in the MVP.
- No browser-native filesystem picker endpoint.
- No auth or multi-user ownership model.
- No websocket API.
- No hosted deployment changes.

## Repository Move

Move:

```txt
src/calliope/
```

to:

```txt
src/backend/calliope/
```

Update Python project configuration so:

- Package discovery points at `src/backend/calliope`.
- Pytest `pythonpath` includes `src/backend`.
- Pyright includes `src/backend` and tests.
- CLI entry point remains `calliope = "calliope.cli:app"`.
- Existing tests continue to run with `uv run pytest`.

No Python modules are renamed. Imports remain `calliope...`.

## Data Model Additions

### `conversation_folders`

- `id`
- `name`
- `parent_id`, nullable self-reference
- `position`, integer for sibling ordering
- `created_at`
- `updated_at`

Folders are nestable. Deleting a folder does not delete sessions. Sessions in a deleted folder become unfiled.

### `chat_sessions`

Add:

- `folder_id`, nullable foreign key to `conversation_folders.id`

Existing sessions without a folder remain valid and appear in the unfiled section.

### `chat_messages`

The existing `role`, `content`, and `metadata_json` fields remain. Add conventions for metadata:

Chat user message metadata:

```json
{
  "turn_kind": "chat_user"
}
```

Assistant message metadata:

```json
{
  "turn_kind": "assistant",
  "policy": "strict_canon",
  "chat_profile_id": "profile_123",
  "source_count": 4,
  "sources": []
}
```

Search-result message metadata:

```json
{
  "turn_kind": "search_result",
  "query": "ancient city beneath the lake",
  "sources": []
}
```

The metadata shape can be normalized into Pydantic schemas for API responses. It does not need a new search-results table in the MVP.

## API Response Shapes

### Message Read

Add a frontend-facing message schema:

```json
{
  "id": "message_123",
  "session_id": "session_123",
  "role": "assistant",
  "content": "The indexed canon says...",
  "metadata": {},
  "created_at": "2026-05-20T12:00:00Z"
}
```

### Session Summary

```json
{
  "id": "session_123",
  "title": "What does canon say...",
  "folder_id": null,
  "created_at": "2026-05-20T12:00:00Z",
  "updated_at": "2026-05-20T12:05:00Z"
}
```

### Session Detail

```json
{
  "id": "session_123",
  "title": "What does canon say...",
  "folder_id": null,
  "created_at": "2026-05-20T12:00:00Z",
  "updated_at": "2026-05-20T12:05:00Z",
  "messages": []
}
```

### Conversation Folder

```json
{
  "id": "folder_123",
  "name": "Worldbuilding",
  "parent_id": null,
  "position": 0,
  "created_at": "2026-05-20T12:00:00Z",
  "updated_at": "2026-05-20T12:00:00Z"
}
```

The frontend can build the folder tree from the flat folder list and session summaries.

## Endpoint Additions And Changes

### Sessions

Add:

```txt
GET   /v1/sessions
GET   /v1/sessions/{id}
PATCH /v1/sessions/{id}
DELETE /v1/sessions/{id}
```

`GET /v1/sessions` returns session summaries ordered by `updated_at` descending. It supports optional `folder_id` filtering. The frontend derives unfiled sessions from the full list by selecting sessions with `folder_id: null`.

`GET /v1/sessions/{id}` returns session detail with messages. This replaces the current single-session endpoint response shape for frontend use.

`PATCH /v1/sessions/{id}` supports:

```json
{
  "title": "New title",
  "folder_id": "folder_123"
}
```

Both fields are optional. `folder_id` may be `null` to unfile the session.

`DELETE /v1/sessions/{id}` deletes a session and its messages/traces.

### Conversation Folders

Add:

```txt
GET    /v1/conversation-folders
POST   /v1/conversation-folders
PATCH  /v1/conversation-folders/{id}
DELETE /v1/conversation-folders/{id}
```

Create request:

```json
{
  "name": "Act II",
  "parent_id": null,
  "position": 0
}
```

Patch request:

```json
{
  "name": "Act III",
  "parent_id": "folder_parent",
  "position": 2
}
```

The backend must reject cycles in folder parentage with a stable error code.

### Chat

Change `POST /v1/chat` request to accept:

```json
{
  "message": "What does canon say about the lake city?",
  "policy": "strict_canon",
  "session_id": "session_123",
  "workspace_id": "workspace_123",
  "chat_profile_id": "profile_123",
  "limit": 8
}
```

`chat_profile_id` is required for frontend-created chat turns. For backward compatibility with existing CLI and API callers, omitted `chat_profile_id` uses the existing `default-chat` profile behavior.

The response should include enough session/message information for the frontend to patch the active conversation without immediately refetching:

```json
{
  "session": {},
  "user_message": {},
  "assistant_message": {},
  "answer": "The indexed canon says...",
  "sources": [],
  "trace_id": "trace_123"
}
```

The existing `answer`, `sources`, and `trace_id` fields remain.

### Search

Keep `POST /v1/search` for source-only searches. Add conversation persistence fields:

```json
{
  "query": "ancient city beneath the lake",
  "workspace_id": "workspace_123",
  "session_id": "session_123",
  "limit": 8,
  "persist": true
}
```

When `persist` is true, the backend creates a session if needed and stores a search-result message. The response includes:

```json
{
  "session": {},
  "search_message": {},
  "sources": []
}
```

For backward compatibility, existing source-only callers can omit `persist` or set it to false and receive the existing response shape.

### Profiles

Add:

```txt
PATCH  /v1/profiles/{id}
DELETE /v1/profiles/{id}
```

Patch supports name, kind, base URL, model, API key ref, and capabilities. The backend must validate that capabilities are known values.

Deleting a profile used by no in-flight request is allowed. Historical messages keep profile ids in metadata for traceability, but the frontend must tolerate deleted historical profile ids.

### Workspaces

Add:

```txt
GET    /v1/workspaces/{id}
PATCH  /v1/workspaces/{id}
DELETE /v1/workspaces/{id}
```

Patch supports name, root path, include globs, and exclude globs. The backend validates the root path and globs using the same rules as creation.

Deleting a workspace does not delete sessions. Historical sessions remain intact and keep workspace evidence only through stored message and trace metadata.

### Reindex

Keep:

```txt
POST /v1/reindex
```

For MVP frontend use, it remains synchronous and returns:

```json
{
  "documents_indexed": 12,
  "chunks_indexed": 84
}
```

The frontend shows loading until the request completes. Background jobs, cancellation, progress polling, and indexing history are outside this MVP.

## Error Codes

Add or confirm stable error codes:

- `session_not_found`
- `conversation_folder_not_found`
- `conversation_folder_cycle`
- `conversation_folder_invalid_parent`
- `profile_in_use`
- `workspace_path_invalid`
- `workspace_delete_failed`

All errors continue to use:

```json
{
  "error": {
    "code": "stable_code",
    "message": "Human readable message.",
    "details": {}
  }
}
```

## Testing Strategy

Backend tests cover:

- Package import behavior after moving to `src/backend`.
- Existing backend tests still pass.
- Folder CRUD.
- Folder cycle rejection.
- Session list/detail with messages.
- Assigning and unassigning sessions to folders.
- Chat with explicit `chat_profile_id`.
- Search persistence into session history.
- Profile update/delete.
- Workspace update/delete.
- Reindex endpoint unchanged for synchronous callers.
- OpenAPI includes all new frontend-facing endpoints.

## Acceptance Criteria

- Existing Python backend remains importable as `calliope`.
- Existing backend tests pass after the repository move.
- The frontend can fetch sessions, messages, folders, profiles, and workspaces.
- The frontend can persist nested folder organization.
- The frontend can send chat requests with an explicit chat profile id.
- The frontend can persist search turns in conversation history.
- The frontend can edit/delete profiles and workspaces.
- Reindex can be triggered from the frontend and returns visible results or errors.
