from pathlib import Path

from calliope.domain.schemas import WorkspaceCreate
from calliope.repositories.workspaces import WorkspaceRepository
from calliope.services.guidelines import (
    resolve_guidelines_for_path,
    resolve_workspace_guidelines,
)
from sqlalchemy.orm import Session


def _create(session: Session, name: str, root_path: str, guidelines: str | None) -> str:
    return WorkspaceRepository(session).create(
        WorkspaceCreate(name=name, root_path=root_path, guidelines=guidelines)
    ).id


def test_resolve_workspace_guidelines_returns_none_when_suppressed(db_session: Session) -> None:
    ws_id = _create(db_session, "w1", "/tmp/w1", "Dark fantasy.")
    assert resolve_workspace_guidelines(db_session, workspace_id=ws_id, apply_guidelines=False) is None


def test_resolve_workspace_guidelines_returns_none_without_workspace_id(db_session: Session) -> None:
    assert resolve_workspace_guidelines(db_session, workspace_id=None, apply_guidelines=True) is None


def test_resolve_workspace_guidelines_returns_none_when_empty(db_session: Session) -> None:
    ws_id = _create(db_session, "w2", "/tmp/w2", None)
    assert resolve_workspace_guidelines(db_session, workspace_id=ws_id, apply_guidelines=True) is None


def test_resolve_workspace_guidelines_returns_text(db_session: Session) -> None:
    ws_id = _create(db_session, "w3", "/tmp/w3", "Dark fantasy.")
    assert resolve_workspace_guidelines(db_session, workspace_id=ws_id, apply_guidelines=True) == "Dark fantasy."


def test_resolve_workspace_guidelines_returns_none_for_unknown_workspace(db_session: Session) -> None:
    assert resolve_workspace_guidelines(db_session, workspace_id="workspace_missing", apply_guidelines=True) is None


def test_resolve_guidelines_for_path_returns_text_for_contained_path(db_session: Session, tmp_path: Path) -> None:
    root = tmp_path / "world"
    root.mkdir()
    _create(db_session, "w4", str(root), "Dark fantasy.")
    target = root / "notes" / "a.md"
    assert resolve_guidelines_for_path(db_session, path=str(target), apply_guidelines=True) == "Dark fantasy."


def test_resolve_guidelines_for_path_returns_none_when_no_workspace(db_session: Session, tmp_path: Path) -> None:
    assert resolve_guidelines_for_path(db_session, path=str(tmp_path / "orphan.md"), apply_guidelines=True) is None


def test_resolve_guidelines_for_path_returns_none_when_suppressed(db_session: Session, tmp_path: Path) -> None:
    root = tmp_path / "world"
    root.mkdir()
    _create(db_session, "w5", str(root), "Dark fantasy.")
    assert resolve_guidelines_for_path(db_session, path=str(root / "a.md"), apply_guidelines=False) is None
