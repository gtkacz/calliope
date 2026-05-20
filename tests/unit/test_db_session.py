from sqlalchemy.orm import sessionmaker

from calliope.db.session import create_db_engine, create_session_factory


def test_create_session_factory_reuses_factory_for_same_database_url() -> None:
    database_url = "sqlite+pysqlite:///:memory:"

    assert create_session_factory(database_url) is create_session_factory(database_url)


def test_create_db_engine_returns_engine() -> None:
    engine = create_db_engine("sqlite+pysqlite:///:memory:")

    assert engine.url.drivername == "sqlite+pysqlite"


def test_create_session_factory_returns_sessionmaker() -> None:
    factory = create_session_factory("sqlite+pysqlite:///:memory:")

    assert isinstance(factory, sessionmaker)
