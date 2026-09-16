from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Any, cast

import pytest
from calliope.api import dependencies as api_dependencies
from calliope.api.app import create_app
from calliope.api.dependencies import get_db_session
from calliope.api.routes import chat as chat_route
from calliope.config import EMBEDDING_DIMENSIONS, Settings
from calliope.domain.enums import ProfileCapability, ProfileKind
from calliope.domain.schemas import ChatRequest, ProfileCreate, WorkspaceCreate
from calliope.ingest.indexer import Reindexer
from calliope.llm.openai_compatible import ChatCompletion
from calliope.repositories.documents import DocumentRepository
from calliope.repositories.profiles import ProfileRepository
from calliope.repositories.workspaces import WorkspaceRepository
from fastapi import Depends
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy.orm import Session

SETTINGS_WITHOUT_ENV_FILE: dict[str, Any] = {"_env_file": None}


class FakeOpenAICompatibleClient:
    chat_models: list[str] = []

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: float = 120,
        sampling_params: object = None,
        use_ollama_native: bool = False,
        num_ctx: int | None = None,
        use_koboldcpp: bool = False,
    ) -> None:
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def embed(self, text: str) -> list[float]:
        value = 1.0 if "Kaelen" in text else 0.1
        return [value] * EMBEDDING_DIMENSIONS

    async def chat(self, messages: list[dict[str, str]]) -> ChatCompletion:
        self.chat_models.append(self.model)
        return ChatCompletion(content="Kaelen was exiled from Velmora. [characters/kaelen.md]")

    async def aclose(self) -> None:
        return None


def _chat_client_with_session(db_session: Session) -> TestClient:
    app = create_app(Settings(api_title="Calliope", **SETTINGS_WITHOUT_ENV_FILE))

    def override_get_db_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app)


def _seed_default_profiles(db_session: Session) -> None:
    repository = ProfileRepository(db_session)
    repository.create(
        ProfileCreate(
            name="default-embeddings",
            kind=ProfileKind.OPENAI_COMPATIBLE,
            base_url="http://models.local/v1",
            model="default-embedding-model",
            capabilities=[ProfileCapability.EMBEDDINGS],
        )
    )
    repository.create(
        ProfileCreate(
            name="default-chat",
            kind=ProfileKind.OPENAI_COMPATIBLE,
            base_url="http://models.local/v1",
            model="default-chat-model",
            capabilities=[ProfileCapability.CHAT],
        )
    )


def _seed_world_workspace(db_session: Session) -> str:
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(
            name="api-chat-world",
            root_path=str(Path("tests/fixtures/world").resolve()),
        )
    )
    Reindexer(
        db_session,
        embedding_client=FakeOpenAICompatibleClient(
            base_url="http://models.local/v1",
            model="indexing-embedding-model",
        ),
    ).reindex_workspace(workspace.id)
    return workspace.id


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
    assert "/v1/workspaces/glob-preview" in paths
    assert "/v1/reindex" in paths
    assert "/v1/search" in paths
    assert "/v1/chat" in paths
    assert "/v1/profiles" in paths
    assert "/v1/documents" in paths
    assert "/v1/sources/{chunk_id}" in paths
    assert "/v1/sessions" in paths
    assert "/v1/sessions/{session_id}" in paths


def test_workspace_glob_preview_is_confined_and_classifies_files(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    (tmp_path / "note.md").write_text("note", encoding="utf-8")
    (tmp_path / "nested" / "skip.md").write_text("skip", encoding="utf-8")
    client = TestClient(
        create_app(
            Settings(
                api_title="Calliope",
                browse_root=str(tmp_path),
                **SETTINGS_WITHOUT_ENV_FILE,
            )
        )
    )

    response = client.post(
        "/v1/workspaces/glob-preview",
        json={
            "root_path": str(tmp_path),
            "include_globs": ["**/*.md"],
            "exclude_globs": ["nested/**"],
        },
    )

    assert response.status_code == 200
    assert response.json()["included"] == {"count": 1, "paths": ["note.md"]}
    assert response.json()["ignored"] == {"count": 1, "paths": ["nested/skip.md"]}

    outside = client.post(
        "/v1/workspaces/glob-preview",
        json={"root_path": str(tmp_path.parent), "include_globs": [], "exclude_globs": []},
    )
    assert outside.status_code == 403


def test_openapi_contains_conversation_folder_routes() -> None:
    client = TestClient(create_app(Settings(api_title="Calliope", **SETTINGS_WITHOUT_ENV_FILE)))

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert {"get", "post"} <= set(paths["/v1/conversation-folders"])
    assert {"patch", "delete"} <= set(paths["/v1/conversation-folders/{folder_id}"])


def test_documents_route_filters_by_workspace_id(db_session: Session) -> None:
    workspace_repo = WorkspaceRepository(db_session)
    first_workspace = workspace_repo.create(
        WorkspaceCreate(name="First World", root_path="/tmp/first-world")
    )
    second_workspace = workspace_repo.create(
        WorkspaceCreate(name="Second World", root_path="/tmp/second-world")
    )
    document_repo = DocumentRepository(db_session)
    document_repo.upsert(
        workspace_id=first_workspace.id,
        path="first/note.md",
        title="First Note",
        frontmatter={},
        content_hash="abc",
        modified_at_ns=1_700_000_000_000_000_000,
    )
    document_repo.upsert(
        workspace_id=second_workspace.id,
        path="second/note.md",
        title="Second Note",
        frontmatter={},
        content_hash="def",
        modified_at_ns=1_700_000_000_000_000_001,
    )
    db_session.commit()
    client = _chat_client_with_session(db_session)

    response = client.get("/v1/documents", params={"workspace_id": first_workspace.id})

    assert response.status_code == 200
    assert [document["path"] for document in response.json()] == ["first/note.md"]


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

    def fake_get_embedding_client(
        session: object,
        settings: object,
    ) -> FakeEmbeddingClient:
        return embedding_client

    def fake_get_chat_client_for_profile(
        session: object,
        profile_id: str | None,
        settings: object,
        policy: object = None,
    ) -> object:
        assert profile_id is None
        raise RuntimeError("chat client setup failed")

    monkeypatch.setattr(chat_route, "get_embedding_client", fake_get_embedding_client)
    monkeypatch.setattr(
        chat_route,
        "get_chat_client_for_profile",
        fake_get_chat_client_for_profile,
    )

    with pytest.raises(RuntimeError, match="chat client setup failed"):
        chat_route.chat(
            ChatRequest(message="Who is Kaelen?"),
            session=cast(Session, object()),
            settings=Settings(api_title="Calliope", **SETTINGS_WITHOUT_ENV_FILE),
        )

    assert embedding_client.closed


def test_chat_route_uses_explicit_chat_profile(
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        api_dependencies,
        "OpenAICompatibleClient",
        FakeOpenAICompatibleClient,
    )
    FakeOpenAICompatibleClient.chat_models = []
    _seed_default_profiles(db_session)
    workspace_id = _seed_world_workspace(db_session)
    chat_profile = ProfileRepository(db_session).create(
        ProfileCreate(
            name="explicit-chat",
            kind=ProfileKind.OPENAI_COMPATIBLE,
            base_url="http://models.local/v1",
            model="explicit-chat-model",
            capabilities=[ProfileCapability.CHAT],
        )
    )
    client = _chat_client_with_session(db_session)

    response = client.post(
        "/v1/chat",
        json={
            "message": "Where was Kaelen exiled from?",
            "workspace_id": workspace_id,
            "chat_profile_id": chat_profile.id,
            "limit": 1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assistant_message"]["metadata"]["chat_profile_id"] == chat_profile.id
    assert FakeOpenAICompatibleClient.chat_models == [
        "explicit-chat-model",
        "explicit-chat-model",
    ]


def test_chat_route_returns_404_for_missing_explicit_chat_profile(
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        api_dependencies,
        "OpenAICompatibleClient",
        FakeOpenAICompatibleClient,
    )
    _seed_default_profiles(db_session)
    client = _chat_client_with_session(db_session)

    response = client.post(
        "/v1/chat",
        json={
            "message": "Where was Kaelen exiled from?",
            "chat_profile_id": "profile_missing",
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "connection_profile_not_found"


def test_chat_route_returns_400_for_non_chat_explicit_profile(
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        api_dependencies,
        "OpenAICompatibleClient",
        FakeOpenAICompatibleClient,
    )
    _seed_default_profiles(db_session)
    embeddings_only = ProfileRepository(db_session).create(
        ProfileCreate(
            name="embeddings-only",
            kind=ProfileKind.OPENAI_COMPATIBLE,
            base_url="http://models.local/v1",
            model="embeddings-only-model",
            capabilities=[ProfileCapability.EMBEDDINGS],
        )
    )
    client = _chat_client_with_session(db_session)

    response = client.post(
        "/v1/chat",
        json={
            "message": "Where was Kaelen exiled from?",
            "chat_profile_id": embeddings_only.id,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "model_profile_missing_capability"


def test_chat_route_omitted_chat_profile_uses_default_chat_profile(
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        api_dependencies,
        "OpenAICompatibleClient",
        FakeOpenAICompatibleClient,
    )
    FakeOpenAICompatibleClient.chat_models = []
    _seed_default_profiles(db_session)
    workspace_id = _seed_world_workspace(db_session)
    client = _chat_client_with_session(db_session)

    response = client.post(
        "/v1/chat",
        json={
            "message": "Where was Kaelen exiled from?",
            "workspace_id": workspace_id,
            "limit": 1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assistant_message"]["metadata"]["chat_profile_id"] is None
    assert FakeOpenAICompatibleClient.chat_models == [
        "default-chat-model",
        "default-chat-model",
    ]


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


def test_openapi_search_response_includes_nullable_session_turn_fields() -> None:
    client = TestClient(create_app(Settings(api_title="Calliope", **SETTINGS_WITHOUT_ENV_FILE)))

    response = client.get("/openapi.json")

    assert response.status_code == 200
    search_response = response.json()["components"]["schemas"]["SearchResponse"]
    properties = search_response["properties"]
    assert properties["session"]["anyOf"][0]["$ref"].endswith("/SessionSummary")
    assert properties["session"]["anyOf"][1]["type"] == "null"
    assert properties["search_message"]["anyOf"][0]["$ref"].endswith("/MessageRead")
    assert properties["search_message"]["anyOf"][1]["type"] == "null"
