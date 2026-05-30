import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from calliope.api.app import create_app
from calliope.api.dependencies import get_db_session
from calliope.config import Settings
from calliope.domain.schemas import WorkspaceCreate
from calliope.repositories.workspaces import WorkspaceRepository
from calliope.services.versioning import VersioningService
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")

SETTINGS_WITHOUT_ENV_FILE: dict[str, Any] = {"_env_file": None}


def _seed_workspace(
    db_session: Session,
    root: Path,
    versioning_enabled: bool | None = None,
) -> None:
    WorkspaceRepository(db_session).create(
        WorkspaceCreate(
            name="versioned",
            root_path=str(root),
            versioning_enabled=versioning_enabled,
        )
    )


def _client(db_session: Session, root: Path, *, versioning: bool = True) -> TestClient:
    settings = Settings(
        api_title="Calliope",
        versioning_enabled=versioning,
        browse_root=str(root),
        **SETTINGS_WITHOUT_ENV_FILE,
    )
    app = create_app(settings)

    def override_get_db_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app)


def test_versioned_write_records_history_and_restores(db_session: Session, tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    note.write_text("v0\n", encoding="utf-8")
    _seed_workspace(db_session, tmp_path)
    client = _client(db_session, tmp_path)

    first = client.put(
        "/v1/filesystem/write",
        json={"path": str(note), "content": "v1\n", "cause": "LLM edit: make it v1"},
    )
    assert first.status_code == 200
    second = client.put("/v1/filesystem/write", json={"path": str(note), "content": "v2\n"})
    assert second.status_code == 200
    assert note.read_text(encoding="utf-8") == "v2\n"

    history = client.get("/v1/filesystem/history", params={"path": str(note)})
    assert history.status_code == 200
    versions = history.json()["versions"]
    # baseline (pre-app "v0") + v1 + v2, newest first.
    assert len(versions) == 3
    assert versions[0]["cause"] == "manual save"
    assert versions[1]["cause"] == "LLM edit: make it v1"
    assert versions[-1]["cause"].startswith("baseline")

    baseline_sha = versions[-1]["sha"]
    restore = client.post(
        "/v1/filesystem/restore",
        json={"path": str(note), "sha": baseline_sha},
    )
    assert restore.status_code == 200
    assert note.read_text(encoding="utf-8") == "v0\n"

    # Restore is itself recorded, so it can be undone in turn.
    after = client.get("/v1/filesystem/history", params={"path": str(note)}).json()["versions"]
    assert len(after) == 4
    assert after[0]["cause"].startswith("restore:")


def test_does_not_pollute_user_git_repo(db_session: Session, tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    note = tmp_path / "note.md"
    note.write_text("hello\n", encoding="utf-8")
    _git(tmp_path, "add", "note.md")
    _git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "add note")

    _seed_workspace(db_session, tmp_path)
    client = _client(db_session, tmp_path)
    client.put("/v1/filesystem/write", json={"path": str(note), "content": "world\n"})

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    lines = [line for line in status.splitlines() if line.strip()]
    # The user's note.md edit is expected; the shadow store must stay invisible.
    assert all(VersioningService(str(tmp_path))._git_dir.name not in line for line in lines)
    assert any("note.md" in line for line in lines)


def test_no_history_when_globally_disabled(db_session: Session, tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    note.write_text("a\n", encoding="utf-8")
    _seed_workspace(db_session, tmp_path)
    client = _client(db_session, tmp_path, versioning=False)

    write = client.put("/v1/filesystem/write", json={"path": str(note), "content": "b\n"})
    assert write.status_code == 200
    assert note.read_text(encoding="utf-8") == "b\n"
    assert not (tmp_path / ".calliope-git").exists()

    history = client.get("/v1/filesystem/history", params={"path": str(note)})
    assert history.status_code == 200
    assert history.json()["versions"] == []


def test_per_workspace_disable_overrides_global(db_session: Session, tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    note.write_text("a\n", encoding="utf-8")
    _seed_workspace(db_session, tmp_path, versioning_enabled=False)
    client = _client(db_session, tmp_path, versioning=True)

    client.put("/v1/filesystem/write", json={"path": str(note), "content": "b\n"})
    assert not (tmp_path / ".calliope-git").exists()
    assert client.get("/v1/filesystem/history", params={"path": str(note)}).json()["versions"] == []


def test_write_succeeds_when_git_unavailable(
    db_session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(VersioningService, "is_available", staticmethod(lambda: False))
    note = tmp_path / "note.md"
    note.write_text("a\n", encoding="utf-8")
    _seed_workspace(db_session, tmp_path)
    client = _client(db_session, tmp_path, versioning=True)

    write = client.put("/v1/filesystem/write", json={"path": str(note), "content": "b\n"})
    assert write.status_code == 200
    assert note.read_text(encoding="utf-8") == "b\n"
    assert not (tmp_path / ".calliope-git").exists()
    assert client.get("/v1/filesystem/history", params={"path": str(note)}).json()["versions"] == []


def test_history_survives_deletion_and_restore_conflicts(
    db_session: Session,
    tmp_path: Path,
) -> None:
    note = tmp_path / "note.md"
    note.write_text("v0\n", encoding="utf-8")
    _seed_workspace(db_session, tmp_path)
    client = _client(db_session, tmp_path)
    client.put("/v1/filesystem/write", json={"path": str(note), "content": "v1\n"})

    note.unlink()

    history = client.get("/v1/filesystem/history", params={"path": str(note)})
    assert history.status_code == 200
    versions = history.json()["versions"]
    assert len(versions) == 2  # baseline + v1 survive the file's deletion

    restore = client.post(
        "/v1/filesystem/restore",
        json={"path": str(note), "sha": versions[0]["sha"]},
    )
    # Cannot restore into a file that no longer exists via the edit-only write path.
    assert restore.status_code == 404


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True)
