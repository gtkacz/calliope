# Calliope Frontend MVP Design

## Summary

Calliope Frontend MVP is a Vue 3 browser app for using the existing local Calliope backend through a ChatGPT-like interface. Users can switch between chat and search turns, choose a response policy, choose a chat-capable model profile, browse past conversations, organize conversations into nested folders, manage LLM profiles and workspaces, and run workspace reindexes.

The MVP is a functional local tool, not a landing page or writing studio. It does not implement streaming, attachments, native filesystem picking, multi-user auth, graph views, or long-running background job orchestration.

Backend API and database additions required by this UI are specified separately in `docs/superpowers/specs/2026-05-20-calliope-fe-backend-api-annex.md`.

## Goals

- Provide a first-screen chat interface for Calliope.
- Support multiple persisted conversations.
- Let users group conversations in nested, nameable folders backed by the database.
- Let users choose `Chat` or `Search` mode per submitted turn.
- Let users choose a canon response policy per chat turn.
- Let users choose a chat-capable connection profile as the active model.
- Let users create, edit, delete, and test LLM connection profiles.
- Let users create, edit, delete, and select workspaces.
- Let users run a workspace reindex and see success or failure.
- Keep the frontend typed, testable, and decoupled from backend internals.

## Non-Goals

- No streaming assistant responses.
- No browser-native absolute folder picker in the MVP.
- No file attachment or image upload controls.
- No local file reads from frontend code.
- No frontend-only persistence for conversations, folders, profiles, or workspaces.
- No multi-user authentication or hosted deployment design.
- No dedicated search page outside conversation history.
- No graph, timeline, or document editor UI.

## Repository Layout

The repository moves to a monorepo-style shape:

```txt
src/
  backend/
    calliope/
      ...
  frontend/
    package.json
    bun.lock
    vite.config.ts
    tsconfig.json
    src/
      app/
      features/
      shared/
```

The existing Python package moves from `src/calliope` to `src/backend/calliope`. Python packaging and test configuration are updated so existing commands still import `calliope` correctly.

The frontend is created at `src/frontend` and uses:

- Vue 3
- TypeScript
- Vite
- Bun for install and scripts
- Vuetify 3
- Pinia
- Vitest and Vue Test Utils

The frontend API base URL is configured by `VITE_CALLIOPE_API_BASE_URL`, defaulting to `http://127.0.0.1:8000`.

## Runtime Architecture

During development:

```txt
Postgres + pgvector
  <- Python FastAPI backend at 127.0.0.1:8000
  <- Vue/Vite frontend at a Vite dev URL
```

The frontend talks only to the backend HTTP API. It does not import Python code, access the database, or scan local folders. Workspace creation uses a typed backend-local absolute path. The workspace input and API naming use "workspace root" language so a future desktop shell or browser capability can replace the typed path with a native folder picker.

Future Docker or Podman Compose can stand up Postgres, backend, and frontend together. The MVP does not require choosing whether production serves the frontend through FastAPI or through a dedicated frontend container.

## User Experience

The app opens directly into the chat workspace.

### App Shell

The app shell has:

- A persistent left conversation drawer.
- A main conversation pane.
- A bottom composer.
- A settings entry in the shell chrome.

The visual direction uses Vuetify components with a custom Calliope theme. The UI should feel compact, modern, and focused rather than like a generic Material demo. Use restrained density, square-ish surfaces, neutral-friendly dark and light support, and typography suitable for repeated writing and research sessions. Cards are for repeated messages, search results, and modal sections only.

### Conversation Drawer

The drawer contains:

- New conversation action.
- Search or filter across conversation titles.
- Active workspace indicator.
- Nested conversation folders.
- Nameable folders with create, rename, delete, and move operations.
- Conversations assigned to folders.
- Recent unfiled conversations.
- Timestamps or relative update times.

Folder and conversation organization is persisted by the backend. The frontend never treats the folder tree as browser-only state.

### Conversation Timeline

The timeline renders:

- User turns.
- Assistant turns.
- Search-result turns.
- Source citations attached to assistant and search-result turns.
- Request-level errors near the failed turn when possible.

Search mode creates a visible turn in the active conversation. It renders retrieved sources only, not an assistant answer. Chat mode creates user and assistant messages with sources attached to the assistant response.

### Composer

The composer contains only controls that work in the MVP:

- Message input.
- Mode selector: `Chat` or `Search`.
- Response policy selector.
- Chat-capable profile/model selector.
- Submit button.

The composer is disabled when required configuration is missing. It shows a non-streaming loading state while waiting for the backend response. It does not include attach, screenshot, microphone, voice, or generic action buttons in the MVP.

### Settings Dialog

The settings dialog has tabs:

- `LLM Profiles`
- `Workspaces`
- `Indexing`

`LLM Profiles` lets users create, edit, delete, list, and test connection profiles. Profiles expose name, kind, base URL, model, API key environment variable reference, and capabilities.

`Workspaces` lets users create, edit, delete, and select workspaces. MVP workspace creation uses a typed backend-local absolute path plus include/exclude glob fields. Validation errors from the backend are shown inline.

`Indexing` lets users choose a workspace, start reindexing, and see the synchronous result or error. Background job polling is deferred.

## Frontend Structure

```txt
src/frontend/src/
  app/
    App.vue
    router.ts
    vuetify.ts
  features/
    chat/
      api.ts
      types.ts
      stores/
      components/
    settings/
      stores/
      components/
    workspaces/
      api.ts
      types.ts
      stores/
      components/
    profiles/
      api.ts
      types.ts
      stores/
      components/
  shared/
    api/
      client.ts
      errors.ts
    components/
```

Feature modules own their API calls, types, stores, and components. Shared code is limited to generic API client behavior, error normalization, layout primitives, and small reusable controls.

## State Management

Pinia owns frontend state:

- `chatStore`: folders, sessions, active session id, active messages, pending chat/search request state, selected mode, selected policy, selected workspace, and selected chat profile.
- `workspaceStore`: workspace list, selected workspace, workspace mutations, reindex state.
- `profileStore`: profile list, chat-capable profiles, profile mutations, profile test state.
- `settingsStore`: settings dialog visibility and active tab.

Vue Query is not part of the initial design. The app has a small number of explicit resources and refresh points, so typed API helpers plus Pinia are enough for the MVP.

## Data Flow

On startup, the frontend loads:

- Workspaces.
- Chat-capable profiles.
- Conversation folder tree and unfiled sessions.
- The most recent session, selected session, or an empty new-thread state.

When the user submits in `Chat` mode, the frontend sends message, optional session id, workspace id, selected policy, selected chat profile id, and retrieval limit. The backend creates a session if needed, stores the user and assistant messages, records sources and trace metadata, and returns enough data for the frontend to update the active thread.

When the user submits in `Search` mode, the frontend sends query, optional session id, workspace id, and retrieval limit. The backend stores a search-result turn in the active conversation and returns sources. The frontend renders the result as part of the conversation timeline.

After settings mutations, the relevant store refreshes its list and preserves the current selection when possible.

## Error Handling

The frontend handles expected failures in visible UI states:

- Backend unreachable: full-page connection state with API URL and retry.
- No workspace: composer disabled until a workspace exists.
- No chat profile: chat mode disabled until a chat-capable profile exists.
- Missing embedding profile or retrieval failure: request-level error near the composer or failed turn.
- Profile test failure: inline result in the profile editor.
- Workspace validation failure: inline path or glob error.
- Reindex failure: visible error in the indexing tab with backend code and details when available.
- Empty conversation: centered empty thread state plus composer.
- Empty folder: compact empty row in the drawer.
- Session not found after refresh: return to latest available session or a new empty thread.

The API client normalizes backend errors shaped as:

```json
{
  "error": {
    "code": "workspace_not_found",
    "message": "Workspace not found.",
    "details": {}
  }
}
```

Components consume typed UI errors instead of parsing raw HTTP responses.

## Testing Strategy

Tests cover:

- API client success and error normalization.
- Pinia store transitions for loading, success, and failure.
- Composer validation and payload creation.
- Drawer folder/session rendering and selection behavior.
- Settings profile and workspace forms.
- Reindex panel loading, success, and failure states.
- One happy-path chat flow with mocked API responses.
- One happy-path search flow with mocked API responses.

End-to-end browser tests are not required for MVP acceptance. Unit and component tests are the required frontend verification layer for this spec.

## Acceptance Criteria

- `src/frontend` is a Bun-managed Vue 3 TypeScript app using Vuetify 3.
- Existing backend code is moved under `src/backend/calliope` without breaking backend tests.
- The app can connect to a running Calliope backend by `VITE_CALLIOPE_API_BASE_URL`.
- A user can view, create, and switch conversations.
- A user can create nested folders and assign conversations to folders.
- A user can submit chat turns without streaming.
- A user can submit search turns that become conversation history.
- A user can choose workspace, response policy, and chat profile from the composer.
- A user can manage profiles from settings.
- A user can manage workspaces from settings.
- A user can run a reindex from settings and see result or error.
- Missing configuration and backend errors are visible and recoverable.
