from datetime import UTC, datetime

from sqlalchemy import inspect, text

from calliope.db.models import (
    Base,
    ChatMessage,
    ChatSession,
    Chunk,
    Document,
    RetrievalTrace,
    Workspace,
)


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
