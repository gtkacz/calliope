import os
from collections.abc import Iterator
from typing import Annotated

from calliope.config import Settings
from calliope.db.session import create_session_factory
from calliope.domain.enums import ProfileCapability
from calliope.domain.schemas import ProfileRead
from calliope.llm.openai_compatible import OpenAICompatibleClient
from calliope.services.profiles import ProfileService
from fastapi import Depends, Request
from sqlalchemy.orm import Session


def get_db_session(request: Request) -> Iterator[Session]:
    settings = getattr(request.app.state, "settings", None) or Settings()
    factory = create_session_factory(settings.database_url)
    with factory() as session:
        yield session


def api_key_for(profile: ProfileRead) -> str | None:
    if profile.api_key_ref is None:
        return None

    return os.environ.get(profile.api_key_ref)


def get_embedding_client(
    session: Annotated[Session, Depends(get_db_session)],
) -> OpenAICompatibleClient:
    profile = ProfileService(session).require_capability(
        "default-embeddings",
        ProfileCapability.EMBEDDINGS,
    )
    return OpenAICompatibleClient(
        base_url=profile.base_url,
        model=profile.model,
        api_key=api_key_for(profile),
    )


def get_chat_client(
    session: Annotated[Session, Depends(get_db_session)],
) -> OpenAICompatibleClient:
    profile = ProfileService(session).require_capability(
        "default-chat",
        ProfileCapability.CHAT,
    )
    return OpenAICompatibleClient(
        base_url=profile.base_url,
        model=profile.model,
        api_key=api_key_for(profile),
    )
