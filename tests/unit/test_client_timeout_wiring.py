from datetime import UTC, datetime
from typing import Any, cast

from calliope.api import dependencies as api_dependencies
from calliope.cli import profile_client
from calliope.config import Settings
from calliope.domain.enums import ProfileCapability, ProfileKind
from calliope.domain.schemas import ProfileRead
from sqlalchemy.orm import Session


class FakeProfileService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def require_default_capability(self, capability: ProfileCapability) -> ProfileRead:
        return ProfileRead(
            id=f"profile_{capability.value}",
            name=f"default-{capability.value}",
            kind=ProfileKind.OPENAI_COMPATIBLE,
            base_url="http://models.local/v1",
            model=f"{capability.value}-model",
            capabilities=[capability],
            created_at=datetime(2026, 5, 30, tzinfo=UTC),
        )

    def require_capability_by_id(
        self,
        profile_id: str,
        capability: ProfileCapability,
    ) -> ProfileRead:
        return ProfileRead(
            id=profile_id,
            name="explicit-chat",
            kind=ProfileKind.OPENAI_COMPATIBLE,
            base_url="http://models.local/v1",
            model="explicit-chat-model",
            capabilities=[capability],
            created_at=datetime(2026, 5, 30, tzinfo=UTC),
        )


class RecordingClient:
    constructed: list[dict[str, Any]] = []

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: float = 30,
        sampling_params: object = None,
    ) -> None:
        self.constructed.append(
            {
                "base_url": base_url,
                "model": model,
                "api_key": api_key,
                "timeout_seconds": timeout_seconds,
            }
        )


def test_api_default_clients_use_configured_llm_timeout(
    monkeypatch,
) -> None:
    monkeypatch.setattr(api_dependencies, "ProfileService", FakeProfileService)
    monkeypatch.setattr(api_dependencies, "OpenAICompatibleClient", RecordingClient)
    RecordingClient.constructed = []
    settings = Settings(llm_request_timeout_seconds=240)
    session = cast(Session, object())

    api_dependencies.get_embedding_client(session, settings)
    api_dependencies.get_chat_client(session, settings)

    assert [client["timeout_seconds"] for client in RecordingClient.constructed] == [240, 240]


def test_api_explicit_chat_client_uses_configured_llm_timeout(
    monkeypatch,
) -> None:
    monkeypatch.setattr(api_dependencies, "ProfileService", FakeProfileService)
    monkeypatch.setattr(api_dependencies, "OpenAICompatibleClient", RecordingClient)
    RecordingClient.constructed = []
    settings = Settings(llm_request_timeout_seconds=180)

    api_dependencies.get_chat_client_for_profile(cast(Session, object()), "profile_chat", settings)

    assert RecordingClient.constructed[0]["timeout_seconds"] == 180


def test_cli_profile_client_uses_configured_llm_timeout(monkeypatch) -> None:
    monkeypatch.setattr("calliope.cli.ProfileService", FakeProfileService)
    monkeypatch.setattr("calliope.cli.OpenAICompatibleClient", RecordingClient)
    RecordingClient.constructed = []
    settings = Settings(llm_request_timeout_seconds=300)

    profile_client(cast(Session, object()), ProfileCapability.CHAT, settings)

    assert RecordingClient.constructed[0]["timeout_seconds"] == 300
