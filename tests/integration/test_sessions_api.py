from collections.abc import Iterator
from datetime import UTC, datetime

from calliope.api.app import create_app
from calliope.api.dependencies import get_db_session
from calliope.config import Settings
from calliope.db.models import ChatMessage, ChatSession
from calliope.domain.errors import AppError
from calliope.domain.schemas import ConversationFolderCreate, SessionPatch
from calliope.repositories.chats import ChatRepository
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

SETTINGS_WITHOUT_ENV_FILE = {"_env_file": None}


def _client_with_session(db_session: Session) -> TestClient:
    app = create_app(Settings(api_title="Calliope", **SETTINGS_WITHOUT_ENV_FILE))

    def override_get_db_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app)


def test_session_repository_lists_details_patches_and_deletes(db_session) -> None:
    repo = ChatRepository(db_session)
    folder = repo.create_folder(ConversationFolderCreate(name="Filed"))
    first = repo.create_session(title="First")
    second = repo.create_session(title="Second")
    question = repo.add_message(first.id, "user", "Question", {"turn_kind": "chat_user"})
    answer = repo.add_message(first.id, "assistant", "Answer", {"turn_kind": "assistant"})
    question.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    answer.created_at = datetime(2026, 1, 2, tzinfo=UTC)
    db_session.commit()

    patched = repo.update_session(first.id, SessionPatch(title="Renamed", folder_id=folder.id))
    assert patched.title == "Renamed"
    assert patched.folder_id == folder.id

    summaries = repo.list_sessions()
    assert {session.id for session in summaries} == {first.id, second.id}
    assert repo.list_sessions(folder_id=folder.id)[0].id == first.id

    detail = repo.get_session_detail(first.id)
    assert detail.folder_id == folder.id
    assert [message.role for message in detail.messages] == ["user", "assistant"]
    assert detail.messages[0].metadata == {"turn_kind": "chat_user"}

    repo.delete_session(first.id)
    assert db_session.get(ChatSession, first.id) is None
    assert db_session.query(ChatMessage).filter_by(session_id=first.id).count() == 0


def test_session_repository_invalid_folder_update_does_not_mutate_title(db_session) -> None:
    repo = ChatRepository(db_session)
    chat_session = repo.create_session(title="Original")
    db_session.commit()

    try:
        repo.update_session(
            chat_session.id,
            SessionPatch(title="Mutated", folder_id="folder_missing"),
        )
    except AppError as exc:
        assert exc.code == "conversation_folder_not_found"
        assert exc.status_code == 404
    else:
        raise AssertionError("expected AppError")

    db_session.rollback()
    db_session.refresh(chat_session)
    assert chat_session.title == "Original"
    assert repo.get_session(chat_session.id).title == "Original"


def test_session_detail_orders_messages_by_created_at_then_id(db_session) -> None:
    repo = ChatRepository(db_session)
    chat_session = repo.create_session(title="Thread")
    first = repo.add_message(chat_session.id, "assistant", "Second by id", {})
    second = repo.add_message(chat_session.id, "user", "First by id", {})
    first.id = "message_b"
    second.id = "message_a"
    shared_created_at = datetime(2026, 1, 1, tzinfo=UTC)
    first.created_at = shared_created_at
    second.created_at = shared_created_at
    db_session.commit()

    detail = repo.get_session_detail(chat_session.id)

    assert [message.id for message in detail.messages] == ["message_a", "message_b"]


def test_session_api_lists_details_patches_and_deletes(db_session) -> None:
    repo = ChatRepository(db_session)
    folder = repo.create_folder(ConversationFolderCreate(name="Filed"))
    older = repo.create_session(title="Older")
    newer = repo.create_session(title="Newer")
    question = repo.add_message(newer.id, "user", "Question", {"turn_kind": "chat_user"})
    answer = repo.add_message(newer.id, "assistant", "Answer", {"turn_kind": "assistant"})
    question.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    answer.created_at = datetime(2026, 1, 2, tzinfo=UTC)
    older.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
    newer.updated_at = datetime(2026, 1, 2, tzinfo=UTC)
    db_session.commit()
    client = _client_with_session(db_session)

    list_response = client.get("/v1/sessions")
    assert list_response.status_code == 200
    listed = list_response.json()
    assert [session["id"] for session in listed] == [newer.id, older.id]

    detail_response = client.get(f"/v1/sessions/{newer.id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == newer.id
    assert [message["role"] for message in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][0]["metadata"] == {"turn_kind": "chat_user"}

    patch_response = client.patch(
        f"/v1/sessions/{newer.id}",
        json={"title": "Renamed", "folder_id": folder.id},
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["title"] == "Renamed"
    assert patched["folder_id"] == folder.id

    filtered_response = client.get("/v1/sessions", params={"folder_id": folder.id})
    assert filtered_response.status_code == 200
    assert [session["id"] for session in filtered_response.json()] == [newer.id]

    delete_response = client.delete(f"/v1/sessions/{newer.id}")
    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert db_session.get(ChatSession, newer.id) is None
    assert db_session.query(ChatMessage).filter_by(session_id=newer.id).count() == 0


def test_session_api_returns_error_response_for_missing_session(db_session) -> None:
    client = _client_with_session(db_session)

    response = client.get("/v1/sessions/session_missing")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "session_not_found",
            "message": "Chat session not found.",
            "details": {"session_id": "session_missing"},
        }
    }


def test_sessions_routes_openapi_shape() -> None:
    client = TestClient(create_app(Settings(api_title="Calliope", **SETTINGS_WITHOUT_ENV_FILE)))

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert {"get"} <= set(paths["/v1/sessions"])
    assert {"get", "patch", "delete"} <= set(paths["/v1/sessions/{session_id}"])
