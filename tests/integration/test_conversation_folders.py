from typing import Any

from calliope.api.app import create_app
from calliope.api.dependencies import get_db_session
from calliope.config import Settings
from calliope.domain.errors import AppError
from calliope.domain.schemas import ConversationFolderCreate, ConversationFolderPatch
from calliope.repositories.chats import ChatRepository
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

SETTINGS_WITHOUT_ENV_FILE: dict[str, Any] = {"_env_file": None}


def _client_with_session(db_session: Session) -> TestClient:
    app = create_app(Settings(api_title="Calliope", **SETTINGS_WITHOUT_ENV_FILE))

    def override_get_db_session() -> Session:
        return db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app)


def test_folder_repository_creates_lists_updates_and_deletes(db_session) -> None:
    repo = ChatRepository(db_session)
    parent = repo.create_folder(ConversationFolderCreate(name="Worldbuilding", position=0))
    child = repo.create_folder(
        ConversationFolderCreate(name="Act I", parent_id=parent.id, position=1)
    )

    listed = repo.list_folders()
    assert [folder.name for folder in listed] == ["Worldbuilding", "Act I"]
    assert listed[1].parent_id == parent.id

    updated = repo.update_folder(
        child.id,
        ConversationFolderPatch(name="Act II", parent_id=None, position=2),
    )
    assert updated.name == "Act II"
    assert updated.parent_id is None
    assert updated.position == 2

    repo.delete_folder(parent.id)
    assert [folder.id for folder in repo.list_folders()] == [child.id]


def test_folder_repository_rejects_cycles(db_session) -> None:
    repo = ChatRepository(db_session)
    parent = repo.create_folder(ConversationFolderCreate(name="Parent", position=0))
    child = repo.create_folder(ConversationFolderCreate(name="Child", parent_id=parent.id))

    try:
        repo.update_folder(parent.id, ConversationFolderPatch(parent_id=child.id))
    except AppError as exc:
        assert exc.code == "conversation_folder_cycle"
        assert exc.status_code == 400
        assert exc.details == {"folder_id": parent.id, "parent_id": child.id}
    else:
        raise AssertionError("expected AppError")


def test_folder_repository_rejects_self_parent(db_session) -> None:
    repo = ChatRepository(db_session)
    folder = repo.create_folder(ConversationFolderCreate(name="Folder"))

    try:
        repo.update_folder(folder.id, ConversationFolderPatch(parent_id=folder.id))
    except AppError as exc:
        assert exc.code == "conversation_folder_cycle"
        assert exc.status_code == 400
        assert exc.details == {"folder_id": folder.id, "parent_id": folder.id}
    else:
        raise AssertionError("expected AppError")


def test_folder_repository_rejects_deeper_descendant_cycle(db_session) -> None:
    repo = ChatRepository(db_session)
    root = repo.create_folder(ConversationFolderCreate(name="Root"))
    child = repo.create_folder(ConversationFolderCreate(name="Child", parent_id=root.id))
    grandchild = repo.create_folder(ConversationFolderCreate(name="Grandchild", parent_id=child.id))

    try:
        repo.update_folder(root.id, ConversationFolderPatch(parent_id=grandchild.id))
    except AppError as exc:
        assert exc.code == "conversation_folder_cycle"
        assert exc.status_code == 400
        assert exc.details == {"folder_id": root.id, "parent_id": grandchild.id}
    else:
        raise AssertionError("expected AppError")


def test_folder_repository_rejects_missing_parent(db_session) -> None:
    repo = ChatRepository(db_session)

    try:
        repo.create_folder(ConversationFolderCreate(name="Child", parent_id="folder_missing"))
    except AppError as exc:
        assert exc.code == "conversation_folder_invalid_parent"
        assert exc.status_code == 400
    else:
        raise AssertionError("expected AppError")


def test_folder_repository_invalid_parent_update_does_not_mutate_other_fields(db_session) -> None:
    repo = ChatRepository(db_session)
    folder = repo.create_folder(ConversationFolderCreate(name="Original", position=0))

    try:
        repo.update_folder(
            folder.id,
            ConversationFolderPatch(name="Mutated", parent_id="folder_missing", position=7),
        )
    except AppError as exc:
        assert exc.code == "conversation_folder_invalid_parent"
        assert exc.status_code == 400
    else:
        raise AssertionError("expected AppError")

    listed = repo.list_folders()
    assert [(item.name, item.position) for item in listed] == [("Original", 0)]


def test_folder_api_creates_lists_updates_and_deletes(db_session) -> None:
    client = _client_with_session(db_session)

    create_response = client.post(
        "/v1/conversation-folders",
        json={"name": "Worldbuilding", "position": 0},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Worldbuilding"
    assert created["parent_id"] is None
    assert created["position"] == 0

    list_response = client.get("/v1/conversation-folders")
    assert list_response.status_code == 200
    assert [folder["id"] for folder in list_response.json()] == [created["id"]]

    patch_response = client.patch(
        f"/v1/conversation-folders/{created['id']}",
        json={"name": "Act I", "position": 1},
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["id"] == created["id"]
    assert patched["name"] == "Act I"
    assert patched["position"] == 1

    delete_response = client.delete(f"/v1/conversation-folders/{created['id']}")
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    final_list_response = client.get("/v1/conversation-folders")
    assert final_list_response.status_code == 200
    assert final_list_response.json() == []


def test_folder_api_returns_error_response_shape_for_invalid_parent(db_session) -> None:
    client = _client_with_session(db_session)

    response = client.post(
        "/v1/conversation-folders",
        json={"name": "Child", "parent_id": "folder_missing"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "conversation_folder_invalid_parent",
            "message": "Conversation folder parent does not exist.",
            "details": {"parent_id": "folder_missing"},
        }
    }
