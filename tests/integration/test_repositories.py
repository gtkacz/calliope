from sqlalchemy import inspect, text

from calliope.db.models import Base


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
