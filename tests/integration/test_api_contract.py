from typing import Annotated, Any, cast

import pytest
from calliope.api.app import create_app
from calliope.api.dependencies import get_db_session
from calliope.api.routes import chat as chat_route
from calliope.config import Settings
from calliope.domain.schemas import ChatRequest
from fastapi import Depends
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy.orm import Session

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
    assert "/v1/sessions" in paths
    assert "/v1/sessions/{session_id}" in paths


def test_openapi_contains_conversation_folder_routes() -> None:
    client = TestClient(create_app(Settings(api_title="Calliope", **SETTINGS_WITHOUT_ENV_FILE)))

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert {"get", "post"} <= set(paths["/v1/conversation-folders"])
    assert {"patch", "delete"} <= set(paths["/v1/conversation-folders/{folder_id}"])


def test_chat_route_closes_embedding_client_when_chat_client_creation_fails(
    monkeypatch: MonkeyPatch,
) -> None:
    class FakeEmbeddingClient:
        def __init__(self) -> None:
            self.closed = False

        async def embed(self, text: str) -> list[float]:
            return [0.0]

        async def aclose(self) -> None:
            self.closed = True

    embedding_client = FakeEmbeddingClient()

    def fake_get_embedding_client(session: object) -> FakeEmbeddingClient:
        return embedding_client

    def fake_get_chat_client(session: object) -> object:
        raise RuntimeError("chat client setup failed")

    monkeypatch.setattr(chat_route, "get_embedding_client", fake_get_embedding_client)
    monkeypatch.setattr(chat_route, "get_chat_client", fake_get_chat_client)

    with pytest.raises(RuntimeError, match="chat client setup failed"):
        chat_route.chat(ChatRequest(message="Who is Kaelen?"), session=cast(Session, object()))

    assert embedding_client.closed


def test_openapi_declares_calliope_contract() -> None:
    client = TestClient(create_app(Settings(api_title="Calliope", **SETTINGS_WITHOUT_ENV_FILE)))

    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Calliope"
    paths = schema["paths"]
    expected_paths = {
        "/v1/workspaces",
        "/v1/reindex",
        "/v1/search",
        "/v1/chat",
        "/v1/profiles",
        "/v1/documents",
        "/v1/sources/{chunk_id}",
        "/v1/sessions",
        "/v1/sessions/{session_id}",
        "/v1/conversation-folders",
        "/v1/conversation-folders/{folder_id}",
    }
    assert expected_paths <= set(paths)
    assert {"get", "post"} <= set(paths["/v1/workspaces"])
    assert "post" in paths["/v1/reindex"]
    assert "post" in paths["/v1/search"]
    assert "post" in paths["/v1/chat"]
    assert {"get", "post"} <= set(paths["/v1/profiles"])
    assert "get" in paths["/v1/documents"]
    assert "get" in paths["/v1/sources/{chunk_id}"]
    assert "get" in paths["/v1/sessions"]
    assert {"get", "patch", "delete"} <= set(paths["/v1/sessions/{session_id}"])
    assert {"get", "post"} <= set(paths["/v1/conversation-folders"])
    assert {"patch", "delete"} <= set(paths["/v1/conversation-folders/{folder_id}"])
