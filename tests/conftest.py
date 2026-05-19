import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from alembic import command

DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg://calliope:calliope@localhost:5432/calliope_test"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def assert_test_database_url(database_url: str) -> None:
    database_name = make_url(database_url).database or ""
    normalized_database_name = database_name.lower()
    if (
        normalized_database_name != "calliope_test"
        and not normalized_database_name.endswith("_test")
    ):
        msg = (
            "Refusing destructive test database operation against "
            f"non-test database {database_name!r}"
        )
        raise RuntimeError(msg)


def ensure_test_database(database_url: str) -> None:
    assert_test_database_url(database_url)
    url = make_url(database_url)
    database_name = url.database
    if database_name is None:
        msg = "Refusing destructive test database operation without a database name"
        raise RuntimeError(msg)

    maintenance_engine = create_engine(
        url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        future=True,
    )
    try:
        with maintenance_engine.connect() as connection:
            exists = connection.execute(
                text("select 1 from pg_database where datname = :database_name"),
                {"database_name": database_name},
            ).scalar()
            if exists is None:
                quoted_database_name = connection.dialect.identifier_preparer.quote(database_name)
                connection.execute(text(f"CREATE DATABASE {quoted_database_name}"))
    finally:
        maintenance_engine.dispose()


def alembic_config(database_url: str) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@pytest.fixture(autouse=True)
def clear_calliope_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in tuple(os.environ):
        if key.startswith("CALLIOPE_") and key != "CALLIOPE_TEST_DATABASE_URL":
            monkeypatch.delenv(key, raising=False)


@pytest.fixture(scope="session")
def database_url() -> str:
    return os.environ.get(
        "CALLIOPE_TEST_DATABASE_URL",
        DEFAULT_TEST_DATABASE_URL,
    )


@pytest.fixture()
def db_engine(database_url: str) -> Iterator[Engine]:
    assert_test_database_url(database_url)
    ensure_test_database(database_url)
    command.upgrade(alembic_config(database_url), "head")
    engine = create_engine(database_url, future=True)
    try:
        yield engine
    finally:
        engine.dispose()
        assert_test_database_url(database_url)
        command.downgrade(alembic_config(database_url), "base")


@pytest.fixture()
def db_session(db_engine) -> Iterator[Session]:
    factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    with factory() as session:
        yield session
