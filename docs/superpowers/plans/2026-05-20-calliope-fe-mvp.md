# Calliope Frontend MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Vue 3 frontend for Calliope backed by the frontend-facing FastAPI/session/folder/profile/workspace APIs required by the MVP specs.

**Architecture:** Move the Python package to `src/backend/calliope` while preserving the import name `calliope`, then extend the backend with session detail/listing, conversation folders, persisted search turns, explicit chat profile selection, and settings mutation APIs. Add `src/frontend` as a typed Vue 3/Vite/Vuetify/Pinia app that talks only to the backend over HTTP and covers chat, search, folders, profile settings, workspace settings, and synchronous reindexing.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic, PostgreSQL/pgvector, pytest, pyright, ruff, Vue 3, TypeScript, Vite, Bun, Vuetify 3, Pinia, Vitest, Vue Test Utils.

---

## Scope Notes

This is one integrated MVP plan, not two independent plans, because the frontend acceptance criteria depend on the backend API annex. Execute backend tasks first so the frontend can target stable response shapes. Keep each task in its own commit.

## File Structure

Backend package move:

- Move `src/calliope/` to `src/backend/calliope/`.
- Modify `pyproject.toml` so hatch, pytest, and pyright point at `src/backend`.
- Keep imports as `calliope...`; no Python module names change.

Backend model/API additions:

- Modify `src/backend/calliope/db/models.py` for `ConversationFolder`, `ChatSession.folder_id`, and `updated_at` support on mutable records where needed.
- Modify `alembic/versions/0001_initial.py` because this project currently has one initial migration and tests apply migrations from scratch.
- Modify `src/backend/calliope/domain/schemas.py` for patch/read request and response models.
- Modify `src/backend/calliope/repositories/chats.py` for session list/detail/update/delete and folder CRUD.
- Create `src/backend/calliope/repositories/conversation_folders.py` only if `chats.py` grows hard to scan; otherwise keep folder persistence near chat session persistence.
- Modify `src/backend/calliope/services/chat.py` and `src/backend/calliope/services/search.py` for frontend response shapes and persisted search messages.
- Modify `src/backend/calliope/api/dependencies.py`, `api/routes/chat.py`, `api/routes/search.py`, `api/routes/sessions.py`, `api/routes/profiles.py`, and `api/routes/workspaces.py`.

Backend tests:

- Modify `tests/conftest.py` only if path assumptions break after the package move.
- Modify `tests/integration/test_repositories.py`, `tests/integration/test_api_contract.py`, `tests/integration/test_chat_service.py`, `tests/integration/test_search_service.py`, and `tests/integration/test_profiles.py`.
- Add `tests/integration/test_conversation_folders.py`.
- Add `tests/integration/test_sessions_api.py`.
- Add `tests/integration/test_workspace_profile_mutations.py`.

Frontend app:

- Create `src/frontend/package.json`, `bun.lock`, `vite.config.ts`, `tsconfig.json`, `tsconfig.node.json`, `index.html`, and `src/frontend/src/`.
- Create `src/frontend/src/app/App.vue`, `main.ts`, `vuetify.ts`, and `router.ts`.
- Create `src/frontend/src/shared/api/client.ts` and `errors.ts`.
- Create typed feature modules under `features/chat`, `features/profiles`, `features/workspaces`, and `features/settings`.
- Component tests live next to feature tests under `src/frontend/src/**/*.test.ts`.

## Tasks

### Task 1: Move Python Package Under `src/backend`

**Files:**
- Move: `src/calliope` -> `src/backend/calliope`
- Modify: `pyproject.toml`
- Test: `tests/unit/test_settings.py`

- [ ] **Step 1: Move the package directory**

Run:

```bash
rtk mkdir -p src/backend
rtk mv src/calliope src/backend/calliope
```

Expected: `src/backend/calliope/__init__.py` exists and `src/calliope` no longer exists.

- [ ] **Step 2: Update Python package configuration**

Change `pyproject.toml` to:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/backend/calliope"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src/backend"]

[tool.pyright]
include = ["src/backend", "tests"]
pythonVersion = "3.12"
typeCheckingMode = "basic"
```

- [ ] **Step 3: Verify imports fail before any test edits are needed**

Run:

```bash
rtk uv run pytest tests/unit/test_settings.py -q
```

Expected: PASS. If it fails with `ModuleNotFoundError: calliope`, re-check `pythonpath = ["src/backend"]`.

- [ ] **Step 4: Run backend static checks for move fallout**

Run:

```bash
rtk uv run ruff check .
rtk uv run pyright
```

Expected: both PASS or only report issues unrelated to import paths. Fix import-path issues before continuing.

- [ ] **Step 5: Commit**

```bash
rtk git add pyproject.toml src/backend tests
rtk git add -u src
rtk git commit -m "chore: move backend package under src/backend"
```

### Task 2: Add Conversation Folder Schema And Metadata Reads

**Files:**
- Modify: `src/backend/calliope/db/models.py`
- Modify: `src/backend/calliope/domain/schemas.py`
- Modify: `alembic/versions/0001_initial.py`
- Modify: `tests/integration/test_repositories.py`

- [ ] **Step 1: Write failing metadata and schema tests**

Append to `tests/integration/test_repositories.py`:

```python
def test_metadata_contains_frontend_conversation_folder_tables() -> None:
    assert "conversation_folders" in Base.metadata.tables
    chat_sessions = Base.metadata.tables["chat_sessions"]
    assert "folder_id" in chat_sessions.columns


def test_deleting_folder_unfiles_sessions(db_session) -> None:
    from calliope.db.models import ConversationFolder

    folder = ConversationFolder(name="Act I", position=0)
    session = ChatSession(title="Scene", folder=folder)
    db_session.add_all([folder, session])
    db_session.commit()

    db_session.delete(folder)
    db_session.commit()
    db_session.refresh(session)

    assert session.folder_id is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
rtk uv run pytest tests/integration/test_repositories.py::test_metadata_contains_frontend_conversation_folder_tables tests/integration/test_repositories.py::test_deleting_folder_unfiles_sessions -q
```

Expected: FAIL because `ConversationFolder` and `chat_sessions.folder_id` do not exist.

- [ ] **Step 3: Add ORM model fields**

In `src/backend/calliope/db/models.py`, import `UniqueConstraint` if needed and add:

```python
class ConversationFolder(Base):
    __tablename__ = "conversation_folders"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("folder"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversation_folders.id", ondelete="CASCADE"),
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    parent: Mapped["ConversationFolder | None"] = relationship(
        remote_side="ConversationFolder.id",
        back_populates="children",
    )
    children: Mapped[list["ConversationFolder"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    sessions: Mapped[list["ChatSession"]] = relationship(back_populates="folder")
```

Then add to `ChatSession`:

```python
    folder_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversation_folders.id", ondelete="SET NULL"),
    )

    folder: Mapped[ConversationFolder | None] = relationship(back_populates="sessions")
```

- [ ] **Step 4: Add Pydantic schemas**

In `src/backend/calliope/domain/schemas.py`, add:

```python
class ConversationFolderCreate(BaseModel):
    name: str
    parent_id: str | None = None
    position: int = 0


class ConversationFolderPatch(BaseModel):
    name: str | None = None
    parent_id: str | None = None
    position: int | None = None


class ConversationFolderRead(BaseModel):
    id: str
    name: str
    parent_id: str | None
    position: int
    created_at: datetime
    updated_at: datetime
```

Change `SessionRead` to:

```python
class SessionSummary(BaseModel):
    id: str
    title: str | None
    folder_id: str | None
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    metadata: dict[str, Any]
    created_at: datetime


class SessionDetail(SessionSummary):
    messages: list[MessageRead]


class SessionPatch(BaseModel):
    title: str | None = None
    folder_id: str | None = None
```

If `SessionRead` is still imported elsewhere, temporarily alias it:

```python
SessionRead = SessionSummary
```

- [ ] **Step 5: Update initial Alembic migration**

In `alembic/versions/0001_initial.py`, create `conversation_folders` before `chat_sessions`:

```python
    op.create_table(
        "conversation_folders",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.String()),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["parent_id"], ["conversation_folders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
```

Add `folder_id` to `chat_sessions`:

```python
        sa.Column("folder_id", sa.String()),
        sa.ForeignKeyConstraint(["folder_id"], ["conversation_folders.id"], ondelete="SET NULL"),
```

In `downgrade()`, drop `conversation_folders` after `chat_sessions`:

```python
    op.drop_table("chat_sessions")
    op.drop_table("conversation_folders")
```

- [ ] **Step 6: Run tests**

Run:

```bash
rtk uv run pytest tests/integration/test_repositories.py::test_metadata_contains_frontend_conversation_folder_tables tests/integration/test_repositories.py::test_deleting_folder_unfiles_sessions -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
rtk git add src/backend/calliope/db/models.py src/backend/calliope/domain/schemas.py alembic/versions/0001_initial.py tests/integration/test_repositories.py
rtk git commit -m "feat: add conversation folder schema"
```

### Task 3: Implement Folder CRUD With Cycle Rejection

**Files:**
- Modify: `src/backend/calliope/repositories/chats.py`
- Modify: `src/backend/calliope/api/routes/sessions.py`
- Add: `tests/integration/test_conversation_folders.py`
- Modify: `tests/integration/test_api_contract.py`

- [ ] **Step 1: Write failing repository tests**

Create `tests/integration/test_conversation_folders.py`:

```python
from calliope.domain.errors import AppError
from calliope.domain.schemas import ConversationFolderCreate, ConversationFolderPatch
from calliope.repositories.chats import ChatRepository


def test_folder_repository_creates_lists_updates_and_deletes(db_session) -> None:
    repo = ChatRepository(db_session)
    parent = repo.create_folder(ConversationFolderCreate(name="Worldbuilding", position=0))
    child = repo.create_folder(
        ConversationFolderCreate(name="Act I", parent_id=parent.id, position=1)
    )

    listed = repo.list_folders()
    assert [folder.name for folder in listed] == ["Worldbuilding", "Act I"]
    assert listed[1].parent_id == parent.id

    updated = repo.update_folder(
        child.id,
        ConversationFolderPatch(name="Act II", parent_id=None, position=2),
    )
    assert updated.name == "Act II"
    assert updated.parent_id is None
    assert updated.position == 2

    repo.delete_folder(parent.id)
    assert [folder.id for folder in repo.list_folders()] == [child.id]


def test_folder_repository_rejects_cycles(db_session) -> None:
    repo = ChatRepository(db_session)
    parent = repo.create_folder(ConversationFolderCreate(name="Parent", position=0))
    child = repo.create_folder(ConversationFolderCreate(name="Child", parent_id=parent.id))

    try:
        repo.update_folder(parent.id, ConversationFolderPatch(parent_id=child.id))
    except AppError as exc:
        assert exc.code == "conversation_folder_cycle"
        assert exc.status_code == 400
        assert exc.details == {"folder_id": parent.id, "parent_id": child.id}
    else:
        raise AssertionError("expected AppError")


def test_folder_repository_rejects_missing_parent(db_session) -> None:
    repo = ChatRepository(db_session)

    try:
        repo.create_folder(ConversationFolderCreate(name="Child", parent_id="folder_missing"))
    except AppError as exc:
        assert exc.code == "conversation_folder_invalid_parent"
        assert exc.status_code == 400
    else:
        raise AssertionError("expected AppError")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
rtk uv run pytest tests/integration/test_conversation_folders.py -q
```

Expected: FAIL because `ChatRepository.create_folder` is missing.

- [ ] **Step 3: Implement folder repository methods**

In `src/backend/calliope/repositories/chats.py`, import `select` and folder schemas, then add:

```python
    def list_folders(self) -> list[ConversationFolderRead]:
        folders = self.session.scalars(
            select(ConversationFolder).order_by(
                ConversationFolder.parent_id.nullsfirst(),
                ConversationFolder.position,
                ConversationFolder.created_at,
                ConversationFolder.id,
            )
        ).all()
        return [self._folder_to_read(folder) for folder in folders]

    def create_folder(self, payload: ConversationFolderCreate) -> ConversationFolderRead:
        self._ensure_valid_parent(payload.parent_id, moving_folder_id=None)
        folder = ConversationFolder(
            name=payload.name,
            parent_id=payload.parent_id,
            position=payload.position,
        )
        self.session.add(folder)
        self.session.commit()
        self.session.refresh(folder)
        return self._folder_to_read(folder)

    def update_folder(
        self,
        folder_id: str,
        payload: ConversationFolderPatch,
    ) -> ConversationFolderRead:
        folder = self._get_folder_row(folder_id)
        if payload.name is not None:
            folder.name = payload.name
        if payload.parent_id is not None:
            self._ensure_valid_parent(payload.parent_id, moving_folder_id=folder_id)
            folder.parent_id = payload.parent_id
        elif "parent_id" in payload.model_fields_set:
            folder.parent_id = None
        if payload.position is not None:
            folder.position = payload.position
        self.session.commit()
        self.session.refresh(folder)
        return self._folder_to_read(folder)

    def delete_folder(self, folder_id: str) -> None:
        folder = self._get_folder_row(folder_id)
        self.session.delete(folder)
        self.session.commit()

    def _get_folder_row(self, folder_id: str) -> ConversationFolder:
        folder = self.session.get(ConversationFolder, folder_id)
        if folder is None:
            raise AppError(
                code="conversation_folder_not_found",
                message="Conversation folder not found.",
                status_code=404,
                details={"folder_id": folder_id},
            )
        return folder

    def _ensure_valid_parent(
        self,
        parent_id: str | None,
        *,
        moving_folder_id: str | None,
    ) -> None:
        if parent_id is None:
            return
        if parent_id == moving_folder_id:
            raise AppError(
                code="conversation_folder_cycle",
                message="Conversation folder cannot be its own parent.",
                status_code=400,
                details={"folder_id": moving_folder_id, "parent_id": parent_id},
            )
        parent = self.session.get(ConversationFolder, parent_id)
        if parent is None:
            raise AppError(
                code="conversation_folder_invalid_parent",
                message="Conversation folder parent does not exist.",
                status_code=400,
                details={"parent_id": parent_id},
            )
        while parent is not None:
            if parent.id == moving_folder_id:
                raise AppError(
                    code="conversation_folder_cycle",
                    message="Conversation folder parent would create a cycle.",
                    status_code=400,
                    details={"folder_id": moving_folder_id, "parent_id": parent_id},
                )
            parent = parent.parent

    @staticmethod
    def _folder_to_read(folder: ConversationFolder) -> ConversationFolderRead:
        return ConversationFolderRead(
            id=folder.id,
            name=folder.name,
            parent_id=folder.parent_id,
            position=folder.position,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
        )
```

- [ ] **Step 4: Add route tests**

Append to `tests/integration/test_api_contract.py`:

```python
def test_openapi_contains_conversation_folder_routes() -> None:
    client = TestClient(create_app(Settings(api_title="Calliope", **SETTINGS_WITHOUT_ENV_FILE)))

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert {"get", "post"} <= set(paths["/v1/conversation-folders"])
    assert {"patch", "delete"} <= set(paths["/v1/conversation-folders/{folder_id}"])
```

- [ ] **Step 5: Add folder routes**

In `src/backend/calliope/api/routes/sessions.py`, add imports and route functions:

```python
from fastapi import Response, status
from calliope.domain.schemas import (
    ConversationFolderCreate,
    ConversationFolderPatch,
    ConversationFolderRead,
)


@router.get("/v1/conversation-folders", response_model=list[ConversationFolderRead])
def list_conversation_folders(
    session: Annotated[Session, Depends(get_db_session)],
) -> list[ConversationFolderRead]:
    return ChatRepository(session).list_folders()


@router.post(
    "/v1/conversation-folders",
    response_model=ConversationFolderRead,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation_folder(
    payload: ConversationFolderCreate,
    session: Annotated[Session, Depends(get_db_session)],
) -> ConversationFolderRead:
    return ChatRepository(session).create_folder(payload)


@router.patch("/v1/conversation-folders/{folder_id}", response_model=ConversationFolderRead)
def update_conversation_folder(
    folder_id: str,
    payload: ConversationFolderPatch,
    session: Annotated[Session, Depends(get_db_session)],
) -> ConversationFolderRead:
    return ChatRepository(session).update_folder(folder_id, payload)


@router.delete("/v1/conversation-folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation_folder(
    folder_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    ChatRepository(session).delete_folder(folder_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 6: Run tests**

Run:

```bash
rtk uv run pytest tests/integration/test_conversation_folders.py tests/integration/test_api_contract.py::test_openapi_contains_conversation_folder_routes -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
rtk git add src/backend/calliope/repositories/chats.py src/backend/calliope/api/routes/sessions.py tests/integration/test_conversation_folders.py tests/integration/test_api_contract.py
rtk git commit -m "feat: add conversation folder api"
```

### Task 4: Implement Session List, Detail, Patch, And Delete

**Files:**
- Modify: `src/backend/calliope/repositories/chats.py`
- Modify: `src/backend/calliope/api/routes/sessions.py`
- Add: `tests/integration/test_sessions_api.py`
- Modify: `tests/integration/test_api_contract.py`

- [ ] **Step 1: Write failing repository tests**

Create `tests/integration/test_sessions_api.py`:

```python
from fastapi.testclient import TestClient

from calliope.api.app import create_app
from calliope.config import Settings
from calliope.db.models import ChatMessage, ChatSession
from calliope.domain.schemas import ConversationFolderCreate, SessionPatch
from calliope.repositories.chats import ChatRepository

SETTINGS_WITHOUT_ENV_FILE = {"_env_file": None}


def test_session_repository_lists_details_patches_and_deletes(db_session) -> None:
    repo = ChatRepository(db_session)
    folder = repo.create_folder(ConversationFolderCreate(name="Filed"))
    first = repo.create_session(title="First")
    second = repo.create_session(title="Second")
    repo.add_message(first.id, "user", "Question", {"turn_kind": "chat_user"})
    repo.add_message(first.id, "assistant", "Answer", {"turn_kind": "assistant"})
    db_session.commit()

    patched = repo.update_session(first.id, SessionPatch(title="Renamed", folder_id=folder.id))
    assert patched.title == "Renamed"
    assert patched.folder_id == folder.id

    summaries = repo.list_sessions()
    assert {session.id for session in summaries} == {first.id, second.id}
    assert repo.list_sessions(folder_id=folder.id)[0].id == first.id

    detail = repo.get_session_detail(first.id)
    assert detail.folder_id == folder.id
    assert [message.role for message in detail.messages] == ["user", "assistant"]
    assert detail.messages[0].metadata == {"turn_kind": "chat_user"}

    repo.delete_session(first.id)
    assert db_session.get(ChatSession, first.id) is None
    assert db_session.query(ChatMessage).filter_by(session_id=first.id).count() == 0


def test_sessions_routes_openapi_shape() -> None:
    client = TestClient(create_app(Settings(api_title="Calliope", **SETTINGS_WITHOUT_ENV_FILE)))

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert {"get"} <= set(paths["/v1/sessions"])
    assert {"get", "patch", "delete"} <= set(paths["/v1/sessions/{session_id}"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
rtk uv run pytest tests/integration/test_sessions_api.py -q
```

Expected: FAIL because session list/detail/update/delete methods are missing or the route shape is old.

- [ ] **Step 3: Implement session repository methods**

In `src/backend/calliope/repositories/chats.py`, add:

```python
    def list_sessions(self, folder_id: str | None = None) -> list[SessionSummary]:
        statement = select(ChatSession).order_by(ChatSession.updated_at.desc(), ChatSession.id)
        if folder_id is not None:
            statement = statement.where(ChatSession.folder_id == folder_id)
        sessions = self.session.scalars(statement).all()
        return [self._session_to_summary(chat_session) for chat_session in sessions]

    def get_session_detail(self, session_id: str) -> SessionDetail:
        chat_session = self.get_session_row(session_id)
        messages = sorted(chat_session.messages, key=lambda message: message.created_at)
        return SessionDetail(
            id=chat_session.id,
            title=chat_session.title,
            folder_id=chat_session.folder_id,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at,
            messages=[self._message_to_read(message) for message in messages],
        )

    def update_session(self, session_id: str, payload: SessionPatch) -> SessionSummary:
        chat_session = self.get_session_row(session_id)
        if payload.title is not None:
            chat_session.title = payload.title
        if payload.folder_id is not None:
            self._get_folder_row(payload.folder_id)
            chat_session.folder_id = payload.folder_id
        elif "folder_id" in payload.model_fields_set:
            chat_session.folder_id = None
        self.session.commit()
        self.session.refresh(chat_session)
        return self._session_to_summary(chat_session)

    def delete_session(self, session_id: str) -> None:
        chat_session = self.get_session_row(session_id)
        self.session.delete(chat_session)
        self.session.commit()

    @staticmethod
    def _session_to_summary(chat_session: ChatSession) -> SessionSummary:
        return SessionSummary(
            id=chat_session.id,
            title=chat_session.title,
            folder_id=chat_session.folder_id,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at,
        )

    @staticmethod
    def _message_to_read(message: ChatMessage) -> MessageRead:
        return MessageRead(
            id=message.id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            metadata=message.metadata_json,
            created_at=message.created_at,
        )
```

Update the old `get_session()` method to return `SessionDetail` or remove it after updating routes.

- [ ] **Step 4: Replace session routes**

In `src/backend/calliope/api/routes/sessions.py`, use:

```python
@router.get("/v1/sessions", response_model=list[SessionSummary])
def list_sessions(
    session: Annotated[Session, Depends(get_db_session)],
    folder_id: str | None = None,
) -> list[SessionSummary]:
    return ChatRepository(session).list_sessions(folder_id=folder_id)


@router.get("/v1/sessions/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> SessionDetail:
    return ChatRepository(session).get_session_detail(session_id)


@router.patch("/v1/sessions/{session_id}", response_model=SessionSummary)
def update_session(
    session_id: str,
    payload: SessionPatch,
    session: Annotated[Session, Depends(get_db_session)],
) -> SessionSummary:
    return ChatRepository(session).update_session(session_id, payload)


@router.delete("/v1/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    ChatRepository(session).delete_session(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 5: Update API contract test expectations**

In `tests/integration/test_api_contract.py`, update expected paths:

```python
expected_paths = {
    "/v1/workspaces",
    "/v1/reindex",
    "/v1/search",
    "/v1/chat",
    "/v1/profiles",
    "/v1/documents",
    "/v1/sources/{chunk_id}",
    "/v1/sessions",
    "/v1/sessions/{session_id}",
    "/v1/conversation-folders",
    "/v1/conversation-folders/{folder_id}",
}
```

And assert:

```python
assert "get" in paths["/v1/sessions"]
assert {"get", "patch", "delete"} <= set(paths["/v1/sessions/{session_id}"])
```

- [ ] **Step 6: Run tests**

Run:

```bash
rtk uv run pytest tests/integration/test_sessions_api.py tests/integration/test_api_contract.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
rtk git add src/backend/calliope/repositories/chats.py src/backend/calliope/api/routes/sessions.py tests/integration/test_sessions_api.py tests/integration/test_api_contract.py
rtk git commit -m "feat: add frontend session api"
```

### Task 5: Add Explicit Chat Profile Selection And Frontend Chat Response Shape

**Files:**
- Modify: `src/backend/calliope/domain/schemas.py`
- Modify: `src/backend/calliope/api/dependencies.py`
- Modify: `src/backend/calliope/api/routes/chat.py`
- Modify: `src/backend/calliope/services/chat.py`
- Modify: `tests/integration/test_chat_service.py`
- Modify: `tests/integration/test_api_contract.py`

- [ ] **Step 1: Write failing chat service test**

Append to `tests/integration/test_chat_service.py`:

```python
def test_chat_service_persists_frontend_messages_and_returns_session_payload(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_vector_search(self, embedding, *, workspace_id, limit):
        return ["chunk_a"]

    def fake_lexical_search(self, query, *, workspace_id, limit):
        return ["chunk_a"]

    def fake_source_for_chunk(self, chunk_id, score=1.0):
        return SourceReference(
            document_id="document_a",
            chunk_id=chunk_id,
            path="characters/kaelen.md",
            heading="Kaelen",
            excerpt="Kaelen exile",
            score=score,
        )

    monkeypatch.setattr(HybridRetriever, "_vector_search", fake_vector_search)
    monkeypatch.setattr(HybridRetriever, "_lexical_search", fake_lexical_search)
    monkeypatch.setattr(ChunkRepository, "source_for_chunk", fake_source_for_chunk)

    service = ChatService(db_session, embedding_client=FakeEmbeddingClient(), chat_client=FakeChatClient())
    try:
        response = service.chat(
            ChatRequest(
                message="Where was Kaelen exiled from?",
                chat_profile_id="profile_chat",
                limit=1,
            )
        )
    finally:
        service.close()

    assert response.session.id.startswith("session_")
    assert response.user_message.metadata == {"turn_kind": "chat_user"}
    assert response.assistant_message.metadata["turn_kind"] == "assistant"
    assert response.assistant_message.metadata["chat_profile_id"] == "profile_chat"
    assert response.assistant_message.metadata["source_count"] == 1
    assert response.sources[0].path == "characters/kaelen.md"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
rtk uv run pytest tests/integration/test_chat_service.py::test_chat_service_persists_frontend_messages_and_returns_session_payload -q
```

Expected: FAIL because `ChatRequest.chat_profile_id` and response session/message fields are missing.

- [ ] **Step 3: Update schemas**

In `src/backend/calliope/domain/schemas.py`, change:

```python
class ChatRequest(BaseModel):
    message: str
    policy: CanonPolicy = CanonPolicy.STRICT_CANON
    session_id: str | None = None
    workspace_id: str | None = None
    chat_profile_id: str | None = None
    limit: int = Field(default=8, ge=1, le=50)


class ChatResponse(BaseModel):
    session: SessionSummary
    user_message: MessageRead
    assistant_message: MessageRead
    answer: str
    sources: list[SourceReference]
    trace_id: str
```

- [ ] **Step 4: Add dependency helper for profile id**

In `src/backend/calliope/api/dependencies.py`, add:

```python
def get_chat_client_for_profile(
    session: Session,
    profile_id: str | None,
) -> OpenAICompatibleClient:
    if profile_id is None:
        return get_chat_client(session)
    profile = ProfileService(session).require_capability_by_id(
        profile_id,
        ProfileCapability.CHAT,
    )
    return OpenAICompatibleClient(
        base_url=profile.base_url,
        model=profile.model,
        api_key=api_key_for(profile),
    )
```

This requires adding `require_capability_by_id()` in `ProfileService` and `get_by_id()` in `ProfileRepository`:

```python
def get_by_id(self, profile_id: str) -> ProfileRead:
    profile = self.session.get(ConnectionProfile, profile_id)
    if profile is None:
        raise AppError(
            code="connection_profile_not_found",
            message="Connection profile not found.",
            status_code=404,
            details={"profile_id": profile_id},
        )
    return self._to_read(profile)
```

- [ ] **Step 5: Use profile id in chat route**

In `src/backend/calliope/api/routes/chat.py`, replace `get_chat_client(session)` with:

```python
chat_client: ChatClient = get_chat_client_for_profile(session, request.chat_profile_id)
```

- [ ] **Step 6: Persist frontend metadata and response fields**

In `ChatService.chat()`, replace message persistence with:

```python
user_message = repository.add_message(
    session_id=session_id,
    role="user",
    content=request.message,
    metadata={"turn_kind": "chat_user"},
)
assistant_message = repository.add_message(
    session_id=session_id,
    role="assistant",
    content=answer,
    metadata={
        "turn_kind": "assistant",
        "policy": request.policy.value,
        "chat_profile_id": request.chat_profile_id,
        "source_count": len(search_response.sources),
        "sources": [source.model_dump(mode="json") for source in search_response.sources],
    },
)
trace = repository.add_trace(
    session_id=session_id,
    message_id=assistant_message.id,
    query=request.message,
    policy=request.policy,
    sources=search_response.sources,
    scores={source.chunk_id: source.score for source in search_response.sources},
)
```

Return:

```python
return ChatResponse(
    session=repository.get_session_summary(session_id),
    user_message=repository._message_to_read(user_message),
    assistant_message=repository._message_to_read(assistant_message),
    answer=answer,
    sources=search_response.sources,
    trace_id=trace.id,
)
```

Add `get_session_summary()` to `ChatRepository`:

```python
def get_session_summary(self, session_id: str) -> SessionSummary:
    return self._session_to_summary(self.get_session_row(session_id))
```

- [ ] **Step 7: Preserve backward compatibility test**

Update existing assertions in `test_chat_service_returns_grounded_answer_and_trace` to include:

```python
assert response.session.id.startswith("session_")
assert response.answer
assert response.user_message.role == "user"
assert response.assistant_message.role == "assistant"
```

Because `chat_profile_id` is optional, existing callers using `ChatRequest(message=...)` continue to work.

- [ ] **Step 8: Run tests**

Run:

```bash
rtk uv run pytest tests/integration/test_chat_service.py tests/integration/test_api_contract.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
rtk git add src/backend/calliope/domain/schemas.py src/backend/calliope/api/dependencies.py src/backend/calliope/api/routes/chat.py src/backend/calliope/services/chat.py src/backend/calliope/repositories/profiles.py src/backend/calliope/services/profiles.py tests/integration/test_chat_service.py tests/integration/test_api_contract.py
rtk git commit -m "feat: return frontend chat turn payload"
```

### Task 6: Persist Search Turns In Session History

**Files:**
- Modify: `src/backend/calliope/domain/schemas.py`
- Modify: `src/backend/calliope/services/search.py`
- Modify: `src/backend/calliope/api/routes/search.py`
- Modify: `tests/integration/test_search_service.py`

- [ ] **Step 1: Write failing search persistence test**

Append to `tests/integration/test_search_service.py`:

```python
def test_search_service_persists_search_result_turn(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_vector_search(self, embedding, *, workspace_id, limit):
        return ["chunk_a"]

    def fake_lexical_search(self, query, *, workspace_id, limit):
        return ["chunk_a"]

    def fake_source_for_chunk(self, chunk_id, score=1.0):
        return SourceReference(
            document_id="document_a",
            chunk_id=chunk_id,
            path="characters/kaelen.md",
            heading="Kaelen",
            excerpt="Kaelen exile",
            score=score,
        )

    monkeypatch.setattr(HybridRetriever, "_vector_search", fake_vector_search)
    monkeypatch.setattr(HybridRetriever, "_lexical_search", fake_lexical_search)
    monkeypatch.setattr(ChunkRepository, "source_for_chunk", fake_source_for_chunk)

    service = SearchService(db_session, FakeEmbeddingClient())
    try:
        response = service.search(
            SearchRequest(query="Kaelen exile", persist=True, limit=1)
        )
    finally:
        service.close()

    assert response.session is not None
    assert response.search_message is not None
    assert response.search_message.role == "search"
    assert response.search_message.metadata["turn_kind"] == "search_result"
    assert response.search_message.metadata["query"] == "Kaelen exile"
    assert response.search_message.metadata["sources"][0]["path"] == "characters/kaelen.md"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
rtk uv run pytest tests/integration/test_search_service.py::test_search_service_persists_search_result_turn -q
```

Expected: FAIL because `persist`, `session`, and `search_message` are missing.

- [ ] **Step 3: Update search schemas**

In `src/backend/calliope/domain/schemas.py`, change:

```python
class SearchRequest(BaseModel):
    query: str
    workspace_id: str | None = None
    session_id: str | None = None
    limit: int = Field(default=8, ge=1, le=50)
    persist: bool = False


class SearchResponse(BaseModel):
    sources: list[SourceReference]
    session: SessionSummary | None = None
    search_message: MessageRead | None = None
```

- [ ] **Step 4: Persist search result when requested**

In `SearchService.search()`, after sources are built:

```python
session_summary = None
search_message = None
if request.persist:
    chat_repo = ChatRepository(self.session)
    session_id = request.session_id
    if session_id is None:
        chat_session = chat_repo.create_session(title=request.query[:80])
        session_id = chat_session.id
    else:
        chat_repo.get_session_row(session_id)
    message = chat_repo.add_message(
        session_id=session_id,
        role="search",
        content=request.query,
        metadata={
            "turn_kind": "search_result",
            "query": request.query,
            "sources": [source.model_dump(mode="json") for source in sources],
        },
    )
    self.session.commit()
    session_summary = chat_repo.get_session_summary(session_id)
    search_message = chat_repo._message_to_read(message)

return SearchResponse(
    sources=sources,
    session=session_summary,
    search_message=search_message,
)
```

Import `ChatRepository`.

- [ ] **Step 5: Preserve source-only behavior**

Add to existing `test_search_returns_sources_for_indexed_workspace`:

```python
assert response.session is None
assert response.search_message is None
```

This verifies callers omitting `persist` still receive the existing source-only information plus nullable frontend fields.

- [ ] **Step 6: Run tests**

Run:

```bash
rtk uv run pytest tests/integration/test_search_service.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
rtk git add src/backend/calliope/domain/schemas.py src/backend/calliope/services/search.py src/backend/calliope/api/routes/search.py tests/integration/test_search_service.py
rtk git commit -m "feat: persist search turns"
```

### Task 7: Add Profile And Workspace Update/Delete APIs

**Files:**
- Modify: `src/backend/calliope/domain/schemas.py`
- Modify: `src/backend/calliope/repositories/profiles.py`
- Modify: `src/backend/calliope/services/profiles.py`
- Modify: `src/backend/calliope/api/routes/profiles.py`
- Modify: `src/backend/calliope/repositories/workspaces.py`
- Modify: `src/backend/calliope/services/workspaces.py`
- Modify: `src/backend/calliope/api/routes/workspaces.py`
- Add: `tests/integration/test_workspace_profile_mutations.py`

- [ ] **Step 1: Write failing mutation tests**

Create `tests/integration/test_workspace_profile_mutations.py`:

```python
from calliope.domain.enums import ProfileCapability, ProfileKind
from calliope.domain.errors import AppError
from calliope.domain.schemas import (
    ProfileCreate,
    ProfilePatch,
    WorkspaceCreate,
    WorkspacePatch,
)
from calliope.repositories.profiles import ProfileRepository
from calliope.repositories.workspaces import WorkspaceRepository


def test_profile_repository_updates_and_deletes(db_session) -> None:
    repo = ProfileRepository(db_session)
    created = repo.create(
        ProfileCreate(
            name="local-chat",
            kind=ProfileKind.OPENAI_COMPATIBLE,
            base_url="http://localhost:4000/v1",
            model="old-model",
            capabilities=[ProfileCapability.CHAT],
        )
    )

    updated = repo.update(
        created.id,
        ProfilePatch(
            name="renamed-chat",
            model="new-model",
            capabilities=[ProfileCapability.CHAT, ProfileCapability.STREAMING],
        ),
    )
    assert updated.name == "renamed-chat"
    assert updated.model == "new-model"
    assert updated.capabilities == [ProfileCapability.CHAT, ProfileCapability.STREAMING]

    repo.delete(created.id)
    assert repo.list() == []


def test_workspace_repository_updates_and_deletes(db_session) -> None:
    repo = WorkspaceRepository(db_session)
    created = repo.create(WorkspaceCreate(name="World", root_path="/tmp/world"))

    updated = repo.update(
        created.id,
        WorkspacePatch(
            name="Renamed World",
            root_path="/tmp/renamed-world",
            include_globs=["**/*.md"],
            exclude_globs=[".git/**"],
        ),
    )
    assert updated.name == "Renamed World"
    assert updated.root_path == "/tmp/renamed-world"

    repo.delete(created.id)
    try:
        repo.get(created.id)
    except AppError as exc:
        assert exc.code == "workspace_not_found"
    else:
        raise AssertionError("expected AppError")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
rtk uv run pytest tests/integration/test_workspace_profile_mutations.py -q
```

Expected: FAIL because `ProfilePatch`, `WorkspacePatch`, and repository methods are missing.

- [ ] **Step 3: Add patch schemas**

In `src/backend/calliope/domain/schemas.py`, add:

```python
class WorkspacePatch(BaseModel):
    name: str | None = None
    root_path: str | None = None
    include_globs: list[str] | None = None
    exclude_globs: list[str] | None = None


class ProfilePatch(BaseModel):
    name: str | None = None
    kind: ProfileKind | None = None
    base_url: str | None = None
    model: str | None = None
    api_key_ref: str | None = None
    capabilities: list[ProfileCapability] | None = None
```

- [ ] **Step 4: Implement profile mutations**

In `ProfileRepository`, add:

```python
    def update(self, profile_id: str, payload: ProfilePatch) -> ProfileRead:
        profile = self._get_row(profile_id)
        if payload.name is not None:
            profile.name = payload.name
        if payload.kind is not None:
            profile.kind = payload.kind.value
        if payload.base_url is not None:
            profile.base_url = payload.base_url
        if payload.model is not None:
            profile.model = payload.model
        if payload.api_key_ref is not None or "api_key_ref" in payload.model_fields_set:
            profile.api_key_ref = payload.api_key_ref
        if payload.capabilities is not None:
            profile.capabilities_json = [capability.value for capability in payload.capabilities]
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise AppError(
                code="connection_profile_already_exists",
                message="Connection profile already exists.",
                status_code=409,
                details={"name": payload.name},
            ) from exc
        self.session.refresh(profile)
        return self._to_read(profile)

    def delete(self, profile_id: str) -> None:
        profile = self._get_row(profile_id)
        self.session.delete(profile)
        self.session.commit()

    def _get_row(self, profile_id: str) -> ConnectionProfile:
        profile = self.session.get(ConnectionProfile, profile_id)
        if profile is None:
            raise AppError(
                code="connection_profile_not_found",
                message="Connection profile not found.",
                status_code=404,
                details={"profile_id": profile_id},
            )
        return profile
```

Expose matching service methods and route handlers:

```python
@router.patch("/{profile_id}", response_model=ProfileRead)
def update_profile(profile_id: str, payload: ProfilePatch, session: Annotated[Session, Depends(get_db_session)]) -> ProfileRead:
    return ProfileService(session).update(profile_id, payload)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: str, session: Annotated[Session, Depends(get_db_session)]) -> Response:
    ProfileService(session).delete(profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 5: Implement workspace mutations**

In `WorkspaceRepository`, add:

```python
    def update(self, workspace_id: str, payload: WorkspacePatch) -> WorkspaceRead:
        workspace = self._get_row(workspace_id)
        if payload.name is not None:
            workspace.name = payload.name
        if payload.root_path is not None:
            workspace.root_path = payload.root_path
        if payload.include_globs is not None:
            workspace.include_globs = payload.include_globs
        if payload.exclude_globs is not None:
            workspace.exclude_globs = payload.exclude_globs
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise AppError(
                code="workspace_already_exists",
                message="Workspace already exists.",
                status_code=409,
                details={"name": payload.name},
            ) from exc
        self.session.refresh(workspace)
        return self._to_read(workspace)

    def delete(self, workspace_id: str) -> None:
        workspace = self._get_row(workspace_id)
        self.session.delete(workspace)
        self.session.commit()

    def _get_row(self, workspace_id: str) -> Workspace:
        workspace = self.session.get(Workspace, workspace_id)
        if workspace is None:
            raise AppError(
                code="workspace_not_found",
                message="Workspace not found.",
                status_code=404,
                details={"workspace_id": workspace_id},
            )
        return workspace
```

Refactor `get()` to call `_get_row()`, expose service methods, and add routes:

```python
@router.get("/v1/workspaces/{workspace_id}", response_model=WorkspaceRead)
def get_workspace(workspace_id: str, session: Annotated[Session, Depends(get_db_session)]) -> WorkspaceRead:
    return WorkspaceService(session).get(workspace_id)


@router.patch("/v1/workspaces/{workspace_id}", response_model=WorkspaceRead)
def update_workspace(workspace_id: str, payload: WorkspacePatch, session: Annotated[Session, Depends(get_db_session)]) -> WorkspaceRead:
    return WorkspaceService(session).update(workspace_id, payload)


@router.delete("/v1/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(workspace_id: str, session: Annotated[Session, Depends(get_db_session)]) -> Response:
    WorkspaceService(session).delete(workspace_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 6: Run tests**

Run:

```bash
rtk uv run pytest tests/integration/test_workspace_profile_mutations.py tests/integration/test_profiles.py tests/integration/test_repositories.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
rtk git add src/backend/calliope/domain/schemas.py src/backend/calliope/repositories/profiles.py src/backend/calliope/services/profiles.py src/backend/calliope/api/routes/profiles.py src/backend/calliope/repositories/workspaces.py src/backend/calliope/services/workspaces.py src/backend/calliope/api/routes/workspaces.py tests/integration/test_workspace_profile_mutations.py
rtk git commit -m "feat: add settings mutation apis"
```

### Task 8: Scaffold Vue Frontend

**Files:**
- Create: `src/frontend/package.json`
- Create: `src/frontend/vite.config.ts`
- Create: `src/frontend/tsconfig.json`
- Create: `src/frontend/tsconfig.node.json`
- Create: `src/frontend/index.html`
- Create: `src/frontend/src/app/main.ts`
- Create: `src/frontend/src/app/App.vue`
- Create: `src/frontend/src/app/vuetify.ts`
- Create: `src/frontend/src/app/router.ts`
- Create: `src/frontend/src/test/setup.ts`

- [ ] **Step 1: Create frontend package manifest**

Create `src/frontend/package.json`:

```json
{
  "name": "calliope-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "vue-tsc --noEmit && vite build",
    "test": "vitest run",
    "test:watch": "vitest",
    "typecheck": "vue-tsc --noEmit"
  },
  "dependencies": {
    "@mdi/font": "^7.4.47",
    "pinia": "^2.3.1",
    "roboto-fontface": "^0.10.0",
    "vue": "^3.5.13",
    "vue-router": "^4.5.0",
    "vuetify": "^3.7.6"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2.1",
    "@vue/test-utils": "^2.4.6",
    "jsdom": "^25.0.1",
    "typescript": "^5.7.2",
    "vite": "^6.0.7",
    "vitest": "^2.1.8",
    "vue-tsc": "^2.2.0"
  }
}
```

- [ ] **Step 2: Install dependencies**

Run:

```bash
rtk bun install --cwd src/frontend
```

Expected: `src/frontend/bun.lock` is created.

- [ ] **Step 3: Add Vite and TypeScript config**

Create `src/frontend/vite.config.ts`:

```ts
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
})
```

Create `src/frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "jsx": "preserve",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "types": ["vitest/globals"],
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.tsx", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

Create `src/frontend/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Add app shell bootstrap**

Create `src/frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Calliope</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/app/main.ts"></script>
  </body>
</html>
```

Create `src/frontend/src/app/main.ts`:

```ts
import '@mdi/font/css/materialdesignicons.css'
import 'roboto-fontface/css/roboto/roboto-fontface.css'
import 'vuetify/styles'

import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import vuetify from './vuetify'

createApp(App).use(createPinia()).use(router).use(vuetify).mount('#app')
```

Create `src/frontend/src/app/App.vue`:

```vue
<template>
  <v-app>
    <v-main class="calliope-app">
      <router-view />
    </v-main>
  </v-app>
</template>

<style scoped>
.calliope-app {
  min-height: 100vh;
  background: rgb(var(--v-theme-background));
}
</style>
```

- [ ] **Step 5: Add Vuetify theme and router**

Create `src/frontend/src/app/vuetify.ts`:

```ts
import { createVuetify } from 'vuetify'

export default createVuetify({
  theme: {
    defaultTheme: 'calliopeLight',
    themes: {
      calliopeLight: {
        dark: false,
        colors: {
          background: '#f7f8fa',
          surface: '#ffffff',
          primary: '#315c72',
          secondary: '#6b5f4a',
          accent: '#4f6f52',
          error: '#b3261e',
        },
      },
    },
  },
  defaults: {
    VBtn: { rounded: 'sm' },
    VCard: { rounded: 'sm' },
    VTextField: { density: 'compact', variant: 'outlined' },
    VTextarea: { density: 'compact', variant: 'outlined' },
    VSelect: { density: 'compact', variant: 'outlined' },
  },
})
```

Create `src/frontend/src/app/router.ts`:

```ts
import { createRouter, createWebHistory } from 'vue-router'

import ChatWorkspace from '@/features/chat/components/ChatWorkspace.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', name: 'chat', component: ChatWorkspace }],
})
```

Create `src/frontend/src/test/setup.ts`:

```ts
import { config } from '@vue/test-utils'

config.global.stubs = {
  transition: false,
  'transition-group': false,
}
```

- [ ] **Step 6: Add temporary chat component for scaffold**

Create `src/frontend/src/features/chat/components/ChatWorkspace.vue`:

```vue
<template>
  <section class="chat-workspace">
    <h1>Calliope</h1>
  </section>
</template>

<style scoped>
.chat-workspace {
  min-height: 100vh;
  padding: 24px;
}
</style>
```

- [ ] **Step 7: Build and test**

Run:

```bash
rtk bun run --cwd src/frontend build
rtk bun run --cwd src/frontend test
```

Expected: build PASS and Vitest reports no test files or PASS once tests are added.

- [ ] **Step 8: Commit**

```bash
rtk git add src/frontend
rtk git commit -m "feat: scaffold vue frontend"
```

### Task 9: Add Frontend API Client, Types, And Store Tests

**Files:**
- Create: `src/frontend/src/shared/api/errors.ts`
- Create: `src/frontend/src/shared/api/client.ts`
- Create: `src/frontend/src/features/chat/types.ts`
- Create: `src/frontend/src/features/chat/api.ts`
- Create: `src/frontend/src/features/profiles/types.ts`
- Create: `src/frontend/src/features/profiles/api.ts`
- Create: `src/frontend/src/features/workspaces/types.ts`
- Create: `src/frontend/src/features/workspaces/api.ts`
- Create: `src/frontend/src/shared/api/client.test.ts`

- [ ] **Step 1: Write failing API client tests**

Create `src/frontend/src/shared/api/client.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, requestJson } from './client'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('requestJson', () => {
  it('returns parsed JSON for successful responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }))))

    await expect(requestJson('/v1/example')).resolves.toEqual({ ok: true })
  })

  it('normalizes backend error envelopes', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: 'workspace_not_found',
              message: 'Workspace not found.',
              details: { workspace_id: 'workspace_missing' },
            },
          }),
          { status: 404 },
        ),
      ),
    )

    await expect(requestJson('/v1/workspaces/workspace_missing')).rejects.toMatchObject({
      code: 'workspace_not_found',
      message: 'Workspace not found.',
      status: 404,
      details: { workspace_id: 'workspace_missing' },
    } satisfies Partial<ApiError>)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
rtk bun run --cwd src/frontend test src/shared/api/client.test.ts
```

Expected: FAIL because `client.ts` does not exist.

- [ ] **Step 3: Implement error and client modules**

Create `src/frontend/src/shared/api/errors.ts`:

```ts
export type ErrorDetails = Record<string, unknown>

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly details: ErrorDetails

  constructor(params: { code: string; message: string; status: number; details?: ErrorDetails }) {
    super(params.message)
    this.name = 'ApiError'
    this.code = params.code
    this.status = params.status
    this.details = params.details ?? {}
  }
}
```

Create `src/frontend/src/shared/api/client.ts`:

```ts
import { ApiError } from './errors'

export { ApiError }

const defaultBaseUrl = 'http://127.0.0.1:8000'

export function apiBaseUrl(): string {
  return import.meta.env.VITE_CALLIOPE_API_BASE_URL ?? defaultBaseUrl
}

export async function requestJson<TResponse>(
  path: string,
  init: RequestInit = {},
): Promise<TResponse> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    let parsed: unknown
    try {
      parsed = await response.json()
    } catch {
      parsed = undefined
    }
    const error = parseErrorEnvelope(parsed, response.status)
    throw error
  }

  if (response.status === 204) {
    return undefined as TResponse
  }

  return (await response.json()) as TResponse
}

function parseErrorEnvelope(payload: unknown, status: number): ApiError {
  if (isBackendError(payload)) {
    return new ApiError({
      code: payload.error.code,
      message: payload.error.message,
      status,
      details: payload.error.details,
    })
  }

  return new ApiError({
    code: 'http_error',
    message: `Request failed with HTTP ${status}.`,
    status,
  })
}

function isBackendError(payload: unknown): payload is {
  error: { code: string; message: string; details: Record<string, unknown> }
} {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    'error' in payload &&
    typeof (payload as { error?: unknown }).error === 'object' &&
    (payload as { error: { code?: unknown; message?: unknown } }).error !== null &&
    typeof (payload as { error: { code?: unknown } }).error.code === 'string' &&
    typeof (payload as { error: { message?: unknown } }).error.message === 'string'
  )
}
```

- [ ] **Step 4: Add shared TypeScript API types**

Create `src/frontend/src/features/chat/types.ts`:

```ts
export type CanonPolicy = 'strict_canon' | 'canon_plus_inference' | 'creative_but_consistent'
export type ComposerMode = 'chat' | 'search'

export interface SourceReference {
  document_id: string
  chunk_id: string
  path: string
  heading: string
  excerpt: string
  score: number
}

export interface ConversationFolder {
  id: string
  name: string
  parent_id: string | null
  position: number
  created_at: string
  updated_at: string
}

export interface SessionSummary {
  id: string
  title: string | null
  folder_id: string | null
  created_at: string
  updated_at: string
}

export interface MessageRead {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'search' | string
  content: string
  metadata: Record<string, unknown>
  created_at: string
}

export interface SessionDetail extends SessionSummary {
  messages: MessageRead[]
}

export interface ChatResponse {
  session: SessionSummary
  user_message: MessageRead
  assistant_message: MessageRead
  answer: string
  sources: SourceReference[]
  trace_id: string
}

export interface SearchResponse {
  sources: SourceReference[]
  session: SessionSummary | null
  search_message: MessageRead | null
}
```

Create `src/frontend/src/features/profiles/types.ts`:

```ts
export type ProfileKind = 'openai_compatible'
export type ProfileCapability = 'chat' | 'embeddings' | 'rerank' | 'streaming'

export interface Profile {
  id: string
  name: string
  kind: ProfileKind
  base_url: string
  model: string
  api_key_ref: string | null
  capabilities: ProfileCapability[]
  created_at: string
}
```

Create `src/frontend/src/features/workspaces/types.ts`:

```ts
export interface Workspace {
  id: string
  name: string
  root_path: string
  include_globs: string[]
  exclude_globs: string[]
  created_at: string
}

export interface ReindexResponse {
  documents_indexed: number
  chunks_indexed: number
}
```

- [ ] **Step 5: Add API helper modules**

Create `src/frontend/src/features/chat/api.ts`:

```ts
import { requestJson } from '@/shared/api/client'

import type {
  CanonPolicy,
  ChatResponse,
  ConversationFolder,
  SearchResponse,
  SessionDetail,
  SessionSummary,
} from './types'

export function listSessions(): Promise<SessionSummary[]> {
  return requestJson('/v1/sessions')
}

export function getSession(sessionId: string): Promise<SessionDetail> {
  return requestJson(`/v1/sessions/${sessionId}`)
}

export function patchSession(
  sessionId: string,
  payload: { title?: string; folder_id?: string | null },
): Promise<SessionSummary> {
  return requestJson(`/v1/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteSession(sessionId: string): Promise<void> {
  return requestJson(`/v1/sessions/${sessionId}`, { method: 'DELETE' })
}

export function listFolders(): Promise<ConversationFolder[]> {
  return requestJson('/v1/conversation-folders')
}

export function createFolder(payload: {
  name: string
  parent_id: string | null
  position: number
}): Promise<ConversationFolder> {
  return requestJson('/v1/conversation-folders', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function patchFolder(
  folderId: string,
  payload: { name?: string; parent_id?: string | null; position?: number },
): Promise<ConversationFolder> {
  return requestJson(`/v1/conversation-folders/${folderId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteFolder(folderId: string): Promise<void> {
  return requestJson(`/v1/conversation-folders/${folderId}`, { method: 'DELETE' })
}

export function sendChat(payload: {
  message: string
  policy: CanonPolicy
  session_id: string | null
  workspace_id: string | null
  chat_profile_id: string
  limit: number
}): Promise<ChatResponse> {
  return requestJson('/v1/chat', { method: 'POST', body: JSON.stringify(payload) })
}

export function sendSearch(payload: {
  query: string
  session_id: string | null
  workspace_id: string | null
  limit: number
  persist: true
}): Promise<SearchResponse> {
  return requestJson('/v1/search', { method: 'POST', body: JSON.stringify(payload) })
}
```

Create `src/frontend/src/features/profiles/api.ts`:

```ts
import { requestJson } from '@/shared/api/client'

import type { Profile, ProfileCapability, ProfileKind } from './types'

export interface ProfilePayload {
  name: string
  kind: ProfileKind
  base_url: string
  model: string
  api_key_ref: string | null
  capabilities: ProfileCapability[]
}

export interface ProfileTestResult {
  ok: boolean
  id: string
  capabilities: ProfileCapability[]
}

export function listProfiles(): Promise<Profile[]> {
  return requestJson('/v1/profiles')
}

export function createProfile(payload: ProfilePayload): Promise<Profile> {
  return requestJson('/v1/profiles', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function patchProfile(
  profileId: string,
  payload: Partial<ProfilePayload>,
): Promise<Profile> {
  return requestJson(`/v1/profiles/${profileId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteProfile(profileId: string): Promise<void> {
  return requestJson(`/v1/profiles/${profileId}`, { method: 'DELETE' })
}

export function testProfile(profileId: string): Promise<ProfileTestResult> {
  return requestJson(`/v1/profiles/${profileId}/test`, { method: 'POST' })
}
```

Create `src/frontend/src/features/workspaces/api.ts`:

```ts
import { requestJson } from '@/shared/api/client'

import type { ReindexResponse, Workspace } from './types'

export interface WorkspacePayload {
  name: string
  root_path: string
  include_globs: string[]
  exclude_globs: string[]
}

export function listWorkspaces(): Promise<Workspace[]> {
  return requestJson('/v1/workspaces')
}

export function getWorkspace(workspaceId: string): Promise<Workspace> {
  return requestJson(`/v1/workspaces/${workspaceId}`)
}

export function createWorkspace(payload: WorkspacePayload): Promise<Workspace> {
  return requestJson('/v1/workspaces', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function patchWorkspace(
  workspaceId: string,
  payload: Partial<WorkspacePayload>,
): Promise<Workspace> {
  return requestJson(`/v1/workspaces/${workspaceId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteWorkspace(workspaceId: string): Promise<void> {
  return requestJson(`/v1/workspaces/${workspaceId}`, { method: 'DELETE' })
}

export function reindexWorkspace(workspaceId: string): Promise<ReindexResponse> {
  return requestJson('/v1/reindex', {
    method: 'POST',
    body: JSON.stringify({ workspace_id: workspaceId }),
  })
}
```

- [ ] **Step 6: Run tests**

Run:

```bash
rtk bun run --cwd src/frontend test src/shared/api/client.test.ts
rtk bun run --cwd src/frontend typecheck
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
rtk git add src/frontend/src/shared src/frontend/src/features
rtk git commit -m "feat: add frontend api client"
```

### Task 10: Add Pinia Stores For Chat, Profiles, Workspaces, And Settings

**Files:**
- Create: `src/frontend/src/features/chat/stores/chatStore.ts`
- Create: `src/frontend/src/features/profiles/stores/profileStore.ts`
- Create: `src/frontend/src/features/workspaces/stores/workspaceStore.ts`
- Create: `src/frontend/src/features/settings/stores/settingsStore.ts`
- Create: `src/frontend/src/features/chat/stores/chatStore.test.ts`

- [ ] **Step 1: Write failing chat store tests**

Create `src/frontend/src/features/chat/stores/chatStore.test.ts`:

```ts
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as chatApi from '../api'
import { useChatStore } from './chatStore'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.restoreAllMocks()
})

describe('chatStore', () => {
  it('loads folders and sessions', async () => {
    vi.spyOn(chatApi, 'listFolders').mockResolvedValue([
      {
        id: 'folder_1',
        name: 'Worldbuilding',
        parent_id: null,
        position: 0,
        created_at: '2026-05-20T12:00:00Z',
        updated_at: '2026-05-20T12:00:00Z',
      },
    ])
    vi.spyOn(chatApi, 'listSessions').mockResolvedValue([
      {
        id: 'session_1',
        title: 'Lake city',
        folder_id: 'folder_1',
        created_at: '2026-05-20T12:00:00Z',
        updated_at: '2026-05-20T12:05:00Z',
      },
    ])

    const store = useChatStore()
    await store.refreshConversationList()

    expect(store.folders).toHaveLength(1)
    expect(store.sessions[0].title).toBe('Lake city')
  })

  it('adds messages from chat response', async () => {
    vi.spyOn(chatApi, 'sendChat').mockResolvedValue({
      session: {
        id: 'session_1',
        title: 'Lake city',
        folder_id: null,
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

    expect(store.activeSessionId).toBe('session_1')
    expect(store.messages.map((message) => message.role)).toEqual(['user', 'assistant'])
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
rtk bun run --cwd src/frontend test src/features/chat/stores/chatStore.test.ts
```

Expected: FAIL because `chatStore.ts` does not exist.

- [ ] **Step 3: Implement chat store**

Create `src/frontend/src/features/chat/stores/chatStore.ts`:

```ts
import { defineStore } from 'pinia'

import * as chatApi from '../api'
import type {
  CanonPolicy,
  ComposerMode,
  ConversationFolder,
  MessageRead,
  SessionSummary,
} from '../types'

interface ChatState {
  folders: ConversationFolder[]
  sessions: SessionSummary[]
  activeSessionId: string | null
  messages: MessageRead[]
  mode: ComposerMode
  policy: CanonPolicy
  selectedWorkspaceId: string | null
  selectedChatProfileId: string | null
  pending: boolean
  errorMessage: string | null
}

export const useChatStore = defineStore('chat', {
  state: (): ChatState => ({
    folders: [],
    sessions: [],
    activeSessionId: null,
    messages: [],
    mode: 'chat',
    policy: 'strict_canon',
    selectedWorkspaceId: null,
    selectedChatProfileId: null,
    pending: false,
    errorMessage: null,
  }),
  getters: {
    canSubmit(state): boolean {
      if (state.pending || state.selectedWorkspaceId === null) return false
      if (state.mode === 'chat' && state.selectedChatProfileId === null) return false
      return true
    },
    unfiledSessions(state): SessionSummary[] {
      return state.sessions.filter((session) => session.folder_id === null)
    },
  },
  actions: {
    async refreshConversationList() {
      const [folders, sessions] = await Promise.all([chatApi.listFolders(), chatApi.listSessions()])
      this.folders = folders
      this.sessions = sessions
    },
    async openSession(sessionId: string) {
      const detail = await chatApi.getSession(sessionId)
      this.activeSessionId = detail.id
      this.messages = detail.messages
    },
    async submitMessage(text: string) {
      const trimmed = text.trim()
      if (trimmed.length === 0 || !this.canSubmit) return
      this.pending = true
      this.errorMessage = null
      try {
        if (this.mode === 'chat') {
          const response = await chatApi.sendChat({
            message: trimmed,
            policy: this.policy,
            session_id: this.activeSessionId,
            workspace_id: this.selectedWorkspaceId,
            chat_profile_id: this.selectedChatProfileId as string,
            limit: 8,
          })
          this.activeSessionId = response.session.id
          this.upsertSession(response.session)
          this.messages.push(response.user_message, response.assistant_message)
        } else {
          const response = await chatApi.sendSearch({
            query: trimmed,
            session_id: this.activeSessionId,
            workspace_id: this.selectedWorkspaceId,
            limit: 8,
            persist: true,
          })
          if (response.session !== null) {
            this.activeSessionId = response.session.id
            this.upsertSession(response.session)
          }
          if (response.search_message !== null) {
            this.messages.push(response.search_message)
          }
        }
      } catch (error) {
        this.errorMessage = error instanceof Error ? error.message : 'Request failed.'
      } finally {
        this.pending = false
      }
    },
    upsertSession(session: SessionSummary) {
      const index = this.sessions.findIndex((existing) => existing.id === session.id)
      if (index === -1) this.sessions.unshift(session)
      else this.sessions.splice(index, 1, session)
    },
  },
})
```

- [ ] **Step 4: Implement settings store**

Create `src/frontend/src/features/settings/stores/settingsStore.ts`:

```ts
import { defineStore } from 'pinia'

export const useSettingsStore = defineStore('settings', {
  state: () => ({ open: false, tab: 'profiles' as 'profiles' | 'workspaces' | 'indexing' }),
  actions: {
    show(tab: 'profiles' | 'workspaces' | 'indexing' = 'profiles') {
      this.tab = tab
      this.open = true
    },
    close() {
      this.open = false
    },
  },
})
```

- [ ] **Step 5: Implement profile store**

Create `src/frontend/src/features/profiles/stores/profileStore.ts`:

```ts
import { defineStore } from 'pinia'

import * as profileApi from '../api'
import type { Profile } from '../types'
import type { ProfilePayload, ProfileTestResult } from '../api'

interface ProfileState {
  profiles: Profile[]
  loading: boolean
  errorMessage: string | null
  testResult: ProfileTestResult | null
}

export const useProfileStore = defineStore('profiles', {
  state: (): ProfileState => ({
    profiles: [],
    loading: false,
    errorMessage: null,
    testResult: null,
  }),
  getters: {
    chatProfiles(state): Profile[] {
      return state.profiles.filter((profile) => profile.capabilities.includes('chat'))
    },
  },
  actions: {
    async refresh() {
      this.loading = true
      this.errorMessage = null
      try {
        this.profiles = await profileApi.listProfiles()
      } catch (error) {
        this.errorMessage = error instanceof Error ? error.message : 'Could not load profiles.'
      } finally {
        this.loading = false
      }
    },
    async saveProfile(payload: ProfilePayload, profileId: string | null = null) {
      const saved =
        profileId === null
          ? await profileApi.createProfile(payload)
          : await profileApi.patchProfile(profileId, payload)
      const index = this.profiles.findIndex((profile) => profile.id === saved.id)
      if (index === -1) this.profiles.push(saved)
      else this.profiles.splice(index, 1, saved)
    },
    async deleteProfile(profileId: string) {
      await profileApi.deleteProfile(profileId)
      this.profiles = this.profiles.filter((profile) => profile.id !== profileId)
    },
    async testProfile(profileId: string) {
      this.testResult = await profileApi.testProfile(profileId)
    },
  },
})
```

- [ ] **Step 6: Implement workspace store**

Create `src/frontend/src/features/workspaces/stores/workspaceStore.ts`:

```ts
import { defineStore } from 'pinia'

import * as workspaceApi from '../api'
import type { ReindexResponse, Workspace } from '../types'
import type { WorkspacePayload } from '../api'

interface WorkspaceState {
  workspaces: Workspace[]
  selectedWorkspaceId: string | null
  loading: boolean
  reindexing: boolean
  errorMessage: string | null
  reindexResult: ReindexResponse | null
}

export const useWorkspaceStore = defineStore('workspaces', {
  state: (): WorkspaceState => ({
    workspaces: [],
    selectedWorkspaceId: null,
    loading: false,
    reindexing: false,
    errorMessage: null,
    reindexResult: null,
  }),
  getters: {
    selectedWorkspace(state): Workspace | null {
      return (
        state.workspaces.find((workspace) => workspace.id === state.selectedWorkspaceId) ?? null
      )
    },
  },
  actions: {
    async refresh() {
      this.loading = true
      this.errorMessage = null
      try {
        this.workspaces = await workspaceApi.listWorkspaces()
        if (this.selectedWorkspaceId === null && this.workspaces.length > 0) {
          this.selectedWorkspaceId = this.workspaces[0].id
        }
      } catch (error) {
        this.errorMessage = error instanceof Error ? error.message : 'Could not load workspaces.'
      } finally {
        this.loading = false
      }
    },
    async saveWorkspace(payload: WorkspacePayload, workspaceId: string | null = null) {
      const saved =
        workspaceId === null
          ? await workspaceApi.createWorkspace(payload)
          : await workspaceApi.patchWorkspace(workspaceId, payload)
      const index = this.workspaces.findIndex((workspace) => workspace.id === saved.id)
      if (index === -1) this.workspaces.push(saved)
      else this.workspaces.splice(index, 1, saved)
      this.selectedWorkspaceId = saved.id
    },
    async deleteWorkspace(workspaceId: string) {
      await workspaceApi.deleteWorkspace(workspaceId)
      this.workspaces = this.workspaces.filter((workspace) => workspace.id !== workspaceId)
      if (this.selectedWorkspaceId === workspaceId) {
        this.selectedWorkspaceId = this.workspaces[0]?.id ?? null
      }
    },
    async reindexSelectedWorkspace() {
      if (this.selectedWorkspaceId === null) return
      this.reindexing = true
      this.reindexResult = null
      this.errorMessage = null
      try {
        this.reindexResult = await workspaceApi.reindexWorkspace(this.selectedWorkspaceId)
      } catch (error) {
        this.errorMessage = error instanceof Error ? error.message : 'Reindex failed.'
      } finally {
        this.reindexing = false
      }
    },
  },
})
```

- [ ] **Step 7: Run tests**

Run:

```bash
rtk bun run --cwd src/frontend test src/features/chat/stores/chatStore.test.ts
rtk bun run --cwd src/frontend typecheck
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
rtk git add src/frontend/src/features
rtk git commit -m "feat: add frontend stores"
```

### Task 11: Build Chat Workspace UI

**Files:**
- Modify: `src/frontend/src/features/chat/components/ChatWorkspace.vue`
- Create: `src/frontend/src/features/chat/components/ConversationDrawer.vue`
- Create: `src/frontend/src/features/chat/components/ConversationTimeline.vue`
- Create: `src/frontend/src/features/chat/components/ComposerBar.vue`
- Create: `src/frontend/src/features/chat/components/ChatWorkspace.test.ts`

- [ ] **Step 1: Write failing component test**

Create `src/frontend/src/features/chat/components/ChatWorkspace.test.ts`:

```ts
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as chatApi from '../api'
import ChatWorkspace from './ChatWorkspace.vue'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.spyOn(chatApi, 'listFolders').mockResolvedValue([])
  vi.spyOn(chatApi, 'listSessions').mockResolvedValue([])
})

describe('ChatWorkspace', () => {
  it('renders the conversation drawer and composer controls', async () => {
    const wrapper = mount(ChatWorkspace, { global: { stubs: ['v-icon'] } })
    await vi.dynamicImportSettled()

    expect(wrapper.text()).toContain('New conversation')
    expect(wrapper.text()).toContain('Chat')
    expect(wrapper.text()).toContain('Search')
    expect(wrapper.find('textarea').exists()).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
rtk bun run --cwd src/frontend test src/features/chat/components/ChatWorkspace.test.ts
```

Expected: FAIL because chat UI components do not exist or scaffold lacks controls.

- [ ] **Step 3: Implement drawer component**

Create `src/frontend/src/features/chat/components/ConversationDrawer.vue`:

```vue
<script setup lang="ts">
import { computed, ref } from 'vue'

import type { ConversationFolder, SessionSummary } from '../types'

const props = defineProps<{
  folders: ConversationFolder[]
  sessions: SessionSummary[]
  activeSessionId: string | null
  activeWorkspaceName: string
}>()

const emit = defineEmits<{
  'new-session': []
  'open-session': [sessionId: string]
  'create-folder': [name: string]
  'rename-folder': [folderId: string, name: string]
  'delete-folder': [folderId: string]
}>()

const filter = ref('')
const newFolderName = ref('')

const visibleSessions = computed(() => {
  const needle = filter.value.trim().toLowerCase()
  if (needle.length === 0) return props.sessions
  return props.sessions.filter((session) => (session.title ?? 'Untitled').toLowerCase().includes(needle))
})

const unfiledSessions = computed(() => visibleSessions.value.filter((session) => session.folder_id === null))

function sessionsForFolder(folderId: string): SessionSummary[] {
  return visibleSessions.value.filter((session) => session.folder_id === folderId)
}

function createFolder() {
  const name = newFolderName.value.trim()
  if (name.length === 0) return
  emit('create-folder', name)
  newFolderName.value = ''
}
</script>

<template>
  <v-navigation-drawer permanent width="320" class="conversation-drawer">
    <div class="drawer-header">
      <v-btn block color="primary" prepend-icon="mdi-plus" @click="emit('new-session')">
        New conversation
      </v-btn>
      <div class="workspace-name">{{ activeWorkspaceName }}</div>
      <v-text-field v-model="filter" label="Filter conversations" prepend-inner-icon="mdi-magnify" />
      <div class="folder-create">
        <v-text-field v-model="newFolderName" label="Folder name" @keyup.enter="createFolder" />
        <v-btn icon="mdi-folder-plus" variant="text" aria-label="Create folder" @click="createFolder" />
      </div>
    </div>

    <v-list density="compact" nav>
      <v-list-group v-for="folder in folders" :key="folder.id" :value="folder.id">
        <template #activator="{ props: activatorProps }">
          <v-list-item v-bind="activatorProps" prepend-icon="mdi-folder" :title="folder.name">
            <template #append>
              <v-btn icon="mdi-delete-outline" variant="text" size="small" aria-label="Delete folder" @click.stop="emit('delete-folder', folder.id)" />
            </template>
          </v-list-item>
        </template>
        <v-list-item
          v-for="session in sessionsForFolder(folder.id)"
          :key="session.id"
          :active="session.id === activeSessionId"
          :title="session.title ?? 'Untitled'"
          prepend-icon="mdi-message-text-outline"
          @click="emit('open-session', session.id)"
        />
        <v-list-item v-if="sessionsForFolder(folder.id).length === 0" title="Empty folder" class="empty-row" />
      </v-list-group>

      <v-list-subheader>Recent unfiled</v-list-subheader>
      <v-list-item
        v-for="session in unfiledSessions"
        :key="session.id"
        :active="session.id === activeSessionId"
        :title="session.title ?? 'Untitled'"
        prepend-icon="mdi-message-text-outline"
        @click="emit('open-session', session.id)"
      />
      <v-list-item v-if="unfiledSessions.length === 0" title="No unfiled conversations" class="empty-row" />
    </v-list>
  </v-navigation-drawer>
</template>

<style scoped>
.conversation-drawer {
  border-right: 1px solid rgba(49, 92, 114, 0.14);
}
.drawer-header {
  display: grid;
  gap: 10px;
  padding: 14px;
}
.workspace-name {
  color: rgba(0, 0, 0, 0.64);
  font-size: 0.82rem;
}
.folder-create {
  display: grid;
  grid-template-columns: 1fr 40px;
  gap: 6px;
  align-items: start;
}
.empty-row {
  opacity: 0.62;
}
</style>
```

- [ ] **Step 4: Implement timeline component**

Create `src/frontend/src/features/chat/components/ConversationTimeline.vue`:

```vue
<script setup lang="ts">
import type { MessageRead, SourceReference } from '../types'

defineProps<{
  messages: MessageRead[]
  pending: boolean
  errorMessage: string | null
}>()

function sourcesFor(message: MessageRead): SourceReference[] {
  const sources = message.metadata.sources
  return Array.isArray(sources) ? (sources as SourceReference[]) : []
}
</script>

<template>
  <div class="timeline">
    <div v-if="messages.length === 0" class="empty-thread">Start a conversation or run a search.</div>
    <article v-for="message in messages" :key="message.id" class="message" :class="`message-${message.role}`">
      <div class="message-role">{{ message.role === 'search' ? 'Search' : message.role }}</div>
      <p class="message-content">{{ message.content }}</p>
      <div v-if="sourcesFor(message).length > 0" class="sources">
        <v-card v-for="source in sourcesFor(message)" :key="source.chunk_id" class="source-card" variant="outlined">
          <v-card-title>{{ source.path }}</v-card-title>
          <v-card-subtitle>{{ source.heading }}</v-card-subtitle>
          <v-card-text>{{ source.excerpt }}</v-card-text>
        </v-card>
      </div>
    </article>
    <v-progress-linear v-if="pending" indeterminate color="primary" />
    <v-alert v-if="errorMessage" type="error" variant="tonal">{{ errorMessage }}</v-alert>
  </div>
</template>

<style scoped>
.timeline {
  display: grid;
  gap: 14px;
  padding: 24px;
  overflow: auto;
}
.empty-thread {
  align-self: center;
  color: rgba(0, 0, 0, 0.58);
  text-align: center;
}
.message {
  max-width: 880px;
  padding: 14px;
  border: 1px solid rgba(49, 92, 114, 0.14);
  border-radius: 8px;
  background: rgb(var(--v-theme-surface));
}
.message-user {
  justify-self: end;
  background: rgba(49, 92, 114, 0.08);
}
.message-role {
  margin-bottom: 6px;
  color: rgba(0, 0, 0, 0.58);
  font-size: 0.78rem;
  text-transform: capitalize;
}
.message-content {
  margin: 0;
  white-space: pre-wrap;
}
.sources {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}
.source-card :deep(.v-card-title) {
  font-size: 0.9rem;
}
</style>
```

- [ ] **Step 5: Implement composer component**

Create `src/frontend/src/features/chat/components/ComposerBar.vue`:

```vue
<script setup lang="ts">
import { computed, ref } from 'vue'

import type { CanonPolicy, ComposerMode } from '../types'
import type { Profile } from '@/features/profiles/types'
import type { Workspace } from '@/features/workspaces/types'

const props = defineProps<{
  mode: ComposerMode
  policy: CanonPolicy
  selectedWorkspaceId: string | null
  selectedChatProfileId: string | null
  workspaces: Workspace[]
  profiles: Profile[]
  pending: boolean
  disabled: boolean
}>()

const emit = defineEmits<{
  'update:mode': [value: ComposerMode]
  'update:policy': [value: CanonPolicy]
  'update:selectedWorkspaceId': [value: string | null]
  'update:selectedChatProfileId': [value: string | null]
  submit: [value: string]
}>()

const text = ref('')

const disabledReason = computed(() => {
  if (props.pending) return 'Waiting for response'
  if (props.workspaces.length === 0) return 'Workspace required'
  if (props.mode === 'chat' && props.profiles.length === 0) return 'Chat profile required'
  return null
})

function submit() {
  const value = text.value.trim()
  if (value.length === 0 || props.disabled) return
  emit('submit', value)
  text.value = ''
}
</script>

<template>
  <div class="composer">
    <v-textarea
      v-model="text"
      rows="2"
      auto-grow
      label="Message"
      hide-details
      @keydown.enter.exact.prevent="submit"
    />
    <div class="composer-controls">
      <v-btn-toggle :model-value="mode" mandatory density="compact" @update:model-value="emit('update:mode', $event)">
        <v-btn value="chat">Chat</v-btn>
        <v-btn value="search">Search</v-btn>
      </v-btn-toggle>
      <v-select
        :model-value="policy"
        :items="['strict_canon', 'canon_plus_inference', 'creative_but_consistent']"
        label="Policy"
        hide-details
        @update:model-value="emit('update:policy', $event as CanonPolicy)"
      />
      <v-select
        :model-value="selectedWorkspaceId"
        :items="workspaces"
        item-title="name"
        item-value="id"
        label="Workspace"
        hide-details
        @update:model-value="emit('update:selectedWorkspaceId', $event)"
      />
      <v-select
        :model-value="selectedChatProfileId"
        :disabled="mode === 'search'"
        :items="profiles"
        item-title="name"
        item-value="id"
        label="Model"
        hide-details
        @update:model-value="emit('update:selectedChatProfileId', $event)"
      />
      <v-btn icon="mdi-send" color="primary" :loading="pending" :disabled="disabled || text.trim().length === 0" aria-label="Submit" @click="submit" />
    </div>
    <div v-if="disabledReason" class="disabled-reason">{{ disabledReason }}</div>
  </div>
</template>

<style scoped>
.composer {
  display: grid;
  gap: 8px;
  padding: 14px;
  border-top: 1px solid rgba(49, 92, 114, 0.14);
  background: rgb(var(--v-theme-surface));
}
.composer-controls {
  display: grid;
  grid-template-columns: auto minmax(160px, 220px) minmax(160px, 220px) minmax(160px, 220px) 44px;
  gap: 8px;
  align-items: center;
}
.disabled-reason {
  color: rgba(0, 0, 0, 0.58);
  font-size: 0.82rem;
}
@media (max-width: 900px) {
  .composer-controls {
    grid-template-columns: 1fr;
  }
}
</style>
```

- [ ] **Step 6: Compose workspace**

Replace `ChatWorkspace.vue` with a two-column app shell:

```vue
<template>
  <div class="chat-shell">
    <ConversationDrawer
      :folders="chat.folders"
      :sessions="chat.sessions"
      :active-session-id="chat.activeSessionId"
      :active-workspace-name="activeWorkspaceName"
      @new-session="startNewConversation"
      @open-session="chat.openSession"
    />
    <section class="chat-main">
      <ConversationTimeline
        :messages="chat.messages"
        :pending="chat.pending"
        :error-message="chat.errorMessage"
      />
      <ComposerBar
        v-model:mode="chat.mode"
        v-model:policy="chat.policy"
        v-model:selected-workspace-id="chat.selectedWorkspaceId"
        v-model:selected-chat-profile-id="chat.selectedChatProfileId"
        :workspaces="workspace.workspaces"
        :profiles="profile.chatProfiles"
        :pending="chat.pending"
        :disabled="!chat.canSubmit"
        @submit="chat.submitMessage"
      />
    </section>
  </div>
</template>
```

On mount, call `workspace.refresh()`, `profile.refresh()`, and `chat.refreshConversationList()`. Select the first workspace and first chat-capable profile if none is selected.

- [ ] **Step 7: Run tests and typecheck**

Run:

```bash
rtk bun run --cwd src/frontend test src/features/chat/components/ChatWorkspace.test.ts
rtk bun run --cwd src/frontend typecheck
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
rtk git add src/frontend/src/features/chat
rtk git commit -m "feat: build chat workspace ui"
```

### Task 12: Build Settings Dialog UI

**Files:**
- Create: `src/frontend/src/features/settings/components/SettingsDialog.vue`
- Create: `src/frontend/src/features/profiles/components/ProfilePanel.vue`
- Create: `src/frontend/src/features/workspaces/components/WorkspacePanel.vue`
- Create: `src/frontend/src/features/workspaces/components/ReindexPanel.vue`
- Modify: `src/frontend/src/features/chat/components/ChatWorkspace.vue`
- Create: `src/frontend/src/features/settings/components/SettingsDialog.test.ts`

- [ ] **Step 1: Write failing settings test**

Create `src/frontend/src/features/settings/components/SettingsDialog.test.ts`:

```ts
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import { useSettingsStore } from '../stores/settingsStore'
import SettingsDialog from './SettingsDialog.vue'

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('SettingsDialog', () => {
  it('renders settings tabs', () => {
    const settings = useSettingsStore()
    settings.show('profiles')

    const wrapper = mount(SettingsDialog)

    expect(wrapper.text()).toContain('LLM Profiles')
    expect(wrapper.text()).toContain('Workspaces')
    expect(wrapper.text()).toContain('Indexing')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
rtk bun run --cwd src/frontend test src/features/settings/components/SettingsDialog.test.ts
```

Expected: FAIL because settings dialog is missing.

- [ ] **Step 3: Implement settings dialog tabs**

Create `src/frontend/src/features/settings/components/SettingsDialog.vue`:

```vue
<script setup lang="ts">
import { useSettingsStore } from '../stores/settingsStore'
import ProfilePanel from '@/features/profiles/components/ProfilePanel.vue'
import WorkspacePanel from '@/features/workspaces/components/WorkspacePanel.vue'
import ReindexPanel from '@/features/workspaces/components/ReindexPanel.vue'

const settings = useSettingsStore()
</script>

<template>
  <v-dialog :model-value="settings.open" max-width="920" @update:model-value="settings.open = $event">
    <v-card>
      <v-card-title class="settings-title">
        Settings
        <v-btn icon="mdi-close" variant="text" aria-label="Close settings" @click="settings.close()" />
      </v-card-title>
      <v-tabs v-model="settings.tab" density="compact">
        <v-tab value="profiles">LLM Profiles</v-tab>
        <v-tab value="workspaces">Workspaces</v-tab>
        <v-tab value="indexing">Indexing</v-tab>
      </v-tabs>
      <v-card-text>
        <v-window v-model="settings.tab">
          <v-window-item value="profiles"><ProfilePanel /></v-window-item>
          <v-window-item value="workspaces"><WorkspacePanel /></v-window-item>
          <v-window-item value="indexing"><ReindexPanel /></v-window-item>
        </v-window>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.settings-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
```

- [ ] **Step 4: Implement profile panel**

Create `src/frontend/src/features/profiles/components/ProfilePanel.vue`:

```vue
<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { useProfileStore } from '../stores/profileStore'
import type { Profile, ProfileCapability } from '../types'

const store = useProfileStore()
const editingId = ref<string | null>(null)
const form = reactive({
  name: '',
  kind: 'openai_compatible' as const,
  base_url: '',
  model: '',
  api_key_ref: '',
  capabilities: ['chat'] as ProfileCapability[],
})

onMounted(() => store.refresh())

function edit(profile: Profile) {
  editingId.value = profile.id
  form.name = profile.name
  form.kind = profile.kind
  form.base_url = profile.base_url
  form.model = profile.model
  form.api_key_ref = profile.api_key_ref ?? ''
  form.capabilities = [...profile.capabilities]
}

async function save() {
  await store.saveProfile(
    {
      name: form.name,
      kind: form.kind,
      base_url: form.base_url,
      model: form.model,
      api_key_ref: form.api_key_ref.trim() === '' ? null : form.api_key_ref,
      capabilities: form.capabilities,
    },
    editingId.value,
  )
  editingId.value = null
}
</script>

<template>
  <div class="settings-grid">
    <v-list density="compact">
      <v-list-item v-for="profile in store.profiles" :key="profile.id" :title="profile.name" :subtitle="profile.model">
        <template #append>
          <v-btn icon="mdi-pencil" variant="text" aria-label="Edit profile" @click="edit(profile)" />
          <v-btn icon="mdi-connection" variant="text" aria-label="Test profile" @click="store.testProfile(profile.id)" />
          <v-btn icon="mdi-delete-outline" variant="text" aria-label="Delete profile" @click="store.deleteProfile(profile.id)" />
        </template>
      </v-list-item>
    </v-list>
    <form class="settings-form" @submit.prevent="save">
      <v-text-field v-model="form.name" label="Name" />
      <v-text-field v-model="form.base_url" label="Base URL" />
      <v-text-field v-model="form.model" label="Model" />
      <v-text-field v-model="form.api_key_ref" label="API key env var" />
      <v-select v-model="form.capabilities" :items="['chat', 'embeddings', 'rerank', 'streaming']" label="Capabilities" multiple chips />
      <v-alert v-if="store.testResult" type="success" variant="tonal">Profile test succeeded</v-alert>
      <v-alert v-if="store.errorMessage" type="error" variant="tonal">{{ store.errorMessage }}</v-alert>
      <v-btn type="submit" color="primary">Save profile</v-btn>
    </form>
  </div>
</template>

<style scoped>
.settings-grid {
  display: grid;
  grid-template-columns: minmax(220px, 320px) 1fr;
  gap: 18px;
}
.settings-form {
  display: grid;
  gap: 10px;
}
</style>
```

- [ ] **Step 5: Implement workspace and reindex panels**

Create `src/frontend/src/features/workspaces/components/WorkspacePanel.vue`:

```vue
<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { useWorkspaceStore } from '../stores/workspaceStore'
import type { Workspace } from '../types'

const store = useWorkspaceStore()
const editingId = ref<string | null>(null)
const form = reactive({
  name: '',
  root_path: '',
  include_globs: '**/*.md, **/*.markdown',
  exclude_globs: '.git/**, .venv/**, node_modules/**',
})

onMounted(() => store.refresh())

function edit(workspace: Workspace) {
  editingId.value = workspace.id
  form.name = workspace.name
  form.root_path = workspace.root_path
  form.include_globs = workspace.include_globs.join(', ')
  form.exclude_globs = workspace.exclude_globs.join(', ')
}

function splitGlobs(value: string): string[] {
  return value.split(',').map((glob) => glob.trim()).filter(Boolean)
}

async function save() {
  await store.saveWorkspace(
    {
      name: form.name,
      root_path: form.root_path,
      include_globs: splitGlobs(form.include_globs),
      exclude_globs: splitGlobs(form.exclude_globs),
    },
    editingId.value,
  )
  editingId.value = null
}
</script>

<template>
  <div class="settings-grid">
    <v-list density="compact">
      <v-list-item v-for="workspace in store.workspaces" :key="workspace.id" :title="workspace.name" :subtitle="workspace.root_path">
        <template #append>
          <v-btn icon="mdi-pencil" variant="text" aria-label="Edit workspace" @click="edit(workspace)" />
          <v-btn icon="mdi-delete-outline" variant="text" aria-label="Delete workspace" @click="store.deleteWorkspace(workspace.id)" />
        </template>
      </v-list-item>
    </v-list>
    <form class="settings-form" @submit.prevent="save">
      <v-text-field v-model="form.name" label="Name" />
      <v-text-field v-model="form.root_path" label="Workspace root" />
      <v-text-field v-model="form.include_globs" label="Include globs" />
      <v-text-field v-model="form.exclude_globs" label="Exclude globs" />
      <v-alert v-if="store.errorMessage" type="error" variant="tonal">{{ store.errorMessage }}</v-alert>
      <v-btn type="submit" color="primary">Save workspace</v-btn>
    </form>
  </div>
</template>

<style scoped>
.settings-grid {
  display: grid;
  grid-template-columns: minmax(240px, 340px) 1fr;
  gap: 18px;
}
.settings-form {
  display: grid;
  gap: 10px;
}
</style>
```

Create `src/frontend/src/features/workspaces/components/ReindexPanel.vue`:

```vue
<script setup lang="ts">
import { onMounted } from 'vue'

import { useWorkspaceStore } from '../stores/workspaceStore'

const store = useWorkspaceStore()

onMounted(() => store.refresh())
</script>

<template>
  <section class="reindex-panel">
    <v-select
      v-model="store.selectedWorkspaceId"
      :items="store.workspaces"
      item-title="name"
      item-value="id"
      label="Workspace"
    />
    <v-btn color="primary" :loading="store.reindexing" :disabled="store.selectedWorkspaceId === null" @click="store.reindexSelectedWorkspace()">
      Reindex
    </v-btn>
    <v-alert v-if="store.reindexResult" type="success" variant="tonal">
      Indexed {{ store.reindexResult.documents_indexed }} documents and {{ store.reindexResult.chunks_indexed }} chunks.
    </v-alert>
    <v-alert v-if="store.errorMessage" type="error" variant="tonal">{{ store.errorMessage }}</v-alert>
  </section>
</template>

<style scoped>
.reindex-panel {
  display: grid;
  max-width: 520px;
  gap: 12px;
}
</style>
```

- [ ] **Step 6: Add settings entry to shell**

In `ChatWorkspace.vue`, add a compact settings icon button in the shell chrome:

```vue
<v-btn icon="mdi-cog" variant="text" aria-label="Settings" @click="settings.show()" />
<SettingsDialog />
```

- [ ] **Step 7: Run tests and typecheck**

Run:

```bash
rtk bun run --cwd src/frontend test src/features/settings/components/SettingsDialog.test.ts
rtk bun run --cwd src/frontend typecheck
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
rtk git add src/frontend/src/features/settings src/frontend/src/features/profiles src/frontend/src/features/workspaces src/frontend/src/features/chat/components/ChatWorkspace.vue
rtk git commit -m "feat: add settings dialog"
```

### Task 13: Startup Error States And Happy-Path Frontend Tests

**Files:**
- Modify: `src/frontend/src/features/chat/components/ChatWorkspace.vue`
- Modify: `src/frontend/src/features/chat/components/ComposerBar.vue`
- Add: `src/frontend/src/features/chat/components/chatFlow.test.ts`

- [ ] **Step 1: Write happy-path chat and search tests**

Create `src/frontend/src/features/chat/components/chatFlow.test.ts`:

```ts
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as chatApi from '../api'
import ChatWorkspace from './ChatWorkspace.vue'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.spyOn(chatApi, 'listFolders').mockResolvedValue([])
  vi.spyOn(chatApi, 'listSessions').mockResolvedValue([])
})

describe('chat flow', () => {
  it('shows recoverable empty configuration state', async () => {
    const wrapper = mount(ChatWorkspace)
    await vi.dynamicImportSettled()

    expect(wrapper.text()).toContain('Create or select a workspace')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
rtk bun run --cwd src/frontend test src/features/chat/components/chatFlow.test.ts
```

Expected: FAIL until workspace/profile stores expose empty configuration text to the UI.

- [ ] **Step 3: Add startup and empty states**

In `ChatWorkspace.vue`, show:

```vue
<v-alert v-if="startupError" type="error" variant="tonal">
  Backend unavailable at {{ apiBaseUrlValue }}.
  <v-btn variant="text" @click="loadInitialData">Retry</v-btn>
</v-alert>
<v-alert v-else-if="workspace.workspaces.length === 0" type="warning" variant="tonal">
  Create or select a workspace in Settings before submitting turns.
</v-alert>
<v-alert v-else-if="profile.chatProfiles.length === 0" type="warning" variant="tonal">
  Create a chat-capable profile in Settings before using Chat mode.
</v-alert>
```

Import `apiBaseUrl()` from the API client and expose it as `apiBaseUrlValue`.

- [ ] **Step 4: Ensure composer disabled reasons are visible**

In `ComposerBar.vue`, compute:

```ts
const disabledReason = computed(() => {
  if (props.pending) return 'Waiting for response'
  if (props.workspaces.length === 0) return 'Workspace required'
  if (props.mode === 'chat' && props.profiles.length === 0) return 'Chat profile required'
  return null
})
```

Render `disabledReason` as compact helper text near the submit button.

- [ ] **Step 5: Run all frontend tests**

Run:

```bash
rtk bun run --cwd src/frontend test
rtk bun run --cwd src/frontend build
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
rtk git add src/frontend/src/features/chat
rtk git commit -m "feat: add frontend empty and error states"
```

### Task 14: Backend Full Verification

**Files:**
- No source changes expected unless verification fails.

- [ ] **Step 1: Run backend test suite**

Run:

```bash
rtk uv run pytest
```

Expected: PASS.

- [ ] **Step 2: Run backend lint and typecheck**

Run:

```bash
rtk uv run ruff check .
rtk uv run pyright
```

Expected: PASS.

- [ ] **Step 3: Fix verification failures with targeted tests**

If a backend verification command fails, write a focused regression test for the failing behavior before changing implementation. Run the focused test to see it fail, fix the code, then rerun the focused test and the full backend verification commands.

- [ ] **Step 4: Commit only if fixes were needed**

```bash
rtk git add src/backend tests pyproject.toml alembic/versions/0001_initial.py
rtk git commit -m "fix: stabilize frontend backend api"
```

Expected: skip this commit if Step 1 and Step 2 passed without source changes.

### Task 15: Frontend Full Verification And Dev Server

**Files:**
- No source changes expected unless verification fails.

- [ ] **Step 1: Run frontend tests and build**

Run:

```bash
rtk bun run --cwd src/frontend test
rtk bun run --cwd src/frontend build
```

Expected: PASS.

- [ ] **Step 2: Start frontend dev server**

Run:

```bash
rtk bun run --cwd src/frontend dev
```

Expected: Vite prints a local URL such as `http://127.0.0.1:5173/`.

- [ ] **Step 3: Smoke the first screen manually**

Open the Vite URL. Expected:

- The app opens directly to the chat workspace.
- The left conversation drawer is visible.
- The composer is visible and disabled when required workspace/profile config is missing.
- The settings dialog opens from the settings icon.

- [ ] **Step 4: Commit only if fixes were needed**

```bash
rtk git add src/frontend
rtk git commit -m "fix: stabilize frontend mvp"
```

Expected: skip this commit if Step 1 passed without source changes.

## Final Verification

Run all required checks before declaring completion:

```bash
rtk uv run pytest
rtk uv run ruff check .
rtk uv run pyright
rtk bun run --cwd src/frontend test
rtk bun run --cwd src/frontend build
```

Expected: all PASS.

## Self-Review Notes

- Spec coverage: package move, session list/detail/patch/delete, conversation folder CRUD and nesting, folder cycle rejection, profile/workspace mutation APIs, explicit chat profile id, persisted search-result turns, synchronous reindex, frontend API client, Pinia state, chat/search composer, folder drawer, settings tabs, empty/error states, and frontend tests are covered.
- Placeholder scan: code-producing steps include concrete file content, commands, and expected outcomes.
- Type consistency: backend response names use `SessionSummary`, `SessionDetail`, `MessageRead`, `ConversationFolderRead`, `ChatResponse`, and `SearchResponse` consistently; frontend mirrors snake_case backend properties in API types.
