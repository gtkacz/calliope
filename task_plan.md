# Task Plan: Settings Profiles and Workspaces UX Revamp

## Goal
Implement the planned frontend settings UX and the bounded backend workspace glob-preview API, retaining compatibility with existing profile capability storage.

## Current Phase
Complete

## Phases

### Phase 1: Inspect existing settings, profile, workspace, and scanner behavior
- [x] Map current components, stores, API types, and test conventions
- [x] Identify browse-boundary and glob behavior to reuse
- **Status:** complete

### Phase 2: Backend validation and preview API
- [x] Trim/reject blank workspace and profile names on create/patch
- [x] Add confined, bounded, no-content-read glob preview endpoint and tests
- **Status:** complete

### Phase 3: Frontend settings UX
- [x] Implement explicit neutral/create/edit states, draft guard, search, and validation
- [x] Implement profile role grouping/legacy compatibility and workspace preview
- **Status:** complete

### Phase 4: Verification
- [x] Add/update focused backend and frontend tests
- [x] Run typecheck, production build, and applicable test suites
- **Status:** complete

### Phase 5: Explain the codebase
- [x] Map the repository, runtime entry points, and deployment shape
- [x] Trace the core domain/data flow and persistence model
- [x] Inspect indexing, retrieval, agent/tool orchestration, and frontend integration
- [x] Verify the mental model against tests and configuration
- [x] Deliver a concise, CS Master's-level walkthrough
- **Status:** complete

## Constraints
- Preserve existing public profile capability format, backend enum behavior, and database schema.
- Preserve unrelated user changes, including the untracked AGENTS.md file.
- Use the scanner glob semantics and permanent version-store ignore for previews without reading file content.

## Errors Encountered
| Error | Attempt | Resolution |
|---|---|---|
| None yet | — | — |
| Full combined verification invoked Bun from repository root | 1 | Backend suite completed (147 passed); rerun frontend commands from `src/frontend`. |
| Profile capability conditional inferred `string[]` | 1 | Declared the visible capability array as `ProfileCapability[]`; typecheck/build pass. |
| Current full backend test run could not connect to localhost PostgreSQL | 1 | 68 non-DB tests passed; 79 DB-backed setups errored because port 5432 is not running. Verify unit tests separately and report the environment dependency. |
