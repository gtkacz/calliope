import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from calliope.db.models import Base


@pytest.fixture(autouse=True)
def clear_calliope_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in tuple(os.environ):
        if key.startswith("CALLIOPE_") and key != "CALLIOPE_TEST_DATABASE_URL":
            monkeypatch.delenv(key, raising=False)


@pytest.fixture(scope="session")
def database_url() -> str:
    return os.environ.get(
        "CALLIOPE_TEST_DATABASE_URL",
        "postgresql+psycopg://calliope:calliope@localhost:5432/calliope",
    )


@pytest.fixture()
def db_engine(database_url: str):
    engine = create_engine(database_url, future=True)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.drop_all(connection)
        Base.metadata.create_all(connection)
    try:
        yield engine
    finally:
        with engine.begin() as connection:
            Base.metadata.drop_all(connection)


@pytest.fixture()
def db_session(db_engine) -> Iterator[Session]:
    factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    with factory() as session:
        yield session
