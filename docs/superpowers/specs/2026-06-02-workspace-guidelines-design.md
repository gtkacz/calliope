# Workspace Guidelines — Design

**Date:** 2026-06-02
**Status:** Approved
**Author:** brainstorming session (Calliope, Feature 1)

## 1. Problem

A worldbuilder works inside a single fictional setting with standing stylistic and
contextual constraints — "this is a dark fantasy world", "render all dates in the
Imperial calendar", "the narrator is always second-person". Today the only way to
convey these to the model is to repeat them in every chat message, write
instruction, and editor instruction. They are forgotten between turns and absent
from the editor surface entirely.

We want a **per-workspace standing directive** ("guidelines") that is injected into
the system prompt of every generation surface, with a per-surface toggle in the web
app so a writer can suppress it for a single request when it would distort output
(e.g. asking a factual lookup that the dark-fantasy framing would wrongly colour).

## 2. Scope

**In scope** — guidelines are injected on the three generation surfaces:

| Surface | Builder | Entry point |
|---------|---------|-------------|
| Chat    | `build_chat_messages`          | `ChatService.chat` |
| Write   | `build_write_messages`         | `WriteService.write` |
| Editor  | `build_document_edit_messages` | `EditorService.propose` (via `/v1/editor/propose`) |

**Explicitly excluded** — the conversation-title builder
(`build_conversation_title_messages`). Title generation is a utility call whose only
job is to compress the first turn into 2–6 words; injecting world framing there adds
tokens and noise without value.

**Out of scope (deferred to a separate spec)** — Feature 2, the adversarial-review
model behind a feature flag.

## 3. Storage model

Guidelines are a **free-text column on the workspace**, not a pointer to an indexed
document.

```
Workspace.guidelines: str | None   -- NULL or empty means "no standing guidelines"
```

### Why free text, not a document pointer

The rejected alternative was "point the workspace at a markdown file whose body is
injected". It was rejected because that file would be discovered by the existing
glob-based indexer, chunked, embedded, and then **retrieved as a canon source** —
the guidelines would contaminate retrieval and could be cited back as if they were
in-world facts. Suppressing it from indexing is possible but bolts a special case
onto the ingest path. A dedicated column keeps the guidelines completely outside the
retrieval system: they are framing, never a source.

### Persistence semantics

- The column is **nullable with no server default**. Existing workspaces read `NULL`
  and behave exactly as today (no guidelines). No data backfill.
- On update we mirror the established `SessionPatch.canvas` convention
  (`schemas.py:261`): in `WorkspacePatch`, `guidelines=None` means *unchanged*; an
  explicit **empty string clears** the stored guidelines. The repository normalises
  `""` to `NULL` on write so "no guidelines" has a single canonical representation.

## 4. Prompt injection

### 4.1 The injected block

A single helper produces the block, so all three surfaces stay identical:

```python
def _format_guidelines_block(guidelines: str) -> str:
    return (
        "WORKSPACE GUIDELINES (standing creative and stylistic context for this world):\n"
        f"{guidelines.strip()}\n"
        "Apply these as background framing for tone, setting, and style. They do NOT "
        "override the grounding rules above: never invent, alter, or contradict canon to "
        "satisfy a guideline, and never emit a guideline as if it were a cited fact."
    )
```

### 4.2 Placement

The block is appended to the **end** of each surface's existing system message,
*after* the grounding/policy text, when (and only when) `guidelines` is non-empty
after stripping. Ordering rationale: the canon-fidelity rules are the
non-negotiable contract and must be read first; the guidelines are background
framing and explicitly defer to those rules in their own closing sentence. This
ordering is what lets the same world framing coexist with `strict_canon` without the
model treating the framing as a licence to invent.

- **Chat** — after `"Cite sources by path when using canon details."`
- **Write** — after `f"GROUNDING:\n{WRITE_POLICY_TEXT[policy]}"`
- **Editor** — after the contradiction-decline note that currently ends
  `system_content`.

When `guidelines` is `None` or blank, the system message is **byte-for-byte
identical** to today — this is the property the "absent" unit tests pin.

### 4.3 Why the system prompt, not the user message

The guidelines are standing instructions about *how* to respond, not content to
reason over. They belong with the other behavioural rules in the system role, where
instruction-tuned models weight them as directives rather than as material to
summarise or quote.

## 5. The per-surface toggle

### 5.1 Request contract

Each generation request schema gains an `apply_guidelines: bool = True` field:

- `ChatRequest.apply_guidelines`
- `WriteRequest.apply_guidelines`
- `EditProposalRequest.apply_guidelines`

**Default `True`** — the common case is that a writer who has set guidelines wants
them applied. The toggle is an escape hatch, not an opt-in.

Because the default is `True` and every existing caller omits the field, no existing
API contract changes shape; this is purely additive.

### 5.2 Resolution

A small service module `calliope/services/guidelines.py` owns resolution. It exposes
two best-effort functions that return `str | None` and **never raise** — a guideline
lookup failure must never break a generation:

- `resolve_workspace_guidelines(session, *, workspace_id, apply_guidelines)` — used
  by chat and write, which carry an explicit `workspace_id`. Returns `None` when the
  toggle is off, when `workspace_id` is `None`, or on any lookup failure.
- `resolve_guidelines_for_path(session, *, path, apply_guidelines)` — used by the
  editor, which has no `workspace_id` but a file path. Resolves the containing
  workspace via the existing `WorkspaceRepository.find_by_path` (longest-root match),
  mirroring how `_resolve_editor_sources` already locates the editor's workspace.

The editor performs two independent best-effort workspace lookups (one for sources,
one for guidelines). The workspaces table holds a handful of rows, so the extra
lookup is negligible, and keeping the two concerns in separate resolvers preserves
clean separation (retrieval context vs. standing framing).

### 5.3 Web app behaviour

- The toggle is **independent per surface**: three Pinia flags
  `applyGuidelinesChat`, `applyGuidelinesWrite`, `applyGuidelinesEditor`, all default
  `true`.
- It **persists as session state** (Pinia), consistent with how `policy`, `mode`,
  and `selectedWorkspaceId` already behave — it survives switching between surfaces
  and sessions within an app session. It is **not** persisted to `localStorage`
  across page reloads; no surface in the app does that today, and adding it would
  introduce a new pattern for no requested benefit.
- The toggle is **only shown when it can do something**: the selected workspace has
  non-empty `guidelines`, and (for the composer) the mode is not `search`. When the
  workspace has no guidelines the control is hidden entirely rather than shown
  disabled — there is nothing to toggle.

## 6. Length handling — soft limit only

There is **no hard cap**. The web app shows a non-blocking warning once the
guidelines text exceeds **2000 characters**, and the user may save anyway.

### Why 2000 characters

Guidelines share the model's context window with retrieved canon. At the default
`limit=5`, retrieval injects roughly `5 × ~1800 chars ≈ 9000 chars` of source text
(the budget already documented on `ChatRequest.limit`). A 2000-character ceiling
(~500 tokens) keeps standing framing to under a quarter of the source budget, so it
informs tone without crowding out the canon the answer must be grounded in — and it
stays safe on the small-context local models (e.g. KoboldCpp/Ollama setups) this
project targets. It is a guard-rail, not a constraint: the limit is advisory because
a legitimately long style bible should not be silently truncated or hard-rejected.

`GUIDELINES_SOFT_LIMIT_CHARS = 2000` is defined as a named constant in the
WorkspacePanel component with a comment recording this rationale.

## 7. Error handling

- **Resolution** is best-effort and silent (logged at `warning`): any failure yields
  `None` and generation proceeds without guidelines, matching the editor's existing
  best-effort source resolution.
- **Persistence** rides the existing `WorkspacePatch`/`WorkspaceCreate` flow and its
  `IntegrityError → AppError` handling; no new failure modes.
- **Input** is free text; there is no server-side validation beyond the column type.
  The soft limit is a UI affordance only.

## 8. Testing strategy

Backend (pytest):

1. Schema defaults — `WorkspaceCreate.guidelines is None`;
   `ChatRequest`/`WriteRequest`/`EditProposalRequest.apply_guidelines is True`.
2. Repository round-trip — create with guidelines, patch to a new value, patch with
   `""` clears to `None`, patch with `None` leaves unchanged; migration-head
   assertion updated to `0008_workspace_guidelines`.
3. Prompt builder — block present when guidelines supplied (all three builders),
   and system message unchanged when guidelines `None`/blank.
4. Guidelines service — both resolvers: suppressed → `None`, missing id → `None`,
   empty stored value → `None`, unknown workspace → `None`, path under root →
   guidelines, path under no workspace → `None`.
5. Service wiring — chat/write/editor each inject the block when guidelines exist and
   the toggle is on, and omit it when the toggle is off.

Frontend (vitest):

6. chatStore sends `apply_guidelines` (default `true`; respects the per-surface flag).
7. ComposerBar shows the toggle only when the selected workspace has guidelines.

## 9. Migration

New Alembic revision `0008_workspace_guidelines` (down-revision
`0007_profile_max_tokens`): `op.add_column("workspaces", sa.Column("guidelines",
sa.Text(), nullable=True))`; downgrade drops it. Pattern is identical to
`0002_versioning_enabled`.
