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


def get_settings(request: Request) -> Settings:
    return getattr(request.app.state, "settings", None) or Settings()


def get_db_session(request: Request) -> Iterator[Session]:
    settings = get_settings(request)
    factory = create_session_factory(settings.database_url)
    with factory() as session:
        yield session


def api_key_for(profile: ProfileRead) -> str | None:
    if profile.api_key_ref is None:
        return None

    return os.environ.get(profile.api_key_ref)


def get_embedding_client(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> OpenAICompatibleClient:
    profile = ProfileService(session).require_default_capability(ProfileCapability.EMBEDDINGS)
    return OpenAICompatibleClient(
        base_url=profile.base_url,
        model=profile.model,
        api_key=api_key_for(profile),
        timeout_seconds=settings.llm_request_timeout_seconds,
    )


def get_chat_client(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> OpenAICompatibleClient:
    profile = ProfileService(session).require_default_capability(ProfileCapability.CHAT)
    return OpenAICompatibleClient(
        base_url=profile.base_url,
        model=profile.model,
        api_key=api_key_for(profile),
        timeout_seconds=settings.llm_request_timeout_seconds,
    )


def get_chat_client_for_profile(
    session: Session,
    profile_id: str | None,
    settings: Settings,
) -> OpenAICompatibleClient:
    if profile_id is None:
        return get_chat_client(session, settings)
    profile = ProfileService(session).require_capability_by_id(
        profile_id,
        ProfileCapability.CHAT,
    )
    return OpenAICompatibleClient(
        base_url=profile.base_url,
        model=profile.model,
        api_key=api_key_for(profile),
        timeout_seconds=settings.llm_request_timeout_seconds,
    )
