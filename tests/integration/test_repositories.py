from datetime import UTC, datetime

from calliope.db.models import (
    Base,
    ChatMessage,
    ChatSession,
    Chunk,
    ConversationFolder,
    Document,
    RetrievalTrace,
    Workspace,
)
from calliope.domain.errors import AppError
from calliope.domain.schemas import WorkspaceCreate
from calliope.repositories.chats import ChatRepository
from calliope.repositories.documents import DocumentRepository
from calliope.repositories.workspaces import WorkspaceRepository
from sqlalchemy import inspect, text


def test_metadata_contains_mvp_tables() -> None:
    assert {
        "workspaces",
        "documents",
        "chunks",
        "chat_sessions",
        "chat_messages",
        "retrieval_traces",
        "connection_profiles",
    }.issubset(Base.metadata.tables)


def test_database_has_vector_extension(db_session) -> None:
    version = db_session.execute(text("select extname from pg_extension where extname='vector'"))

    assert version.scalar_one() == "vector"


def test_database_tables_are_created(db_engine) -> None:
    inspector = inspect(db_engine)

    assert "chunks" in inspector.get_table_names()


def test_database_schema_is_applied_by_migrations(db_session) -> None:
    version = db_session.execute(text("select version_num from alembic_version"))

    assert version.scalar_one() == "0001_initial"


def test_vector_l2_distance_orders_nearest_chunk_first(db_session) -> None:
    workspace = Workspace(
        name="vector-test",
        root_path="/tmp/vector-test",
        include_globs=["**/*.md"],
        exclude_globs=[],
    )
    document = Document(
        workspace=workspace,
        path="notes.md",
        title="Notes",
        frontmatter_json={},
        content_hash="abc",
        modified_at=datetime.now(UTC),
    )
    nearer = Chunk(
        document=document,
        chunk_index=0,
        heading_path="Near",
        text="near",
        token_count=1,
        metadata_json={},
        embedding=[0.0] * 384,
    )
    farther = Chunk(
        document=document,
        chunk_index=1,
        heading_path="Far",
        text="far",
        token_count=1,
        metadata_json={},
        embedding=[1.0] * 384,
    )
    db_session.add_all([workspace, document, nearer, farther])
    db_session.commit()

    ordered_ids = db_session.execute(
        text("select id from chunks order by embedding <-> :query limit 2"),
        {"query": "[" + ",".join(["0"] * 384) + "]"},
    ).scalars()

    assert list(ordered_ids) == [nearer.id, farther.id]


def test_owned_rows_are_deleted_with_parent_records(db_session) -> None:
    workspace = Workspace(
        name="cascade-test",
        root_path="/tmp/cascade-test",
        include_globs=["**/*.md"],
        exclude_globs=[],
    )
    document = Document(
        workspace=workspace,
        path="notes.md",
        title="Notes",
        frontmatter_json={},
        content_hash="abc",
        modified_at=datetime.now(UTC),
    )
    chunk = Chunk(
        document=document,
        chunk_index=0,
        heading_path="Root",
        text="text",
        token_count=1,
        metadata_json={},
    )
    session = ChatSession(title="Session")
    message = ChatMessage(session=session, role="user", content="Question", metadata_json={})
    trace = RetrievalTrace(
        session=session,
        message=message,
        query="Question",
        policy="default",
        selected_sources_json=[],
        scores_json={},
    )
    db_session.add_all([workspace, document, chunk, session, message, trace])
    db_session.commit()

    db_session.delete(workspace)
    db_session.delete(session)
    db_session.commit()

    assert db_session.get(Document, document.id) is None
    assert db_session.get(Chunk, chunk.id) is None
    assert db_session.get(ChatMessage, message.id) is None
    assert db_session.get(RetrievalTrace, trace.id) is None


def test_deleting_message_nulls_retrieval_trace_message_reference(db_session) -> None:
    session = ChatSession(title="Session")
    message = ChatMessage(session=session, role="user", content="Question", metadata_json={})
    trace = RetrievalTrace(
        session=session,
        message=message,
        query="Question",
        policy="default",
        selected_sources_json=[],
        scores_json={},
    )
    db_session.add_all([session, message, trace])
    db_session.commit()

    db_session.delete(message)
    db_session.commit()
    db_session.refresh(trace)

    assert trace.message_id is None


def test_metadata_contains_frontend_conversation_folder_tables() -> None:
    assert "conversation_folders" in Base.metadata.tables
    chat_sessions = Base.metadata.tables["chat_sessions"]
    assert "folder_id" in chat_sessions.columns
    folder_id = chat_sessions.columns["folder_id"]
    folder_fk = next(iter(folder_id.foreign_keys))
    assert folder_fk.ondelete == "SET NULL"

    conversation_folders = Base.metadata.tables["conversation_folders"]
    parent_id = conversation_folders.columns["parent_id"]
    parent_fk = next(iter(parent_id.foreign_keys))
    assert parent_fk.ondelete == "CASCADE"


def test_deleting_folder_unfiles_sessions(db_session) -> None:
    folder = ConversationFolder(name="Act I", position=0)
    session = ChatSession(title="Scene", folder=folder)
    db_session.add_all([folder, session])
    db_session.commit()

    db_session.delete(folder)
    db_session.commit()
    db_session.refresh(session)

    assert session.folder_id is None


def test_chat_repository_get_session_returns_folder_id(db_session) -> None:
    folder = ConversationFolder(name="Act I", position=0)
    session = ChatSession(title="Scene", folder=folder)
    db_session.add_all([folder, session])
    db_session.commit()

    read = ChatRepository(db_session).get_session(session.id)

    assert read.folder_id == folder.id


def test_chat_repository_get_session_returns_none_folder_id_for_unfiled_session(db_session) -> None:
    session = ChatSession(title="Loose Scene")
    db_session.add(session)
    db_session.commit()

    read = ChatRepository(db_session).get_session(session.id)

    assert read.folder_id is None


def test_workspace_repository_creates_and_lists(db_session) -> None:
    repo = WorkspaceRepository(db_session)
    created = repo.create(WorkspaceCreate(name="World", root_path="/tmp/world"))

    listed = repo.list()

    assert created.id.startswith("workspace_")
    assert [workspace.name for workspace in listed] == ["World"]


def test_workspace_repository_get_raises_for_missing_workspace(db_session) -> None:
    repo = WorkspaceRepository(db_session)

    try:
        repo.get("workspace_missing")
    except AppError as exc:
        assert exc.code == "workspace_not_found"
        assert exc.status_code == 404
        assert exc.details == {"workspace_id": "workspace_missing"}
    else:
        raise AssertionError("expected AppError")


def test_workspace_repository_duplicate_name_raises_and_rolls_back(db_session) -> None:
    repo = WorkspaceRepository(db_session)
    repo.create(WorkspaceCreate(name="World", root_path="/tmp/world"))

    try:
        repo.create(WorkspaceCreate(name="World", root_path="/tmp/other-world"))
    except AppError as exc:
        assert exc.code == "workspace_already_exists"
        assert exc.message == "Workspace already exists."
        assert exc.status_code == 409
        assert exc.details == {"name": "World"}
    else:
        raise AssertionError("expected AppError")

    assert [workspace.name for workspace in repo.list()] == ["World"]


def test_document_repository_upsert_returns_flushed_document_row(db_session) -> None:
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(name="Document World", root_path="/tmp/document-world")
    )

    document = DocumentRepository(db_session).upsert(
        workspace_id=workspace.id,
        path="notes.md",
        title="Notes",
        frontmatter={},
        content_hash="abc",
        modified_at_ns=1_700_000_000_000_000_000,
    )

    assert isinstance(document, Document)
    assert document.id.startswith("document_")
    assert db_session.get(Document, document.id) is document


def test_document_repository_public_reads_hide_deleted_documents(db_session) -> None:
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(name="Deleted Document World", root_path="/tmp/deleted-document-world")
    )
    repo = DocumentRepository(db_session)
    document = repo.upsert(
        workspace_id=workspace.id,
        path="notes.md",
        title="Notes",
        frontmatter={},
        content_hash="abc",
        modified_at_ns=1_700_000_000_000_000_000,
    )
    document.deleted_at = datetime.now(UTC)
    db_session.commit()

    assert repo.list() == []
    try:
        repo.get(document.id)
    except AppError as exc:
        assert exc.code == "document_not_found"
        assert exc.status_code == 404
    else:
        raise AssertionError("expected AppError")

    revived = repo.upsert(
        workspace_id=workspace.id,
        path="notes.md",
        title="Notes",
        frontmatter={},
        content_hash="def",
        modified_at_ns=1_700_000_000_000_000_001,
    )

    assert revived.id == document.id
    assert revived.deleted_at is None
    assert [listed.id for listed in repo.list()] == [document.id]
