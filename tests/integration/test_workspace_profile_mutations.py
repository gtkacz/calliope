from calliope.domain.enums import ProfileCapability, ProfileKind
from calliope.domain.errors import AppError
from calliope.domain.schemas import (
    ProfileCreate,
    ProfilePatch,
    WorkspaceCreate,
    WorkspacePatch,
)
from calliope.repositories.profiles import ProfileRepository
from calliope.repositories.workspaces import WorkspaceRepository


def test_profile_repository_updates_and_deletes(db_session) -> None:
    repo = ProfileRepository(db_session)
    created = repo.create(
        ProfileCreate(
            name="local-chat",
            kind=ProfileKind.OPENAI_COMPATIBLE,
            base_url="http://localhost:4000/v1",
            model="old-model",
            capabilities=[ProfileCapability.CHAT],
        )
    )

    updated = repo.update(
        created.id,
        ProfilePatch(
            name="renamed-chat",
            model="new-model",
            capabilities=[ProfileCapability.CHAT, ProfileCapability.STREAMING],
        ),
    )
    assert updated.name == "renamed-chat"
    assert updated.model == "new-model"
    assert updated.capabilities == [ProfileCapability.CHAT, ProfileCapability.STREAMING]

    repo.delete(created.id)
    assert repo.list() == []


def test_workspace_repository_updates_and_deletes(db_session) -> None:
    repo = WorkspaceRepository(db_session)
    created = repo.create(WorkspaceCreate(name="World", root_path="/tmp/world"))

    updated = repo.update(
        created.id,
        WorkspacePatch(
            name="Renamed World",
            root_path="/tmp/renamed-world",
            include_globs=["**/*.md"],
            exclude_globs=[".git/**"],
        ),
    )
    assert updated.name == "Renamed World"
    assert updated.root_path == "/tmp/renamed-world"

    repo.delete(created.id)
    try:
        repo.get(created.id)
    except AppError as exc:
        assert exc.code == "workspace_not_found"
    else:
        raise AssertionError("expected AppError")
