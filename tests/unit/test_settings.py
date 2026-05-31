import os
from typing import Any

import pytest
from calliope.config import EMBEDDING_DIMENSIONS, Settings


def test_settings_defaults_are_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CALLIOPE_API_TITLE", raising=False)
    monkeypatch.delenv("CALLIOPE_DATABASE_URL", raising=False)
    monkeypatch.delenv("CALLIOPE_EMBEDDING_DIMENSIONS", raising=False)
    monkeypatch.delenv("CALLIOPE_LLM_REQUEST_TIMEOUT_SECONDS", raising=False)

    settings_kwargs: dict[str, Any] = {"_env_file": None}
    settings = Settings(**settings_kwargs)

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.api_title == "Calliope"
    assert settings.embedding_dimensions == EMBEDDING_DIMENSIONS
    assert settings.llm_request_timeout_seconds == 120


def test_calliope_env_is_cleared_before_settings_load() -> None:
    assert "CALLIOPE_EMBEDDING_DIMENSIONS" not in os.environ

    settings_kwargs: dict[str, Any] = {"_env_file": None}
    settings = Settings(**settings_kwargs)

    assert settings.embedding_dimensions == EMBEDDING_DIMENSIONS


def test_settings_loads_llm_request_timeout_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CALLIOPE_LLM_REQUEST_TIMEOUT_SECONDS", "240")

    settings_kwargs: dict[str, Any] = {"_env_file": None}
    settings = Settings(**settings_kwargs)

    assert settings.llm_request_timeout_seconds == 240
