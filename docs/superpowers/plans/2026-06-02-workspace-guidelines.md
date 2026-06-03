# Workspace Guidelines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-workspace free-text "guidelines" directive that is injected into the chat, write, and editor system prompts, with a per-surface toggle (default on) in the web app.

**Architecture:** A nullable `guidelines` text column on `workspaces` flows through the existing domain-schema → repository → service → prompt-builder layers. A new `services/guidelines.py` module resolves the active guidelines per request (best-effort, never raises). Each generation request gains an `apply_guidelines: bool = True` flag. The web app stores three independent Pinia toggle flags and surfaces a control only when the selected workspace actually has guidelines.

**Tech Stack:** Python · FastAPI · SQLAlchemy · Alembic · Pydantic · pytest (backend, run via `uv`); Vue 3 `<script setup>` · Pinia · Vuetify · TypeScript · vitest (frontend, run via `bun`).

**Spec:** `docs/superpowers/specs/2026-06-02-workspace-guidelines-design.md`

---

## Conventions for every task

- **Backend commands** run from the repo root `/home/gtkacz/Codes/calliope`.
- **Frontend commands** run from `/home/gtkacz/Codes/calliope/src/frontend`.
- A Postgres test database must be reachable (see `tests/conftest.py`; override with `CALLIOPE_TEST_DATABASE_URL`).
- `git add` only the exact paths listed — the repo already has unrelated uncommitted changes that must NOT be swept into these commits.
- Stay on `main` (no feature branch).

## File Structure

**Backend — modify**
- `src/backend/calliope/db/models.py` — add `Workspace.guidelines` column.
- `src/backend/calliope/domain/schemas.py` — add `guidelines` to workspace schemas; add `apply_guidelines` to the three request schemas.
- `src/backend/calliope/repositories/workspaces.py` — persist/clear/read `guidelines`.
- `src/backend/calliope/prompts/builder.py` — `_format_guidelines_block` + `guidelines` param on the three builders.
- `src/backend/calliope/services/chat.py` — resolve + forward guidelines.
- `src/backend/calliope/services/write.py` — resolve + forward guidelines.
- `src/backend/calliope/services/editor.py` — `guidelines` param forwarded to the builder.
- `src/backend/calliope/api/routes/editor.py` — resolve guidelines by path and pass to the service.

**Backend — create**
- `alembic/versions/0008_workspace_guidelines.py` — the migration.
- `src/backend/calliope/services/guidelines.py` — the two resolver functions.

**Frontend — modify**
- `src/frontend/src/app/icons.ts` — register the toggle glyph.
- `src/frontend/src/features/workspaces/types.ts` — `Workspace.guidelines`.
- `src/frontend/src/features/workspaces/api.ts` — `WorkspacePayload.guidelines`.
- `src/frontend/src/features/workspaces/components/WorkspacePanel.vue` — guidelines textarea + soft-limit warning.
- `src/frontend/src/features/chat/api.ts` — `apply_guidelines` on `sendChat`/`sendWrite` payloads.
- `src/frontend/src/features/chat/stores/chatStore.ts` — three toggle flags + send them.
- `src/frontend/src/features/chat/components/ComposerBar.vue` — the composer toggle.
- `src/frontend/src/features/editor/api.ts` — `apply_guidelines` on `ProposeEditParams`.
- `src/frontend/src/features/editor/components/EditorPanel.vue` — the editor toggle.

**Tests — modify**
- `tests/unit/test_schemas.py`, `tests/integration/test_repositories.py`, `tests/unit/test_prompt_builder.py`, `tests/integration/test_chat_service.py`, `src/frontend/src/features/chat/stores/chatStore.test.ts`, `src/frontend/src/features/chat/components/ComposerBar.test.ts`.

**Tests — create**
- `tests/integration/test_guidelines_service.py`, `tests/integration/test_write_service.py`, `tests/integration/test_editor_service.py`.

---

## Task 1: Database column + migration

**Files:**
- Modify: `src/backend/calliope/db/models.py:27`
- Create: `alembic/versions/0008_workspace_guidelines.py`
- Modify (test): `tests/integration/test_repositories.py:49`

- [ ] **Step 1: Update the migration-head assertion (failing test)**

In `tests/integration/test_repositories.py`, change line 49 from:

```python
    assert version.scalar_one() == "0007_profile_max_tokens"
```

to:

```python
    assert version.scalar_one() == "0008_workspace_guidelines"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/integration/test_repositories.py::test_database_schema_is_applied_by_migrations -v`
Expected: FAIL — `assert '0007_profile_max_tokens' == '0008_workspace_guidelines'`.

- [ ] **Step 3: Add the model column**

In `src/backend/calliope/db/models.py`, insert immediately after the `versioning_enabled` column (line 27), before `created_at`:

```python
    # Free-text standing directive injected into the chat/write/editor system
    # prompts; NULL or empty means the workspace has no standing guidelines.
    guidelines: Mapped[str | None] = mapped_column(Text, nullable=True)
```

(`Text` is already imported on line 8.)

- [ ] **Step 4: Create the migration**

Create `alembic/versions/0008_workspace_guidelines.py`:

```python
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_workspace_guidelines"
down_revision: str | None = "0007_profile_max_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable with no server_default: existing workspaces read NULL and behave
    # exactly as before (no standing guidelines), so no data backfill is needed.
    op.add_column(
        "workspaces",
        sa.Column("guidelines", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "guidelines")
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/integration/test_repositories.py::test_database_schema_is_applied_by_migrations -v`
Expected: PASS (the `db_engine` fixture upgrades to head, which is now `0008`).

- [ ] **Step 6: Commit**

```bash
git add src/backend/calliope/db/models.py alembic/versions/0008_workspace_guidelines.py tests/integration/test_repositories.py
git commit -m "feat: add workspace guidelines column and migration"
```

---

## Task 2: Domain schemas

**Files:**
- Modify: `src/backend/calliope/domain/schemas.py`
- Modify (test): `tests/unit/test_schemas.py`

- [ ] **Step 1: Write the failing tests**

In `tests/unit/test_schemas.py`, replace the top import line:

```python
from calliope.domain.schemas import SourceReference, WorkspaceCreate
```

with:

```python
from calliope.domain.schemas import (
    ChatRequest,
    EditProposalRequest,
    SourceReference,
    WorkspaceCreate,
    WriteRequest,
)
```

Then, inside `test_workspace_create_defaults_globs`, add a final assertion after line 17 (`assert payload.versioning_enabled is None`):

```python
    # Guidelines are unset by default — the workspace has no standing directive.
    assert payload.guidelines is None
```

And append a new test at the end of the file:

```python
def test_generation_requests_apply_guidelines_by_default() -> None:
    assert ChatRequest(message="hi").apply_guidelines is True
    assert WriteRequest(message="hi").apply_guidelines is True
    assert EditProposalRequest(path="a.md", instruction="x").apply_guidelines is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_schemas.py -v`
Expected: FAIL — `AttributeError`/`ImportError` on the new symbols and `payload.guidelines`.

- [ ] **Step 3: Add the schema fields**

In `src/backend/calliope/domain/schemas.py`:

In `WorkspaceCreate`, after the `versioning_enabled` field (line 24):

```python
    guidelines: str | None = None
```

In `WorkspacePatch`, after the `versioning_enabled` field (line 32):

```python
    guidelines: str | None = None
```

In `ChatRequest`, after `cited_document_ids` (line 158):

```python
    # Whether to inject the workspace's standing guidelines (default on); the
    # web app toggles this per request.
    apply_guidelines: bool = True
```

In `EditProposalRequest`, after `chat_profile_id` (line 172):

```python
    apply_guidelines: bool = True
```

In `WriteRequest`, after `cited_document_ids` (line 275):

```python
    apply_guidelines: bool = True
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_schemas.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/backend/calliope/domain/schemas.py tests/unit/test_schemas.py
git commit -m "feat: add guidelines and apply_guidelines fields to schemas"
```

---

## Task 3: Workspace repository persistence

**Files:**
- Modify: `src/backend/calliope/repositories/workspaces.py`
- Modify (test): `tests/integration/test_repositories.py`

- [ ] **Step 1: Write the failing test**

In `tests/integration/test_repositories.py`, update the schema import (line 15):

```python
from calliope.domain.schemas import WorkspaceCreate, WorkspacePatch
```

Append this test to the end of the file:

```python
def test_workspace_guidelines_round_trip(db_session) -> None:
    repo = WorkspaceRepository(db_session)
    created = repo.create(
        WorkspaceCreate(
            name="guided",
            root_path="/tmp/guided",
            guidelines="This is a dark fantasy world.",
        )
    )
    assert created.guidelines == "This is a dark fantasy world."

    updated = repo.update(created.id, WorkspacePatch(guidelines="Now high fantasy."))
    assert updated.guidelines == "Now high fantasy."

    # An omitted (None) guidelines field leaves the stored value unchanged.
    unchanged = repo.update(created.id, WorkspacePatch(name="renamed"))
    assert unchanged.guidelines == "Now high fantasy."

    # An empty string clears the standing guidelines back to None.
    cleared = repo.update(created.id, WorkspacePatch(guidelines=""))
    assert cleared.guidelines is None

    # Empty guidelines on create are normalised to None as well.
    blank = repo.create(WorkspaceCreate(name="blank", root_path="/tmp/blank", guidelines=""))
    assert blank.guidelines is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/integration/test_repositories.py::test_workspace_guidelines_round_trip -v`
Expected: FAIL — `WorkspaceRead` has no `guidelines` populated / `TypeError` on `_to_read`, or assertion error.

- [ ] **Step 3: Implement persistence**

In `src/backend/calliope/repositories/workspaces.py`:

In `create()`, add to the `Workspace(...)` constructor (after `versioning_enabled=payload.versioning_enabled,` on line 21) — note the `or None` normalises an empty string to a single canonical "no guidelines" value:

```python
            guidelines=payload.guidelines or None,
```

In `update()`, add after the `versioning_enabled` block (after line 61):

```python
        # None means unchanged; an empty string clears the standing guidelines.
        if payload.guidelines is not None:
            workspace.guidelines = payload.guidelines or None
```

In `_to_read()`, add to the `WorkspaceRead(...)` constructor (after `versioning_enabled=workspace.versioning_enabled,` on line 119):

```python
            guidelines=workspace.guidelines,
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/integration/test_repositories.py::test_workspace_guidelines_round_trip -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/backend/calliope/repositories/workspaces.py tests/integration/test_repositories.py
git commit -m "feat: persist workspace guidelines through the repository"
```

---

## Task 4: Prompt-builder guidelines block

**Files:**
- Modify: `src/backend/calliope/prompts/builder.py`
- Modify (test): `tests/unit/test_prompt_builder.py`

- [ ] **Step 1: Write the failing tests**

In `tests/unit/test_prompt_builder.py`, replace the import (line 3):

```python
from calliope.prompts.builder import (
    build_chat_messages,
    build_conversation_title_messages,
    build_document_edit_messages,
    build_write_messages,
)
```

and add `EditMode` to the enums import (line 1):

```python
from calliope.domain.enums import CanonPolicy, EditMode
```

Append these tests:

```python
def test_build_chat_messages_appends_guidelines_block() -> None:
    source = SourceReference(
        document_id="document_1",
        chunk_id="chunk_1",
        path="characters/kaelen.md",
        heading="Kaelen",
        context="Kaelen was exiled from Velmora.",
        score=0.9,
    )

    messages = build_chat_messages(
        message="Who exiled Kaelen?",
        policy=CanonPolicy.STRICT_CANON,
        sources=[source],
        guidelines="This is a dark fantasy world.",
    )

    assert "WORKSPACE GUIDELINES" in messages[0]["content"]
    assert "dark fantasy world" in messages[0]["content"]


def test_build_chat_messages_omits_guidelines_block_when_blank() -> None:
    source = SourceReference(
        document_id="document_1",
        chunk_id="chunk_1",
        path="characters/kaelen.md",
        heading="Kaelen",
        context="Kaelen was exiled from Velmora.",
        score=0.9,
    )

    messages = build_chat_messages(
        message="Who exiled Kaelen?",
        policy=CanonPolicy.STRICT_CANON,
        sources=[source],
        guidelines="   ",
    )

    assert "WORKSPACE GUIDELINES" not in messages[0]["content"]


def test_build_write_messages_appends_guidelines_block() -> None:
    messages = build_write_messages(
        message="Expand the introduction.",
        policy=CanonPolicy.CREATIVE_BUT_CONSISTENT,
        canvas="# Title",
        sources=[],
        guidelines="This is a dark fantasy world.",
    )

    assert "WORKSPACE GUIDELINES" in messages[0]["content"]


def test_build_document_edit_messages_appends_guidelines_block() -> None:
    messages = build_document_edit_messages(
        content="# Doc",
        instruction="Add a closing line.",
        mode=EditMode.APPEND,
        guidelines="This is a dark fantasy world.",
    )

    assert "WORKSPACE GUIDELINES" in messages[0]["content"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_prompt_builder.py -v`
Expected: FAIL — `build_chat_messages() got an unexpected keyword argument 'guidelines'`.

- [ ] **Step 3: Add the helper**

In `src/backend/calliope/prompts/builder.py`, add after `_format_cited_document` (end of file, after line 302):

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

- [ ] **Step 4: Wire the helper into `build_chat_messages`**

Change the signature (add the param after `history`, lines 112-118):

```python
def build_chat_messages(
    *,
    message: str,
    policy: CanonPolicy,
    sources: list[SourceReference],
    cited_documents: list[CitedDocument] | None = None,
    history: list[HistoryTurn] | None = None,
    guidelines: str | None = None,
) -> list[dict[str, str]]:
```

Replace the `system_msg` block (lines 133-140):

```python
    system_content = (
        "You are Calliope, a grounded worldbuilding assistant.\n"
        f"{POLICY_TEXT[policy]}\n"
        "Cite sources by path when using canon details."
    )
    if guidelines and guidelines.strip():
        system_content += f"\n\n{_format_guidelines_block(guidelines)}"
    system_msg: dict[str, str] = {"role": "system", "content": system_content}
```

- [ ] **Step 5: Wire the helper into `build_write_messages`**

Change the signature (add the param after `history`, lines 182-190):

```python
def build_write_messages(
    *,
    message: str,
    policy: CanonPolicy,
    canvas: str,
    sources: list[SourceReference],
    cited_documents: list[CitedDocument] | None = None,
    history: list[HistoryTurn] | None = None,
    guidelines: str | None = None,
) -> list[dict[str, str]]:
```

Replace the `system_msg` block (lines 208-233) — the content is identical to today, just assigned to a variable first so the block can be appended:

```python
    system_content = (
        "You are Calliope, collaborating on a single living markdown document "
        "(the canvas).\n"
        "Your task is to apply the writer's instruction to the current canvas and "
        "return the complete revised document.\n"
        "The canvas in the user message is the sole source of document state; do not "
        "rely on conversation history for the document's prior content.\n\n"
        "OUTPUT CONTRACT — read this carefully before generating any text:\n"
        "- Return ONLY the raw markdown of the revised document, from the very first "
        "character to the very last.\n"
        "- Do NOT wrap output in code fences (no ```markdown, no ``` of any kind).\n"
        "- Do NOT add any preamble, commentary, explanation, or sign-off before or "
        "after the document.\n"
        '- Do NOT insert grounding markers, citation tags, "(inference)", '
        '"(invented)", or "[path/to/file.md]" anywhere in the document body. '
        "Canon sources constrain what you may write, not how you annotate it.\n\n"
        f"{_COMPLETENESS_CONTRACT}\n"
        "- If the canvas is empty, create the document from scratch based on the "
        "instruction and sources.\n"
        "- If you reach what feels like a natural stopping point before the document "
        "is complete: keep writing. There is no partial credit.\n\n"
        f"GROUNDING:\n{WRITE_POLICY_TEXT[policy]}"
    )
    if guidelines and guidelines.strip():
        system_content += f"\n\n{_format_guidelines_block(guidelines)}"
    system_msg: dict[str, str] = {"role": "system", "content": system_content}
```

- [ ] **Step 6: Wire the helper into `build_document_edit_messages`**

Change the signature (add the param after `sources`, lines 246-253):

```python
def build_document_edit_messages(
    *,
    content: str,
    instruction: str,
    mode: EditMode,
    policy: CanonPolicy = CanonPolicy.CANON_PLUS_INFERENCE,
    sources: list[SourceReference] | None = None,
    guidelines: str | None = None,
) -> list[dict[str, str]]:
```

`system_content` is already a variable; append the block right after its assignment (after line 281, before `user_content = ...`):

```python
    if guidelines and guidelines.strip():
        system_content += f"\n\n{_format_guidelines_block(guidelines)}"
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_prompt_builder.py -v`
Expected: PASS (all 6 tests, including the two pre-existing ones).

- [ ] **Step 8: Commit**

```bash
git add src/backend/calliope/prompts/builder.py tests/unit/test_prompt_builder.py
git commit -m "feat: inject workspace guidelines into chat, write, and editor prompts"
```

---

## Task 5: Guidelines resolver service + chat wiring

**Files:**
- Create: `src/backend/calliope/services/guidelines.py`
- Create (test): `tests/integration/test_guidelines_service.py`
- Modify: `src/backend/calliope/services/chat.py`
- Modify (test): `tests/integration/test_chat_service.py`

- [ ] **Step 1: Write the failing resolver tests**

Create `tests/integration/test_guidelines_service.py`:

```python
from pathlib import Path

from calliope.domain.schemas import WorkspaceCreate
from calliope.repositories.workspaces import WorkspaceRepository
from calliope.services.guidelines import (
    resolve_guidelines_for_path,
    resolve_workspace_guidelines,
)
from sqlalchemy.orm import Session


def _create(session: Session, name: str, root_path: str, guidelines: str | None) -> str:
    return WorkspaceRepository(session).create(
        WorkspaceCreate(name=name, root_path=root_path, guidelines=guidelines)
    ).id


def test_resolve_workspace_guidelines_returns_none_when_suppressed(db_session: Session) -> None:
    ws_id = _create(db_session, "w1", "/tmp/w1", "Dark fantasy.")
    assert resolve_workspace_guidelines(db_session, workspace_id=ws_id, apply_guidelines=False) is None


def test_resolve_workspace_guidelines_returns_none_without_workspace_id(db_session: Session) -> None:
    assert resolve_workspace_guidelines(db_session, workspace_id=None, apply_guidelines=True) is None


def test_resolve_workspace_guidelines_returns_none_when_empty(db_session: Session) -> None:
    ws_id = _create(db_session, "w2", "/tmp/w2", None)
    assert resolve_workspace_guidelines(db_session, workspace_id=ws_id, apply_guidelines=True) is None


def test_resolve_workspace_guidelines_returns_text(db_session: Session) -> None:
    ws_id = _create(db_session, "w3", "/tmp/w3", "Dark fantasy.")
    assert resolve_workspace_guidelines(db_session, workspace_id=ws_id, apply_guidelines=True) == "Dark fantasy."


def test_resolve_workspace_guidelines_returns_none_for_unknown_workspace(db_session: Session) -> None:
    assert resolve_workspace_guidelines(db_session, workspace_id="workspace_missing", apply_guidelines=True) is None


def test_resolve_guidelines_for_path_returns_text_for_contained_path(db_session: Session, tmp_path: Path) -> None:
    root = tmp_path / "world"
    root.mkdir()
    _create(db_session, "w4", str(root), "Dark fantasy.")
    target = root / "notes" / "a.md"
    assert resolve_guidelines_for_path(db_session, path=str(target), apply_guidelines=True) == "Dark fantasy."


def test_resolve_guidelines_for_path_returns_none_when_no_workspace(db_session: Session, tmp_path: Path) -> None:
    assert resolve_guidelines_for_path(db_session, path=str(tmp_path / "orphan.md"), apply_guidelines=True) is None


def test_resolve_guidelines_for_path_returns_none_when_suppressed(db_session: Session, tmp_path: Path) -> None:
    root = tmp_path / "world"
    root.mkdir()
    _create(db_session, "w5", str(root), "Dark fantasy.")
    assert resolve_guidelines_for_path(db_session, path=str(root / "a.md"), apply_guidelines=False) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/integration/test_guidelines_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'calliope.services.guidelines'`.

- [ ] **Step 3: Create the service**

Create `src/backend/calliope/services/guidelines.py`:

```python
from __future__ import annotations

import logging

from calliope.repositories.workspaces import WorkspaceRepository
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def resolve_workspace_guidelines(
    session: Session,
    *,
    workspace_id: str | None,
    apply_guidelines: bool,
) -> str | None:
    """Standing guidelines for a workspace addressed by id (chat/write surfaces).

    Returns None when the request suppresses guidelines, when no workspace is
    given, when the workspace stores none, or on any lookup failure. Best-effort:
    a guideline lookup must never break a generation, so this never raises."""
    if not apply_guidelines or workspace_id is None:
        return None
    try:
        workspace = WorkspaceRepository(session).get(workspace_id)
    except Exception:
        logger.warning(
            "guideline resolution failed for workspace_id %r; continuing without guidelines",
            workspace_id,
            exc_info=True,
        )
        return None
    return workspace.guidelines or None


def resolve_guidelines_for_path(
    session: Session,
    *,
    path: str,
    apply_guidelines: bool,
) -> str | None:
    """Standing guidelines for the workspace whose root contains `path`.

    Used by the editor surface, which has no workspace id but a file path. Mirrors
    the editor's existing best-effort workspace resolution; returns None when
    suppressed, when no workspace contains the path, or on any lookup failure."""
    if not apply_guidelines:
        return None
    try:
        workspace = WorkspaceRepository(session).find_by_path(path)
    except Exception:
        logger.warning(
            "guideline resolution failed for path %r; continuing without guidelines",
            path,
            exc_info=True,
        )
        return None
    if workspace is None:
        return None
    return workspace.guidelines or None
```

- [ ] **Step 4: Run the resolver tests to verify they pass**

Run: `uv run pytest tests/integration/test_guidelines_service.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Write the failing chat-wiring tests**

In `tests/integration/test_chat_service.py`, add a recording client class after `RecordingTitleChatClient` (after line 38):

```python
class RecordingChatClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    async def chat(self, messages: list[dict[str, str]]) -> ChatCompletion:
        self.calls.append(messages)
        return ChatCompletion(content="Kaelen was exiled from Velmora. [characters/kaelen.md]")
```

Append these two tests to the end of the file:

```python
def test_chat_service_injects_workspace_guidelines(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(HybridRetriever, "_vector_search", lambda *a, **k: ["chunk_a"])
    monkeypatch.setattr(HybridRetriever, "_lexical_search", lambda *a, **k: ["chunk_a"])
    monkeypatch.setattr(
        ChunkRepository,
        "source_for_chunk",
        lambda self, chunk_id, score=1.0: SourceReference(
            document_id="document_a",
            chunk_id=chunk_id,
            path="characters/kaelen.md",
            heading="Kaelen",
            context="Kaelen exile",
            score=score,
        ),
    )

    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(
            name="guided-world",
            root_path="/tmp/guided-world",
            guidelines="This is a dark fantasy world.",
        )
    )
    client = RecordingChatClient()
    service = ChatService(db_session, embedding_client=FakeEmbeddingClient(), chat_client=client)
    try:
        service.chat(
            ChatRequest(message="Where was Kaelen exiled from?", workspace_id=workspace.id, limit=1)
        )
    finally:
        service.close()

    assert "WORKSPACE GUIDELINES" in client.calls[0][0]["content"]
    assert "dark fantasy world" in client.calls[0][0]["content"]


def test_chat_service_omits_guidelines_when_toggle_off(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(HybridRetriever, "_vector_search", lambda *a, **k: ["chunk_a"])
    monkeypatch.setattr(HybridRetriever, "_lexical_search", lambda *a, **k: ["chunk_a"])
    monkeypatch.setattr(
        ChunkRepository,
        "source_for_chunk",
        lambda self, chunk_id, score=1.0: SourceReference(
            document_id="document_a",
            chunk_id=chunk_id,
            path="characters/kaelen.md",
            heading="Kaelen",
            context="Kaelen exile",
            score=score,
        ),
    )

    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(
            name="guided-world-off",
            root_path="/tmp/guided-world-off",
            guidelines="This is a dark fantasy world.",
        )
    )
    client = RecordingChatClient()
    service = ChatService(db_session, embedding_client=FakeEmbeddingClient(), chat_client=client)
    try:
        service.chat(
            ChatRequest(
                message="Where was Kaelen exiled from?",
                workspace_id=workspace.id,
                apply_guidelines=False,
                limit=1,
            )
        )
    finally:
        service.close()

    assert "WORKSPACE GUIDELINES" not in client.calls[0][0]["content"]
```

- [ ] **Step 6: Run the wiring tests to verify they fail**

Run: `uv run pytest tests/integration/test_chat_service.py::test_chat_service_injects_workspace_guidelines -v`
Expected: FAIL — `"WORKSPACE GUIDELINES"` not present (service does not yet resolve/forward guidelines).

- [ ] **Step 7: Wire guidelines into `ChatService`**

In `src/backend/calliope/services/chat.py`, add a new import line immediately before `from calliope.services.search import SearchService` (line 17), so it stays in isort order (`services.guidelines` sorts before `services.search`):

```python
from calliope.services.guidelines import resolve_workspace_guidelines
```

Replace the `messages = build_chat_messages(...)` call (lines 114-120) with:

```python
        guidelines = resolve_workspace_guidelines(
            self.session,
            workspace_id=request.workspace_id,
            apply_guidelines=request.apply_guidelines,
        )
        messages = build_chat_messages(
            message=request.message,
            policy=request.policy,
            sources=search_response.sources,
            cited_documents=cited_documents or None,
            history=history,
            guidelines=guidelines,
        )
```

- [ ] **Step 8: Run the wiring tests to verify they pass**

Run: `uv run pytest tests/integration/test_chat_service.py -v`
Expected: PASS (all chat-service tests, including the two new ones).

- [ ] **Step 9: Commit**

```bash
git add src/backend/calliope/services/guidelines.py src/backend/calliope/services/chat.py tests/integration/test_guidelines_service.py tests/integration/test_chat_service.py
git commit -m "feat: resolve and inject workspace guidelines in chat service"
```

---

## Task 6: Write service wiring

**Files:**
- Modify: `src/backend/calliope/services/write.py`
- Create (test): `tests/integration/test_write_service.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/integration/test_write_service.py`:

```python
from calliope.config import EMBEDDING_DIMENSIONS
from calliope.domain.enums import CanonPolicy
from calliope.domain.schemas import SourceReference, WorkspaceCreate, WriteRequest
from calliope.llm.openai_compatible import ChatCompletion
from calliope.repositories.chunks import ChunkRepository
from calliope.repositories.workspaces import WorkspaceRepository
from calliope.retrieval.hybrid import HybridRetriever
from calliope.services.write import WriteService
import pytest
from sqlalchemy.orm import Session


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        return [0.1] * EMBEDDING_DIMENSIONS


class RecordingChatClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    async def chat(self, messages: list[dict[str, str]]) -> ChatCompletion:
        self.calls.append(messages)
        return ChatCompletion(content="# Revised\n\nBody.")


def _patch_retrieval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(HybridRetriever, "_vector_search", lambda *a, **k: ["chunk_a"])
    monkeypatch.setattr(HybridRetriever, "_lexical_search", lambda *a, **k: ["chunk_a"])
    monkeypatch.setattr(
        ChunkRepository,
        "source_for_chunk",
        lambda self, chunk_id, score=1.0: SourceReference(
            document_id="document_a",
            chunk_id=chunk_id,
            path="characters/kaelen.md",
            heading="Kaelen",
            context="Kaelen exile",
            score=score,
        ),
    )


def test_write_service_injects_workspace_guidelines(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_retrieval(monkeypatch)
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(
            name="write-guided",
            root_path="/tmp/write-guided",
            guidelines="This is a dark fantasy world.",
        )
    )
    client = RecordingChatClient()
    service = WriteService(db_session, embedding_client=FakeEmbeddingClient(), chat_client=client)
    try:
        service.write(
            WriteRequest(
                message="Expand the intro.",
                canvas="# Title",
                policy=CanonPolicy.CREATIVE_BUT_CONSISTENT,
                workspace_id=workspace.id,
                limit=1,
            )
        )
    finally:
        service.close()

    assert "WORKSPACE GUIDELINES" in client.calls[0][0]["content"]


def test_write_service_omits_guidelines_when_toggle_off(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_retrieval(monkeypatch)
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(
            name="write-guided-off",
            root_path="/tmp/write-guided-off",
            guidelines="This is a dark fantasy world.",
        )
    )
    client = RecordingChatClient()
    service = WriteService(db_session, embedding_client=FakeEmbeddingClient(), chat_client=client)
    try:
        service.write(
            WriteRequest(
                message="Expand the intro.",
                canvas="# Title",
                workspace_id=workspace.id,
                apply_guidelines=False,
                limit=1,
            )
        )
    finally:
        service.close()

    assert "WORKSPACE GUIDELINES" not in client.calls[0][0]["content"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/integration/test_write_service.py -v`
Expected: FAIL — `"WORKSPACE GUIDELINES"` not present.

- [ ] **Step 3: Wire guidelines into `WriteService`**

In `src/backend/calliope/services/write.py`, add a new import line immediately before `from calliope.services.search import SearchService` (line 18), so it stays in isort order (`services.guidelines` sorts before `services.search`):

```python
from calliope.services.guidelines import resolve_workspace_guidelines
```

Replace the `messages = build_write_messages(...)` call (lines 117-124) with:

```python
        guidelines = resolve_workspace_guidelines(
            self.session,
            workspace_id=request.workspace_id,
            apply_guidelines=request.apply_guidelines,
        )
        messages = build_write_messages(
            message=request.message,
            policy=request.policy,
            canvas=request.canvas,
            sources=search_response.sources,
            cited_documents=cited_documents or None,
            history=history,
            guidelines=guidelines,
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/integration/test_write_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/backend/calliope/services/write.py tests/integration/test_write_service.py
git commit -m "feat: resolve and inject workspace guidelines in write service"
```

---

## Task 7: Editor service + route wiring

**Files:**
- Modify: `src/backend/calliope/services/editor.py`
- Modify: `src/backend/calliope/api/routes/editor.py`
- Create (test): `tests/integration/test_editor_service.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/integration/test_editor_service.py`:

```python
from calliope.domain.enums import EditMode
from calliope.domain.schemas import EditProposalRequest, FileContent
from calliope.llm.openai_compatible import ChatCompletion
from calliope.services.editor import EditorService


class StubFilesystem:
    def read_file(self, path: str) -> FileContent:
        return FileContent(path=path, content="# Doc\n\nBody.")


class RecordingChatClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    async def chat(self, messages: list[dict[str, str]]) -> ChatCompletion:
        self.calls.append(messages)
        return ChatCompletion(content="A new line.")


def test_editor_service_injects_guidelines() -> None:
    client = RecordingChatClient()
    service = EditorService(filesystem=StubFilesystem(), chat_client=client)
    try:
        service.propose(
            EditProposalRequest(path="/notes/a.md", instruction="Add a closing line.", mode=EditMode.APPEND),
            guidelines="This is a dark fantasy world.",
        )
    finally:
        service.close()

    assert "WORKSPACE GUIDELINES" in client.calls[0][0]["content"]


def test_editor_service_omits_guidelines_when_none() -> None:
    client = RecordingChatClient()
    service = EditorService(filesystem=StubFilesystem(), chat_client=client)
    try:
        service.propose(
            EditProposalRequest(path="/notes/a.md", instruction="Add a closing line.", mode=EditMode.APPEND),
            guidelines=None,
        )
    finally:
        service.close()

    assert "WORKSPACE GUIDELINES" not in client.calls[0][0]["content"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/integration/test_editor_service.py -v`
Expected: FAIL — `propose() got an unexpected keyword argument 'guidelines'`.

- [ ] **Step 3: Add the `guidelines` param to `EditorService.propose`**

In `src/backend/calliope/services/editor.py`, change the `propose` signature (lines 30-36):

```python
    def propose(
        self,
        request: EditProposalRequest,
        *,
        policy: CanonPolicy = CanonPolicy.CANON_PLUS_INFERENCE,
        sources: list[SourceReference] | None = None,
        guidelines: str | None = None,
    ) -> EditProposal:
```

Forward it to the builder (lines 38-44):

```python
        messages = build_document_edit_messages(
            content=current.content,
            instruction=request.instruction,
            mode=request.mode,
            policy=policy,
            sources=sources,
            guidelines=guidelines,
        )
```

- [ ] **Step 4: Run the service tests to verify they pass**

Run: `uv run pytest tests/integration/test_editor_service.py -v`
Expected: PASS.

- [ ] **Step 5: Wire the route to resolve guidelines by path**

In `src/backend/calliope/api/routes/editor.py`, add an import after line 21 (`from calliope.services.filesystem import FilesystemService`):

```python
from calliope.services.guidelines import resolve_guidelines_for_path
```

In `propose_edit`, after the `sources = _resolve_editor_sources(...)` line (line 46), add:

```python
    guidelines = resolve_guidelines_for_path(
        session,
        path=request.path,
        apply_guidelines=request.apply_guidelines,
    )
```

Change the `service.propose(...)` call (line 55) to forward it:

```python
        return service.propose(
            request,
            policy=_EDITOR_POLICY,
            sources=sources,
            guidelines=guidelines,
        )
```

- [ ] **Step 6: Verify the full backend suite is green**

Run: `uv run pytest tests/ -q`
Expected: PASS (no regressions; the editor route change is covered transitively by the contract test and the new service tests).

- [ ] **Step 7: Commit**

```bash
git add src/backend/calliope/services/editor.py src/backend/calliope/api/routes/editor.py tests/integration/test_editor_service.py
git commit -m "feat: resolve and inject workspace guidelines in editor surface"
```

---

## Task 8: Frontend types, API payloads, and icon

**Files:**
- Modify: `src/frontend/src/features/workspaces/types.ts`
- Modify: `src/frontend/src/features/workspaces/api.ts`
- Modify: `src/frontend/src/features/chat/api.ts`
- Modify: `src/frontend/src/features/editor/api.ts`
- Modify: `src/frontend/src/app/icons.ts`

- [ ] **Step 1: Add `guidelines` to the `Workspace` read type**

In `src/frontend/src/features/workspaces/types.ts`, add to the `Workspace` interface after `exclude_globs` (line 6):

```typescript
  guidelines: string | null
```

- [ ] **Step 2: Add `guidelines` to the workspace write payload**

In `src/frontend/src/features/workspaces/api.ts`, add to `WorkspacePayload` after `exclude_globs` (line 9):

```typescript
  guidelines: string | null
```

- [ ] **Step 3: Add `apply_guidelines` to chat and write payloads**

In `src/frontend/src/features/chat/api.ts`, add `apply_guidelines: boolean;` to the `sendChat` payload object type (after `cited_document_ids: string[];`, line 81):

```typescript
  apply_guidelines: boolean;
```

and to the `sendWrite` payload object type (after `cited_document_ids: string[];`, line 110):

```typescript
  apply_guidelines: boolean;
```

- [ ] **Step 4: Add `apply_guidelines` to the editor params**

In `src/frontend/src/features/editor/api.ts`, add to `ProposeEditParams` after `chat_profile_id` (line 12):

```typescript
  apply_guidelines: boolean;
```

- [ ] **Step 5: Register the toggle icon**

In `src/frontend/src/app/icons.ts`, add the import alphabetically between `mdiScaleBalance` (line 29) and `mdiShieldCheckOutline` (line 30):

```typescript
  mdiScriptTextOutline,
```

and add the alias entry between `'mdi-scale-balance'` (line 68) and `'mdi-shield-check-outline'` (line 69):

```typescript
  'mdi-script-text-outline': mdiScriptTextOutline,
```

- [ ] **Step 6: Verify the type-checker is happy so far**

Run: `bun run typecheck`
Expected: FAIL — `WorkspacePanel.vue` `save()` now omits the required `guidelines` payload field. (This is expected; Task 9 fixes it. If you prefer a green checkpoint, do Steps of Task 9 before committing; otherwise commit and proceed — the next task closes the gap.)

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/features/workspaces/types.ts src/frontend/src/features/workspaces/api.ts src/frontend/src/features/chat/api.ts src/frontend/src/features/editor/api.ts src/frontend/src/app/icons.ts
git commit -m "feat: add guidelines to frontend workspace and request types"
```

---

## Task 9: Chat store flags + workspace panel field

**Files:**
- Modify: `src/frontend/src/features/chat/stores/chatStore.ts`
- Modify: `src/frontend/src/features/workspaces/components/WorkspacePanel.vue`
- Modify (test): `src/frontend/src/features/chat/stores/chatStore.test.ts`

- [ ] **Step 1: Write the failing store tests**

In `src/frontend/src/features/chat/stores/chatStore.test.ts`, append two tests inside the `describe('chatStore', ...)` block (before its closing `})`):

```typescript
  it('sends apply_guidelines true by default for chat', async () => {
    const sendChat = vi.spyOn(chatApi, 'sendChat').mockResolvedValue({
      session: {
        id: 'session_1',
        title: 'Lake city',
        folder_id: null,
        workspace_id: 'workspace_1',
        created_at: '2026-05-20T12:00:00Z',
        updated_at: '2026-05-20T12:05:00Z',
      },
      user_message: {
        id: 'message_user',
        session_id: 'session_1',
        role: 'user',
        content: 'Question',
        metadata: { turn_kind: 'chat_user' },
        created_at: '2026-05-20T12:00:00Z',
      },
      assistant_message: {
        id: 'message_assistant',
        session_id: 'session_1',
        role: 'assistant',
        content: 'Answer',
        metadata: { turn_kind: 'assistant' },
        created_at: '2026-05-20T12:01:00Z',
      },
      answer: 'Answer',
      sources: [],
      trace_id: 'trace_1',
    })

    const store = useChatStore()
    store.selectedWorkspaceId = 'workspace_1'
    store.selectedChatProfileId = 'profile_1'
    await store.submitMessage('Question')

    expect(sendChat).toHaveBeenCalledWith(
      expect.objectContaining({ apply_guidelines: true }),
    )
  })

  it('respects the chat guidelines toggle when disabled', async () => {
    const sendChat = vi.spyOn(chatApi, 'sendChat').mockResolvedValue({
      session: {
        id: 'session_1',
        title: 'Lake city',
        folder_id: null,
        workspace_id: 'workspace_1',
        created_at: '2026-05-20T12:00:00Z',
        updated_at: '2026-05-20T12:05:00Z',
      },
      user_message: {
        id: 'message_user',
        session_id: 'session_1',
        role: 'user',
        content: 'Question',
        metadata: { turn_kind: 'chat_user' },
        created_at: '2026-05-20T12:00:00Z',
      },
      assistant_message: {
        id: 'message_assistant',
        session_id: 'session_1',
        role: 'assistant',
        content: 'Answer',
        metadata: { turn_kind: 'assistant' },
        created_at: '2026-05-20T12:01:00Z',
      },
      answer: 'Answer',
      sources: [],
      trace_id: 'trace_1',
    })

    const store = useChatStore()
    store.selectedWorkspaceId = 'workspace_1'
    store.selectedChatProfileId = 'profile_1'
    store.applyGuidelinesChat = false
    await store.submitMessage('Question')

    expect(sendChat).toHaveBeenCalledWith(
      expect.objectContaining({ apply_guidelines: false }),
    )
  })
```

- [ ] **Step 2: Run the store tests to verify they fail**

Run: `bun run test src/features/chat/stores/chatStore.test.ts`
Expected: FAIL — `apply_guidelines` is not in the sent payload; `applyGuidelinesChat` is not a state field.

- [ ] **Step 3: Add the toggle flags to the store**

In `src/frontend/src/features/chat/stores/chatStore.ts`, add to the `ChatState` interface after `canvas: string;` (line 29):

```typescript
  applyGuidelinesChat: boolean;
  applyGuidelinesWrite: boolean;
  applyGuidelinesEditor: boolean;
```

Add to the `state` initializer after `canvas: "",` (line 48):

```typescript
    applyGuidelinesChat: true,
    applyGuidelinesWrite: true,
    applyGuidelinesEditor: true,
```

In `submitMessage`, add `apply_guidelines: this.applyGuidelinesChat,` to the `chatApi.sendChat({...})` call (after `cited_document_ids: reconciledIds,`, line 131):

```typescript
            apply_guidelines: this.applyGuidelinesChat,
```

and add `apply_guidelines: this.applyGuidelinesWrite,` to the `chatApi.sendWrite({...})` call (after `cited_document_ids: reconciledIds,`, line 154):

```typescript
            apply_guidelines: this.applyGuidelinesWrite,
```

- [ ] **Step 4: Run the store tests to verify they pass**

Run: `bun run test src/features/chat/stores/chatStore.test.ts`
Expected: PASS.

- [ ] **Step 5: Add the guidelines field to the workspace panel**

In `src/frontend/src/features/workspaces/components/WorkspacePanel.vue`:

Update the script import (line 2) to add `computed`:

```typescript
import { computed, onMounted, reactive, ref } from 'vue'
```

Add to the `WorkspaceForm` interface after `exclude_globs: string[]` (line 12):

```typescript
  guidelines: string
```

Add to the `form` initializer after `exclude_globs: [...]` (line 22):

```typescript
  guidelines: '',
```

Add the soft-limit constant and computed after the `form` declaration (after line 23):

```typescript
// Soft ceiling only. At the default retrieval limit, sources already inject
// ~9000 chars of canon into the prompt; keeping guidelines under ~a quarter of
// that leaves room for the grounding the answer must use, and stays safe on the
// small-context local models this project targets. Advisory — a longer style
// bible is still allowed; we only warn.
const GUIDELINES_SOFT_LIMIT_CHARS = 2000

const guidelinesTooLong = computed(
  () => form.guidelines.length > GUIDELINES_SOFT_LIMIT_CHARS,
)
```

In `edit()`, copy the field after `form.exclude_globs = [...workspace.exclude_globs]` (line 32):

```typescript
  form.guidelines = workspace.guidelines ?? ''
```

In `save()`, send the field inside the payload object after `exclude_globs: form.exclude_globs,` (line 41):

```typescript
      guidelines: form.guidelines,
```

In the template, add a new field after the Exclude globs `panel-field` block (after line 148, before the error `v-alert`):

```html
      <div class="panel-field">
        <label class="calliope-eyebrow panel-field__label">Guidelines</label>
        <v-textarea
          v-model="form.guidelines"
          :rows="4"
          auto-grow
          hide-details
          placeholder="Standing context for every response in this workspace — e.g. “this is a dark fantasy world.”"
        />
        <span class="panel-field__hint">
          Injected into chat, write, and editor prompts for this workspace. Toggle
          per request in the composer.
        </span>
        <v-alert
          v-if="guidelinesTooLong"
          type="warning"
          variant="tonal"
          density="compact"
          class="panel-alert"
        >
          {{ form.guidelines.length }} characters — long guidelines crowd out
          retrieved canon and may weaken grounding on small-context models. You can
          still save.
        </v-alert>
      </div>
```

- [ ] **Step 6: Verify type-check and the workspace + store tests**

Run: `bun run typecheck`
Expected: PASS (the `save()` payload now includes `guidelines`, closing the Task 8 gap).

Run: `bun run test src/features/chat/stores/chatStore.test.ts`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/features/chat/stores/chatStore.ts src/frontend/src/features/workspaces/components/WorkspacePanel.vue src/frontend/src/features/chat/stores/chatStore.test.ts
git commit -m "feat: workspace guidelines editor field and chat-store toggle flags"
```

---

## Task 10: Composer toggle

**Files:**
- Modify: `src/frontend/src/features/chat/components/ComposerBar.vue`
- Modify (test): `src/frontend/src/features/chat/components/ComposerBar.test.ts`

- [ ] **Step 1: Write the failing component tests**

In `src/frontend/src/features/chat/components/ComposerBar.test.ts`, append two tests inside the `describe('ComposerBar', ...)` block (before its closing `})`):

```typescript
  it('shows the guidelines toggle when the selected workspace has guidelines', () => {
    const wrapper = mount(ComposerBar, {
      props: {
        mode: 'chat',
        policy: 'strict_canon',
        selectedWorkspaceId: 'workspace_1',
        selectedChatProfileId: 'profile_1',
        workspaces: [
          {
            id: 'workspace_1',
            name: 'World',
            root_path: '/tmp/world',
            include_globs: [],
            exclude_globs: [],
            created_at: '2026-05-20T12:00:00Z',
            guidelines: 'This is a dark fantasy world.',
          },
        ],
        profiles: [],
        pending: false,
        disabled: false,
      },
    })

    expect(wrapper.find('[data-test="guidelines-toggle"]').exists()).toBe(true)
  })

  it('hides the guidelines toggle when the workspace has no guidelines', () => {
    const wrapper = mount(ComposerBar, {
      props: {
        mode: 'chat',
        policy: 'strict_canon',
        selectedWorkspaceId: 'workspace_1',
        selectedChatProfileId: 'profile_1',
        workspaces: [
          {
            id: 'workspace_1',
            name: 'World',
            root_path: '/tmp/world',
            include_globs: [],
            exclude_globs: [],
            created_at: '2026-05-20T12:00:00Z',
            guidelines: null,
          },
        ],
        profiles: [],
        pending: false,
        disabled: false,
      },
    })

    expect(wrapper.find('[data-test="guidelines-toggle"]').exists()).toBe(false)
  })
```

- [ ] **Step 2: Run the component tests to verify they fail**

Run: `bun run test src/features/chat/components/ComposerBar.test.ts`
Expected: FAIL — no element matches `[data-test="guidelines-toggle"]`.

- [ ] **Step 3: Add the toggle logic to the script**

In `src/frontend/src/features/chat/components/ComposerBar.vue`, add after the `chat` store declaration (after line 31, `const chat = useChatStore();`):

```typescript
const selectedWorkspaceGuidelines = computed<string | null>(() => {
  const ws = props.workspaces.find((w) => w.id === props.selectedWorkspaceId);
  return ws?.guidelines ?? null;
});

// Only meaningful when the workspace actually has guidelines and the mode
// generates text — search performs retrieval only, with no system prompt.
const guidelinesAvailable = computed<boolean>(
  () =>
    props.mode !== "search" &&
    (selectedWorkspaceGuidelines.value?.trim().length ?? 0) > 0,
);

// Chat and write keep independent toggles; proxy to the active surface's flag.
const applyGuidelines = computed<boolean>({
  get: () =>
    props.mode === "write"
      ? chat.applyGuidelinesWrite
      : chat.applyGuidelinesChat,
  set: (value) => {
    if (props.mode === "write") {
      chat.applyGuidelinesWrite = value;
    } else {
      chat.applyGuidelinesChat = value;
    }
  },
});
```

(`computed` is already imported on line 2; `Workspace` is already imported on line 7.)

- [ ] **Step 4: Add the toggle button to the template**

In the `.composer__pills` block, add this immediately after the closing `</div>` of `.composer__policy` (after line 334, before the workspace `<v-select>`):

```html
          <v-tooltip
            v-if="guidelinesAvailable"
            :text="
              applyGuidelines
                ? 'Workspace guidelines: applied'
                : 'Workspace guidelines: ignored'
            "
            location="top"
            :open-delay="120"
            max-width="252"
          >
            <template #activator="{ props: tipProps }">
              <button
                v-bind="tipProps"
                type="button"
                class="composer__guidelines-toggle"
                :class="{ 'is-active': applyGuidelines }"
                role="switch"
                :aria-checked="applyGuidelines"
                aria-label="Apply workspace guidelines"
                data-test="guidelines-toggle"
                @click="applyGuidelines = !applyGuidelines"
              >
                <v-icon icon="$mdi-script-text-outline" size="17" />
              </button>
            </template>
          </v-tooltip>
```

- [ ] **Step 5: Add the toggle styles**

In the `<style scoped>` block, add after the `.composer__policy-seg.is-active { ... }` rule (after line 551), mirroring the existing policy-segment styling:

```css
.composer__guidelines-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 26px;
  padding: 0;
  background: var(--calliope-ink);
  border: 1px solid var(--calliope-border-strong);
  border-radius: var(--calliope-radius-pill);
  color: var(--calliope-paper-dim);
  cursor: pointer;
  flex: none;
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out),
    box-shadow var(--calliope-duration-fast) var(--calliope-ease-out);
}

.composer__guidelines-toggle:hover {
  color: var(--calliope-paper);
}

.composer__guidelines-toggle:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--calliope-bronze-veil);
}

.composer__guidelines-toggle.is-active {
  background: var(--calliope-bronze);
  color: var(--calliope-ink);
  box-shadow: 0 0 9px 1px var(--calliope-bronze-glow);
}
```

- [ ] **Step 6: Run the component tests + type-check to verify they pass**

Run: `bun run test src/features/chat/components/ComposerBar.test.ts`
Expected: PASS (including the pre-existing citation test).

Run: `bun run typecheck`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/features/chat/components/ComposerBar.vue src/frontend/src/features/chat/components/ComposerBar.test.ts
git commit -m "feat: add per-request guidelines toggle to the composer"
```

---

## Task 11: Editor panel toggle

**Files:**
- Modify: `src/frontend/src/features/editor/components/EditorPanel.vue`

- [ ] **Step 1: Add the availability computed and pass the flag**

In `src/frontend/src/features/editor/components/EditorPanel.vue`, add after the `workspaceRoot` computed (after line 36):

```typescript
const guidelinesAvailable = computed<boolean>(
  () => (workspace.selectedWorkspace?.guidelines?.trim().length ?? 0) > 0,
);
```

In `propose()`, add the flag to the `proposeEdit({...})` call (after `chat_profile_id: chat.selectedChatProfileId,`, line 79):

```typescript
      apply_guidelines: chat.applyGuidelinesEditor,
```

- [ ] **Step 2: Add the toggle control to the template**

Add this section immediately after the Instruction `editor-panel__section` block (after line 214, before the "Select a chat profile" alert section):

```html
        <div v-if="guidelinesAvailable" class="editor-panel__section">
          <label class="editor-panel__guidelines">
            <input
              v-model="chat.applyGuidelinesEditor"
              type="checkbox"
              class="editor-panel__guidelines-box"
            />
            <span class="calliope-eyebrow">Apply workspace guidelines</span>
          </label>
        </div>
```

- [ ] **Step 3: Add minimal styles for the control**

In the `<style scoped>` block, add after the `.editor-panel__label { ... }` rule (after line 424):

```css
.editor-panel__guidelines {
  display: inline-flex;
  align-items: center;
  gap: var(--calliope-space-xs);
  cursor: pointer;
}

.editor-panel__guidelines-box {
  accent-color: var(--calliope-bronze);
  cursor: pointer;
}
```

- [ ] **Step 4: Verify type-check and the full frontend suite**

Run: `bun run typecheck`
Expected: PASS.

Run: `bun run test`
Expected: PASS (whole vitest suite).

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/features/editor/components/EditorPanel.vue
git commit -m "feat: add guidelines toggle to the editor panel"
```

---

## Final verification

- [ ] **Backend:** from repo root, `uv run pytest tests/ -q` → all green.
- [ ] **Frontend type-check:** from `src/frontend`, `bun run typecheck` → no errors.
- [ ] **Frontend tests:** from `src/frontend`, `bun run test` → all green.
- [ ] **Manual smoke (optional):** create/edit a workspace, set guidelines >2000 chars → warning shows, save still works; in the composer the script-text toggle appears only when the selected workspace has guidelines and the mode is chat/write; toggling it off for one request omits the guidelines from that generation.

## Notes on scope and DRY

- The conversation-title builder is intentionally untouched (per spec §2).
- Both editor workspace lookups (sources + guidelines) are independent best-effort calls; the workspaces table is tiny, so the duplicate lookup is acceptable and keeps the two concerns cleanly separated (spec §5.2).
- The toggle flags live in the existing chat Pinia store as session state — consistent with `policy`/`mode`; no new persistence layer (spec §5.3).
