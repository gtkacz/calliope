from typing import Any

import pytest

from calliope.config import Settings


def test_settings_defaults_are_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CALLIOPE_API_TITLE", raising=False)
    monkeypatch.delenv("CALLIOPE_DATABASE_URL", raising=False)
    monkeypatch.delenv("CALLIOPE_EMBEDDING_DIMENSIONS", raising=False)

    settings_kwargs: dict[str, Any] = {"_env_file": None}
    settings = Settings(**settings_kwargs)

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.api_title == "Calliope"
    assert settings.embedding_dimensions == 384
