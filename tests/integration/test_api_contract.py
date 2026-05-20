from typing import Annotated, Any

from fastapi import Depends
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy.orm import Session

from calliope.api.app import create_app
from calliope.api.dependencies import get_db_session
from calliope.config import Settings

SETTINGS_WITHOUT_ENV_FILE: dict[str, Any] = {"_env_file": None}


def test_openapi_document_exists() -> None:
    client = TestClient(create_app(Settings(api_title="Calliope", **SETTINGS_WITHOUT_ENV_FILE)))

    response = client.get("/openapi.json")

    assert response.status_code == 200
    body = response.json()
    assert body["info"]["title"] == "Calliope"


def test_app_retains_injected_settings() -> None:
    settings = Settings(api_title="Calliope Test", **SETTINGS_WITHOUT_ENV_FILE)
    app = create_app(settings)

    assert app.state.settings is settings


def test_db_session_uses_injected_app_settings(monkeypatch: MonkeyPatch) -> None:
    captured_database_urls: list[str] = []
    settings = Settings(
        api_title="Calliope Test",
        database_url="sqlite+pysqlite:///injected-test.db",
        **SETTINGS_WITHOUT_ENV_FILE,
    )

    class FakeSessionContext:
        def __call__(self) -> "FakeSessionContext":
            return self

        def __enter__(self) -> object:
            return object()

        def __exit__(self, *args: object) -> None:
            return None

    def fake_create_session_factory(database_url: str) -> FakeSessionContext:
        captured_database_urls.append(database_url)
        return FakeSessionContext()

    monkeypatch.setattr(
        "calliope.api.dependencies.create_session_factory",
        fake_create_session_factory,
    )

    app = create_app(settings)

    @app.get("/_test-db-session")
    def test_route(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> dict[str, bool]:
        return {"has_session": session is not None}

    client = TestClient(app)

    response = client.get("/_test-db-session")

    assert response.status_code == 200
    assert response.json() == {"has_session": True}
    assert captured_database_urls == [settings.database_url]


def test_openapi_contains_mvp_routes() -> None:
    client = TestClient(create_app(Settings(api_title="Calliope", **SETTINGS_WITHOUT_ENV_FILE)))

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/v1/workspaces" in paths
    assert "/v1/reindex" in paths
    assert "/v1/search" in paths
    assert "/v1/chat" in paths
    assert "/v1/profiles" in paths
    assert "/v1/documents" in paths
    assert "/v1/sources/{chunk_id}" in paths
    assert "/v1/sessions/{session_id}" in paths
