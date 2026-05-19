from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from calliope.config import Settings


def create_db_engine(database_url: str):
    return create_engine(database_url, future=True)


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=create_db_engine(database_url), expire_on_commit=False)


def get_session(settings: Settings | None = None) -> Iterator[Session]:
    factory = create_session_factory((settings or Settings()).database_url)
    with factory() as session:
        yield session
